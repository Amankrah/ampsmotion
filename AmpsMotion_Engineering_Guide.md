# AmpsMotion — Engineering Guide

## Desktop Scoring System for AmpeSports

**Version:** 1.0  
**Stack:** Python · PySide6 · SQLite · OpenCV  
**Target Platforms:** Windows 10+, macOS 12+, Ubuntu 22.04+

---

## 1. Executive Summary

AmpsMotion is a desktop application that digitises the officiating workflow for AmpeSports — a Ghanaian indigenous sport built on rhythmic foot-tapping exchanges ("bouts"). The software serves three audiences simultaneously:

- **Ampfres (Officials):** Set up matches/fixtures, record Opa/Oshi calls and scores in real-time, manage timers, track fouls/violations, handle substitutions and eliminations.
- **Audience / Broadcast:** A second-screen live scoreboard that displays the current match state, scores, round info, and player standings.
- **Video Assistant Ampfre (VAR):** Camera feed integration with instant-replay and highlight-clipping capabilities.

The application must faithfully encode all three game modes defined in the Official AmpeSports Rules (April 2024): **1 vs 1**, **Team vs Team (Shooter Mode)**, and **Tournament**.

---

## 2. Domain Model — AmpeSports Rules Digest

This section distils the rulebook into the data structures and state machines the application must implement.

### 2.1 Core Terminology

| Term | Definition |
|---|---|
| **Ampes (AP)** | The unit of scoring |
| **Bout** | A single foot-thrust exchange between two players (one Opa, one Oshi) |
| **Round** | 1v1: 60 seconds of continuous play. Team: one full cycle through the player queue |
| **Game** | 15 rounds (Team vs Team mode only) |
| **Match** | 1v1: 5, 10, or 15 rounds. Team/Tournament: 3 games |
| **Opa (Opare)** | "Different legs" — players thrust different feet |
| **Oshi (Oshiwa)** | "Same legs" — players thrust the same foot |
| **Red Zone** | The 3m × 3m centre area where bouts take place |
| **AmpsKourt** | The 20m × 25m playing court |
| **Ampfre** | An official (Master, Caller, Recorder, Timer, Counter, Video Assistant) |
| **Shooter Mode** | Team mode mechanic: winning team eliminates one opponent per round |

### 2.2 Game Modes

#### 2.2.1 — 1 vs 1 Mode

```
Match
 └─ 5 | 10 | 15 Rounds
      └─ Each round = 60 seconds of continuous bouts
         • 10-sec pause = automatic round loss
         • 2-min rest interval between rounds
         • Score: count of successful Opa/Oshi per player
         • Round winner: player with highest AP
Match winner: player with highest cumulative AP
```

**Scoring per bout:** When the Caller Ampfre announces the outcome (Opa or Oshi), one player wins 1 AP. The Recorder Ampfres independently tally Opa-wins and Oshi-wins for each player.

#### 2.2.2 — Team vs Team Mode (Shooter Mode)

```
Match
 └─ 3 Games
      └─ Each Game = 15 Rounds
           └─ Each Round = one cycle through the player queue
              • Round winner eliminates 1 opponent → +3 AP bonus
              • When ≤ 3 players remain, bonus changes:
                  1st eliminated  → +5 AP
                  2nd eliminated  → +10 AP
                  Last eliminated → +15 AP
Teams: 15 players each, max 5 substitutions per match
```

**Player queue movement:** Players occupy Boxes 1–15 across 5 lanes. After playing in the Red Zone (Box 1), the player cycles to Box 15 and works back down. Eliminated players exit via the Exit Lane.

#### 2.2.3 — Tournament Mode

Follows Team vs Team rules with a bracket structure: Group stages → Round of 16 → Quarter-finals → Semi-finals → Final.

### 2.3 Officials Required

| Role | Count | Responsibility |
|---|---|---|
| Master Ampfre | 1 | Oversees all, master recorder, announces scores, declares winner |
| Caller Ampfre | 1 | Calls "Opa" or "Oshi" for each bout |
| Recorder Ampfre | 2 | Independent score recorders (one per player/team) |
| Timer | 1 | Calls START/STOP, manages 60-sec rounds (1v1) |
| Counter | 1 | Counts total bouts per round |
| Video Assistant Ampfre | 1 | Manages camera/replay technology |

### 2.4 Fouls & Violations

| Type | Trigger | Penalty |
|---|---|---|
| Delay of Game | Not ready when called | Warning → −1 AP on repeat |
| Excessive Contact | Shoving, tripping, obstruction | Warning → −3 AP on repeat |
| Illegal Foot Thrust | Deceptive thrust | Loss of bout |
| Encroachment | Crossing centre line | Bout awarded to opponent |
| Illegal Substitution | Unauthorized or mid-round sub | Loss of round |
| Improper Positioning | Wrong box at round start | Round awarded to opponent |
| Re-entry After Elimination | Eliminated player re-enters | Round loss; repeat → −3 AP then match elimination |
| Unsportsmanlike Conduct | Verbal abuse, taunting | Warning → penalty → disqualification |
| Intentional Foul | Deliberate foul for advantage | Immediate disqualification |
| Equipment Tampering | Altering equipment | Disqualification |

### 2.5 Age Categories

| Category | Ages |
|---|---|
| Juvenile (a) | 6–12 |
| Juvenile (b) | 13–17 |
| Young Adults (a) | 18–29 |
| Young Adults (b) | 30–39 |
| Middle-aged Adults (a) | 40–49 |
| Middle-aged Adults (b) | 50–59 |
| Old Adults | 60+ |

---

## 3. System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AmpsMotion Desktop App                   │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │  Ampfre       │  │  Audience     │  │  VAR / Replay     │  │
│  │  Console      │  │  Display      │  │  Control          │  │
│  │  (PySide6)    │  │  (PySide6     │  │  (PySide6 +       │  │
│  │               │  │   2nd window)  │  │   OpenCV)         │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────────┘  │
│         │                 │                  │               │
│  ┌──────▼─────────────────▼──────────────────▼────────────┐  │
│  │              Event Bus (Qt Signals / QObject)           │  │
│  └──────┬─────────────────┬──────────────────┬────────────┘  │
│         │                 │                  │               │
│  ┌──────▼───────┐  ┌──────▼───────┐  ┌──────▼────────────┐  │
│  │  Scoring      │  │  Match        │  │  Camera            │  │
│  │  Engine        │  │  Manager      │  │  Manager           │  │
│  │               │  │               │  │  (OpenCV)          │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬────────────┘  │
│         │                 │                  │               │
│  ┌──────▼─────────────────▼──────────────────▼────────────┐  │
│  │              Data Layer (SQLAlchemy + SQLite)            │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
   ┌───────────┐
   │  SQLite    │
   │  Database  │
   └───────────┘
