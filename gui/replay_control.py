"""
VAR Replay Control Panel

Full-featured VAR operator panel with:
- Live camera feed display
- Instant replay with timeline scrubbing
- Speed controls (slow-motion)
- Frame-by-frame navigation
- Clip marking and export
- Match recording controls
"""

from typing import Optional
from pathlib import Path

import numpy as np
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QSlider, QSpinBox,
    QButtonGroup, QFileDialog, QSizePolicy, QSplitter,
    QGroupBox, QProgressBar
)
from PySide6.QtCore import Qt, Signal, Slot, QTimer
from PySide6.QtGui import QKeySequence, QShortcut

from gui.styles.theme import (
    SURFACE_CARD, SURFACE_ELEVATED, SURFACE_MAIN, SURFACE_DARK,
    BORDER_DEFAULT, BORDER_ACCENT,
    TEXT_PRIMARY, TEXT_SECONDARY, TEXT_MUTED,
    PRIMARY_GOLD, PRIMARY_GREEN, PRIMARY_RED,
    SPACING_SM, SPACING_MD, SPACING_LG, SPACING_XL,
    RADIUS_SM, RADIUS_MD,
    FONT_SIZE_SM, FONT_SIZE_BASE, FONT_SIZE_LG, FONT_SIZE_XL,
)
from gui.camera_feed import CameraFeedWidget
from camera.ring_buffer import ReplayBuffer
from camera.replay_engine import ReplayEngine, PlaybackState
from camera.recorder import MatchRecorder
from camera.capture import CaptureThread


class TimelineWidget(QWidget):
    """Timeline scrubber with position indicator and marks."""

    position_changed = Signal(int)  # Frame index

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        # Time labels
        time_row = QHBoxLayout()
        self.current_time_label = QLabel("00:00.000")
        self.current_time_label.setStyleSheet(f"""
            color: {PRIMARY_GOLD};
            font-family: monospace;
            font-size: {FONT_SIZE_BASE}pt;
        """)

        self.duration_label = QLabel("/ 00:00.000")
        self.duration_label.setStyleSheet(f"""
            color: {TEXT_SECONDARY};
            font-family: monospace;
            font-size: {FONT_SIZE_BASE}pt;
        """)

        time_row.addWidget(self.current_time_label)
        time_row.addWidget(self.duration_label)
        time_row.addStretch()

        self.frame_label = QLabel("Frame: 0 / 0")
        self.frame_label.setStyleSheet(f"color: {TEXT_MUTED}; font-size: {FONT_SIZE_SM}pt;")
        time_row.addWidget(self.frame_label)

        layout.addLayout(time_row)

        # Timeline slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(0)
        self.slider.valueChanged.connect(self._on_slider_changed)
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: {SURFACE_ELEVATED};
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {PRIMARY_GOLD};
                width: 16px;
                margin: -4px 0;
                border-radius: 8px;
            }}
            QSlider::handle:horizontal:hover {{
                background: {PRIMARY_GOLD};
            }}
            QSlider::sub-page:horizontal {{
                background: {PRIMARY_GREEN};
                border-radius: 4px;
            }}
        """)
        layout.addWidget(self.slider)

    def set_range(self, total_frames: int, fps: int = 30) -> None:
        """Set timeline range."""
        self._fps = fps
        self.slider.setMaximum(max(0, total_frames - 1))
        self._update_duration_label(total_frames)

    def set_position(self, frame: int) -> None:
        """Set current position without emitting signal."""
        self.slider.blockSignals(True)
        self.slider.setValue(frame)
        self.slider.blockSignals(False)
        self._update_time_label(frame)
        self.frame_label.setText(f"Frame: {frame} / {self.slider.maximum()}")

    def _on_slider_changed(self, value: int) -> None:
        self._update_time_label(value)
        self.position_changed.emit(value)

    def _update_time_label(self, frame: int) -> None:
        fps = getattr(self, '_fps', 30)
        seconds = frame / fps
        mins = int(seconds) // 60
        secs = seconds % 60
        self.current_time_label.setText(f"{mins:02d}:{secs:06.3f}")

    def _update_duration_label(self, total_frames: int) -> None:
        fps = getattr(self, '_fps', 30)
        seconds = total_frames / fps
        mins = int(seconds) // 60
        secs = seconds % 60
        self.duration_label.setText(f"/ {mins:02d}:{secs:06.3f}")


class SpeedControlWidget(QWidget):
    """Playback speed control buttons."""

    speed_changed = Signal(float)

    SPEEDS = [0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0]

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_speed = 1.0
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(SPACING_SM)

        label = QLabel("Speed:")
        label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(label)

        self.button_group = QButtonGroup(self)

        for speed in self.SPEEDS:
            btn = QPushButton(f"{speed}x")
            btn.setCheckable(True)
            btn.setFixedWidth(50)

            if speed == 1.0:
                btn.setChecked(True)

            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {SURFACE_CARD};
                    color: {TEXT_PRIMARY};
                    border: 1px solid {BORDER_DEFAULT};
                    border-radius: {RADIUS_SM}px;
                    padding: {SPACING_SM}px;
                    font-size: {FONT_SIZE_SM}pt;
                }}
                QPushButton:hover {{
                    background-color: {SURFACE_ELEVATED};
                    border-color: {BORDER_ACCENT};
                }}
                QPushButton:checked {{
                    background-color: {PRIMARY_GOLD};
                    color: {SURFACE_DARK};
                    border-color: {PRIMARY_GOLD};
                }}
            """)

            btn.clicked.connect(lambda checked, s=speed: self._on_speed_clicked(s))
            self.button_group.addButton(btn)
            layout.addWidget(btn)

    def _on_speed_clicked(self, speed: float) -> None:
        self._current_speed = speed
        self.speed_changed.emit(speed)

    def set_speed(self, speed: float) -> None:
        """Set current speed (updates button state)."""
        self._current_speed = speed
        for btn in self.button_group.buttons():
            if btn.text() == f"{speed}x":
                btn.setChecked(True)
                break


