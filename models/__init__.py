"""
AmpsMotion Database Models

SQLAlchemy ORM models for the AmpeSports scoring system.
"""

from models.base import Base, engine, SessionLocal, get_session, init_db
from models.player import Player, AgeCategory
from models.team import Team
from models.match import Match, Game, Round, GameMode, MatchStatus
from models.bout import Bout, BoutResult
from models.foul import FoulRecord, FoulType, PenaltyAction, FOUL_PENALTIES
from models.official import Official, OfficialRole
from models.tournament import Tournament

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_session",
    "init_db",
    "Player",
    "AgeCategory",
    "Team",
    "Match",
    "Game",
    "Round",
    "GameMode",
    "MatchStatus",
    "Bout",
    "BoutResult",
    "FoulRecord",
    "FoulType",
    "PenaltyAction",
    "FOUL_PENALTIES",
    "Official",
    "OfficialRole",
    "Tournament",
]
