"""
Match Recorder

Full-match recording to video file using OpenCV VideoWriter.
Records continuously from camera feed during a match.
Supports optional audio recording when audio device is available.
"""

import cv2
import wave
import numpy as np
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread, Event
from typing import Optional

from PySide6.QtCore import QObject, Signal, Slot

# Optional audio support
try:
    import sounddevice as sd
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False


class RecordingState:
    """Recording state constants."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    FINALIZING = "finalizing"


class AudioRecorder:
    """
    Records audio from system microphone to WAV file.

    Uses sounddevice for cross-platform audio capture.
    Runs in a separate thread to avoid blocking.
    """

    def __init__(
        self,
        output_path: Path,
        sample_rate: int = 44100,
        channels: int = 2,
        device: Optional[int] = None
    ):
        """
        Initialize audio recorder.

        Args:
            output_path: Path for output WAV file
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels (1=mono, 2=stereo)
            device: Audio input device index (None for default)
        """
        self.output_path = output_path
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device

        self._recording = False
        self._paused = False
        self._stop_event = Event()
        self._thread: Optional[Thread] = None
        self._audio_data: list[np.ndarray] = []

    @property
    def is_available(self) -> bool:
        """Check if audio recording is available."""
        return AUDIO_AVAILABLE

    @staticmethod
    def get_audio_devices() -> list[dict]:
        """
        Get list of available audio input devices.

        Returns:
            List of device info dicts with 'id', 'name', 'channels'
        """
        if not AUDIO_AVAILABLE:
            return []

        devices = []
        try:
            for i, dev in enumerate(sd.query_devices()):
                if dev['max_input_channels'] > 0:
                    devices.append({
                        'id': i,
                        'name': dev['name'],
                        'channels': dev['max_input_channels'],
                        'sample_rate': dev['default_samplerate'],
                    })
        except Exception:
            pass
        return devices

    def start(self) -> bool:
        """
        Start audio recording.

        Returns:
            True if recording started successfully
        """
        if not AUDIO_AVAILABLE:
            return False

        if self._recording:
            return False

        self._audio_data = []
        self._stop_event.clear()
        self._recording = True
        self._paused = False

        self._thread = Thread(target=self._record_loop, daemon=True)
        self._thread.start()

        return True

    def _record_loop(self) -> None:
        """Audio recording loop (runs in thread)."""
        try:
            def audio_callback(indata, frames, time_info, status):
                if not self._paused:
                    self._audio_data.append(indata.copy())

            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                device=self.device,
                callback=audio_callback
            ):
                while not self._stop_event.is_set():
                    self._stop_event.wait(timeout=0.1)

        except Exception as e:
            print(f"Audio recording error: {e}")
            self._recording = False

    def pause(self) -> None:
        """Pause audio recording."""
        self._paused = True

    def resume(self) -> None:
        """Resume audio recording."""
        self._paused = False

    def stop(self) -> Optional[str]:
        """
        Stop recording and save to WAV file.

        Returns:
            Output file path, or None if failed
        """
        if not self._recording:
            return None

        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)

        self._recording = False

        # Save to WAV file
        if not self._audio_data:
            return None

        try:
            audio_array = np.concatenate(self._audio_data, axis=0)

            # Convert float32 to int16 for WAV
            audio_int16 = (audio_array * 32767).astype(np.int16)

            with wave.open(str(self.output_path), 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_int16.tobytes())

            return str(self.output_path)

        except Exception as e:
            print(f"Error saving audio: {e}")
            return None

    @property
    def duration(self) -> float:
        """Get recording duration in seconds."""
        if not self._audio_data:
            return 0.0
        total_frames = sum(chunk.shape[0] for chunk in self._audio_data)
        return total_frames / self.sample_rate


class MatchRecorder(QObject):
    """
    Records full match video from camera feed with optional audio.

    Handles continuous recording during a match with support
    for pausing and resuming. Audio is recorded separately and
    can be muxed in post-processing.

    Usage:
        recorder = MatchRecorder(output_dir="recordings", record_audio=True)
        capture_thread.frame_ready.connect(recorder.write_frame)

        recorder.start_recording(match_id=123)
        # ... match happens ...
        recorder.stop_recording()
    """

    # Signals
    recording_started = Signal(str)  # output file path
    recording_stopped = Signal(str, float)  # output file path, duration
    recording_paused = Signal()
    recording_resumed = Signal()
    recording_error = Signal(str)  # error message
    frame_written = Signal(int)  # frame count
    audio_available = Signal(bool)  # audio recording availability

    def __init__(
        self,
        output_dir: str = "recordings",
        fps: int = 30,
        codec: str = "mp4v",
        format: str = "mp4",
        record_audio: bool = False,
        audio_device: Optional[int] = None,
        audio_sample_rate: int = 44100,
        audio_channels: int = 2,
        parent: Optional[QObject] = None
    ):
        """
        Initialize the match recorder.

        Args:
            output_dir: Directory to save recordings
            fps: Target frames per second
            codec: Video codec (mp4v, XVID, H264)
            format: Output format (mp4, avi)
            record_audio: Whether to record audio alongside video
            audio_device: Audio input device index (None for default)
            audio_sample_rate: Audio sample rate in Hz
            audio_channels: Number of audio channels
        """
        super().__init__(parent)
        self.output_dir = Path(output_dir)
        self.fps = fps
        self.codec = codec
        self.format = format

        # Audio settings
        self._record_audio = record_audio and AUDIO_AVAILABLE
        self._audio_device = audio_device
        self._audio_sample_rate = audio_sample_rate
        self._audio_channels = audio_channels
        self._audio_recorder: Optional[AudioRecorder] = None
        self._audio_path: Optional[Path] = None

        # Recording state
        self._state = RecordingState.IDLE
        self._writer: Optional[cv2.VideoWriter] = None
        self._output_path: Optional[Path] = None
        self._frame_count = 0
        self._start_time: Optional[datetime] = None
        self._frame_size: Optional[tuple[int, int]] = None

        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Emit audio availability
        self.audio_available.emit(AUDIO_AVAILABLE)

    @property
    def is_audio_available(self) -> bool:
        """Check if audio recording is available on this system."""
        return AUDIO_AVAILABLE

    @property
    def audio_enabled(self) -> bool:
        """Check if audio recording is enabled."""
        return self._record_audio

    @audio_enabled.setter
    def audio_enabled(self, value: bool) -> None:
        """Enable or disable audio recording."""
        self._record_audio = value and AUDIO_AVAILABLE

    @staticmethod
    def get_audio_devices() -> list[dict]:
        """Get list of available audio input devices."""
        return AudioRecorder.get_audio_devices()

    @property
    def audio_path(self) -> Optional[str]:
        """Get path to audio recording file."""
        return str(self._audio_path) if self._audio_path else None

    @property
    def state(self) -> str:
        """Get current recording state."""
        return self._state

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._state == RecordingState.RECORDING

    @property
    def frame_count(self) -> int:
        """Get number of frames written."""
        return self._frame_count

    @property
    def duration(self) -> float:
        """Get recording duration in seconds."""
        return self._frame_count / self.fps

    @property
    def output_path(self) -> Optional[str]:
        """Get current output file path."""
        return str(self._output_path) if self._output_path else None

    def start_recording(
        self,
        match_id: Optional[int] = None,
        filename: Optional[str] = None,
        frame_size: Optional[tuple[int, int]] = None
    ) -> bool:
        """
        Start recording video and optionally audio.

        Args:
            match_id: Optional match ID for filename
            filename: Optional custom filename (without extension)
            frame_size: Optional frame size (width, height). If not provided,
                       will be determined from first frame.

        Returns:
            True if recording started successfully
        """
        if self._state != RecordingState.IDLE:
            self.recording_error.emit("Already recording")
            return False

        # Generate filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if filename:
            base_name = filename
        elif match_id:
            base_name = f"match_{match_id}_{timestamp}"
        else:
            base_name = f"recording_{timestamp}"

        self._output_path = self.output_dir / f"{base_name}.{self.format}"
        self._frame_size = frame_size
        self._frame_count = 0
        self._start_time = datetime.now(timezone.utc)

        # If frame size is provided, create writer now
        if frame_size:
            if not self._create_writer(frame_size):
                return False

        # Start audio recording if enabled
        if self._record_audio:
            self._audio_path = self.output_dir / f"{base_name}_audio.wav"
            self._audio_recorder = AudioRecorder(
                output_path=self._audio_path,
                sample_rate=self._audio_sample_rate,
                channels=self._audio_channels,
                device=self._audio_device
            )
            if not self._audio_recorder.start():
                self.recording_error.emit("Failed to start audio recording")
                # Continue without audio

        self._state = RecordingState.RECORDING
        self.recording_started.emit(str(self._output_path))
        return True

    def _create_writer(self, frame_size: tuple[int, int]) -> bool:
        """Create the video writer."""
        width, height = frame_size
        fourcc = cv2.VideoWriter.fourcc(*self.codec)

        self._writer = cv2.VideoWriter(
            str(self._output_path),
            fourcc,
            self.fps,
            (width, height)
        )

        if not self._writer.isOpened():
            self.recording_error.emit(f"Failed to create video file: {self._output_path}")
            self._state = RecordingState.IDLE
            return False

        self._frame_size = frame_size
        return True

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and finalize the video and audio files.

        Returns:
            Output file path, or None if not recording
        """
        if self._state == RecordingState.IDLE:
            return None

        self._state = RecordingState.FINALIZING

        output_path = str(self._output_path) if self._output_path else None
        duration = self.duration

        # Stop video writer
        if self._writer:
            self._writer.release()
            self._writer = None

        # Stop audio recording
        audio_path = None
        if self._audio_recorder:
            audio_path = self._audio_recorder.stop()
            self._audio_recorder = None

        self._state = RecordingState.IDLE

        if output_path:
            self.recording_stopped.emit(output_path, duration)

        return output_path

    def pause_recording(self) -> None:
        """Pause video and audio recording."""
        if self._state == RecordingState.RECORDING:
            self._state = RecordingState.PAUSED

            # Pause audio recording
            if self._audio_recorder:
                self._audio_recorder.pause()

            self.recording_paused.emit()

    def resume_recording(self) -> None:
        """Resume video and audio recording after pause."""
        if self._state == RecordingState.PAUSED:
            self._state = RecordingState.RECORDING

            # Resume audio recording
            if self._audio_recorder:
                self._audio_recorder.resume()

            self.recording_resumed.emit()

    def get_recording_info(self) -> dict:
        """
        Get information about the current recording.

        Returns:
            Dict with video_path, audio_path, duration, frame_count, etc.
        """
        return {
            "state": self._state,
            "video_path": str(self._output_path) if self._output_path else None,
            "audio_path": str(self._audio_path) if self._audio_path else None,
            "audio_enabled": self._record_audio,
            "audio_available": AUDIO_AVAILABLE,
            "frame_count": self._frame_count,
            "duration": self.duration,
            "fps": self.fps,
            "frame_size": self._frame_size,
        }

    @Slot(np.ndarray)
    def write_frame(self, frame: np.ndarray) -> None:
        """
        Write a frame to the recording.

        Connect this to CaptureThread.frame_ready signal.

        Args:
            frame: BGR numpy array from OpenCV
        """
        if self._state != RecordingState.RECORDING:
            return

        # Create writer on first frame if not yet created
        if self._writer is None:
            height, width = frame.shape[:2]
            if not self._create_writer((width, height)):
                return

        # Ensure frame matches expected size
        height, width = frame.shape[:2]
        if self._frame_size and (width, height) != self._frame_size:
            frame = cv2.resize(frame, self._frame_size)

        # Write frame
        self._writer.write(frame)
        self._frame_count += 1
        self.frame_written.emit(self._frame_count)

    def add_chapter_marker(self, label: str) -> dict:
        """
        Add a chapter marker at current position.

        Useful for marking round starts/ends.

        Args:
            label: Chapter label

        Returns:
            Chapter marker dict
        """
        return {
            "frame": self._frame_count,
            "time": self.duration,
            "label": label,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }


class MultiStreamRecorder(QObject):
    """
    Records from multiple camera sources simultaneously.

    Creates separate files for each camera angle.
    """

    recording_started = Signal(list)  # List of output file paths
    recording_stopped = Signal(list, float)  # List of paths, duration
    recording_error = Signal(int, str)  # camera_id, error

    def __init__(
        self,
        camera_count: int,
        output_dir: str = "recordings",
        fps: int = 30,
        codec: str = "mp4v",
        format: str = "mp4",
        parent: Optional[QObject] = None
    ):
        super().__init__(parent)
        self.camera_count = camera_count
        self.output_dir = Path(output_dir)
        self.fps = fps
        self.codec = codec
        self.format = format

        # Create recorders for each camera
        self._recorders: list[MatchRecorder] = []
        for i in range(camera_count):
            recorder = MatchRecorder(
                output_dir=str(self.output_dir),
                fps=fps,
                codec=codec,
                format=format
            )
            recorder.recording_error.connect(
                lambda msg, cam=i: self.recording_error.emit(cam, msg)
            )
            self._recorders.append(recorder)

    def start_recording(
        self,
        match_id: Optional[int] = None,
        frame_sizes: Optional[list[tuple[int, int]]] = None
    ) -> bool:
        """
        Start recording from all cameras.

        Args:
            match_id: Optional match ID for filename
            frame_sizes: Optional list of frame sizes per camera

        Returns:
            True if all cameras started successfully
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_started = True
        output_paths = []

        for i, recorder in enumerate(self._recorders):
            filename = f"match_{match_id}_cam{i}_{timestamp}" if match_id else f"recording_cam{i}_{timestamp}"
            frame_size = frame_sizes[i] if frame_sizes and i < len(frame_sizes) else None

            if recorder.start_recording(filename=filename, frame_size=frame_size):
                output_paths.append(recorder.output_path)
            else:
                all_started = False

        if output_paths:
            self.recording_started.emit(output_paths)

        return all_started

    def stop_recording(self) -> list[str]:
        """
        Stop recording on all cameras.

        Returns:
            List of output file paths
        """
        output_paths = []
        total_duration = 0

        for recorder in self._recorders:
            path = recorder.stop_recording()
            if path:
                output_paths.append(path)
                total_duration = max(total_duration, recorder.duration)

        self.recording_stopped.emit(output_paths, total_duration)
        return output_paths

    def pause_recording(self) -> None:
        """Pause all recordings."""
        for recorder in self._recorders:
            recorder.pause_recording()

    def resume_recording(self) -> None:
        """Resume all recordings."""
        for recorder in self._recorders:
            recorder.resume_recording()

    @Slot(list)
    def write_frames(self, frames: list) -> None:
        """
        Write frames from all cameras.

        Connect to MultiCameraCapture.frames_ready signal.

        Args:
            frames: List of (camera_id, frame) tuples
        """
        for camera_id, frame in frames:
            if camera_id < len(self._recorders) and frame is not None:
                self._recorders[camera_id].write_frame(frame)

    def get_recorder(self, camera_id: int) -> Optional[MatchRecorder]:
        """Get recorder for a specific camera."""
        if 0 <= camera_id < len(self._recorders):
            return self._recorders[camera_id]
        return None