```

### 3.1 Design Principles

- **Separation of Concerns:** GUI shells are thin presenters. All game logic lives in the Scoring Engine and Match Manager.
- **Event-Driven:** The Qt signal/slot mechanism is used as the primary inter-module communication bus. Every scoring action emits a signal that both the Ampfre Console and Audience Display consume.
- **Offline-First:** All data persists to a local SQLite database. No internet connection required during a match.
- **Multi-Window:** The Audience Display runs as a separate `QMainWindow` that can be dragged to a second monitor or projector. It is read-only and auto-updates via signals.
- **Replay Buffer:** OpenCV captures camera frames into a circular ring buffer. The VAR operator can scrub, slow-mo, and clip segments.

---

## 4. Technology Stack

| Layer | Technology | Justification |
|---|---|---|
| Language | Python 3.11+ | Rapid development, rich ecosystem |
| GUI Framework | PySide6 (Qt 6) | Native look on all platforms, multi-window, rich widgets, multimedia |
| Database | SQLite via SQLAlchemy 2.0 | Zero-config, embedded, sufficient for single-event workloads |
| ORM | SQLAlchemy 2.0 (declarative) | Type-safe models, migrations via Alembic |
| Camera / Video | OpenCV (`cv2`) + PySide6 QMediaPlayer | Frame capture, replay processing, format transcoding |
| Timer Precision | `QTimer` + `QElapsedTimer` | Sub-100ms precision for round timing |
| Packaging | PyInstaller / Nuitka | Single-file executable distribution |
| Testing | pytest + pytest-qt | GUI widget testing with Qt event loop |
| Linting / Typing | ruff + mypy | Code quality enforcement |

### 4.1 Python Package Dependencies

```
# requirements.txt
PySide6>=6.6
SQLAlchemy>=2.0
alembic>=1.13
opencv-python-headless>=4.9
numpy>=1.26
pydantic>=2.5        # data validation for scoring events
appdirs>=1.4         # cross-platform config/data paths
pytest>=8.0
pytest-qt>=4.3
ruff>=0.3
mypy>=1.8
pyinstaller>=6.3     # for distribution builds
```

---

## 5. Project Structure

```
ampsmotion/
├── main.py                        # Entry point
├── app.py                         # QApplication setup, window management
├── config.py                      # Settings, paths, constants
│
├── models/                        # SQLAlchemy ORM + Pydantic schemas
│   ├── __init__.py
│   ├── base.py                    # DeclarativeBase, engine, session factory
│   ├── player.py                  # Player model
│   ├── team.py                    # Team model
│   ├── match.py                   # Match, Game, Round models
│   ├── bout.py                    # Bout model (individual foot-thrust record)
│   ├── official.py                # Ampfre/Official model
│   ├── tournament.py              # Tournament bracket model
│   ├── foul.py                    # Foul/Violation records
│   └── schemas.py                 # Pydantic validation schemas
│
├── engine/                        # Core game logic (no GUI imports)
│   ├── __init__.py
│   ├── scoring.py                 # ScoringEngine — AP calculation, bonus logic
│   ├── match_manager.py           # MatchManager — state machine for match lifecycle
│   ├── timer.py                   # RoundTimer — precision countdown
│   ├── rules.py                   # Rule enforcement, foul/violation penalties
│   └── tournament_bracket.py      # Bracket generation and progression
│
├── gui/                           # PySide6 UI layer
│   ├── __init__.py
│   ├── main_window.py             # Main application window (Ampfre Console)
│   ├── widgets/
│   │   ├── match_setup.py         # Match/fixture creation wizard
│   │   ├── team_roster.py         # Team/player management panel
│   │   ├── scoring_panel.py       # Live bout recording (Opa/Oshi buttons)
│   │   ├── round_timer.py         # Visual countdown timer widget
│   │   ├── scoreboard.py          # Compact score summary in Ampfre Console
│   │   ├── foul_panel.py          # Foul/violation recording
│   │   ├── substitution_panel.py  # Substitution management
│   │   ├── court_visualizer.py    # AmpsKourt 2D representation
│   │   └── tournament_bracket.py  # Visual bracket display
│   ├── audience_display.py        # Full-screen second-window scoreboard
│   ├── replay_control.py          # VAR replay panel
│   ├── camera_feed.py             # Live camera preview widget
│   ├── styles/
│   │   ├── theme.py               # Color palette, fonts
│   │   └── ampsmotion.qss         # Qt stylesheet
│   └── resources/
│       ├── icons/                  # App icons, foul icons, etc.
│       └── fonts/                  # Custom fonts
│
├── camera/                        # Camera integration layer
│   ├── __init__.py
│   ├── capture.py                 # OpenCV camera capture thread
│   ├── ring_buffer.py             # Circular frame buffer for replay
│   ├── replay_engine.py           # Scrub, slow-mo, clip export
│   └── recorder.py                # Full-match recording to file
│
├── services/                      # Application services
│   ├── __init__.py
│   ├── event_bus.py               # Central QObject signal hub
│   ├── export.py                  # PDF scoresheet, CSV stats export
│   └── backup.py                  # Database backup utility
│
├── migrations/                    # Alembic migration scripts
│   ├── env.py
│   └── versions/
│
├── tests/
│   ├── test_scoring.py
│   ├── test_match_manager.py
│   ├── test_rules.py
│   ├── test_timer.py
│   └── test_gui/
│       ├── test_scoring_panel.py
│       └── test_audience_display.py
│
├── scripts/
│   ├── seed_demo_data.py          # Populate DB with demo match data
│   └── build.py                   # PyInstaller build script
│
├── alembic.ini
├── pyproject.toml
└── README.md
```

---

## 6. Database Schema

### 6.1 Entity-Relationship Overview

```
Tournament 1──N Match
Match 1──N Game
Game 1──N Round
Round 1──N Bout
Match N──1 Team (home)
Match N──1 Team (away)
Team 1──N Player
Match N──N Official (via match_officials)
Round 1──N FoulRecord
Match 1──N Substitution
```

### 6.2 SQLAlchemy Models

```python
# models/base.py
from sqlalchemy.orm import DeclarativeBase, MappedAsDataclass
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

class Base(DeclarativeBase, MappedAsDataclass):
    pass

engine = create_engine("sqlite:///ampsmotion.db", echo=False)
SessionLocal = sessionmaker(bind=engine)
```

```python
# models/player.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Integer, ForeignKey, Enum as SAEnum
import enum
from .base import Base

class AgeCategory(enum.Enum):
    JUVENILE_A = "Juvenile (a) 6-12"
    JUVENILE_B = "Juvenile (b) 13-17"
    YOUNG_ADULT_A = "Young Adults (a) 18-29"
    YOUNG_ADULT_B = "Young Adults (b) 30-39"
    MIDDLE_AGED_A = "Middle-aged Adults (a) 40-49"
    MIDDLE_AGED_B = "Middle-aged Adults (b) 50-59"
    OLD_ADULT = "Old Adults 60+"

class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    jersey_number: Mapped[int] = mapped_column(Integer)
    age: Mapped[int] = mapped_column(Integer)
    age_category: Mapped[AgeCategory] = mapped_column(SAEnum(AgeCategory))
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), default=None)

    team: Mapped["Team"] = relationship(back_populates="players", default=None)
```

```python
# models/team.py
class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    abbreviation: Mapped[str] = mapped_column(String(5))
    captain_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"), default=None
    )

    players: Mapped[list["Player"]] = relationship(
        back_populates="team", default_factory=list
    )
```

```python
# models/match.py
import enum
from datetime import datetime

class GameMode(enum.Enum):
    ONE_VS_ONE = "1v1"
    TEAM_VS_TEAM = "team_vs_team"
    TOURNAMENT = "tournament"

