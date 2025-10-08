# backend/app/helpers/players.py

from collections import defaultdict

from django.db.models import (
    Sum, Count, F, Q, Case, When, IntegerField, FloatField, Value, OuterRef,
    Subquery
)
from django.db.models.functions import Coalesce
from django.db.models.expressions import Window
from django.db.models.functions.window import DenseRank

# Normalize Action.name to the four required types; unknown actions go to 'UNKNOWN'
ACTION_NAME_NORMALIZER = {
    'Pick & Roll': 'Pick & Roll',
    'Pick-and-Roll': 'Pick & Roll',
    'PnR': 'Pick & Roll',
    'Isolation': 'Isolation',
    'Post-up': 'Post-up',
    'Post Up': 'Post-up',
    'Off-Ball Screen': 'Off-Ball Screen',
}
CANONICAL_ACTIONS = ['Pick & Roll', 'Isolation', 'Post-up', 'Off-Ball Screen', 'UNKNOWN']


def _norm_action_name(raw: str | None) -> str:
    if not raw:
        return 'UNKNOWN'
    return ACTION_NAME_NORMALIZER.get(raw, raw) if raw in ACTION_NAME_NORMALIZER else (raw if raw in CANONICAL_ACTIONS else 'UNKNOWN')


def get_player_summary_stats(player_id: int | str) -> dict:
    """
    Return player summary data matching sample_summary_data.json structure:
    {
      "playerId": ...,
      "totals": {...},
      "ranks": {...},   # Set to None initially, calculated by get_ranks
      "actions": {
        "Pick & Roll": { "shots": [...], "passes": [...], "turnovers": [...], "totals": {...} },
        ...
      }
    }
    """

    # ---- Event lists with coordinates/results ----
    # Use select_related to reduce N+1 queries; prefetch_related for further optimization
    from app.dbmodels.models import ShotEvent, PassEvent, TurnoverEvent
    
    shot_qs = (
        ShotEvent.objects
        .select_related('event__action', 'event__game')  # Remove game FK if not available
        .filter(event__player_id=player_id)
        .values(
            'event__x_ft', 'event__y_ft', 'shot_result', 'points',
            'event__action__name', 'event__occurred_at', 'event__game_id'
        )
    )
    pass_qs = (
        PassEvent.objects
        .select_related('event__action')
        .filter(event__player_id=player_id)
        .values(
            'event__x_ft', 'event__y_ft', 'target_player_id',
            'event__action__name', 'event__occurred_at', 'event__game_id'
        )
    )
    to_qs = (
        TurnoverEvent.objects
        .select_related('event__action')
        .filter(event__player_id=player_id)
        .values(
            'event__x_ft', 'event__y_ft', 'turnover_type',
            'event__action__name', 'event__occurred_at', 'event__game_id'
        )
    )

    # Initialize action buckets
    actions = {k: {'shots': [], 'passes': [], 'turnovers': [], 'totals': {
        'shots': 0, 'makes': 0, 'misses': 0, 'passes': 0, 'turnovers': 0, 'points': 0
    }} for k in CANONICAL_ACTIONS}

    # Process shots
    for r in shot_qs:
        act = _norm_action_name(r.get('event__action__name'))
        x, y = r['event__x_ft'], r['event__y_ft']
        # Coordinates can be None; frontend will filter out null points
        actions[act]['shots'].append({
            'x': x, 'y': y,
            'shot_result': r['shot_result'],     # 'make' | 'miss'
            'points': int(r['points'] or 0),
            'occurred_at': r.get('event__occurred_at'),
            'game_id': r.get('event__game_id'),
        })
        actions[act]['totals']['shots'] += 1
        if r['shot_result'] == 'make':
            actions[act]['totals']['makes'] += 1
        else:
            actions[act]['totals']['misses'] += 1
        actions[act]['totals']['points'] += int(r['points'] or 0)

    # Process passes
    for r in pass_qs:
        act = _norm_action_name(r.get('event__action__name'))
        actions[act]['passes'].append({
            'x': r['event__x_ft'], 'y': r['event__y_ft'],
            'target_player_id': r.get('target_player_id'),
            'occurred_at': r.get('event__occurred_at'),
            'game_id': r.get('event__game_id'),
        })
        actions[act]['totals']['passes'] += 1

    # Process turnovers
    for r in to_qs:
        act = _norm_action_name(r.get('event__action__name'))
        actions[act]['turnovers'].append({
            'x': r['event__x_ft'], 'y': r['event__y_ft'],
            'turnover_type': r.get('turnover_type'),
            'occurred_at': r.get('event__occurred_at'),
            'game_id': r.get('event__game_id'),
        })
        actions[act]['totals']['turnovers'] += 1

    # ---- Aggregate top-level totals (sum from action totals) ----
    totals = {'points': 0, 'makes': 0, 'misses': 0, 'passes': 0, 'turnovers': 0, 'shots': 0}
    for act in CANONICAL_ACTIONS:
        t = actions[act]['totals']
        totals['points'] += t['points']
        totals['makes'] += t['makes']
        totals['misses'] += t['misses']
        totals['passes'] += t['passes']
        totals['turnovers'] += t['turnovers']
        totals['shots'] += t['shots']

    # Ranks will be calculated by get_ranks function
    return {
        'playerId': int(player_id) if str(player_id).isdigit() else player_id,
        'totals': totals,
        'ranks': {'points': None, 'makes': None, 'misses': None, 'passes': None, 'turnovers': None, 'shots': None},
        'actions': actions
    }


