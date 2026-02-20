"""
Pydantic schemas for data validation.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from models.player import AgeCategory
from models.match import GameMode, MatchStatus
from models.bout import BoutResult
from models.foul import FoulType, PenaltyAction


# ============ Player Schemas ============

class PlayerCreate(BaseModel):
    """Schema for creating a new player."""
    name: str = Field(..., min_length=1, max_length=200)
    age: int = Field(..., ge=6, le=100)
    jersey_number: Optional[int] = Field(None, ge=1, le=99)
    team_id: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class PlayerResponse(BaseModel):
    """Schema for player response."""
    id: int
    name: str
    age: int
    jersey_number: Optional[int]
    age_category: AgeCategory
    team_id: Optional[int]
    is_active: bool
    is_eliminated: bool

    class Config:
        from_attributes = True


# ============ Team Schemas ============

class TeamCreate(BaseModel):
    """Schema for creating a new team."""
    name: str = Field(..., min_length=1, max_length=200)
    abbreviation: str = Field(..., min_length=2, max_length=5)
    primary_color: str = Field(default="#2196F3", pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(default="#FFFFFF", pattern=r"^#[0-9A-Fa-f]{6}$")


class TeamResponse(BaseModel):
    """Schema for team response."""
    id: int
    name: str
    abbreviation: str
    primary_color: str
    secondary_color: str
    player_count: int
    total_wins: int
    total_losses: int

    class Config:
        from_attributes = True


# ============ Match Schemas ============

class MatchCreate(BaseModel):
    """Schema for creating a new match."""
    game_mode: GameMode
    total_rounds: int = Field(..., ge=5, le=15)

    # 1v1 mode
    player1_id: Optional[int] = None
    player2_id: Optional[int] = None

    # Team mode
    home_team_id: Optional[int] = None
    away_team_id: Optional[int] = None

    @field_validator("total_rounds")
    @classmethod
    def valid_round_count(cls, v: int) -> int:
        if v not in [5, 10, 15]:
            raise ValueError("Total rounds must be 5, 10, or 15")
        return v


class MatchResponse(BaseModel):
    """Schema for match response."""
    id: int
    game_mode: GameMode
    status: MatchStatus
    total_rounds: int
    player1_total_ap: int
    player2_total_ap: int
    home_total_ap: int
    away_total_ap: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ============ Bout Schemas ============

class BoutCreate(BaseModel):
    """Schema for recording a bout."""
    round_id: int
    caller_result: BoutResult
    winner_id: int
    loser_id: int
    time_remaining_ms: Optional[int] = None


class BoutResponse(BaseModel):
    """Schema for bout response."""
    id: int
    round_id: int
    sequence: int
    caller_result: BoutResult
    winner_id: int
    loser_id: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ============ Foul Schemas ============

class FoulCreate(BaseModel):
    """Schema for recording a foul."""
    match_id: int
    round_id: Optional[int] = None
    player_id: int
    foul_type: FoulType
    notes: Optional[str] = Field(None, max_length=500)


class FoulResponse(BaseModel):
    """Schema for foul response."""
    id: int
    match_id: int
    player_id: int
    foul_type: FoulType
    penalty: PenaltyAction
    ap_deducted: int
    occurrence_number: int
    timestamp: datetime

    class Config:
        from_attributes = True


# ============ Score Update Schema ============

class ScoreUpdate(BaseModel):
    """
    Immutable snapshot of the current score state.
    Used for real-time updates to the GUI.
    """
    player1_ap: int = 0
    player2_ap: int = 0
    player1_opa_wins: int = 0
    player1_oshi_wins: int = 0
    player2_opa_wins: int = 0
    player2_oshi_wins: int = 0
    current_round: int = 0
    total_rounds: int = 0
    bout_count: int = 0
    round_time_remaining_ms: int = 0
    home_eliminations: int = 0
    away_eliminations: int = 0
    is_round_active: bool = False
    is_match_active: bool = False