class MatchStatus(enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    PROTESTED = "protested"

class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    game_mode: Mapped[GameMode] = mapped_column(SAEnum(GameMode))
    status: Mapped[MatchStatus] = mapped_column(
        SAEnum(MatchStatus), default=MatchStatus.SCHEDULED
    )
    total_rounds: Mapped[int] = mapped_column(Integer)  # 5, 10, or 15

    # 1v1 mode
    player1_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"), default=None
    )
    player2_id: Mapped[int | None] = mapped_column(
        ForeignKey("players.id"), default=None
    )

    # Team mode
    home_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), default=None
    )
    away_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("teams.id"), default=None
    )

    # Tournament reference
    tournament_id: Mapped[int | None] = mapped_column(
        ForeignKey("tournaments.id"), default=None
    )

    toss_winner: Mapped[str | None] = mapped_column(String(10), default=None)
    toss_choice: Mapped[str | None] = mapped_column(String(10), default=None)

    started_at: Mapped[datetime | None] = mapped_column(default=None)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)

    winner_score: Mapped[int] = mapped_column(Integer, default=0)
    loser_score: Mapped[int] = mapped_column(Integer, default=0)

    games: Mapped[list["Game"]] = relationship(default_factory=list)
```

```python
# models/bout.py
class BoutResult(enum.Enum):
    OPA = "opa"     # Different legs — one player wins
    OSHI = "oshi"   # Same legs — one player wins

class Bout(Base):
    __tablename__ = "bouts"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    round_id: Mapped[int] = mapped_column(ForeignKey("rounds.id"))
    sequence: Mapped[int] = mapped_column(Integer)  # bout number within round
    caller_result: Mapped[BoutResult] = mapped_column(SAEnum(BoutResult))
    winner_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    loser_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    timestamp: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)
```

```python
# models/foul.py
class FoulType(enum.Enum):
    DELAY_OF_GAME = "delay_of_game"
    EXCESSIVE_CONTACT = "excessive_contact"
    ILLEGAL_FOOT_THRUST = "illegal_foot_thrust"
    ENCROACHMENT = "encroachment"
    ILLEGAL_SUBSTITUTION = "illegal_substitution"
    IMPROPER_POSITIONING = "improper_positioning"
    REENTRY_AFTER_ELIMINATION = "reentry_after_elimination"
    UNSPORTSMANLIKE_CONDUCT = "unsportsmanlike_conduct"
    INTENTIONAL_FOUL = "intentional_foul"
    EQUIPMENT_TAMPERING = "equipment_tampering"

class PenaltyAction(enum.Enum):
    WARNING = "warning"
    AP_DEDUCTION = "ap_deduction"
    BOUT_LOSS = "bout_loss"
    ROUND_LOSS = "round_loss"
    DISQUALIFICATION = "disqualification"

