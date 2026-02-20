"""
AmpsMotion Configuration

Centralized settings, paths, and constants for the application.
"""

from pathlib import Path
from dataclasses import dataclass
import appdirs


# Application info
APP_NAME = "AmpsMotion"
APP_AUTHOR = "AmpeSports"
APP_VERSION = "1.0.0"


@dataclass(frozen=True)
class Paths:
    """Application paths."""
    # Data directory (stores database, settings)
    data_dir: Path = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))

    # Config directory (stores user preferences)
    config_dir: Path = Path(appdirs.user_config_dir(APP_NAME, APP_AUTHOR))

    # Cache directory (stores temporary files)
    cache_dir: Path = Path(appdirs.user_cache_dir(APP_NAME, APP_AUTHOR))

    # Log directory
    log_dir: Path = Path(appdirs.user_log_dir(APP_NAME, APP_AUTHOR))

    @property
    def database(self) -> Path:
        return self.data_dir / "ampsmotion.db"

    @property
    def settings(self) -> Path:
        return self.config_dir / "settings.json"

    @property
    def replay_cache(self) -> Path:
        return self.cache_dir / "replays"

    @property
    def exports(self) -> Path:
        return self.data_dir / "exports"

    def ensure_directories(self) -> None:
        """Create all required directories."""
        for dir_path in [self.data_dir, self.config_dir, self.cache_dir,
                         self.log_dir, self.replay_cache, self.exports]:
            dir_path.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class TimerSettings:
    """Timer-related settings."""
    # 1v1 round duration in milliseconds
    round_duration_ms: int = 60_000  # 60 seconds

    # Rest interval between rounds in milliseconds
    rest_interval_ms: int = 120_000  # 2 minutes

    # Pause violation threshold in milliseconds
    pause_limit_ms: int = 10_000  # 10 seconds

    # Timer tick interval in milliseconds
    tick_interval_ms: int = 100

    # Warning thresholds in seconds
    warning_thresholds: tuple[int, ...] = (30, 10, 5)


@dataclass(frozen=True)
class TeamSettings:
    """Team mode settings."""
    # Maximum players per team
    max_players: int = 15

    # Maximum substitutions per match
    max_substitutions: int = 5

    # Number of games per team match
    games_per_match: int = 3

    # Rounds per game
    rounds_per_game: int = 15


@dataclass(frozen=True)
class CameraSettings:
    """Camera and replay settings."""
    # Default camera index
    default_camera: int = 0

    # Target FPS
    target_fps: int = 30

    # Replay buffer duration in seconds
    replay_buffer_seconds: int = 120

    # Supported video formats for export
    export_formats: tuple[str, ...] = ("mp4", "avi", "mkv")


@dataclass(frozen=True)
class UISettings:
    """UI-related settings."""
    # Minimum window size
    min_width: int = 1280
    min_height: int = 800

    # Font sizes
    score_font_size: int = 120
    timer_font_size: int = 72
    label_font_size: int = 16

    # Animation durations in milliseconds
    score_animation_ms: int = 300


# Singleton instances
PATHS = Paths()
TIMER_SETTINGS = TimerSettings()
TEAM_SETTINGS = TeamSettings()
CAMERA_SETTINGS = CameraSettings()
UI_SETTINGS = UISettings()


def init_config() -> None:
    """Initialize configuration and create required directories."""
    PATHS.ensure_directories()