def get_ranks(summary_stats: dict) -> dict:
    """
    Calculate dense-rank for the player against all players using totals from get_player_summary_stats.
    Uses Subquery + Window(DenseRank). Requires PostgreSQL.
    Returns format:
    { 'points': 3, 'makes': 5, 'misses': 12, 'passes': 8, 'turnovers': 9, 'shots': 4 }
    """
    player_id = summary_stats.get('playerId')

    # --- Calculate totals for each player (across three sub-tables) ---
    from app.dbmodels.models import ShotEvent, PassEvent, TurnoverEvent
    
    # Shots totals per player
    shots_totals = (
        ShotEvent.objects
        .values('event__player_id')
        .annotate(
            total_points=Coalesce(Sum('points'), 0),
            total_makes=Coalesce(Sum(Case(When(shot_result='make', then=1), default=0, output_field=IntegerField())), 0),
            total_misses=Coalesce(Sum(Case(When(shot_result='miss', then=1), default=0, output_field=IntegerField())), 0),
            total_shots=Coalesce(Count('id'), 0),
        )
    )

    # Pass totals per player
    pass_totals = (
        PassEvent.objects
        .values('event__player_id')
        .annotate(total_passes=Coalesce(Count('id'), 0))
    )

    # Turnover totals per player
    to_totals = (
        TurnoverEvent.objects
        .values('event__player_id')
        .annotate(total_turnovers=Coalesce(Count('id'), 0))
    )

    # Merge through Subquery to Player (or any player table/distinct player id from event tables)
    # Note: Replace Player with your player model class
    from app.dbmodels.models import Player  # Avoid circular import at top

    # Subquery: shots summary for a player
    def sq_shots(expr):
        return Subquery(
            shots_totals.filter(event__player_id=OuterRef('pk')).values(expr)[:1]
        )

    # Subquery: passes summary for a player
    def sq_passes():
        return Subquery(
            pass_totals.filter(event__player_id=OuterRef('pk')).values('total_passes')[:1]
        )

    # Subquery: turnovers summary for a player
    def sq_turnovers():
        return Subquery(
            to_totals.filter(event__player_id=OuterRef('pk')).values('total_turnovers')[:1]
        )

    ranked = (
        Player.objects
        .annotate(
            total_points=Coalesce(sq_shots('total_points'), 0),
            total_makes=Coalesce(sq_shots('total_makes'), 0),
            total_misses=Coalesce(sq_shots('total_misses'), 0),
            total_shots=Coalesce(sq_shots('total_shots'), 0),
            total_passes=Coalesce(sq_passes(), 0),
            total_turnovers=Coalesce(sq_turnovers(), 0),
        )
        .annotate(
            rank_points=Window(expression=DenseRank(), order_by=F('total_points').desc()),
            rank_makes=Window(expression=DenseRank(), order_by=F('total_makes').desc()),
            rank_misses=Window(expression=DenseRank(), order_by=F('total_misses').desc()),  # 如果需要
            rank_shots=Window(expression=DenseRank(), order_by=F('total_shots').desc()),
            rank_passes=Window(expression=DenseRank(), order_by=F('total_passes').desc()),
            rank_turnovers=Window(expression=DenseRank(), order_by=F('total_turnovers').desc()),
        )
        .filter(pk=player_id)
        .values(
            'rank_points', 'rank_makes', 'rank_misses', 'rank_shots', 'rank_passes', 'rank_turnovers'
        )
        .first()
    )

    # Fallback for players with no events
    if not ranked:
        return {
            'points': None, 'makes': None, 'misses': None,
            'passes': None, 'turnovers': None, 'shots': None
        }

    return {
        'points': ranked['rank_points'],
        'makes': ranked['rank_makes'],
        'misses': ranked['rank_misses'],
        'passes': ranked['rank_passes'],
        'turnovers': ranked['rank_turnovers'],
        'shots': ranked['rank_shots'],
    }