class FoulRecord(Base):
    __tablename__ = "foul_records"

    id: Mapped[int] = mapped_column(init=False, primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"))
    round_id: Mapped[int | None] = mapped_column(
        ForeignKey("rounds.id"), default=None
    )
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"))
    foul_type: Mapped[FoulType] = mapped_column(SAEnum(FoulType))
    penalty: Mapped[PenaltyAction] = mapped_column(SAEnum(PenaltyAction))
    ap_deducted: Mapped[int] = mapped_column(Integer, default=0)
    notes: Mapped[str | None] = mapped_column(String(500), default=None)
    timestamp: Mapped[datetime] = mapped_column(default_factory=datetime.utcnow)
```

---

## 7. Scoring Engine — Core Game Logic

The scoring engine is the heart of AmpsMotion. It runs independently of the GUI and encapsulates all AmpeSports rules.

### 7.1 State Machine

```
                    ┌──────────────┐
                    │   IDLE       │
                    └──────┬───────┘
                           │ setup_match()
                    ┌──────▼───────┐
                    │   SETUP      │ ← Rosters, officials, toss
                    └──────┬───────┘
                           │ start_match()
          ┌────────────────▼────────────────┐
          │           MATCH_ACTIVE           │
          │  ┌────────────────────────────┐  │
          │  │       ROUND_ACTIVE         │  │
          │  │  ┌──────────────────────┐  │  │
          │  │  │   BOUT_IN_PROGRESS   │  │  │
          │  │  │  (awaiting Opa/Oshi  │  │  │
          │  │  │   call from Caller)  │  │  │
          │  │  └──────────┬───────────┘  │  │
          │  │             │ record_bout() │  │
          │  │  ┌──────────▼───────────┐  │  │
          │  │  │   BOUT_RESOLVED      │  │  │
          │  │  │  (AP awarded)        │  │  │
          │  │  └──────────┬───────────┘  │  │
          │  │             │               │  │
          │  │    [more bouts?]            │  │
          │  │      yes → loop             │  │
          │  │      no  ↓                  │  │
          │  └────────────┬───────────────┘  │
          │               │ end_round()      │
          │  ┌────────────▼───────────────┐  │
          │  │     ROUND_COMPLETE          │  │
          │  │  (eliminations in team mode) │  │
          │  └────────────┬───────────────┘  │
          │               │                  │
          │     [more rounds?]               │
          │       yes → ROUND_ACTIVE         │
          │       no  ↓                      │
          └────────────────┬────────────────┘
                           │
                    ┌──────▼───────┐
                    │  COMPLETED   │
                    └──────────────┘

        At any point: PAUSED ←→ (any active state)
                      PROTESTED (after COMPLETED)
```

### 7.2 ScoringEngine Class

```python
# engine/scoring.py
from PySide6.QtCore import QObject, Signal
from models.match import GameMode
from models.bout import BoutResult

class ScoreUpdate:
    """Immutable snapshot of the current score state."""
    def __init__(self, player1_ap: int, player2_ap: int,
                 player1_opa: int, player1_oshi: int,
                 player2_opa: int, player2_oshi: int,
                 current_round: int, total_rounds: int,
                 bout_count: int, round_time_remaining: float,
                 home_eliminations: int = 0, away_eliminations: int = 0):
        self.player1_ap = player1_ap
        self.player2_ap = player2_ap
        self.player1_opa = player1_opa
        self.player1_oshi = player1_oshi
        self.player2_opa = player2_opa
        self.player2_oshi = player2_oshi
        self.current_round = current_round
        self.total_rounds = total_rounds
        self.bout_count = bout_count
        self.round_time_remaining = round_time_remaining
        self.home_eliminations = home_eliminations
        self.away_eliminations = away_eliminations


class ScoringEngine(QObject):
    """
    Core scoring logic for all AmpeSports game modes.
    Emits Qt Signals so GUI layers can react without polling.
    """

    # Signals
    score_updated = Signal(ScoreUpdate)
    round_started = Signal(int)          # round number
    round_ended = Signal(int, str)       # round number, winner
    bout_recorded = Signal(dict)         # bout details
    player_eliminated = Signal(int, int) # player_id, team_id
    foul_applied = Signal(dict)          # foul details
    match_completed = Signal(dict)       # final results
    timer_tick = Signal(float)           # seconds remaining

    # Team mode bonus constants
    TEAM_ROUND_WIN_BONUS = 3
    ENDGAME_BONUSES = {1: 5, 2: 10, 3: 15}  # elimination order → bonus

    def __init__(self, game_mode: GameMode, total_rounds: int):
        super().__init__()
        self.game_mode = game_mode
        self.total_rounds = total_rounds
        self._reset_state()

    def _reset_state(self):
        self._p1_ap = 0
        self._p2_ap = 0
        self._p1_opa_count = 0
        self._p1_oshi_count = 0
        self._p2_opa_count = 0
        self._p2_oshi_count = 0
        self._current_round = 0
        self._bout_count = 0
        self._round_active = False
        self._home_roster: list[int] = []   # active player IDs
        self._away_roster: list[int] = []
        self._home_eliminated: list[int] = []
        self._away_eliminated: list[int] = []

    def record_bout(self, result: BoutResult, winner_id: int, loser_id: int):
        """
        Called by the Ampfre Console when the Caller announces
        Opa or Oshi and the Master Ampfre identifies the winner.
        """
        if not self._round_active:
            raise RuntimeError("Cannot record bout outside an active round")

        self._bout_count += 1

        # Tally Opa/Oshi counts and award 1 AP
        if result == BoutResult.OPA:
            if winner_id == self._p1_id:
                self._p1_opa_count += 1
                self._p1_ap += 1
            else:
                self._p2_opa_count += 1
                self._p2_ap += 1
        else:  # OSHI
            if winner_id == self._p1_id:
                self._p1_oshi_count += 1
                self._p1_ap += 1
            else:
                self._p2_oshi_count += 1
                self._p2_ap += 1

        self.bout_recorded.emit({
            "round": self._current_round,
            "bout": self._bout_count,
            "result": result.value,
            "winner_id": winner_id,
            "loser_id": loser_id,
        })
        self._emit_score_update()

    def apply_foul_penalty(self, player_id: int, foul_type, ap_deduction: int):
        """Deduct AP as a foul penalty."""
        if player_id == self._p1_id:
            self._p1_ap = max(0, self._p1_ap - ap_deduction)
        else:
            self._p2_ap = max(0, self._p2_ap - ap_deduction)
        self._emit_score_update()

    def eliminate_player(self, player_id: int, from_team: str):
        """
        Team mode: Remove a player after a round loss.
        Awards bonus AP based on how many players remain.
        """
        if from_team == "home":
            self._home_roster.remove(player_id)
            self._home_eliminated.append(player_id)
            remaining = len(self._home_roster)
        else:
            self._away_roster.remove(player_id)
            self._away_eliminated.append(player_id)
            remaining = len(self._away_roster)

        # Calculate bonus
        if remaining > 3:
            bonus = self.TEAM_ROUND_WIN_BONUS  # +3 AP
        else:
            elim_order = 3 - remaining  # 1st, 2nd, or 3rd
            bonus = self.ENDGAME_BONUSES.get(elim_order, self.TEAM_ROUND_WIN_BONUS)

        # Award bonus to the winning team
        winning_team = "away" if from_team == "home" else "home"
        if winning_team == "home":
            self._p1_ap += bonus
        else:
            self._p2_ap += bonus

        self.player_eliminated.emit(player_id, 0)
        self._emit_score_update()

    def _emit_score_update(self):
        update = ScoreUpdate(
            player1_ap=self._p1_ap,
            player2_ap=self._p2_ap,
            player1_opa=self._p1_opa_count,
            player1_oshi=self._p1_oshi_count,
            player2_opa=self._p2_opa_count,
            player2_oshi=self._p2_oshi_count,
            current_round=self._current_round,
            total_rounds=self.total_rounds,
            bout_count=self._bout_count,
            round_time_remaining=0,  # set by timer
            home_eliminations=len(self._home_eliminated),
            away_eliminations=len(self._away_eliminated),
        )
        self.score_updated.emit(update)
```

### 7.3 Round Timer

```python
# engine/timer.py
from PySide6.QtCore import QObject, Signal, QTimer, QElapsedTimer

class RoundTimer(QObject):
    """
    Precision countdown timer for 1v1 rounds (60 seconds).
    Emits tick every 100ms and fires round_expired when time runs out.
    Also enforces the 10-second pause rule.
    """

    tick = Signal(float)           # seconds remaining
    round_expired = Signal()       # time's up
    pause_violation = Signal(int)  # player_id who paused > 10s

    ROUND_DURATION_MS = 60_000     # 60 seconds
    TICK_INTERVAL_MS = 100         # update every 100ms
    PAUSE_LIMIT_MS = 10_000        # 10-second inactivity threshold

    def __init__(self):
        super().__init__()
        self._timer = QTimer(self)
        self._timer.setInterval(self.TICK_INTERVAL_MS)
        self._timer.timeout.connect(self._on_tick)
        self._elapsed = QElapsedTimer()
        self._remaining_ms = self.ROUND_DURATION_MS
        self._last_bout_time_ms = 0

    def start(self):
        self._remaining_ms = self.ROUND_DURATION_MS
        self._elapsed.start()
        self._last_bout_time_ms = 0
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def pause(self):
        self._remaining_ms -= self._elapsed.elapsed()
        self._timer.stop()

    def resume(self):
        self._elapsed.restart()
        self._timer.start()

    def notify_bout_activity(self):
        """Call this every time a bout is recorded to reset pause timer."""
        self._last_bout_time_ms = self._elapsed.elapsed()

    def _on_tick(self):
        elapsed = self._elapsed.elapsed()
        remaining = max(0, self.ROUND_DURATION_MS - elapsed) / 1000.0
        self.tick.emit(remaining)

        # Check 10-second pause rule
        since_last = elapsed - self._last_bout_time_ms
        if since_last >= self.PAUSE_LIMIT_MS:
            self.pause_violation.emit(-1)  # caller determines which player

        if remaining <= 0:
            self._timer.stop()
            self.round_expired.emit()
```

---

## 8. GUI Design — PySide6 Screens

### 8.1 Main Window Layout (Ampfre Console)

The main window uses a `QStackedWidget` to navigate between functional screens. A persistent sidebar provides quick navigation.

```python
# gui/main_window.py
from PySide6.QtWidgets import (
    QMainWindow, QStackedWidget, QDockWidget,
    QToolBar, QStatusBar
)
from PySide6.QtCore import Qt

class MainWindow(QMainWindow):
    """Primary Ampfre Console — the operator's control panel."""

    def __init__(self, event_bus):
        super().__init__()
        self.setWindowTitle("AmpsMotion — Ampfre Console")
        self.setMinimumSize(1280, 800)
        self.event_bus = event_bus

        # Central stacked widget
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Screens
        self.match_setup_screen = MatchSetupWidget(event_bus)
        self.scoring_screen = ScoringScreen(event_bus)
        self.tournament_screen = TournamentBracketWidget(event_bus)
        self.history_screen = MatchHistoryWidget(event_bus)

        self.stack.addWidget(self.match_setup_screen)   # index 0
        self.stack.addWidget(self.scoring_screen)        # index 1
        self.stack.addWidget(self.tournament_screen)     # index 2
        self.stack.addWidget(self.history_screen)        # index 3

        # Toolbar
        self._build_toolbar()

        # Dock: Audience Display launcher
        self._build_docks()

        # Status bar
        self.statusBar().showMessage("Ready")

    def _build_toolbar(self):
        tb = QToolBar("Navigation")
        tb.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, tb)
        tb.addAction("Setup Match", lambda: self.stack.setCurrentIndex(0))
        tb.addAction("Live Scoring", lambda: self.stack.setCurrentIndex(1))
        tb.addAction("Tournament", lambda: self.stack.setCurrentIndex(2))
        tb.addAction("Match History", lambda: self.stack.setCurrentIndex(3))
        tb.addSeparator()
        tb.addAction("Open Audience Display", self._open_audience_display)
        tb.addAction("Open VAR Panel", self._open_var_panel)
