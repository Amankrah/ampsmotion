"""
AmpsMotion GUI Widgets

Reusable widget components for the Ampfre Console.
"""

from gui.widgets.match_setup import MatchSetupWidget
from gui.widgets.scoring_panel import ScoringScreen, ScoringPanel
from gui.widgets.round_timer import RoundTimerWidget
from gui.widgets.scoreboard import ScoreboardWidget
from gui.widgets.match_history import MatchHistoryWidget
from gui.widgets.substitution_panel import SubstitutionPanel, TeamSubstitutionWidget
from gui.widgets.court_visualizer import CourtVisualizer, CompactCourtVisualizer
from gui.widgets.tournament_bracket import (
    TournamentBracketWidget,
    KnockoutBracketWidget,
    GroupTable,
    MatchCard,
)

__all__ = [
    "MatchSetupWidget",
    "ScoringScreen",
    "ScoringPanel",
    "RoundTimerWidget",
    "ScoreboardWidget",
    "MatchHistoryWidget",
    "SubstitutionPanel",
    "TeamSubstitutionWidget",
    "CourtVisualizer",
    "CompactCourtVisualizer",
    "TournamentBracketWidget",
    "KnockoutBracketWidget",
    "GroupTable",
    "MatchCard",
]
