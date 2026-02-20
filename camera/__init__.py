"""
AmpsMotion Camera Integration

Camera capture, replay buffer, and clip export functionality.
"""

from camera.ring_buffer import ReplayBuffer, TimestampedFrame
from camera.capture import CaptureThread, MultiCameraCapture
from camera.replay_engine import ReplayEngine, PlaybackState, ClipExporter
from camera.recorder import MatchRecorder, MultiStreamRecorder, RecordingState

__all__ = [
    # Ring Buffer
    "ReplayBuffer",
    "TimestampedFrame",
    # Capture
    "CaptureThread",
    "MultiCameraCapture",
    # Replay
    "ReplayEngine",
    "PlaybackState",
    "ClipExporter",
    # Recording
    "MatchRecorder",
    "MultiStreamRecorder",
    "RecordingState",
]