```

### 8.2 Match Setup Wizard

A multi-step form that guides the Ampfre through match configuration.

```
┌─────────────────────────────────────────────────┐
│              MATCH SETUP WIZARD                  │
├─────────────────────────────────────────────────┤
│                                                  │
│  Step 1: Game Mode                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐     │
│  │  1 vs 1  │ │ Team vs  │ │  Tournament  │     │
│  │          │ │  Team    │ │              │     │
│  └──────────┘ └──────────┘ └──────────────┘     │
│                                                  │
│  Step 2: Match Configuration                     │
│  Rounds: [5 ▼] [10] [15]                        │
│  Age Category: [Young Adults (a) 18-29  ▼]      │
│                                                  │
│  Step 3: Players / Teams                         │
│  ┌─────────────────┐  ┌─────────────────┐       │
│  │ Player 1 / Home  │  │ Player 2 / Away │       │
│  │ [Name........]   │  │ [Name........]  │       │
│  │ [Add Player  ]   │  │ [Add Player  ]  │       │
│  │ [Import Team ]   │  │ [Import Team ]  │       │
│  └─────────────────┘  └─────────────────┘       │
│                                                  │
│  Step 4: Officials                               │
│  Master Ampfre:    [______________]              │
│  Caller Ampfre:    [______________]              │
│  Recorder 1:       [______________]              │
│  Recorder 2:       [______________]              │
│  Timer:            [______________]              │
│  Counter:          [______________]              │
│  Video Assistant:  [______________]              │
│                                                  │
│  Step 5: Toss                                    │
│  Winner: [⊙ Home  ⊙ Away]                       │
│  Choice: [⊙ Opa   ⊙ Oshi]                       │
│                                                  │
│         [◀ Back]          [Start Match ▶]        │
└─────────────────────────────────────────────────┘
```

### 8.3 Live Scoring Panel (Ampfre Console)

This is the primary screen during a match. Designed for speed — the Master Ampfre must record bouts as fast as they happen (sub-second reaction).

```
┌─────────────────────────────────────────────────────────────┐
│  ROUND 3 / 15                    ⏱ 00:42                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   PLAYER 1 (Opa)          │          PLAYER 2 (Oshi)        │
│   ┌─────────────────┐     │     ┌─────────────────┐         │
│   │                 │     │     │                 │         │
│   │      24 AP      │     │     │      18 AP      │         │
│   │                 │     │     │                 │         │
│   └─────────────────┘     │     └─────────────────┘         │
│   Opa wins: 14            │     Opa wins: 10                │
│   Oshi wins: 10           │     Oshi wins: 8                │
│                            │                                 │
│  ┌───────────────────────────────────────────────────┐      │
│  │           BOUT RECORDING (Caller Input)            │      │
│  │                                                    │      │
│  │   ┌──────────────┐       ┌──────────────┐         │      │
│  │   │     OPA      │       │    OSHI      │         │      │
│  │   │  (Diff Leg)  │       │  (Same Leg)  │         │      │
│  │   └──────────────┘       └──────────────┘         │      │
│  │                                                    │      │
│  │   Winner:  [⊙ P1]  [⊙ P2]                        │      │
│  │                                                    │      │
│  │   [ ✓ Record Bout ]    [ ⚠ Foul ]    [ ↩ Undo ]  │      │
│  └───────────────────────────────────────────────────┘      │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │  Pause   │  │  Resume  │  │End Round │  │ End Match  │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│                                                              │
│  BOUT LOG:                                                   │
│  #47  OPA   → P1 wins  (00:41)                              │
│  #46  OSHI  → P2 wins  (00:39)                              │
│  #45  OPA   → P1 wins  (00:37)                              │
│  ...                                                         │
└─────────────────────────────────────────────────────────────┘
```

**Keyboard shortcuts (critical for speed):**

| Key | Action |
|---|---|
| `O` | Record Opa |
| `S` | Record Oshi |
| `1` | Winner = Player 1 / Home |
| `2` | Winner = Player 2 / Away |
| `Enter` | Confirm & record bout |
| `Ctrl+Z` | Undo last bout |
| `Space` | Pause / Resume timer |
| `F` | Open Foul dialog |
| `Ctrl+E` | End round |

### 8.4 Team Mode Extensions

When in Team vs Team mode, the scoring panel adds:

- **Player Queue Display:** A visual representation of Boxes 1–15 showing which player is in each position, who is currently in the Red Zone, and who has been eliminated.
- **Elimination Button:** After a round win, the winning team selects which opponent to eliminate.
- **Substitution Panel:** Accessible via the sidebar, tracks the 5-substitution limit.

### 8.5 Audience Display (Second Window)

A separate `QMainWindow` designed to be full-screened on a projector or broadcast monitor. Purely read-only — it subscribes to signals from the `ScoringEngine`.

```python
# gui/audience_display.py
from PySide6.QtWidgets import QMainWindow, QLabel, QVBoxLayout, QWidget
from PySide6.QtCore import Qt, Slot

class AudienceDisplay(QMainWindow):
    """
    Full-screen scoreboard for spectators.
    Connects to ScoringEngine signals for live updates.
    """

    def __init__(self, scoring_engine):
        super().__init__()
        self.setWindowTitle("AmpsMotion — Live Scoreboard")
        self.setWindowFlags(Qt.WindowType.Window)

        self.scoring_engine = scoring_engine

        # Build UI
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.match_title = QLabel("AmpeSports — 1 vs 1")
        self.match_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.match_title.setStyleSheet("font-size: 48px; font-weight: bold;")

        self.score_display = QLabel("0 — 0")
        self.score_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.score_display.setStyleSheet("font-size: 120px; font-weight: bold;")

        self.round_info = QLabel("Round 1 / 15")
        self.round_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.round_info.setStyleSheet("font-size: 36px;")

        self.timer_display = QLabel("01:00")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.timer_display.setStyleSheet("font-size: 72px; color: #00CC00;")

        layout.addWidget(self.match_title)
        layout.addWidget(self.score_display)
        layout.addWidget(self.round_info)
        layout.addWidget(self.timer_display)

        # Connect signals
        self.scoring_engine.score_updated.connect(self._on_score_updated)
        self.scoring_engine.timer_tick.connect(self._on_timer_tick)

    @Slot(ScoreUpdate)
    def _on_score_updated(self, update: ScoreUpdate):
        self.score_display.setText(
            f"{update.player1_ap}  —  {update.player2_ap}"
        )
        self.round_info.setText(
            f"Round {update.current_round} / {update.total_rounds}"
        )

    @Slot(float)
    def _on_timer_tick(self, remaining: float):
        mins = int(remaining) // 60
        secs = int(remaining) % 60
        self.timer_display.setText(f"{mins:02d}:{secs:02d}")
        # Colour red when < 10 seconds
        if remaining < 10:
            self.timer_display.setStyleSheet(
                "font-size: 72px; color: #FF3333;"
            )

    def enter_fullscreen(self):
        self.showFullScreen()
```

**Audience Display design goals:** High contrast (dark background, bright text), large fonts visible from 30+ metres, animated score transitions, team colours prominently displayed.

---

## 9. Camera Integration & Replay System

### 9.1 Architecture

```
Camera(s)                  Ring Buffer              Replay Engine
┌────────┐  frames/sec   ┌──────────────┐        ┌──────────────┐
│ USB/IP │ ────────────► │  Circular     │ ◄───── │  VAR Panel   │
│ Camera │   OpenCV       │  Frame Store  │  seek  │  (GUI)       │
└────────┘  QThread       │  (N seconds)  │        │  Slow-mo     │
                          └──────┬───────┘        │  Clip export │
                                 │                └──────────────┘
                                 ▼
                          ┌──────────────┐
                          │  MP4 File    │ (full match recording)
                          │  (optional)  │
                          └──────────────┘
