"""
Live Camera Feed Widget

Displays live camera feed from OpenCV capture thread.
Used for VAR preview and monitoring.
"""

from typing import Optional

import cv2
import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QComboBox, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QImage, QPixmap

from gui.styles.theme import (
    SURFACE_CARD, SURFACE_ELEVATED, SURFACE_DARK,
    BORDER_DEFAULT, BORDER_ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    PRIMARY_GOLD, PRIMARY_GREEN, PRIMARY_RED,
    SPACING_SM, SPACING_MD, SPACING_LG,
    RADIUS_SM, RADIUS_MD,
    FONT_SIZE_SM, FONT_SIZE_BASE,
)


class CameraFeedWidget(QWidget):
    """
    Live camera feed display widget.

    Displays frames from a CaptureThread and optionally
    pushes them to a ReplayBuffer.

    Usage:
        feed = CameraFeedWidget()
        capture_thread.frame_ready.connect(feed.update_frame)
        feed.show()
    """

    # Signals
    frame_captured = Signal(np.ndarray)  # Emits each frame for external processing
    recording_started = Signal()
    recording_stopped = Signal()

    def __init__(
        self,
        camera_id: int = 0,
        show_controls: bool = True,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.camera_id = camera_id
        self.show_controls = show_controls

        self._is_recording = False
        self._frame_count = 0
        self._last_frame: Optional[np.ndarray] = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        # Video display area
        self.video_frame = QFrame()
        self.video_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_DARK};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_MD}px;
            }}
        """)

        video_layout = QVBoxLayout(self.video_frame)
        video_layout.setContentsMargins(0, 0, 0, 0)

        # Video label for displaying frames
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(320, 240)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )
        self.video_label.setStyleSheet(f"""
            QLabel {{
                background-color: {SURFACE_DARK};
                color: {TEXT_MUTED};
            }}
        """)
        self.video_label.setText("No Camera Feed")

        video_layout.addWidget(self.video_label)

        # Status overlay
        self.status_label = QLabel()
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {PRIMARY_GOLD};
                font-size: {FONT_SIZE_SM}pt;
                padding: {SPACING_SM}px;
                background-color: rgba(0, 0, 0, 0.5);
                border-radius: {RADIUS_SM}px;
            }}
        """)
        self.status_label.hide()

        layout.addWidget(self.video_frame, 1)

        # Controls
        if self.show_controls:
            controls = self._create_controls()
            layout.addWidget(controls)

    def _create_controls(self) -> QWidget:
        """Create camera control panel."""
        controls = QFrame()
        controls.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_CARD};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_SM}px;
                padding: {SPACING_SM}px;
            }}
        """)

        layout = QHBoxLayout(controls)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_MD)

        # Camera selector
        camera_label = QLabel("Camera:")
        camera_label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(camera_label)

        self.camera_combo = QComboBox()
        self.camera_combo.addItems([
            "Camera 0 (Default)",
            "Camera 1",
            "Camera 2",
            "Camera 3",
        ])
        self.camera_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {SURFACE_ELEVATED};
                color: {TEXT_PRIMARY};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_SM}px;
                padding: {SPACING_SM}px;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: {BORDER_ACCENT};
            }}
            QComboBox::drop-down {{
                border: none;
                padding-right: {SPACING_SM}px;
            }}
        """)
        self.camera_combo.currentIndexChanged.connect(self._on_camera_changed)
        layout.addWidget(self.camera_combo)

        layout.addStretch()

        # Recording indicator
        self.rec_indicator = QLabel()
        self.rec_indicator.setFixedSize(12, 12)
        self.rec_indicator.setStyleSheet(f"""
            QLabel {{
                background-color: {TEXT_MUTED};
                border-radius: 6px;
            }}
        """)
        layout.addWidget(self.rec_indicator)

        self.rec_label = QLabel("Not Recording")
        self.rec_label.setStyleSheet(f"color: {TEXT_MUTED};")
        layout.addWidget(self.rec_label)

        # Frame counter
        self.frame_counter = QLabel("Frames: 0")
        self.frame_counter.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self.frame_counter)

        return controls

    @Slot(np.ndarray)
    def update_frame(self, frame: np.ndarray) -> None:
        """
        Update the display with a new frame.

        Args:
            frame: BGR numpy array from OpenCV
        """
        self._last_frame = frame
        self._frame_count += 1

        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Get display size
        display_size = self.video_label.size()

        # Resize frame to fit display while maintaining aspect ratio
        height, width = rgb_frame.shape[:2]
        aspect = width / height

        if display_size.width() / display_size.height() > aspect:
            # Height constrained
            new_height = display_size.height()
            new_width = int(new_height * aspect)
        else:
            # Width constrained
            new_width = display_size.width()
            new_height = int(new_width / aspect)

        if new_width > 0 and new_height > 0:
            resized = cv2.resize(rgb_frame, (new_width, new_height))

            # Create QImage
            bytes_per_line = 3 * new_width
            q_image = QImage(
                resized.data,
                new_width,
                new_height,
                bytes_per_line,
                QImage.Format.Format_RGB888
            )

            # Display
            pixmap = QPixmap.fromImage(q_image)
            self.video_label.setPixmap(pixmap)

        # Update frame counter
        if hasattr(self, 'frame_counter'):
            self.frame_counter.setText(f"Frames: {self._frame_count}")

        # Emit for external processing
        self.frame_captured.emit(frame)

    def set_recording(self, is_recording: bool) -> None:
        """Update recording indicator."""
        self._is_recording = is_recording

        if is_recording:
            self.rec_indicator.setStyleSheet(f"""
                QLabel {{
                    background-color: {PRIMARY_RED};
                    border-radius: 6px;
                }}
            """)
            self.rec_label.setText("REC")
            self.rec_label.setStyleSheet(f"color: {PRIMARY_RED}; font-weight: bold;")
            self.recording_started.emit()
        else:
            self.rec_indicator.setStyleSheet(f"""
                QLabel {{
                    background-color: {TEXT_MUTED};
                    border-radius: 6px;
                }}
            """)
            self.rec_label.setText("Not Recording")
            self.rec_label.setStyleSheet(f"color: {TEXT_MUTED};")
            self.recording_stopped.emit()

    def show_error(self, message: str) -> None:
        """Display an error message on the video area."""
        self.video_label.setText(f"Error: {message}")
        self.video_label.setStyleSheet(f"""
            QLabel {{
                background-color: {SURFACE_DARK};
                color: {PRIMARY_RED};
                font-size: {FONT_SIZE_BASE}pt;
            }}
        """)

    def show_status(self, message: str, duration_ms: int = 3000) -> None:
        """Show a temporary status message overlay."""
        self.status_label.setText(message)
        self.status_label.show()
        # Auto-hide after duration (would need QTimer for actual implementation)

    def get_last_frame(self) -> Optional[np.ndarray]:
        """Get the most recently displayed frame."""
        return self._last_frame

    def reset_frame_count(self) -> None:
        """Reset the frame counter."""
        self._frame_count = 0
        if hasattr(self, 'frame_counter'):
            self.frame_counter.setText("Frames: 0")

    def _on_camera_changed(self, index: int) -> None:
        """Handle camera selection change."""
        self.camera_id = index
        # Actual camera switching would be handled by parent widget
        # that manages the CaptureThread