class ReplayControlWidget(QWidget):
    """
    VAR operator's replay control panel.

    Combines live feed, replay controls, and recording functionality.
    """

    def __init__(
        self,
        event_bus=None,
        parent: Optional[QWidget] = None
    ):
        super().__init__(parent)
        self.event_bus = event_bus

        # Components (will be initialized when camera is started)
        self._capture_thread: Optional[CaptureThread] = None
        self._replay_buffer: Optional[ReplayBuffer] = None
        self._replay_engine: Optional[ReplayEngine] = None
        self._recorder: Optional[MatchRecorder] = None

        self._is_live = True  # Live vs replay mode

        self._setup_ui()
        self._setup_shortcuts()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_LG, SPACING_LG, SPACING_LG, SPACING_LG)
        layout.setSpacing(SPACING_MD)

        # Header
        header = self._create_header()
        layout.addWidget(header)

        # Main content
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Video display
        video_panel = self._create_video_panel()
        splitter.addWidget(video_panel)

        # Right: Controls
        controls_panel = self._create_controls_panel()
        splitter.addWidget(controls_panel)

        splitter.setSizes([700, 300])
        layout.addWidget(splitter, 1)

        # Bottom: Timeline
        self.timeline = TimelineWidget()
        self.timeline.position_changed.connect(self._on_timeline_seek)
        layout.addWidget(self.timeline)

    def _create_header(self) -> QWidget:
        header = QFrame()
        header.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_CARD};
                border-radius: {RADIUS_MD}px;
                padding: {SPACING_SM}px;
            }}
        """)

        layout = QHBoxLayout(header)

        title = QLabel("VAR Replay Control")
        title.setStyleSheet(f"""
            color: {TEXT_PRIMARY};
            font-size: {FONT_SIZE_XL}pt;
            font-weight: bold;
        """)
        layout.addWidget(title)

        layout.addStretch()

        # Mode indicator
        self.mode_label = QLabel("LIVE")
        self.mode_label.setStyleSheet(f"""
            color: {PRIMARY_GREEN};
            font-size: {FONT_SIZE_LG}pt;
            font-weight: bold;
            padding: {SPACING_SM}px {SPACING_MD}px;
            background-color: rgba(67, 160, 71, 0.2);
            border-radius: {RADIUS_SM}px;
        """)
        layout.addWidget(self.mode_label)

        # Recording status
        self.rec_status = QLabel("NOT RECORDING")
        self.rec_status.setStyleSheet(f"""
            color: {TEXT_MUTED};
            font-size: {FONT_SIZE_BASE}pt;
            padding: {SPACING_SM}px {SPACING_MD}px;
        """)
        layout.addWidget(self.rec_status)

        return header

    def _create_video_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_MAIN};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_MD}px;
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        # Camera feed
        self.camera_feed = CameraFeedWidget(show_controls=False)
        layout.addWidget(self.camera_feed, 1)

        return panel

    def _create_controls_panel(self) -> QWidget:
        panel = QFrame()
        panel.setStyleSheet(f"""
            QFrame {{
                background-color: {SURFACE_MAIN};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_MD}px;
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        layout.setSpacing(SPACING_LG)

        # Playback controls
        playback_group = QGroupBox("Playback")
        playback_group.setStyleSheet(f"""
            QGroupBox {{
                color: {TEXT_PRIMARY};
                font-weight: bold;
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_SM}px;
                margin-top: 10px;
                padding-top: 10px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)

        playback_layout = QVBoxLayout(playback_group)

        # Transport controls
        transport = QHBoxLayout()

        self.live_btn = QPushButton("LIVE")
        self.live_btn.setCheckable(True)
        self.live_btn.setChecked(True)
        self.live_btn.clicked.connect(self._go_live)
        self._style_button(self.live_btn, PRIMARY_GREEN)
        transport.addWidget(self.live_btn)

        self.play_btn = QPushButton("Play")
        self.play_btn.clicked.connect(self._toggle_play)
        self._style_button(self.play_btn)
        transport.addWidget(self.play_btn)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.clicked.connect(self._pause)
        self._style_button(self.pause_btn)
        transport.addWidget(self.pause_btn)

        playback_layout.addLayout(transport)

        # Frame step controls
        step_layout = QHBoxLayout()

        self.step_back_btn = QPushButton("<< Frame")
        self.step_back_btn.clicked.connect(lambda: self._step_frame(-1))
        self._style_button(self.step_back_btn)
        step_layout.addWidget(self.step_back_btn)

        self.step_forward_btn = QPushButton("Frame >>")
        self.step_forward_btn.clicked.connect(lambda: self._step_frame(1))
        self._style_button(self.step_forward_btn)
        step_layout.addWidget(self.step_forward_btn)

        playback_layout.addLayout(step_layout)

        # Speed controls
        self.speed_control = SpeedControlWidget()
        self.speed_control.speed_changed.connect(self._on_speed_changed)
        playback_layout.addWidget(self.speed_control)

        layout.addWidget(playback_group)

        # Clip controls
        clip_group = QGroupBox("Clip Export")
        clip_group.setStyleSheet(playback_group.styleSheet())

        clip_layout = QVBoxLayout(clip_group)

        mark_layout = QHBoxLayout()

        self.mark_in_btn = QPushButton("Mark In [I]")
        self.mark_in_btn.clicked.connect(self._mark_in)
        self._style_button(self.mark_in_btn)
        mark_layout.addWidget(self.mark_in_btn)

        self.mark_out_btn = QPushButton("Mark Out [O]")
        self.mark_out_btn.clicked.connect(self._mark_out)
        self._style_button(self.mark_out_btn)
        mark_layout.addWidget(self.mark_out_btn)

        clip_layout.addLayout(mark_layout)

        # Clip info
        self.clip_info = QLabel("No clip marked")
        self.clip_info.setStyleSheet(f"color: {TEXT_MUTED};")
        clip_layout.addWidget(self.clip_info)

        self.export_btn = QPushButton("Export Clip")
        self.export_btn.clicked.connect(self._export_clip)
        self._style_button(self.export_btn, PRIMARY_GOLD)
        self.export_btn.setEnabled(False)
        clip_layout.addWidget(self.export_btn)

        # Export progress
        self.export_progress = QProgressBar()
        self.export_progress.setVisible(False)
        self.export_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {SURFACE_ELEVATED};
                border-radius: {RADIUS_SM}px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {PRIMARY_GREEN};
                border-radius: {RADIUS_SM}px;
            }}
        """)
        clip_layout.addWidget(self.export_progress)

        layout.addWidget(clip_group)

        # Recording controls
        rec_group = QGroupBox("Recording")
        rec_group.setStyleSheet(playback_group.styleSheet())

        rec_layout = QVBoxLayout(rec_group)

        rec_buttons = QHBoxLayout()

        self.rec_start_btn = QPushButton("Start Rec")
        self.rec_start_btn.clicked.connect(self._start_recording)
        self._style_button(self.rec_start_btn, PRIMARY_RED)
        rec_buttons.addWidget(self.rec_start_btn)

        self.rec_stop_btn = QPushButton("Stop Rec")
        self.rec_stop_btn.clicked.connect(self._stop_recording)
        self.rec_stop_btn.setEnabled(False)
        self._style_button(self.rec_stop_btn)
        rec_buttons.addWidget(self.rec_stop_btn)

        rec_layout.addLayout(rec_buttons)

        layout.addWidget(rec_group)

        layout.addStretch()

        return panel

    def _style_button(self, btn: QPushButton, color: Optional[str] = None) -> None:
        """Apply consistent button styling."""
        bg_color = color if color else SURFACE_CARD
        text_color = SURFACE_DARK if color else TEXT_PRIMARY

        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color};
                color: {text_color};
                border: 1px solid {BORDER_DEFAULT};
                border-radius: {RADIUS_SM}px;
                padding: {SPACING_SM}px {SPACING_MD}px;
                font-size: {FONT_SIZE_BASE}pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {SURFACE_ELEVATED if not color else color};
                border-color: {BORDER_ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {SURFACE_DARK};
            }}
            QPushButton:disabled {{
                background-color: {SURFACE_ELEVATED};
                color: {TEXT_MUTED};
            }}
        """)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts."""
        # Playback
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._toggle_play)
        QShortcut(QKeySequence(Qt.Key.Key_L), self, self._go_live)

        # Frame stepping
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, lambda: self._step_frame(-1))
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, lambda: self._step_frame(1))
        QShortcut(QKeySequence(Qt.Key.Key_Comma), self, lambda: self._step_frame(-10))
        QShortcut(QKeySequence(Qt.Key.Key_Period), self, lambda: self._step_frame(10))

        # Speed
        QShortcut(QKeySequence(Qt.Key.Key_BracketLeft), self, lambda: self._change_speed(-1))
        QShortcut(QKeySequence(Qt.Key.Key_BracketRight), self, lambda: self._change_speed(1))

        # Clip marking
        QShortcut(QKeySequence(Qt.Key.Key_I), self, self._mark_in)
        QShortcut(QKeySequence(Qt.Key.Key_O), self, self._mark_out)

    def initialize_camera(
        self,
        camera_source: int = 0,
        fps: int = 30,
        buffer_seconds: int = 120
    ) -> None:
        """
        Initialize camera capture and replay system.

        Args:
            camera_source: Camera index or RTSP URL
            fps: Target FPS
            buffer_seconds: Replay buffer duration
        """
        # Create replay buffer
        self._replay_buffer = ReplayBuffer(max_seconds=buffer_seconds, fps=fps)

        # Create replay engine
        self._replay_engine = ReplayEngine(self._replay_buffer, fps=fps)
        self._replay_engine.frame_ready.connect(self._on_replay_frame)
        self._replay_engine.position_changed.connect(self._on_position_changed)
        self._replay_engine.playback_state_changed.connect(self._on_playback_state_changed)
        self._replay_engine.clip_exported.connect(self._on_clip_exported)
        self._replay_engine.export_progress.connect(self._on_export_progress)

        # Create recorder
        self._recorder = MatchRecorder(fps=fps)
        self._recorder.recording_started.connect(self._on_recording_started)
        self._recorder.recording_stopped.connect(self._on_recording_stopped)

        # Create capture thread
        self._capture_thread = CaptureThread(source=camera_source, fps=fps)
        self._capture_thread.frame_ready.connect(self._on_live_frame)
        self._capture_thread.error.connect(self._on_camera_error)

        # Start capture
        self._capture_thread.start()

    def shutdown(self) -> None:
        """Shutdown camera and cleanup."""
        if self._capture_thread:
            self._capture_thread.stop()

        if self._recorder and self._recorder.is_recording:
            self._recorder.stop_recording()

    @Slot(np.ndarray)
    def _on_live_frame(self, frame: np.ndarray) -> None:
        """Handle new frame from camera."""
        # Add to replay buffer
        if self._replay_buffer:
            self._replay_buffer.push(frame)

        # Update timeline range
        if self._replay_buffer:
            self.timeline.set_range(self._replay_buffer.size)

        # Display if in live mode
        if self._is_live:
            self.camera_feed.update_frame(frame)
            self.timeline.set_position(self._replay_buffer.size - 1)

        # Write to recording if active
        if self._recorder:
            self._recorder.write_frame(frame)

    @Slot(np.ndarray)
    def _on_replay_frame(self, frame: np.ndarray) -> None:
        """Handle frame from replay engine."""
        if not self._is_live:
            self.camera_feed.update_frame(frame)

    @Slot(int, int)
    def _on_position_changed(self, current: int, total: int) -> None:
        """Handle replay position change."""
        self.timeline.set_position(current)

    @Slot(str)
    def _on_playback_state_changed(self, state: str) -> None:
        """Handle playback state change."""
        self.play_btn.setText("Pause" if state == PlaybackState.PLAYING else "Play")

    def _go_live(self) -> None:
        """Switch to live feed."""
        self._is_live = True
        self.live_btn.setChecked(True)
        self.mode_label.setText("LIVE")
        self.mode_label.setStyleSheet(f"""
            color: {PRIMARY_GREEN};
            font-size: {FONT_SIZE_LG}pt;
            font-weight: bold;
            padding: {SPACING_SM}px {SPACING_MD}px;
            background-color: rgba(67, 160, 71, 0.2);
            border-radius: {RADIUS_SM}px;
        """)

        if self._replay_engine:
            self._replay_engine.stop()

    def _toggle_play(self) -> None:
        """Toggle play/pause."""
        if not self._replay_engine:
            return

        if self._is_live:
            # Switch to replay mode
            self._is_live = False
            self.live_btn.setChecked(False)
            self.mode_label.setText("REPLAY")
            self.mode_label.setStyleSheet(f"""
                color: {PRIMARY_GOLD};
                font-size: {FONT_SIZE_LG}pt;
                font-weight: bold;
                padding: {SPACING_SM}px {SPACING_MD}px;
                background-color: rgba(232, 185, 35, 0.2);
                border-radius: {RADIUS_SM}px;
            """)

        self._replay_engine.toggle_play_pause()

    def _pause(self) -> None:
        """Pause replay."""
        if self._replay_engine:
            self._replay_engine.pause()

    def _step_frame(self, direction: int) -> None:
        """Step frames."""
        if not self._replay_engine:
            return

        if self._is_live:
            self._is_live = False
            self.live_btn.setChecked(False)
            self.mode_label.setText("REPLAY")

        if direction > 0:
            self._replay_engine.step_forward(abs(direction))
        else:
            self._replay_engine.step_backward(abs(direction))

    def _change_speed(self, direction: int) -> None:
        """Change playback speed."""
        if self._replay_engine:
            new_speed = self._replay_engine.cycle_speed(direction)
            self.speed_control.set_speed(new_speed)

    @Slot(float)
    def _on_speed_changed(self, speed: float) -> None:
        """Handle speed control change."""
        if self._replay_engine:
            self._replay_engine.set_speed(speed)

    def _on_timeline_seek(self, frame: int) -> None:
        """Handle timeline seek."""
        if self._replay_engine:
            if self._is_live:
                self._is_live = False
                self.live_btn.setChecked(False)
                self.mode_label.setText("REPLAY")

            self._replay_engine.seek_to_index(frame)

    def _mark_in(self) -> None:
        """Set mark-in point."""
        if self._replay_engine:
            frame = self._replay_engine.set_mark_in()
            self._update_clip_info()

    def _mark_out(self) -> None:
        """Set mark-out point."""
        if self._replay_engine:
            frame = self._replay_engine.set_mark_out()
            self._update_clip_info()

    def _update_clip_info(self) -> None:
        """Update clip info display."""
        if not self._replay_engine:
            return

        mark_in = self._replay_engine.mark_in
        mark_out = self._replay_engine.mark_out

        if mark_in is not None and mark_out is not None:
            duration = self._replay_engine.get_marked_duration()
            self.clip_info.setText(
                f"In: {mark_in} | Out: {mark_out} | Duration: {duration:.2f}s"
            )
            self.export_btn.setEnabled(True)
        elif mark_in is not None:
            self.clip_info.setText(f"In: {mark_in} | Out: not set")
            self.export_btn.setEnabled(False)
        elif mark_out is not None:
            self.clip_info.setText(f"In: not set | Out: {mark_out}")
            self.export_btn.setEnabled(False)
        else:
            self.clip_info.setText("No clip marked")
            self.export_btn.setEnabled(False)

    def _export_clip(self) -> None:
        """Export marked clip."""
        if not self._replay_engine:
            return

        # Get save path
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Clip",
            "clip.mp4",
            "Video Files (*.mp4 *.avi)"
        )

        if path:
            self.export_progress.setVisible(True)
            self.export_progress.setValue(0)
            self._replay_engine.export_clip(path)

    @Slot(int, int)
    def _on_export_progress(self, current: int, total: int) -> None:
        """Update export progress."""
        percent = int(current / total * 100) if total > 0 else 0
        self.export_progress.setValue(percent)

    @Slot(str)
    def _on_clip_exported(self, path: str) -> None:
        """Handle clip export complete."""
        self.export_progress.setVisible(False)
        self.clip_info.setText(f"Exported: {Path(path).name}")

    def _start_recording(self) -> None:
        """Start match recording."""
        if self._recorder:
            self._recorder.start_recording()

    def _stop_recording(self) -> None:
        """Stop match recording."""
        if self._recorder:
            self._recorder.stop_recording()

    @Slot(str)
    def _on_recording_started(self, path: str) -> None:
        """Handle recording started."""
        self.rec_start_btn.setEnabled(False)
        self.rec_stop_btn.setEnabled(True)
        self.rec_status.setText("RECORDING")
        self.rec_status.setStyleSheet(f"""
            color: {PRIMARY_RED};
            font-size: {FONT_SIZE_BASE}pt;
            font-weight: bold;
            padding: {SPACING_SM}px {SPACING_MD}px;
        """)

    @Slot(str, float)
    def _on_recording_stopped(self, path: str, duration: float) -> None:
        """Handle recording stopped."""
        self.rec_start_btn.setEnabled(True)
        self.rec_stop_btn.setEnabled(False)
        self.rec_status.setText(f"Saved: {Path(path).name}")
        self.rec_status.setStyleSheet(f"color: {TEXT_MUTED};")

    def _on_camera_error(self, error: str) -> None:
        """Handle camera error."""
        self.camera_feed.show_error(error)
