"""
Round Timer - Precision countdown timer for AmpeSports rounds.

Provides sub-100ms precision for 1v1 mode's 60-second rounds
and enforces the 10-second pause rule.
"""

from PySide6.QtCore import QObject, Qt, Signal, QTimer, QElapsedTimer


class RoundTimer(QObject):
    """
    Precision countdown timer for 1v1 rounds (60 seconds).

    Emits tick every 100ms and fires round_expired when time runs out.
    Also enforces the 10-second pause rule (automatic round loss if
    no bout activity for 10+ seconds).

    Usage:
        timer = RoundTimer()
        timer.tick.connect(on_tick)
        timer.round_expired.connect(on_expired)
        timer.start()

        # Call when a bout is recorded to reset pause timer
        timer.notify_bout_activity()
    """

    # Signals
    tick = Signal(int)              # milliseconds remaining
    round_expired = Signal()         # time's up
    pause_violation = Signal(int)    # player_id who paused > 10s (-1 if unknown)
    warning_threshold = Signal(int)  # emitted when time falls below thresholds

    # Constants
    ROUND_DURATION_MS = 60_000       # 60 seconds
    TICK_INTERVAL_MS = 100           # update every 100ms
    PAUSE_LIMIT_MS = 10_000          # 10-second inactivity threshold

    # Warning thresholds (in seconds)
    WARNING_THRESHOLDS = [30, 10, 5]

    def __init__(self, duration_ms: int = None):
        """
        Initialize the round timer.

        Args:
            duration_ms: Custom duration in milliseconds (default: 60000)
        """
        super().__init__()

        self._duration_ms = duration_ms or self.ROUND_DURATION_MS
        self._remaining_ms = self._duration_ms
        self._is_running = False
        self._is_paused = False

        # Internal Qt timers
        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_INTERVAL_MS)
        self._timer.setTimerType(Qt.TimerType.PreciseTimer)
        self._timer.timeout.connect(self._on_tick)

        # Elapsed time tracking for precision
        self._elapsed = QElapsedTimer()
        self._start_elapsed_ms = 0

        # Pause rule tracking
        self._last_bout_time_ms = 0
        self._pause_warning_sent = False

        # Warning threshold tracking
        self._warnings_sent: set[int] = set()

    @property
    def is_running(self) -> bool:
        """Check if the timer is currently running."""
        return self._is_running and not self._is_paused

    @property
    def is_paused(self) -> bool:
        """Check if the timer is paused."""
        return self._is_paused

    @property
    def remaining_ms(self) -> int:
        """Get remaining time in milliseconds."""
        if self._is_running and not self._is_paused:
            elapsed = self._elapsed.elapsed()
            return max(0, self._duration_ms - (self._start_elapsed_ms + elapsed))
        return self._remaining_ms

    @property
    def remaining_seconds(self) -> float:
        """Get remaining time in seconds."""
        return self.remaining_ms / 1000.0

    @property
    def elapsed_ms(self) -> int:
        """Get elapsed time in milliseconds."""
        return self._duration_ms - self.remaining_ms

    def start(self) -> None:
        """Start the timer from the beginning."""
        self._remaining_ms = self._duration_ms
        self._start_elapsed_ms = 0
        self._last_bout_time_ms = 0
        self._pause_warning_sent = False
        self._warnings_sent.clear()
        self._is_running = True
        self._is_paused = False

        self._elapsed.start()
        self._timer.start()

        # Emit initial tick
        self.tick.emit(self._remaining_ms)

    def stop(self) -> None:
        """Stop the timer completely."""
        self._timer.stop()
        self._is_running = False
        self._is_paused = False
        self._remaining_ms = self._calc_remaining()

    def pause(self) -> None:
        """Pause the timer, preserving remaining time."""
        if self._is_running and not self._is_paused:
            self._timer.stop()
            self._remaining_ms = self._calc_remaining()
            self._is_paused = True

    def resume(self) -> None:
        """Resume a paused timer."""
        if self._is_running and self._is_paused:
            # Start fresh elapsed timer from current remaining time
            self._start_elapsed_ms = self._duration_ms - self._remaining_ms
            self._elapsed.restart()
            self._is_paused = False
            self._timer.start()

    def reset(self, duration_ms: int = None) -> None:
        """Reset the timer to initial state."""
        self.stop()
        if duration_ms is not None:
            self._duration_ms = duration_ms
        self._remaining_ms = self._duration_ms
        self._start_elapsed_ms = 0
        self._last_bout_time_ms = 0
        self._pause_warning_sent = False
        self._warnings_sent.clear()

    def notify_bout_activity(self) -> None:
        """
        Call this every time a bout is recorded to reset the pause timer.

        The 10-second pause rule states that if there's no bout activity
        for 10+ seconds, the inactive player loses the round.
        """
        self._last_bout_time_ms = self.elapsed_ms
        self._pause_warning_sent = False

    def _calc_remaining(self) -> int:
        """Calculate remaining time based on elapsed timer."""
        if not self._elapsed.isValid():
            return self._remaining_ms
        elapsed = self._elapsed.elapsed()
        return max(0, self._duration_ms - (self._start_elapsed_ms + elapsed))

    def _on_tick(self) -> None:
        """Handle timer tick - emitted every 100ms."""
        remaining = self._calc_remaining()
        self._remaining_ms = remaining

        # Emit tick signal
        self.tick.emit(remaining)

        # Check warning thresholds
        remaining_sec = remaining // 1000
        for threshold in self.WARNING_THRESHOLDS:
            if remaining_sec <= threshold and threshold not in self._warnings_sent:
                self._warnings_sent.add(threshold)
                self.warning_threshold.emit(threshold)

        # Check 10-second pause rule
        since_last_bout = self.elapsed_ms - self._last_bout_time_ms
        if since_last_bout >= self.PAUSE_LIMIT_MS and not self._pause_warning_sent:
            self._pause_warning_sent = True
            self.pause_violation.emit(-1)  # -1 = caller must determine player

        # Check if time expired
        if remaining <= 0:
            self._timer.stop()
            self._is_running = False
            self.round_expired.emit()

    def add_time(self, ms: int) -> None:
        """Add time to the remaining duration (for time-outs, etc.)."""
        self._remaining_ms = min(
            self._remaining_ms + ms,
            self._duration_ms * 2  # Cap at 2x original duration
        )
        if self._is_running and not self._is_paused:
            # Adjust the start elapsed to account for added time
            self._start_elapsed_ms = max(0, self._start_elapsed_ms - ms)

    def subtract_time(self, ms: int) -> None:
        """Subtract time from the remaining duration (for penalties, etc.)."""
        self._remaining_ms = max(0, self._remaining_ms - ms)
        if self._remaining_ms == 0 and self._is_running:
            self._timer.stop()
            self._is_running = False
            self.round_expired.emit()