class MultiCameraFeedWidget(QWidget):
    """
    Multi-camera feed display for VAR setups.

    Displays multiple camera feeds in a grid layout.
    """

    camera_selected = Signal(int)  # camera_id

    def __init__(
        self,
        camera_count: int = 4,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.camera_count = camera_count
        self.feeds: list[CameraFeedWidget] = []
        self.selected_camera = 0

        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_MD)

        # Header
        header = QHBoxLayout()
        title = QLabel("Multi-Camera View")
        title.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: 14pt;
            font-weight: bold;
        """)
        header.addWidget(title)
        header.addStretch()
        layout.addLayout(header)

        # Camera grid (2x2 for 4 cameras)
        from PySide6.QtWidgets import QGridLayout
        grid = QGridLayout()
        grid.setSpacing(SPACING_SM)

        cols = 2
        for i in range(self.camera_count):
            feed = CameraFeedWidget(camera_id=i, show_controls=False)
            feed.setMinimumSize(320, 240)

            # Make clickable
            feed.mousePressEvent = lambda e, cam=i: self._select_camera(cam)

            self.feeds.append(feed)
            grid.addWidget(feed, i // cols, i % cols)

        layout.addLayout(grid, 1)

        # Highlight selected camera
        self._update_selection()

    def _select_camera(self, camera_id: int) -> None:
        """Select a camera for main display."""
        self.selected_camera = camera_id
        self._update_selection()
        self.camera_selected.emit(camera_id)

    def _update_selection(self) -> None:
        """Update visual selection indicator."""
        for i, feed in enumerate(self.feeds):
            if i == self.selected_camera:
                feed.video_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {SURFACE_DARK};
                        border: 2px solid {PRIMARY_GOLD};
                        border-radius: {RADIUS_MD}px;
                    }}
                """)
            else:
                feed.video_frame.setStyleSheet(f"""
                    QFrame {{
                        background-color: {SURFACE_DARK};
                        border: 1px solid {BORDER_DEFAULT};
                        border-radius: {RADIUS_MD}px;
                    }}
                """)

    @Slot(list)
    def update_frames(self, frames: list) -> None:
        """
        Update all camera feeds.

        Args:
            frames: List of (camera_id, frame) tuples
        """
        for camera_id, frame in frames:
            if camera_id < len(self.feeds) and frame is not None:
                self.feeds[camera_id].update_frame(frame)

    def get_selected_feed(self) -> Optional[CameraFeedWidget]:
        """Get the currently selected camera feed."""
        if 0 <= self.selected_camera < len(self.feeds):
            return self.feeds[self.selected_camera]
        return None
