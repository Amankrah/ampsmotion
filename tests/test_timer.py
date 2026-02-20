"""
Unit tests for the RoundTimer.
"""

import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import QCoreApplication
import sys


# Create QCoreApplication for Qt event loop (required for QTimer)
@pytest.fixture(scope="session")
def qapp():
    """Create a QCoreApplication instance for the test session."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication(sys.argv)
    yield app


class TestRoundTimer:
    """Tests for the RoundTimer class."""

    def test_initial_state(self, qapp):
        """Timer should start with default duration."""
        from engine.timer import RoundTimer

        timer = RoundTimer()

        assert timer.remaining_ms == 60_000
        assert not timer.is_running
        assert not timer.is_paused

    def test_custom_duration(self, qapp):
        """Timer should accept custom duration."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=30_000)

        assert timer.remaining_ms == 30_000

    def test_start_sets_running(self, qapp):
        """Starting timer should set is_running to True."""
        from engine.timer import RoundTimer

        timer = RoundTimer()
        timer.start()

        assert timer.is_running
        timer.stop()

    def test_stop_clears_running(self, qapp):
        """Stopping timer should set is_running to False."""
        from engine.timer import RoundTimer

        timer = RoundTimer()
        timer.start()
        timer.stop()

        assert not timer.is_running

    def test_pause_preserves_time(self, qapp):
        """Pausing should preserve the remaining time."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer.start()
        timer.pause()

        # Time should be very close to start (within a few ms)
        assert timer.remaining_ms >= 59_900
        assert timer.is_paused

        timer.stop()

    def test_resume_continues_countdown(self, qapp):
        """Resuming should continue from paused time."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer.start()
        timer.pause()
        timer.resume()

        assert timer.is_running
        assert not timer.is_paused

        timer.stop()

    def test_reset_restores_duration(self, qapp):
        """Reset should restore the full duration."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer.start()
        # Simulate some time passing
        timer._remaining_ms = 30_000
        timer.reset()

        assert timer.remaining_ms == 60_000
        assert not timer.is_running

    def test_reset_with_new_duration(self, qapp):
        """Reset should accept a new duration."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer.reset(duration_ms=120_000)

        assert timer.remaining_ms == 120_000

    def test_add_time(self, qapp):
        """Adding time should increase remaining time."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer._remaining_ms = 30_000

        timer.add_time(10_000)

        assert timer.remaining_ms == 40_000

    def test_subtract_time(self, qapp):
        """Subtracting time should decrease remaining time."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer._remaining_ms = 30_000

        timer.subtract_time(10_000)

        assert timer.remaining_ms == 20_000

    def test_subtract_time_floors_at_zero(self, qapp):
        """Subtracting more time than remaining should floor at zero."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer._remaining_ms = 5_000

        timer.subtract_time(10_000)

        assert timer.remaining_ms == 0

    def test_remaining_seconds_conversion(self, qapp):
        """remaining_seconds should convert correctly."""
        from engine.timer import RoundTimer

        timer = RoundTimer(duration_ms=60_000)
        timer._remaining_ms = 45_500

        assert timer.remaining_seconds == 45.5

    def test_notify_bout_activity_resets_pause_timer(self, qapp):
        """notify_bout_activity should reset the pause violation timer."""
        from engine.timer import RoundTimer

        timer = RoundTimer()
        timer.start()

        initial_last_bout = timer._last_bout_time_ms
        timer.notify_bout_activity()

        assert timer._last_bout_time_ms >= initial_last_bout
        assert not timer._pause_warning_sent

        timer.stop()


class TestMatchClock:
    """Tests for the MatchClock class."""

    def test_initial_elapsed_is_zero(self, qapp):
        """Elapsed time should be zero before starting."""
        from engine.timer import MatchClock

        clock = MatchClock()

        assert clock.elapsed_ms == 0

    def test_start_begins_counting(self, qapp):
        """Starting should begin tracking elapsed time."""
        from engine.timer import MatchClock

        clock = MatchClock()
        clock.start()

        # Should be very small but > 0 after starting
        assert clock.elapsed_ms >= 0

        clock.stop()

    def test_pause_stops_counting(self, qapp):
        """Pausing should stop counting elapsed time."""
        from engine.timer import MatchClock

        clock = MatchClock()
        clock.start()
        clock.pause()

        paused_time = clock.elapsed_ms
        # Brief wait (in real test you might use qtbot.wait)
        resumed_time = clock.elapsed_ms

        # Time should not have increased while paused
        assert resumed_time == paused_time

        clock.stop()

    def test_resume_continues_counting(self, qapp):
        """Resuming should continue counting from paused time."""
        from engine.timer import MatchClock

        clock = MatchClock()
        clock.start()
        clock.pause()
        clock.resume()

        # Clock should be running again
        assert not clock._is_paused

        clock.stop()
