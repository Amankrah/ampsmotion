"""
Tests for Replay Engine

Tests scrubbing, speed control, frame stepping, and clip export functionality.
"""

import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from camera.ring_buffer import ReplayBuffer, TimestampedFrame
from camera.replay_engine import ReplayEngine, PlaybackState, ClipExporter


class TestReplayBuffer:
    """Tests for ReplayBuffer functionality."""

    def test_buffer_initialization(self):
        """Test buffer initializes with correct capacity."""
        buffer = ReplayBuffer(max_seconds=10, fps=30)

        assert buffer.max_frames == 300  # 10 * 30
        assert buffer.fps == 30
        assert buffer.size == 0
        assert buffer.duration_seconds == 0

    def test_push_frame(self):
        """Test pushing frames to buffer."""
        buffer = ReplayBuffer(max_seconds=1, fps=30)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        buffer.push(frame)

        assert buffer.size == 1
        assert buffer.newest_frame is not None
        assert buffer.newest_frame.frame_number == 1

    def test_buffer_circular_overflow(self):
        """Test buffer wraps around at max capacity."""
        buffer = ReplayBuffer(max_seconds=1, fps=10)  # 10 frames max
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Push 15 frames
        for i in range(15):
            buffer.push(frame)

        # Should only have 10 frames
        assert buffer.size == 10
        assert buffer.is_full

        # Oldest frame should be #6 (1-5 were pushed out)
        assert buffer.oldest_frame.frame_number == 6

    def test_get_frame_at_index(self):
        """Test retrieving frame by index."""
        buffer = ReplayBuffer(max_seconds=1, fps=30)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        for i in range(5):
            buffer.push(frame)

        retrieved = buffer.get_frame_at(2)
        assert retrieved is not None
        assert retrieved.frame_number == 3

        # Out of range
        assert buffer.get_frame_at(10) is None
        assert buffer.get_frame_at(-1) is None

    def test_get_last_n_seconds(self):
        """Test retrieving last N seconds of frames."""
        buffer = ReplayBuffer(max_seconds=10, fps=10)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Push 50 frames (5 seconds)
        for i in range(50):
            buffer.push(frame)

        # Get last 2 seconds (20 frames)
        frames = buffer.get_last_n_seconds(2)
        assert len(frames) == 20

        # Get more than available
        frames = buffer.get_last_n_seconds(10)
        assert len(frames) == 50

    def test_get_frames_in_range(self):
        """Test retrieving frame range."""
        buffer = ReplayBuffer(max_seconds=10, fps=30)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        for i in range(10):
            buffer.push(frame)

        frames = buffer.get_frames_in_range(2, 5)
        assert len(frames) == 4  # Indices 2, 3, 4, 5

    def test_clear_buffer(self):
        """Test clearing buffer."""
        buffer = ReplayBuffer(max_seconds=1, fps=30)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        for i in range(10):
            buffer.push(frame)

        buffer.clear()

        assert buffer.size == 0
        assert buffer.oldest_frame is None
        assert buffer.newest_frame is None


