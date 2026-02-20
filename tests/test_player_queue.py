"""
Tests for the PlayerQueue class.

Verifies Box/Lane system, queue advancement, eliminations, and substitutions.
"""

import pytest
from engine.player_queue import PlayerQueue, PlayerPosition, Lane


class TestPlayerQueueSetup:
    """Tests for queue initialization and roster setup."""

    def test_setup_roster_creates_positions(self):
        """Setting up roster creates correct player positions."""
        queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 16)]

        queue.setup_roster(roster)

        assert len(queue.players) == 15
        assert queue.players[0].box_number == 1
        assert queue.players[0].is_active
        assert queue.players[14].box_number == 15

    def test_setup_roster_assigns_lanes(self):
        """Roster setup assigns correct lanes to boxes."""
        queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 16)]

        queue.setup_roster(roster)

        # Lane 1: Boxes 1-3
        assert queue.players[0].lane == Lane.LANE_1
        assert queue.players[2].lane == Lane.LANE_1
        # Lane 2: Boxes 4-6
        assert queue.players[3].lane == Lane.LANE_2
        # Lane 5: Boxes 13-15
        assert queue.players[14].lane == Lane.LANE_5

    def test_setup_roster_rejects_too_many_players(self):
        """Roster setup rejects more than 15 players."""
        queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 20)]

        with pytest.raises(ValueError):
            queue.setup_roster(roster)

    def test_active_player_is_box_1(self):
        """Active player is always the one in Box 1."""
        queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 16)]

        queue.setup_roster(roster)

        active = queue.active_player
        assert active is not None
        assert active.player_id == 1
        assert active.box_number == 1
        assert active.is_active


class TestPlayerQueueAdvancement:
    """Tests for queue advancement after bouts."""

    def setup_method(self):
        """Set up a queue with 15 players."""
        self.queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 16)]
        self.queue.setup_roster(roster)

    def test_advance_queue_moves_box_1_to_end(self):
        """Advancing queue moves Box 1 player to Box 15."""
        original_active = self.queue.active_player
        assert original_active.player_id == 1

        self.queue.advance_queue()

        # Player 1 should now be at Box 15
        player_1 = next(p for p in self.queue.players if p.player_id == 1)
        assert player_1.box_number == 15
        assert not player_1.is_active

    def test_advance_queue_new_active_player(self):
        """After advancement, a new player is active in Box 1."""
        self.queue.advance_queue()

        active = self.queue.active_player
        assert active is not None
        assert active.player_id == 2
        assert active.box_number == 1

    def test_advance_queue_all_shift_forward(self):
        """All players shift forward by one box."""
        # Get original positions
        original_positions = {p.player_id: p.box_number for p in self.queue.players}

        self.queue.advance_queue()

        for player in self.queue.players:
            original_box = original_positions[player.player_id]
            if original_box == 1:
                # Was at Box 1, now at Box 15
                assert player.box_number == 15
            else:
                # Moved forward by 1
                assert player.box_number == original_box - 1

    def test_multiple_advancements_cycle(self):
        """After 15 advancements, players return to original positions."""
        original = {p.player_id: p.box_number for p in self.queue.players}

        for _ in range(15):
            self.queue.advance_queue()

        # All players back to original positions
        for player in self.queue.players:
            assert player.box_number == original[player.player_id]


class TestPlayerQueueElimination:
    """Tests for player elimination."""

    def setup_method(self):
        """Set up a queue with 15 players."""
        self.queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 16)]
        self.queue.setup_roster(roster)

    def test_eliminate_player_removes_from_active(self):
        """Eliminating a player removes them from active roster."""
        assert self.queue.active_count == 15

        self.queue.eliminate_player(5)

        assert self.queue.active_count == 14
        assert 5 in self.queue.eliminated

    def test_eliminate_player_marks_as_eliminated(self):
        """Eliminated player has correct state."""
        self.queue.eliminate_player(5)

        player_5 = next(p for p in self.queue.players if p.player_id == 5)
        assert player_5.is_eliminated
        assert player_5.lane == Lane.EXIT
        assert player_5.box_number == 0

    def test_eliminate_compacts_queue(self):
        """After elimination, remaining players fill gaps."""
        self.queue.eliminate_player(5)

        # Get active players
        active_boxes = [p.box_number for p in self.queue.players if not p.is_eliminated]
        active_boxes.sort()

        # Should be contiguous 1-14
        assert active_boxes == list(range(1, 15))

    def test_is_team_eliminated(self):
        """Team elimination detected when all players eliminated."""
        # Eliminate all but one
        for i in range(1, 15):
            self.queue.eliminate_player(i)

        assert not self.queue.is_team_eliminated

        # Eliminate the last one
        self.queue.eliminate_player(15)

        assert self.queue.is_team_eliminated
        assert self.queue.active_count == 0


