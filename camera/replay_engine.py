"""
Replay Engine for VAR Functionality

Provides scrubbing, slow-motion, frame-stepping, and clip export
capabilities using the ring buffer.
"""

import cv2
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import QObject, Signal, QTimer

from camera.ring_buffer import ReplayBuffer, TimestampedFrame


class PlaybackState:
    """Playback state constants."""
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"
    FRAME_STEP = "frame_step"


class ReplayEngine(QObject):
    """
    Replay engine for VAR instant replay functionality.

    Provides:
    - Scrubbing through buffered frames
    - Variable speed playback (slow-motion)
    - Frame-by-frame navigation
    - Clip marking and export

    Usage:
        engine = ReplayEngine(replay_buffer)
        engine.frame_ready.connect(display_widget.update_frame)
        engine.seek_to_seconds(10)  # Go back 10 seconds
        engine.play(speed=0.5)      # Play at half speed
    """

    # Signals
    frame_ready = Signal(np.ndarray)  # Current frame to display
    position_changed = Signal(int, int)  # (current_frame, total_frames)
    playback_state_changed = Signal(str)  # PlaybackState value
    clip_exported = Signal(str)  # Export file path
    export_progress = Signal(int, int)  # (current, total)

    # Playback speeds
    SPEEDS = [0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]

    def __init__(
        self,
        replay_buffer: ReplayBuffer,
        fps: int = 30,
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.buffer = replay_buffer
        self.fps = fps

        # Playback state
        self._state = PlaybackState.STOPPED
        self._current_index = 0
        self._speed = 1.0
        self._is_looping = False

        # Clip marking
        self._mark_in: Optional[int] = None
        self._mark_out: Optional[int] = None

        # Playback timer
        self._playback_timer = QTimer(self)
        self._playback_timer.timeout.connect(self._on_playback_tick)

    @property
    def state(self) -> str:
        """Get current playback state."""
        return self._state

    @property
    def current_index(self) -> int:
        """Get current frame index in buffer."""
        return self._current_index

    @property
    def total_frames(self) -> int:
        """Get total frames in buffer."""
        return self.buffer.size

    @property
    def current_time(self) -> float:
        """Get current position in seconds."""
        return self._current_index / self.fps

    @property
    def total_time(self) -> float:
        """Get total buffer duration in seconds."""
        return self.buffer.duration_seconds

    @property
    def speed(self) -> float:
        """Get current playback speed."""
        return self._speed

    @property
    def mark_in(self) -> Optional[int]:
        """Get mark-in point."""
        return self._mark_in

    @property
    def mark_out(self) -> Optional[int]:
        """Get mark-out point."""
        return self._mark_out

    def play(self, speed: float = 1.0) -> None:
        """
        Start playback at specified speed.

        Args:
            speed: Playback speed (0.125 to 2.0)
        """
        self._speed = max(0.125, min(2.0, speed))
        self._state = PlaybackState.PLAYING

        # Calculate timer interval based on speed
        # Normal: 1000ms / fps = ~33ms for 30fps
        # At 0.5x: 66ms, at 2x: 16ms
        interval_ms = int(1000 / (self.fps * self._speed))
        self._playback_timer.setInterval(interval_ms)
        self._playback_timer.start()

        self.playback_state_changed.emit(self._state)

    def pause(self) -> None:
        """Pause playback."""
        self._playback_timer.stop()
        self._state = PlaybackState.PAUSED
        self.playback_state_changed.emit(self._state)

    def stop(self) -> None:
        """Stop playback and reset to beginning."""
        self._playback_timer.stop()
        self._state = PlaybackState.STOPPED
        self._current_index = 0
        self.playback_state_changed.emit(self._state)
        self._emit_current_frame()

    def toggle_play_pause(self) -> None:
        """Toggle between play and pause."""
        if self._state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play(self._speed)

    def set_speed(self, speed: float) -> None:
        """
        Set playback speed.

        Args:
            speed: New playback speed
        """
        self._speed = max(0.125, min(2.0, speed))
        if self._state == PlaybackState.PLAYING:
            # Restart timer with new interval
            self.play(self._speed)

    def cycle_speed(self, direction: int = 1) -> float:
        """
        Cycle through available speeds.

        Args:
            direction: 1 for faster, -1 for slower

        Returns:
            New speed value
        """
        try:
            current_idx = self.SPEEDS.index(self._speed)
        except ValueError:
            current_idx = self.SPEEDS.index(1.0)

        new_idx = max(0, min(len(self.SPEEDS) - 1, current_idx + direction))
        self.set_speed(self.SPEEDS[new_idx])
        return self._speed

    def seek_to_index(self, index: int) -> None:
        """
        Seek to a specific frame index.

        Args:
            index: Frame index in buffer
        """
        self._current_index = max(0, min(self.buffer.size - 1, index))
        self._emit_current_frame()

    def seek_to_seconds(self, seconds: float) -> None:
        """
        Seek to a specific time position.

        Args:
            seconds: Time in seconds from start of buffer
        """
        index = int(seconds * self.fps)
        self.seek_to_index(index)

    def seek_relative(self, seconds: float) -> None:
        """
        Seek relative to current position.

        Args:
            seconds: Seconds to move (negative for backward)
        """
        new_index = self._current_index + int(seconds * self.fps)
        self.seek_to_index(new_index)

    def seek_to_end(self) -> None:
        """Seek to the most recent frame (live position)."""
        self.seek_to_index(self.buffer.size - 1)

    def step_forward(self, frames: int = 1) -> None:
        """
        Step forward by N frames.

        Args:
            frames: Number of frames to step
        """
        self._state = PlaybackState.FRAME_STEP
        self._playback_timer.stop()
        self.seek_to_index(self._current_index + frames)
        self.playback_state_changed.emit(self._state)

    def step_backward(self, frames: int = 1) -> None:
        """
        Step backward by N frames.

        Args:
            frames: Number of frames to step
        """
        self._state = PlaybackState.FRAME_STEP
        self._playback_timer.stop()
        self.seek_to_index(self._current_index - frames)
        self.playback_state_changed.emit(self._state)

    def set_mark_in(self) -> int:
        """
        Set mark-in point at current position.

        Returns:
            Mark-in frame index
        """
        self._mark_in = self._current_index
        return self._mark_in

    def set_mark_out(self) -> int:
        """
        Set mark-out point at current position.

        Returns:
            Mark-out frame index
        """
        self._mark_out = self._current_index
        return self._mark_out

    def clear_marks(self) -> None:
        """Clear mark-in and mark-out points."""
        self._mark_in = None
        self._mark_out = None

    def get_marked_duration(self) -> float:
        """
        Get duration of marked segment in seconds.

        Returns:
            Duration in seconds, or 0 if marks not set
        """
        if self._mark_in is None or self._mark_out is None:
            return 0
        return abs(self._mark_out - self._mark_in) / self.fps

    def export_clip(
        self,
        output_path: str,
        format: str = "mp4",
        codec: str = "mp4v",
        on_progress: Optional[Callable[[int, int], None]] = None
    ) -> bool:
        """
        Export marked segment to video file.

        Args:
            output_path: Output file path (without extension)
            format: Output format (mp4, avi)
            codec: Video codec (mp4v, XVID, H264)
            on_progress: Optional progress callback(current, total)

        Returns:
            True if export successful
        """
        if self._mark_in is None or self._mark_out is None:
            return False

        start_idx = min(self._mark_in, self._mark_out)
        end_idx = max(self._mark_in, self._mark_out)

        # Get frames
        frames = self.buffer.get_frames_in_range(start_idx, end_idx)
        if not frames:
            return False

        # Determine output path
        path = Path(output_path)
        if not path.suffix:
            path = path.with_suffix(f".{format}")

        # Get frame dimensions from first frame
        first_frame = frames[0].frame
        height, width = first_frame.shape[:2]

        # Create video writer
        fourcc = cv2.VideoWriter.fourcc(*codec)
        writer = cv2.VideoWriter(
            str(path),
            fourcc,
            self.fps,
            (width, height)
        )

        if not writer.isOpened():
            return False

        try:
            total = len(frames)
            for i, tsframe in enumerate(frames):
                writer.write(tsframe.frame)
                self.export_progress.emit(i + 1, total)
                if on_progress:
                    on_progress(i + 1, total)
        finally:
            writer.release()

        self.clip_exported.emit(str(path))
        return True

    def get_frame_at_index(self, index: int) -> Optional[np.ndarray]:
        """
        Get a specific frame by index.

        Args:
            index: Frame index in buffer

        Returns:
            Frame as numpy array, or None if not found
        """
        frame = self.buffer.get_frame_at(index)
        if frame:
            return frame.frame
        return None

    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the current frame.

        Returns:
            Current frame as numpy array
        """
        return self.get_frame_at_index(self._current_index)

    def get_current_timestamp(self) -> Optional[datetime]:
        """
        Get timestamp of current frame.

        Returns:
            Timestamp of current frame
        """
        frame = self.buffer.get_frame_at(self._current_index)
        if frame:
            return frame.timestamp
        return None

    def set_loop(self, enabled: bool) -> None:
        """Enable/disable looping playback."""
        self._is_looping = enabled

    def _on_playback_tick(self) -> None:
        """Handle playback timer tick."""
        if self._state != PlaybackState.PLAYING:
            return

        # Advance frame
        self._current_index += 1

        # Check bounds
        if self._current_index >= self.buffer.size:
            if self._is_looping:
                self._current_index = 0
            else:
                self.pause()
                self._current_index = self.buffer.size - 1
                return

        self._emit_current_frame()

    def _emit_current_frame(self) -> None:
        """Emit current frame and position signals."""
        frame = self.get_current_frame()
        if frame is not None:
            self.frame_ready.emit(frame)

        self.position_changed.emit(self._current_index, self.buffer.size)


class ClipExporter:
    """
    Utility class for exporting video clips with various options.
    """

    @staticmethod
    def export_with_overlay(
        frames: list[TimestampedFrame],
        output_path: str,
        fps: int = 30,
        overlay_text: Optional[str] = None,
        show_timestamp: bool = True,
        codec: str = "mp4v"
    ) -> bool:
        """
        Export clip with optional text overlay.

        Args:
            frames: List of TimestampedFrame objects
            output_path: Output file path
            fps: Frames per second
            overlay_text: Optional text to overlay
            show_timestamp: Whether to show timestamp on frames
            codec: Video codec

        Returns:
            True if export successful
        """
        if not frames:
            return False

        path = Path(output_path)
        first_frame = frames[0].frame
        height, width = first_frame.shape[:2]

        fourcc = cv2.VideoWriter.fourcc(*codec)
        writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))

        if not writer.isOpened():
            return False

        try:
            for tsframe in frames:
                frame = tsframe.frame.copy()

                # Add timestamp overlay
                if show_timestamp:
                    timestamp_str = tsframe.timestamp.strftime("%H:%M:%S.%f")[:-3]
                    cv2.putText(
                        frame,
                        timestamp_str,
                        (10, height - 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (255, 255, 255),
                        2
                    )
                    cv2.putText(
                        frame,
                        timestamp_str,
                        (10, height - 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 0, 0),
                        1
                    )

                # Add custom overlay text
                if overlay_text:
                    cv2.putText(
                        frame,
                        overlay_text,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (255, 255, 255),
                        2
                    )
                    cv2.putText(
                        frame,
                        overlay_text,
                        (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0, 0, 0),
                        1
                    )

                writer.write(frame)
        finally:
            writer.release()

        return True

    @staticmethod
    def export_still_image(
        frame: np.ndarray,
        output_path: str,
        format: str = "jpg",
        quality: int = 95
    ) -> bool:
        """
        Export a single frame as an image.

        Args:
            frame: Frame to export
            output_path: Output file path
            format: Image format (jpg, png)
            quality: JPEG quality (0-100)

        Returns:
            True if export successful
        """
        path = Path(output_path)
        if not path.suffix:
            path = path.with_suffix(f".{format}")

        if format.lower() == "jpg" or format.lower() == "jpeg":
            params = [cv2.IMWRITE_JPEG_QUALITY, quality]
        elif format.lower() == "png":
            params = [cv2.IMWRITE_PNG_COMPRESSION, 9 - (quality // 11)]
        else:
            params = []

        return cv2.imwrite(str(path), frame, params)
