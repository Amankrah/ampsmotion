"""
Player Queue System for Team Mode

Manages the Box/Lane system for Shooter Mode:
- 15 players per team
- 5 lanes with boxes 1-15
- Players cycle from Box 1 (Red Zone) to Box 15 after playing
- Eliminated players exit via Exit Lane
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Lane(Enum):
    """The 5 lanes on the AmpsKourt."""
    LANE_1 = 1  # Boxes 1-3
    LANE_2 = 2  # Boxes 4-6
    LANE_3 = 3  # Boxes 7-9
    LANE_4 = 4  # Boxes 10-12
    LANE_5 = 5  # Boxes 13-15
    EXIT = 6    # Eliminated players


@dataclass
class PlayerPosition:
    """A player's position in the queue."""
    player_id: int
    player_name: str
    box_number: int  # 1-15, or 0 if eliminated
    lane: Lane
    is_eliminated: bool = False
    is_active: bool = False  # Currently in Red Zone (Box 1)


@dataclass
class PlayerQueue:
    """
    Manages the player queue for a team in Shooter Mode.

    The queue represents the Box/Lane system:
    - Box 1 is the Red Zone (active player)
    - Players cycle through boxes 1-15
    - After playing in Box 1, player moves to Box 15
    - Eliminated players exit the queue

    Attributes:
        team_id: The team's ID
        team_name: The team's name
        players: List of PlayerPosition objects
        eliminated: List of eliminated player IDs
        substitution_count: Number of substitutions made (max 5)
    """
    team_id: int
    team_name: str
    players: list[PlayerPosition] = field(default_factory=list)
    eliminated: list[int] = field(default_factory=list)
    substitution_count: int = 0

    MAX_PLAYERS = 15
    MAX_SUBSTITUTIONS = 5

    def setup_roster(self, roster: list[tuple[int, str]]) -> None:
        """
        Initialize the queue with a roster of players.

        Args:
            roster: List of (player_id, player_name) tuples, in playing order
        """
        if len(roster) > self.MAX_PLAYERS:
            raise ValueError(f"Roster cannot exceed {self.MAX_PLAYERS} players")

        self.players = []
        self.eliminated = []

        for i, (player_id, player_name) in enumerate(roster):
            box_number = i + 1
            lane = self._get_lane_for_box(box_number)
            is_active = (box_number == 1)

            self.players.append(PlayerPosition(
                player_id=player_id,
                player_name=player_name,
                box_number=box_number,
                lane=lane,
                is_eliminated=False,
                is_active=is_active,
            ))

    def _get_lane_for_box(self, box_number: int) -> Lane:
        """Determine which lane a box belongs to."""
        if box_number <= 0:
            return Lane.EXIT
        elif box_number <= 3:
            return Lane.LANE_1
        elif box_number <= 6:
            return Lane.LANE_2
        elif box_number <= 9:
            return Lane.LANE_3
        elif box_number <= 12:
            return Lane.LANE_4
        else:
            return Lane.LANE_5

    @property
    def active_player(self) -> Optional[PlayerPosition]:
        """Get the player currently in the Red Zone (Box 1)."""
        for player in self.players:
            if player.is_active and not player.is_eliminated:
                return player
        return None

    @property
    def active_count(self) -> int:
        """Number of players still in the game (not eliminated)."""
        return len([p for p in self.players if not p.is_eliminated])

    @property
    def is_team_eliminated(self) -> bool:
        """Check if all players have been eliminated."""
        return self.active_count == 0

    def advance_queue(self) -> None:
        """
        Advance the queue after a bout.
        The current Box 1 player moves to Box 15 (or the last available position).
        All other players shift down one box.
        """
        active_players = [p for p in self.players if not p.is_eliminated]
        if not active_players:
            return

        # Find the current active player
        current_active = self.active_player
        if not current_active:
            return

        # Shift all non-eliminated players forward
        for player in active_players:
            if player.box_number == 1:
                # Move from Box 1 to the end
                player.box_number = len(active_players)
                player.is_active = False
            else:
                # Shift forward
                player.box_number -= 1
                if player.box_number == 1:
                    player.is_active = True

            player.lane = self._get_lane_for_box(player.box_number)

    def eliminate_player(self, player_id: int) -> Optional[PlayerPosition]:
        """
        Eliminate a player from the queue.

        Args:
            player_id: The ID of the player to eliminate

        Returns:
            The eliminated PlayerPosition, or None if not found
        """
        for player in self.players:
            if player.player_id == player_id and not player.is_eliminated:
                player.is_eliminated = True
                player.is_active = False
                player.box_number = 0
                player.lane = Lane.EXIT
                self.eliminated.append(player_id)

                # Reorder remaining players
                self._compact_queue()

                return player
        return None

    def _compact_queue(self) -> None:
        """
        Reorder active players after an elimination.
        Ensures boxes 1-N are filled without gaps.
        """
        active_players = [p for p in self.players if not p.is_eliminated]
        active_players.sort(key=lambda p: p.box_number if p.box_number > 0 else float('inf'))

        for i, player in enumerate(active_players):
            player.box_number = i + 1
            player.lane = self._get_lane_for_box(player.box_number)
            player.is_active = (player.box_number == 1)

    def substitute_player(self, out_player_id: int, in_player_id: int,
                          in_player_name: str) -> bool:
        """
        Substitute one player for another.

        Args:
            out_player_id: Player being removed
            in_player_id: Player coming in
            in_player_name: Name of the incoming player

        Returns:
            True if substitution was successful, False otherwise
        """
        if self.substitution_count >= self.MAX_SUBSTITUTIONS:
            return False

        # Find the player being substituted out
        out_player = None
        for player in self.players:
            if player.player_id == out_player_id and not player.is_eliminated:
                out_player = player
                break

        if out_player is None:
            return False

        # Cannot substitute the active player (in Red Zone)
        if out_player.is_active:
            return False

        # Replace the player
        out_player.player_id = in_player_id
        out_player.player_name = in_player_name
        self.substitution_count += 1

        return True

    def get_player_at_box(self, box_number: int) -> Optional[PlayerPosition]:
        """Get the player at a specific box position."""
        for player in self.players:
            if player.box_number == box_number and not player.is_eliminated:
                return player
        return None

    def get_queue_state(self) -> list[dict]:
        """
        Get the current queue state for display.

        Returns:
            List of dicts with player info, sorted by box number
        """
        active_players = [p for p in self.players if not p.is_eliminated]
        active_players.sort(key=lambda p: p.box_number)

        return [
            {
                "player_id": p.player_id,
                "player_name": p.player_name,
                "box_number": p.box_number,
                "lane": p.lane.value,
                "is_active": p.is_active,
            }
            for p in active_players
        ]

    def get_eliminated_players(self) -> list[dict]:
        """Get list of eliminated players."""
        eliminated = [p for p in self.players if p.is_eliminated]
        return [
            {
                "player_id": p.player_id,
                "player_name": p.player_name,
            }
            for p in eliminated
        ]

    def can_substitute(self) -> bool:
        """Check if more substitutions are allowed."""
        return self.substitution_count < self.MAX_SUBSTITUTIONS

    def remaining_substitutions(self) -> int:
        """Get the number of remaining substitutions."""
        return self.MAX_SUBSTITUTIONS - self.substitution_count