```

### 9.2 Camera Capture Thread

```python
# camera/capture.py
import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

class CaptureThread(QThread):
    """
    Runs an OpenCV VideoCapture in a background thread.
    Emits frames as numpy arrays for display and buffering.
    """

    frame_ready = Signal(np.ndarray)  # BGR frame
    error = Signal(str)

    def __init__(self, source: int | str = 0, fps: int = 30):
        super().__init__()
        self.source = source  # 0 = default webcam, or RTSP URL
        self.target_fps = fps
        self._running = False

    def run(self):
        cap = cv2.VideoCapture(self.source)
        if not cap.isOpened():
            self.error.emit(f"Cannot open camera: {self.source}")
            return

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

    def stop(self):
        self._running = False
        self.wait()
```

### 9.3 Ring Buffer for Instant Replay

```python
# camera/ring_buffer.py
import numpy as np
from collections import deque
from dataclasses import dataclass
from datetime import datetime

@dataclass
class TimestampedFrame:
    frame: np.ndarray
    timestamp: datetime
    frame_number: int

class ReplayBuffer:
    """
    Circular buffer holding the last N seconds of video frames.
    The VAR operator can scrub backward through this buffer.
    """

    def __init__(self, max_seconds: int = 120, fps: int = 30):
        self.max_frames = max_seconds * fps
        self._buffer: deque[TimestampedFrame] = deque(maxlen=self.max_frames)
        self._frame_counter = 0

    def push(self, frame: np.ndarray):
        self._frame_counter += 1
        self._buffer.append(TimestampedFrame(
            frame=frame,
            timestamp=datetime.utcnow(),
            frame_number=self._frame_counter,
        ))

    def get_last_n_seconds(self, seconds: int, fps: int = 30) -> list[TimestampedFrame]:
        count = min(seconds * fps, len(self._buffer))
        return list(self._buffer)[-count:]

    def get_frame_at(self, index: int) -> TimestampedFrame | None:
        if 0 <= index < len(self._buffer):
            return self._buffer[index]
        return None

    @property
    def size(self) -> int:
        return len(self._buffer)
```

### 9.4 Replay Controls (VAR Panel)

The VAR panel provides:

- **Live feed** from one or more cameras
- **Instant replay** — scrub backward up to the buffer duration (default 120s)
- **Slow motion** — 0.25×, 0.5×, 0.75× playback speed
- **Frame-by-frame** — step forward/backward one frame at a time
- **Clip export** — mark in/out points and export to MP4 for highlights
- **Full match recording** — continuous write to disk via `cv2.VideoWriter`

```python
# gui/replay_control.py  (simplified structure)
class ReplayControlWidget(QWidget):
    """VAR operator's replay panel."""

    def __init__(self, capture_thread, replay_buffer):
        super().__init__()
        # Video display area
        self.video_label = QLabel()
        # Scrub slider
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        # Speed controls
        self.speed_group = QButtonGroup()
        for speed in [0.25, 0.5, 0.75, 1.0]:
            btn = QPushButton(f"{speed}×")
            self.speed_group.addButton(btn)
        # Frame step buttons
        self.prev_frame_btn = QPushButton("◀ Frame")
        self.next_frame_btn = QPushButton("Frame ▶")
        # Clip controls
        self.mark_in_btn = QPushButton("Mark In")
        self.mark_out_btn = QPushButton("Mark Out")
        self.export_clip_btn = QPushButton("Export Clip")
```

---

## 10. Event Bus — Inter-Module Communication

```python
# services/event_bus.py
from PySide6.QtCore import QObject, Signal

class EventBus(QObject):
    """
    Central signal hub. All modules connect to this single object
    rather than directly to each other, enabling loose coupling.
    """

    # Match lifecycle
    match_created = Signal(dict)
    match_started = Signal(int)         # match_id
    match_paused = Signal(int)
    match_resumed = Signal(int)
    match_completed = Signal(dict)

    # Scoring
    bout_recorded = Signal(dict)
    score_updated = Signal(object)      # ScoreUpdate
    round_started = Signal(int)
    round_ended = Signal(int, str)

    # Team mode
    player_eliminated = Signal(int, int)
    substitution_made = Signal(dict)

    # Fouls
    foul_recorded = Signal(dict)

    # Timer
    timer_tick = Signal(float)
    timer_expired = Signal()

    # Camera
    camera_frame = Signal(object)       # numpy array
    replay_requested = Signal(int)      # seconds to go back

    # UI navigation
    navigate_to = Signal(str)           # screen name
```

**Usage pattern:**

```python
# In ScoringEngine
self.event_bus.bout_recorded.emit(bout_data)

# In AudienceDisplay
self.event_bus.score_updated.connect(self._on_score_updated)

# In ReplayControl
self.event_bus.replay_requested.connect(self._load_replay)
```

---

## 11. Data Export — Scoresheet Generation

The application must produce official scoresheets matching the formats defined in the rulebook.

### 11.1 1 vs 1 Mode Scoresheet

Export fields: match info, per-round breakdown (Opa count, Oshi count, total AP per player, round winner), final result, officiating crew.

### 11.2 Team vs Team / Tournament Scoresheet

Export fields: match info, per-game per-round breakdown, shooter mode results (eliminations per game, AP per game, game winner), final result, officiating crew.

### 11.3 Implementation

```python
# services/export.py
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph

class ScoresheetExporter:
    """Generate PDF scoresheets matching the official AmpeSports format."""

    def export_1v1(self, match_data: dict, filepath: str):
        doc = SimpleDocTemplate(filepath, pagesize=A4)
        elements = []
        # Header
        elements.append(Paragraph("AmpeSports — 1 vs 1 Scoresheet"))
        # Match info table
        # Round results table
        # Final result
        # Officials table
        doc.build(elements)

    def export_team(self, match_data: dict, filepath: str):
        # Similar structure with shooter mode section
        ...

    def export_csv(self, match_data: dict, filepath: str):
        """Raw data export for analysis."""
        ...
```

---

## 12. Tournament Bracket Management

```python
# engine/tournament_bracket.py

class TournamentBracket:
    """
    Manages tournament progression:
    Group Stage → Round of 16 → Quarters → Semis → Final
    """

    STAGES = [
        "group_stage",
        "round_of_16",
        "quarter_final",
        "semi_final",
        "final",
    ]

    def __init__(self, teams: list[dict]):
        self.teams = teams
        self.brackets: dict[str, list[dict]] = {}
        self._generate_groups()

    def _generate_groups(self):
        """Seed teams into groups using serpentine seeding."""
        ...

    def advance_winner(self, match_id: int, winner_team_id: int):
        """Move the winner to the next stage bracket slot."""
        ...

    def get_current_stage(self) -> str:
        ...

    def get_bracket_display(self) -> dict:
        """Return a nested dict suitable for the bracket visualization widget."""
        ...
```

---

## 13. Styling & Theming

### 13.1 Colour Palette

```python
# gui/styles/theme.py

COLORS = {
    # Primary — inspired by Ghana flag colours
    "primary_red": "#CE1126",       # Red zone, fouls
    "primary_gold": "#FCD116",      # Score highlights, AP
    "primary_green": "#006B3F",     # Success, round win
    "primary_black": "#000000",     # Background

    # Neutral
    "surface": "#1A1A2E",           # Dark surface
    "surface_light": "#16213E",     # Card backgrounds
    "text_primary": "#FFFFFF",
    "text_secondary": "#A0A0B0",

    # Semantic
    "danger": "#FF4444",
    "warning": "#FFB74D",
    "success": "#4CAF50",
    "info": "#42A5F5",

    # Team
    "team_home": "#2196F3",
    "team_away": "#FF5722",
}
```

### 13.2 Qt Stylesheet

```css
/* gui/styles/ampsmotion.qss */

