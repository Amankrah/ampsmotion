"""
Ring Buffer for Instant Replay

Circular buffer holding the last N seconds of video frames.
The VAR operator can scrub backward through this buffer.
"""

from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

import numpy as np


@dataclass
class TimestampedFrame:
    """A video frame with timestamp and frame number."""
    frame: np.ndarray
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    frame_number: int = 0


class ReplayBuffer:
    """
    Circular buffer holding the last N seconds of video frames.

    The VAR operator can scrub backward through this buffer for
    instant replay functionality.

    Usage:
        buffer = ReplayBuffer(max_seconds=120, fps=30)

        # Push frames from camera
        buffer.push(frame)

        # Get last 10 seconds for replay
        frames = buffer.get_last_n_seconds(10)

        # Seek to specific frame
        frame = buffer.get_frame_at(100)
    """

    def __init__(self, max_seconds: int = 120, fps: int = 30):
        """
        Initialize the replay buffer.

        Args:
            max_seconds: Maximum seconds of video to store
            fps: Expected frames per second
        """
        self.max_frames = max_seconds * fps
        self.fps = fps
        self._buffer: deque[TimestampedFrame] = deque(maxlen=self.max_frames)
        self._frame_counter = 0

    def push(self, frame: np.ndarray) -> None:
        """
        Add a frame to the buffer.

        Args:
            frame: BGR numpy array from OpenCV
        """
        self._frame_counter += 1
        self._buffer.append(TimestampedFrame(
            frame=frame,
            timestamp=datetime.now(timezone.utc),
            frame_number=self._frame_counter,
        ))

    def get_last_n_seconds(self, seconds: int) -> list[TimestampedFrame]:
        """
        Get the last N seconds of frames.

        Args:
            seconds: Number of seconds to retrieve

        Returns:
            List of TimestampedFrame objects
        """
        count = min(seconds * self.fps, len(self._buffer))
        return list(self._buffer)[-count:]

    def get_frame_at(self, index: int) -> Optional[TimestampedFrame]:
        """
        Get a specific frame by buffer index.

        Args:
            index: Index into the buffer (0 = oldest)

        Returns:
            TimestampedFrame or None if index out of range
        """
        if 0 <= index < len(self._buffer):
            return self._buffer[index]
        return None

    def get_frame_by_number(self, frame_number: int) -> Optional[TimestampedFrame]:
        """
        Get a frame by its frame number.

        Args:
            frame_number: The frame number to find

        Returns:
            TimestampedFrame or None if not found
        """
        for frame in self._buffer:
            if frame.frame_number == frame_number:
                return frame
        return None

    def get_frames_in_range(self, start_index: int, end_index: int) -> list[TimestampedFrame]:
        """
        Get frames between two indices (inclusive).

        Args:
            start_index: Start index (0 = oldest)
            end_index: End index

        Returns:
            List of TimestampedFrame objects
        """
        start = max(0, start_index)
        end = min(len(self._buffer), end_index + 1)
        return list(self._buffer)[start:end]

    def clear(self) -> None:
        """Clear all frames from the buffer."""
        self._buffer.clear()
        self._frame_counter = 0

    @property
    def size(self) -> int:
        """Number of frames currently in the buffer."""
        return len(self._buffer)

    @property
    def duration_seconds(self) -> float:
        """Current duration of buffered video in seconds."""
        return self.size / self.fps

    @property
    def is_full(self) -> bool:
        """Check if buffer is at maximum capacity."""
        return self.size >= self.max_frames

    @property
    def oldest_frame(self) -> Optional[TimestampedFrame]:
        """Get the oldest frame in the buffer."""
        if self._buffer:
            return self._buffer[0]
        return None

    @property
    def newest_frame(self) -> Optional[TimestampedFrame]:
        """Get the newest frame in the buffer."""
        if self._buffer:
            return self._buffer[-1]
        return None