class TestReplayEngine:
    """Tests for ReplayEngine functionality."""

    @pytest.fixture
    def replay_engine(self):
        """Create replay engine with populated buffer."""
        buffer = ReplayBuffer(max_seconds=10, fps=30)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Push 150 frames (5 seconds)
        for i in range(150):
            buffer.push(frame)

        engine = ReplayEngine(buffer, fps=30)
        return engine

    def test_initial_state(self, replay_engine):
        """Test engine initial state."""
        engine = replay_engine

        assert engine.state == PlaybackState.STOPPED
        assert engine.current_index == 0
        assert engine.speed == 1.0
        assert engine.total_frames == 150

    def test_seek_to_index(self, replay_engine):
        """Test seeking to specific frame."""
        engine = replay_engine

        engine.seek_to_index(50)
        assert engine.current_index == 50

        # Clamp to bounds
        engine.seek_to_index(1000)
        assert engine.current_index == 149

        engine.seek_to_index(-10)
        assert engine.current_index == 0

    def test_seek_to_seconds(self, replay_engine):
        """Test seeking to time position."""
        engine = replay_engine

        engine.seek_to_seconds(2.0)  # 2 seconds = 60 frames at 30fps
        assert engine.current_index == 60

    def test_seek_relative(self, replay_engine):
        """Test relative seeking."""
        engine = replay_engine

        engine.seek_to_index(50)
        engine.seek_relative(1.0)  # +30 frames
        assert engine.current_index == 80

        engine.seek_relative(-2.0)  # -60 frames
        assert engine.current_index == 20

    def test_seek_to_end(self, replay_engine):
        """Test seeking to end."""
        engine = replay_engine

        engine.seek_to_end()
        assert engine.current_index == 149

    def test_step_forward(self, replay_engine):
        """Test stepping forward."""
        engine = replay_engine
        engine.seek_to_index(50)

        engine.step_forward(1)
        assert engine.current_index == 51
        assert engine.state == PlaybackState.FRAME_STEP

        engine.step_forward(10)
        assert engine.current_index == 61

    def test_step_backward(self, replay_engine):
        """Test stepping backward."""
        engine = replay_engine
        engine.seek_to_index(50)

        engine.step_backward(1)
        assert engine.current_index == 49
        assert engine.state == PlaybackState.FRAME_STEP

        engine.step_backward(10)
        assert engine.current_index == 39

    def test_set_speed(self, replay_engine):
        """Test setting playback speed."""
        engine = replay_engine

        engine.set_speed(0.5)
        assert engine.speed == 0.5

        engine.set_speed(2.0)
        assert engine.speed == 2.0

        # Clamp to bounds
        engine.set_speed(0.01)
        assert engine.speed == 0.125

        engine.set_speed(10.0)
        assert engine.speed == 2.0

    def test_cycle_speed(self, replay_engine):
        """Test cycling through speeds."""
        engine = replay_engine

        # Start at 1.0
        assert engine.speed == 1.0

        # Cycle up
        new_speed = engine.cycle_speed(1)
        assert new_speed == 1.5

        new_speed = engine.cycle_speed(1)
        assert new_speed == 2.0

        # Cycle down
        new_speed = engine.cycle_speed(-1)
        assert new_speed == 1.5

    def test_mark_in_out(self, replay_engine):
        """Test marking clip points."""
        engine = replay_engine

        engine.seek_to_index(30)
        engine.set_mark_in()
        assert engine.mark_in == 30

        engine.seek_to_index(90)
        engine.set_mark_out()
        assert engine.mark_out == 90

    def test_marked_duration(self, replay_engine):
        """Test calculating marked duration."""
        engine = replay_engine

        # No marks
        assert engine.get_marked_duration() == 0

        engine.seek_to_index(30)
        engine.set_mark_in()
        engine.seek_to_index(90)
        engine.set_mark_out()

        # 60 frames at 30fps = 2 seconds
        assert engine.get_marked_duration() == 2.0

    def test_clear_marks(self, replay_engine):
        """Test clearing marks."""
        engine = replay_engine

        engine.seek_to_index(30)
        engine.set_mark_in()
        engine.seek_to_index(90)
        engine.set_mark_out()

        engine.clear_marks()

        assert engine.mark_in is None
        assert engine.mark_out is None

    def test_get_current_frame(self, replay_engine):
        """Test getting current frame."""
        engine = replay_engine

        engine.seek_to_index(50)
        frame = engine.get_current_frame()

        assert frame is not None
        assert isinstance(frame, np.ndarray)

    def test_pause_stop(self, replay_engine):
        """Test pause and stop."""
        engine = replay_engine

        engine.play()
        assert engine.state == PlaybackState.PLAYING

        engine.pause()
        assert engine.state == PlaybackState.PAUSED

        engine.stop()
        assert engine.state == PlaybackState.STOPPED
        assert engine.current_index == 0

    def test_toggle_play_pause(self, replay_engine):
        """Test play/pause toggle."""
        engine = replay_engine

        engine.toggle_play_pause()
        assert engine.state == PlaybackState.PLAYING

        engine.toggle_play_pause()
        assert engine.state == PlaybackState.PAUSED


class TestClipExporter:
    """Tests for ClipExporter utility."""

    def test_export_still_image(self, tmp_path):
        """Test exporting a single frame as image."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add some content
        frame[100:200, 100:200] = [0, 255, 0]

        output_path = str(tmp_path / "test_frame")

        result = ClipExporter.export_still_image(
            frame=frame,
            output_path=output_path,
            format="jpg"
        )

        assert result
        assert (tmp_path / "test_frame.jpg").exists()

    def test_export_still_image_png(self, tmp_path):
        """Test exporting as PNG."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        output_path = str(tmp_path / "test_frame.png")

        result = ClipExporter.export_still_image(
            frame=frame,
            output_path=output_path,
            format="png"
        )

        assert result
        assert (tmp_path / "test_frame.png").exists()


class TestReplayEngineSignals:
    """Tests for ReplayEngine Qt signals."""

    @pytest.fixture
    def engine_with_signals(self):
        """Create engine and attach signal spies."""
        buffer = ReplayBuffer(max_seconds=5, fps=30)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        for i in range(90):  # 3 seconds
            buffer.push(frame)

        engine = ReplayEngine(buffer, fps=30)

        # Attach signal spies
        engine.frame_ready_spy = []
        engine.position_changed_spy = []
        engine.playback_state_changed_spy = []

        engine.frame_ready.connect(
            lambda f: engine.frame_ready_spy.append(f)
        )
        engine.position_changed.connect(
            lambda c, t: engine.position_changed_spy.append((c, t))
        )
        engine.playback_state_changed.connect(
            lambda s: engine.playback_state_changed_spy.append(s)
        )

        return engine

    def test_seek_emits_frame_ready(self, engine_with_signals):
        """Test that seeking emits frame_ready signal."""
        engine = engine_with_signals

        engine.seek_to_index(45)

        assert len(engine.frame_ready_spy) == 1
        assert len(engine.position_changed_spy) == 1
        assert engine.position_changed_spy[0] == (45, 90)

    def test_step_emits_state_change(self, engine_with_signals):
        """Test that stepping emits state change."""
        engine = engine_with_signals

        engine.step_forward(1)

        assert PlaybackState.FRAME_STEP in engine.playback_state_changed_spy

    def test_play_emits_state_change(self, engine_with_signals):
        """Test that play emits state change."""
        engine = engine_with_signals

        engine.play()

        assert PlaybackState.PLAYING in engine.playback_state_changed_spy

        engine.pause()

        assert PlaybackState.PAUSED in engine.playback_state_changed_spy