QMainWindow {
    background-color: #1A1A2E;
}

QLabel {
    color: #FFFFFF;
    font-family: "Segoe UI", "SF Pro Display", "Ubuntu", sans-serif;
}

QPushButton {
    background-color: #16213E;
    color: #FFFFFF;
    border: 1px solid #333355;
    border-radius: 8px;
    padding: 12px 24px;
    font-size: 16px;
    font-weight: bold;
}

QPushButton:hover {
    background-color: #1A2744;
    border-color: #FCD116;
}

QPushButton:pressed {
    background-color: #0F1A30;
}

QPushButton#opa_button {
    background-color: #006B3F;
    font-size: 24px;
    min-height: 80px;
}

QPushButton#oshi_button {
    background-color: #CE1126;
    font-size: 24px;
    min-height: 80px;
}

/* Audience display score */
QLabel#score_display {
    font-size: 120px;
    font-weight: bold;
    color: #FCD116;
}

QLabel#timer_display {
    font-size: 72px;
    font-family: "JetBrains Mono", "Consolas", monospace;
}
```

---

## 14. Application Entry Point

```python
# main.py
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from app import AmpsMotionApp

def main():
    # High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)

    # Load stylesheet
    with open("gui/styles/ampsmotion.qss", "r") as f:
        app.setStyleSheet(f.read())

    # Initialize application controller
    amps_app = AmpsMotionApp()
    amps_app.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

```python
# app.py
from PySide6.QtCore import QObject
from services.event_bus import EventBus
from engine.scoring import ScoringEngine
from engine.match_manager import MatchManager
from camera.capture import CaptureThread
from camera.ring_buffer import ReplayBuffer
from gui.main_window import MainWindow
from gui.audience_display import AudienceDisplay
from models.base import Base, engine as db_engine

class AmpsMotionApp(QObject):
    """Top-level application controller. Wires everything together."""

    def __init__(self):
        super().__init__()

        # Create database tables
        Base.metadata.create_all(db_engine)

        # Core services
        self.event_bus = EventBus()
        self.match_manager = MatchManager(self.event_bus)
        self.replay_buffer = ReplayBuffer(max_seconds=120, fps=30)

        # Camera (lazy init — only when VAR panel opened)
        self.capture_thread = None

        # GUI
        self.main_window = MainWindow(self.event_bus)
        self.audience_display = None  # created on demand

    def show(self):
        self.main_window.show()

    def open_audience_display(self):
        if self.audience_display is None:
            self.audience_display = AudienceDisplay(self.event_bus)
        self.audience_display.enter_fullscreen()

    def start_camera(self, source=0):
        if self.capture_thread is None:
            self.capture_thread = CaptureThread(source=source)
            self.capture_thread.frame_ready.connect(self.replay_buffer.push)
            self.capture_thread.start()
```

---

## 15. Development Roadmap

### Phase 1 — MVP (Weeks 1–4)

| Week | Deliverable |
|---|---|
| 1 | Project scaffold, DB schema, models, migrations |
| 2 | ScoringEngine + RoundTimer for 1v1 mode, unit tests |
| 3 | Ampfre Console GUI: match setup + live scoring panel |
| 4 | Audience Display window, PDF scoresheet export |

### Phase 2 — Team Mode (Weeks 5–7)

| Week | Deliverable |
|---|---|
| 5 | Team roster management, player queue logic, Box/Lane system |
| 6 | Shooter Mode scoring with elimination cascades |
| 7 | Team-mode GUI extensions, substitution panel |

### Phase 3 — Tournament & VAR (Weeks 8–10)

| Week | Deliverable |
|---|---|
| 8 | Tournament bracket engine + bracket visualization |
| 9 | Camera capture integration, ring buffer, live preview |
| 10 | Replay controls (scrub, slow-mo, clip export) |

### Phase 4 — Polish & Distribution (Weeks 11–12)

| Week | Deliverable |
|---|---|
| 11 | Theming, animations, keyboard shortcuts, accessibility |
| 12 | PyInstaller packaging, installers for Windows/macOS/Linux, user manual |



Great question. The sections in the guide are organized by *topic* (for reference), but you should build by *dependency order* — which is closer to the phased roadmap in Section 15, with some important sequencing within each phase. Here's a practical walkthrough:

## Build Order (What Depends on What)

**The core principle:** always build from the inside out — data models first, then engine logic, then GUI on top. Never start with the GUI.

### Phase 1 — Foundation (Week 1–2)

Start here because *everything* else depends on these layers:

**Step 1: Project scaffold + database models (Section 5 + 6)**
Set up your `pyproject.toml`, install dependencies, create the folder structure, then write all your SQLAlchemy models (`Player`, `Team`, `Match`, `Game`, `Round`, `Bout`, `FoulRecord`). Run Alembic to generate your first migration. This is your ground truth — if the data model is wrong, everything built on top will be wrong.

**Step 2: Event Bus (Section 10)**
Build `EventBus` early because both the engine and GUI layers will import it. It's a small file but it's the glue between everything.

**Step 3: Scoring Engine — 1v1 only (Section 7)**
Write `ScoringEngine` and `RoundTimer` for the simplest mode first. This is pure Python with no GUI — you can test it entirely with pytest. Get `record_bout()`, `apply_foul_penalty()`, the state machine transitions, and the 60-second timer working correctly before touching any PySide6 code.

**Step 4: Unit tests for the engine (Section 16.1)**
Write the tests from Section 16.1 now, not later. The scoring engine is the most critical piece — if it miscounts AP, the whole application is broken. These tests are fast to run and will save you enormous debugging time later.

### Phase 2 — First GUI (Week 3–4)

Now that you have a working engine with tests, put a face on it:

**Step 5: Main window shell + Match Setup wizard (Section 8.1 + 8.2)**
Build the `QMainWindow` with the `QStackedWidget` and the match setup form. At this point, you can create a match in the database, assign players, assign officials, and record the toss result. No live scoring yet — just setup.

**Step 6: Live Scoring Panel — 1v1 (Section 8.3)**
This is the most interaction-heavy screen. Wire the Opa/Oshi buttons and winner selection to `ScoringEngine.record_bout()`. Implement the keyboard shortcuts early — they're not a nice-to-have, they're essential because Ampfres need to record bouts as fast as they happen. Connect the `RoundTimer` to the timer display widget.

**Step 7: Audience Display (Section 8.5)**
Build the second `QMainWindow`. Connect it to the same `EventBus` signals. Test multi-monitor support using `QApplication.screens()`. At this point you have a working 1v1 scoring system end-to-end.

**Step 8: Scoresheet export — 1v1 (Section 11)**
Add PDF export so a completed 1v1 match can produce the official scoresheet. This closes the loop on the 1v1 workflow.

### Phase 3 — Team Mode (Week 5–7)

This is the most complex phase because Shooter Mode adds elimination cascades and the Box/Lane queue system:

**Step 9: Extend the Scoring Engine for Team mode (Section 7.2)**
Add `eliminate_player()`, the endgame bonus logic (+5/+10/+15), roster management, and the substitution counter (max 5). Write tests for every edge case — especially the transition from normal elimination (+3 AP) to endgame bonuses (when ≤ 3 players remain).

