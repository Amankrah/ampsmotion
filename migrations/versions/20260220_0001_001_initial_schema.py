"""Initial schema - all AmpsMotion tables

Revision ID: 001
Revises:
Create Date: 2026-02-20

Creates all tables for the AmpsMotion scoring system:
- players: Individual players
- teams: Teams for team mode
- tournaments: Tournament brackets (Phase 4 placeholder)
- matches: Match records
- games: Games within team matches
- rounds: Rounds within games
- bouts: Individual foot-thrust exchanges
- foul_records: Foul/violation tracking
- officials: Officials (Ampfre)
- match_officials: Match-official association
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### Teams table ###
    op.create_table(
        'teams',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('abbreviation', sa.String(5), nullable=False),
        sa.Column('captain_id', sa.Integer(), nullable=True),
        sa.Column('primary_color', sa.String(7), server_default='#2196F3'),
        sa.Column('secondary_color', sa.String(7), server_default='#FFFFFF'),
        sa.Column('total_wins', sa.Integer(), server_default='0'),
        sa.Column('total_losses', sa.Integer(), server_default='0'),
        sa.Column('total_ap_scored', sa.Integer(), server_default='0'),
        sa.Column('total_ap_conceded', sa.Integer(), server_default='0'),
    )

    # ### Players table ###
    op.create_table(
        'players',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('jersey_number', sa.Integer(), nullable=True),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('age_category', sa.Enum(
            'JUVENILE_A', 'JUVENILE_B',
            'YOUNG_ADULT_A', 'YOUNG_ADULT_B',
            'MIDDLE_AGED_A', 'MIDDLE_AGED_B',
            'OLD_ADULT',
            name='agecategory'
        ), nullable=False),
        sa.Column('team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('is_eliminated', sa.Boolean(), server_default='0'),
    )

    # Add foreign key constraint for teams.captain_id after players table exists
    op.create_foreign_key(
        'fk_teams_captain_id',
        'teams', 'players',
        ['captain_id'], ['id'],
        use_alter=True
    )

    # ### Tournaments table ###
    op.create_table(
        'tournaments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('team_count', sa.Integer(), server_default='16'),
        sa.Column('current_stage', sa.String(50), server_default='group_stage'),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
        sa.Column('is_complete', sa.Boolean(), server_default='0'),
        sa.Column('winner_team_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # ### Matches table ###
    op.create_table(
        'matches',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('game_mode', sa.Enum(
            'ONE_VS_ONE', 'TEAM_VS_TEAM', 'TOURNAMENT',
            name='gamemode'
        ), nullable=False),
        sa.Column('status', sa.Enum(
            'SCHEDULED', 'IN_PROGRESS', 'PAUSED', 'COMPLETED', 'PROTESTED',
            name='matchstatus'
        ), server_default='SCHEDULED'),
        sa.Column('total_rounds', sa.Integer(), nullable=False),

        # 1v1 participants
        sa.Column('player1_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=True),
        sa.Column('player2_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=True),

        # Team participants
        sa.Column('home_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True),
        sa.Column('away_team_id', sa.Integer(), sa.ForeignKey('teams.id'), nullable=True),

        # Tournament reference
        sa.Column('tournament_id', sa.Integer(), sa.ForeignKey('tournaments.id'), nullable=True),
        sa.Column('tournament_stage', sa.String(50), nullable=True),

        # Toss
        sa.Column('toss_winner', sa.String(20), nullable=True),
        sa.Column('toss_choice', sa.String(10), nullable=True),

        # Timing
        sa.Column('scheduled_at', sa.DateTime(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),

        # Scores
        sa.Column('player1_total_ap', sa.Integer(), server_default='0'),
        sa.Column('player2_total_ap', sa.Integer(), server_default='0'),
        sa.Column('home_total_ap', sa.Integer(), server_default='0'),
        sa.Column('away_total_ap', sa.Integer(), server_default='0'),

        # Winner
        sa.Column('winner_id', sa.Integer(), nullable=True),

        # Team mode substitutions
        sa.Column('home_substitutions_used', sa.Integer(), server_default='0'),
        sa.Column('away_substitutions_used', sa.Integer(), server_default='0'),
        sa.Column('max_substitutions', sa.Integer(), server_default='5'),
    )

    # ### Games table ###
    op.create_table(
        'games',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id'), nullable=False),
        sa.Column('game_number', sa.Integer(), nullable=False),
        sa.Column('home_ap', sa.Integer(), server_default='0'),
        sa.Column('away_ap', sa.Integer(), server_default='0'),
        sa.Column('home_eliminations', sa.Integer(), server_default='0'),
        sa.Column('away_eliminations', sa.Integer(), server_default='0'),
        sa.Column('is_complete', sa.Boolean(), server_default='0'),
        sa.Column('winner', sa.String(10), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    # ### Rounds table ###
    op.create_table(
        'rounds',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('game_id', sa.Integer(), sa.ForeignKey('games.id'), nullable=False),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('opa_player_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=True),
        sa.Column('oshi_player_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=True),

        # 1v1 scores
        sa.Column('player1_ap', sa.Integer(), server_default='0'),
        sa.Column('player2_ap', sa.Integer(), server_default='0'),
        sa.Column('player1_opa_wins', sa.Integer(), server_default='0'),
        sa.Column('player1_oshi_wins', sa.Integer(), server_default='0'),
        sa.Column('player2_opa_wins', sa.Integer(), server_default='0'),
        sa.Column('player2_oshi_wins', sa.Integer(), server_default='0'),

        # Bout tracking
        sa.Column('bout_count', sa.Integer(), server_default='0'),

        # Timing
        sa.Column('duration_seconds', sa.Integer(), server_default='60'),
        sa.Column('actual_duration_ms', sa.Integer(), nullable=True),

        # Status
        sa.Column('is_complete', sa.Boolean(), server_default='0'),
        sa.Column('winner_id', sa.Integer(), nullable=True),
        sa.Column('winner_side', sa.String(10), nullable=True),

        # Timestamps
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),

        # Team mode: eliminated player
        sa.Column('eliminated_player_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=True),
    )

    # ### Bouts table ###
    op.create_table(
        'bouts',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('round_id', sa.Integer(), sa.ForeignKey('rounds.id'), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('caller_result', sa.Enum('OPA', 'OSHI', name='boutresult'), nullable=False),
        sa.Column('winner_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('loser_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('time_remaining_ms', sa.Integer(), nullable=True),
    )

    # ### Foul Records table ###
    op.create_table(
        'foul_records',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id'), nullable=False),
        sa.Column('round_id', sa.Integer(), sa.ForeignKey('rounds.id'), nullable=True),
        sa.Column('player_id', sa.Integer(), sa.ForeignKey('players.id'), nullable=False),
        sa.Column('foul_type', sa.Enum(
            'DELAY_OF_GAME', 'EXCESSIVE_CONTACT', 'ILLEGAL_FOOT_THRUST',
            'ENCROACHMENT', 'ILLEGAL_SUBSTITUTION', 'IMPROPER_POSITIONING',
            'REENTRY_AFTER_ELIMINATION', 'UNSPORTSMANLIKE_CONDUCT',
            'INTENTIONAL_FOUL', 'EQUIPMENT_TAMPERING',
            name='foultype'
        ), nullable=False),
        sa.Column('penalty', sa.Enum(
            'WARNING', 'AP_DEDUCTION', 'BOUT_LOSS', 'ROUND_LOSS', 'DISQUALIFICATION',
            name='penaltyaction'
        ), nullable=False),
        sa.Column('ap_deducted', sa.Integer(), server_default='0'),
        sa.Column('occurrence_number', sa.Integer(), server_default='1'),
        sa.Column('notes', sa.String(500), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
    )

    # ### Officials table ###
    op.create_table(
        'officials',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('primary_role', sa.Enum(
            'MASTER_AMPFRE', 'CALLER_AMPFRE', 'RECORDER_AMPFRE',
            'TIMER', 'COUNTER', 'VIDEO_ASSISTANT',
            name='officialrole'
        ), server_default='RECORDER_AMPFRE'),
        sa.Column('certification_level', sa.Integer(), server_default='1'),
        sa.Column('email', sa.String(200), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1'),
    )

    # ### Match Officials association table ###
    op.create_table(
        'match_officials',
        sa.Column('match_id', sa.Integer(), sa.ForeignKey('matches.id'), primary_key=True),
        sa.Column('official_id', sa.Integer(), sa.ForeignKey('officials.id'), primary_key=True),
        sa.Column('role', sa.String(50), nullable=True),
    )

    # ### Create indexes for common queries ###
    op.create_index('ix_players_team_id', 'players', ['team_id'])
    op.create_index('ix_players_name', 'players', ['name'])
    op.create_index('ix_matches_status', 'matches', ['status'])
    op.create_index('ix_matches_game_mode', 'matches', ['game_mode'])
    op.create_index('ix_games_match_id', 'games', ['match_id'])
    op.create_index('ix_rounds_game_id', 'rounds', ['game_id'])
    op.create_index('ix_bouts_round_id', 'bouts', ['round_id'])
    op.create_index('ix_foul_records_match_id', 'foul_records', ['match_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_foul_records_match_id', 'foul_records')
    op.drop_index('ix_bouts_round_id', 'bouts')
    op.drop_index('ix_rounds_game_id', 'rounds')
    op.drop_index('ix_games_match_id', 'games')
    op.drop_index('ix_matches_game_mode', 'matches')
    op.drop_index('ix_matches_status', 'matches')
    op.drop_index('ix_players_name', 'players')
    op.drop_index('ix_players_team_id', 'players')

    # Drop tables in reverse order of creation
    op.drop_table('match_officials')
    op.drop_table('officials')
    op.drop_table('foul_records')
    op.drop_table('bouts')
    op.drop_table('rounds')
    op.drop_table('games')
    op.drop_table('matches')
    op.drop_table('tournaments')

    # Drop the captain foreign key before dropping players/teams
    op.drop_constraint('fk_teams_captain_id', 'teams', type_='foreignkey')

    op.drop_table('players')
    op.drop_table('teams')

    # Drop enums (SQLite doesn't require this, but PostgreSQL would)
    # These are automatically cleaned up in SQLite