class MatchClock(QObject):
    """
    A continuous clock that tracks total match elapsed time.
    Used for bout timestamps and replay synchronization.
    """

    tick = Signal(int)  # elapsed milliseconds

    def __init__(self):
        super().__init__()
        self._elapsed = QElapsedTimer()
        self._timer = QTimer(self)
        self._timer.setInterval(1000)  # Update every second
        self._timer.timeout.connect(self._on_tick)
        self._total_paused_ms = 0
        self._pause_start_ms = 0
        self._is_paused = False

    @property
    def elapsed_ms(self) -> int:
        """Get total elapsed time in milliseconds."""
        if not self._elapsed.isValid():
            return 0
        paused_time = self._total_paused_ms
        if self._is_paused:
            paused_time += self._elapsed.elapsed() - self._pause_start_ms
        return self._elapsed.elapsed() - paused_time

    def start(self) -> None:
        """Start the match clock."""
        self._elapsed.start()
        self._total_paused_ms = 0
        self._is_paused = False
        self._timer.start()

    def stop(self) -> None:
        """Stop the match clock."""
        self._timer.stop()

    def pause(self) -> None:
        """Pause the match clock."""
        if not self._is_paused:
            self._pause_start_ms = self._elapsed.elapsed()
            self._is_paused = True

    def resume(self) -> None:
        """Resume the match clock."""
        if self._is_paused:
            self._total_paused_ms += self._elapsed.elapsed() - self._pause_start_ms
            self._is_paused = False

    def _on_tick(self) -> None:
        """Emit elapsed time every second."""
        self.tick.emit(self.elapsed_ms)