**Step 10: Team GUI extensions (Section 8.4)**
Build the player queue visualizer (Boxes 1–15), the elimination selection UI, and the substitution panel. This is the most complex GUI work because you need to visually represent player positions across the AmpsKourt lanes.

**Step 11: Scoresheet export — Team mode (Section 11.2)**
Extend the exporter for the Shooter Mode scoresheet format.

### Phase 4 — Tournament (Week 8)

**Step 12: Tournament bracket engine + GUI (Section 12 + Section 8, tournament widget)**
Build bracket generation (group stage seeding, progression logic) and the visual bracket display. Tournament mode reuses all Team vs Team logic — it just adds the bracket wrapper around multiple matches.

### Phase 5 — Camera / VAR (Week 9–10)

This is deliberately last because it's an *addon* — the scoring system must work perfectly without cameras:

**Step 13: Camera capture thread (Section 9.2)**
Get OpenCV reading frames on a `QThread` and displaying them in a preview widget.

**Step 14: Ring buffer + replay controls (Section 9.3 + 9.4)**
Build the circular buffer, then the VAR panel with scrub, slow-mo, frame-step, and clip export.

### Phase 6 — Polish & Ship (Week 11–12)

**Step 15: Theming (Section 13)**
Apply the QSS stylesheet, Ghana-inspired colour palette, and ensure the Audience Display looks great on projectors.

**Step 16: Packaging**
PyInstaller builds for Windows/macOS/Linux.

---

## Why This Order and Not the Section Order

The document sections are grouped by *architecture layer* (models, engine, GUI, camera) which makes sense for reference. But if you built by section order, you'd write all the models including Tournament before you even test whether a single bout records correctly. The build order above follows a different principle: **get the smallest complete workflow working end-to-end as early as possible**, then widen it.

By the end of Week 4 you'll have a working 1v1 scoring app with a live audience display and PDF export. That's something you can demo and get feedback on, even though Team mode and cameras aren't built yet. Each subsequent phase adds a complete capability rather than leaving half-finished layers everywhere.

---

## 16. Testing Strategy

### 16.1 Unit Tests

```python
# tests/test_scoring.py
import pytest
from engine.scoring import ScoringEngine
from models.match import GameMode
from models.bout import BoutResult

class TestScoringEngine1v1:

    def setup_method(self):
        self.engine = ScoringEngine(GameMode.ONE_VS_ONE, total_rounds=5)
        self.engine._p1_id = 1
        self.engine._p2_id = 2
        self.engine._round_active = True

    def test_opa_win_awards_1ap(self):
        self.engine.record_bout(BoutResult.OPA, winner_id=1, loser_id=2)
        assert self.engine._p1_ap == 1
        assert self.engine._p1_opa_count == 1

    def test_oshi_win_awards_1ap(self):
        self.engine.record_bout(BoutResult.OSHI, winner_id=2, loser_id=1)
        assert self.engine._p2_ap == 1
        assert self.engine._p2_oshi_count == 1

    def test_foul_deduction(self):
        self.engine._p1_ap = 10
        self.engine.apply_foul_penalty(1, "excessive_contact", 3)
        assert self.engine._p1_ap == 7

    def test_foul_cannot_go_negative(self):
        self.engine._p1_ap = 1
        self.engine.apply_foul_penalty(1, "excessive_contact", 3)
        assert self.engine._p1_ap == 0


class TestScoringEngineTeamMode:

    def setup_method(self):
        self.engine = ScoringEngine(GameMode.TEAM_VS_TEAM, total_rounds=15)
        self.engine._home_roster = list(range(1, 16))
        self.engine._away_roster = list(range(16, 31))
        self.engine._p1_id = "home"
        self.engine._p2_id = "away"

    def test_elimination_awards_3ap_when_more_than_3_remain(self):
        initial_home_ap = self.engine._p1_ap
        self.engine.eliminate_player(16, "away")
        assert self.engine._p1_ap == initial_home_ap + 3

    def test_endgame_elimination_bonuses(self):
        # Reduce away to 3 players
        self.engine._away_roster = [16, 17, 18]
        self.engine._p1_ap = 0

        self.engine.eliminate_player(16, "away")  # 1st of 3 → +5
        assert self.engine._p1_ap == 5

        self.engine.eliminate_player(17, "away")  # 2nd of 3 → +10
        assert self.engine._p1_ap == 15

        self.engine.eliminate_player(18, "away")  # last → +15
        assert self.engine._p1_ap == 30
```

### 16.2 GUI Tests with pytest-qt

```python
# tests/test_gui/test_scoring_panel.py
from pytestqt.qtbot import QtBot
from gui.widgets.scoring_panel import ScoringPanel

def test_opa_button_emits_signal(qtbot):
    panel = ScoringPanel(event_bus=MockEventBus())
    qtbot.addWidget(panel)

    with qtbot.waitSignal(panel.bout_submitted, timeout=1000):
        qtbot.mouseClick(panel.opa_button, Qt.MouseButton.LeftButton)
```

### 16.3 Integration Tests

End-to-end tests that simulate a full match from setup → scoring → completion → export, verifying that the database state, scoresheet output, and audience display all reflect the correct final scores.

---

## 17. Key Implementation Notes

### 17.1 Thread Safety

- OpenCV capture runs on a `QThread`. Frame data is passed to the main thread via `Signal(np.ndarray)`.
- Database writes should happen on the main thread or use a dedicated writer thread with a queue. SQLite does not support concurrent writes.
- The `ReplayBuffer` is written to by the capture thread and read by the GUI thread. Use a `threading.Lock` or Qt's `QMutex` around buffer access.

### 17.2 Performance Targets

| Metric | Target |
|---|---|
| Bout recording latency (key press → DB + display update) | < 50ms |
| Timer display refresh rate | 10 Hz (100ms) |
| Audience display update latency | < 100ms after bout recorded |
| Camera preview frame rate | 30 FPS |
| Replay scrub responsiveness | < 200ms per seek |
| Application startup time | < 3 seconds |

### 17.3 Data Integrity

- Every bout is persisted to SQLite immediately upon recording (WAL mode for performance).
- The two independent Recorder Ampfre tallies are stored separately and compared at round end. If they disagree, the application flags a discrepancy for review (matching the rulebook's reconciliation procedure).
- Match state is auto-saved on every significant event, enabling crash recovery.

### 17.4 Multi-Monitor Support

PySide6's `QScreen` API detects available monitors. The Audience Display should default to the secondary screen if one is connected:

```python
screens = QApplication.screens()
if len(screens) > 1:
    audience_display.setScreen(screens[1])
    audience_display.showFullScreen()
```

---

## 18. Glossary

| Term | Meaning |
|---|---|
| **AP** | Ampes — the scoring unit |
| **Ampfre** | Official / referee |
| **AmpsKourt** | The playing court (20m × 25m) |
| **Bout** | A single foot-thrust exchange |
| **Opa (Opare)** | "Different legs" call |
| **Oshi (Oshiwa)** | "Same legs" call |
| **Red Zone** | The 3m × 3m centre area where bouts occur |
| **Shooter Mode** | Team mode with player elimination |
| **VAR** | Video Assistant Ampfre — replay technology operator |

---

*This guide provides the architectural blueprint for AmpsMotion. Each section maps directly to implementation work and can be assigned to individual developers or sprints. The domain model in Section 2 should be treated as the authoritative rules reference alongside the Official AmpeSports Rule Book (April 2024).*