class TestPlayerQueueSubstitution:
    """Tests for player substitution."""

    def setup_method(self):
        """Set up a queue with 15 players."""
        self.queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 16)]
        self.queue.setup_roster(roster)

    def test_substitute_replaces_player(self):
        """Substitution replaces one player with another."""
        success = self.queue.substitute_player(5, 100, "New Player")

        assert success
        assert self.queue.substitution_count == 1

        # Player 100 should be in the queue
        player_100 = next((p for p in self.queue.players if p.player_id == 100), None)
        assert player_100 is not None
        assert player_100.player_name == "New Player"

    def test_cannot_substitute_active_player(self):
        """Cannot substitute the player in Box 1 (Red Zone)."""
        # Player 1 is active
        success = self.queue.substitute_player(1, 100, "New Player")

        assert not success

    def test_max_substitutions_enforced(self):
        """Cannot exceed 5 substitutions."""
        # Make 5 valid substitutions - use players at the back of the queue
        for i in range(5):
            # Get a player that's NOT active (not box 1)
            non_active = [p for p in self.queue.players if not p.is_active and not p.is_eliminated]
            if non_active:
                player_out = non_active[-1].player_id  # Pick one from the back
                self.queue.substitute_player(player_out, 100 + i, f"Sub {i}")

        assert self.queue.substitution_count == 5
        assert not self.queue.can_substitute()

        # 6th should fail
        non_active = [p for p in self.queue.players if not p.is_active and not p.is_eliminated]
        if non_active:
            player_out = non_active[-1].player_id
            success = self.queue.substitute_player(player_out, 200, "Extra Sub")
            assert not success

    def test_remaining_substitutions(self):
        """Track remaining substitutions correctly."""
        assert self.queue.remaining_substitutions() == 5

        # Find a non-active player to substitute
        non_active = [p for p in self.queue.players if not p.is_active]
        player_out_id = non_active[0].player_id

        success = self.queue.substitute_player(
            player_out_id,
            100,
            "Sub 1"
        )

        assert success
        assert self.queue.remaining_substitutions() == 4


class TestPlayerQueueQueries:
    """Tests for queue query methods."""

    def setup_method(self):
        """Set up a queue with 15 players."""
        self.queue = PlayerQueue(team_id=1, team_name="Test Team")
        roster = [(i, f"Player {i}") for i in range(1, 16)]
        self.queue.setup_roster(roster)

    def test_get_player_at_box(self):
        """Get player at specific box position."""
        player = self.queue.get_player_at_box(5)

        assert player is not None
        assert player.player_id == 5
        assert player.box_number == 5

    def test_get_player_at_empty_box(self):
        """Returns None for empty box."""
        # Eliminate some players to create gaps after compaction
        self.queue.eliminate_player(1)
        self.queue.eliminate_player(2)

        # After elimination, boxes 1-13 are filled, 14-15 are "empty"
        player = self.queue.get_player_at_box(15)

        assert player is None

    def test_get_queue_state(self):
        """Get queue state returns correct format."""
        state = self.queue.get_queue_state()

        assert len(state) == 15
        assert state[0]["box_number"] == 1
        assert state[0]["is_active"]
        assert "player_id" in state[0]
        assert "player_name" in state[0]

    def test_get_eliminated_players(self):
        """Get eliminated players list."""
        self.queue.eliminate_player(5)
        self.queue.eliminate_player(10)

        eliminated = self.queue.get_eliminated_players()

        assert len(eliminated) == 2
        player_ids = [p["player_id"] for p in eliminated]
        assert 5 in player_ids
        assert 10 in player_ids
