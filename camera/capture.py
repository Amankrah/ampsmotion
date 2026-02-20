"""
Camera Capture Thread

OpenCV-based camera capture running in a background thread.
Emits frames for display and replay buffer.
"""

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal


class CaptureThread(QThread):
    """
    Runs an OpenCV VideoCapture in a background thread.
    Emits frames as numpy arrays for display and buffering.

    Usage:
        thread = CaptureThread(source=0)
        thread.frame_ready.connect(on_frame)
        thread.start()

        # Later
        thread.stop()
    """

    frame_ready = Signal(np.ndarray)  # BGR frame
    error = Signal(str)

    def __init__(self, source: int | str = 0, fps: int = 30):
        """
        Initialize the capture thread.

        Args:
            source: Camera index (0 = default webcam) or RTSP URL
            fps: Target frames per second
        """
        super().__init__()
        self.source = source
        self.target_fps = fps
        self._running = False

    def run(self) -> None:
        """Main thread loop - captures frames from the camera."""
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self.error.emit(f"Cannot open camera: {self.source}")
            return

        # Try to set FPS
        cap.set(cv2.CAP_PROP_FPS, self.target_fps)

        self._running = True

        while self._running:
            ret, frame = cap.read()
            if ret:
                self.frame_ready.emit(frame)
            else:
                self.error.emit("Frame capture failed")
                break

        cap.release()

    def stop(self) -> None:
        """Stop the capture thread."""
        self._running = False
        self.wait()


class MultiCameraCapture(QThread):
    """
    Captures from multiple cameras simultaneously.
    Used for multi-angle VAR setups.
    """

    frames_ready = Signal(list)  # List of (camera_id, frame) tuples
    error = Signal(int, str)  # (camera_id, error_message)

    def __init__(self, sources: list[int | str], fps: int = 30):
        """
        Initialize multi-camera capture.

        Args:
            sources: List of camera indices or RTSP URLs
            fps: Target frames per second
        """
        super().__init__()
        self.sources = sources
        self.target_fps = fps
        self._running = False

    def run(self) -> None:
        """Main thread loop - captures from all cameras."""
        captures = []

        for i, source in enumerate(self.sources):
            cap = cv2.VideoCapture(source)
            if not cap.isOpened():
                self.error.emit(i, f"Cannot open camera: {source}")
                cap = None
            else:
                cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            captures.append(cap)

        self._running = True

        while self._running:
            frames = []
            for i, cap in enumerate(captures):
                if cap is not None:
                    ret, frame = cap.read()
                    if ret:
                        frames.append((i, frame))
                    else:
                        frames.append((i, None))
                else:
                    frames.append((i, None))

            self.frames_ready.emit(frames)

        # Release all captures
        for cap in captures:
            if cap is not None:
                cap.release()

    def stop(self) -> None:
        """Stop all camera captures."""
        self._running = False
        self.wait()
