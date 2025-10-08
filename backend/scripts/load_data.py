#!/usr/bin/env python3
"""
Idempotent ETL script for basketball data loading
Supports bulk operations, error recovery, and comprehensive logging
"""

import os
import sys
import json
import argparse
import logging
import time
import random
from pathlib import Path
from typing import Dict, List, Iterator, Tuple, Optional, Any
from collections import defaultdict, Counter
from datetime import datetime, date

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
sys.path.append(str(Path(__file__).parent.parent))

import django
django.setup()

from django.db import transaction, connection
from django.db.models import Q, Max
from django.core.exceptions import ValidationError
import psycopg2.extras

from app.dbmodels.models import (
    Season, Team, Game, GameTeam, Player, Action, 
    Event, ShotEvent, PassEvent, TurnoverEvent
)

# Configuration
ACTION_MAPPING = {
    'pickAndRoll': 'PNR',
    'pick_and_roll': 'PNR', 
    'isolation': 'ISO',
    'postUp': 'POST',
    'post_up': 'POST',
    'offBallScreen': 'OFFBALL',
    'off_ball_screen': 'OFFBALL'
}

DEFAULT_ACTIONS = [
    ('PNR', 'Pick & Roll'),
    ('ISO', 'Isolation'), 
    ('POST', 'Post-up'),
    ('OFFBALL', 'Off-Ball Screen'),
    ('UNKNOWN', 'Unknown Action')
]

# Whitelist of fields that can be updated on conflict
UPDATEABLE_FIELDS = ['x_ft', 'y_ft', 'occurred_at', 'action_id', 'team_id']

class ETLMetrics:
    """Track ETL statistics"""
    def __init__(self):
        self.actions_created = 0
        self.teams_upserted = 0
        self.players_upserted = 0
        self.games_upserted = 0
        self.events_inserted = 0
        self.events_updated = 0
        self.events_skipped = 0
        self.shot_rows = 0
        self.pass_rows = 0
        self.turnover_rows = 0
        self.warnings_emitted = 0
        self.errors_parsed = 0
        self.retry_attempts = 0
        self.start_time = time.time()
    
    def elapsed_time(self):
        return time.time() - self.start_time
    
    def events_per_second(self):
        total = self.events_inserted + self.events_updated + self.events_skipped
        return total / self.elapsed_time() if self.elapsed_time() > 0 else 0

def retry_on_deadlock(func, max_retries=3, base_delay=1.0):
    """Retry function on deadlock or temporary errors with exponential backoff"""
    for attempt in range(max_retries + 1):
        try:
            return func()
        except Exception as e:
            error_msg = str(e).lower()
            if attempt == max_retries or not any(keyword in error_msg for keyword in ['deadlock', 'lock timeout', 'serialization failure', 'connection']):
                raise
            
            delay = base_delay * (2 ** attempt) + random.uniform(0, 1)
            logging.warning(f"Retryable error (attempt {attempt + 1}/{max_retries + 1}): {e}. Retrying in {delay:.2f}s...")
            time.sleep(delay)

def load_actions() -> Dict[str, Action]:
    """Initialize action dictionary with standardized codes"""
    actions = {}
    for code, name in DEFAULT_ACTIONS:
        action, created = Action.objects.get_or_create(
            code=code,
            defaults={'name': name}
        )
        actions[code] = action
        if created:
            logging.info(f"Created action: {code} - {name}")
    return actions

def load_dim_tables(raw_dir: Path, date_filter: Optional[Tuple[date, date]] = None) -> Dict[str, Any]:
    """Load dimension tables with idempotent operations"""
    
    # Load raw data
    with open(raw_dir / 'teams.json') as f:
        teams_data = json.load(f)
    with open(raw_dir / 'players.json') as f:
        players_data = json.load(f)
    with open(raw_dir / 'games.json') as f:
        games_data = json.load(f)
    
    # Create default season
    season, created = Season.objects.get_or_create(
        year_start=2023,
        year_end=2024,
        defaults={'year_start': 2023, 'year_end': 2024}
    )
    
    # Load teams
    teams_map = {}
    for team_data in teams_data:
        team, created = Team.objects.get_or_create(
            team_id=team_data['team_id'],
            defaults={'name': team_data['name']}
        )
        teams_map[team_data['team_id']] = team
    
    # Load players  
    players_map = {}
    for player_data in players_data:
        player, created = Player.objects.get_or_create(
            player_id=player_data['player_id'],
            defaults={
                'name': player_data['name'],
                'team_id': teams_map[player_data['team_id']]
            }
        )
        players_map[player_data['player_id']] = player
    
    # Load games with optional date filtering
    games_map = {}
    for game_data in games_data:
        game_date = datetime.strptime(game_data['date'], '%Y-%m-%d').date()
        
        if date_filter:
            since, until = date_filter
            if since and game_date < since:
                continue
            if until and game_date > until:
                continue
        
        game, created = Game.objects.get_or_create(
            game_id=game_data['id'],
            defaults={
                'date': game_data['date'],
                'season_id': season
            }
        )
        games_map[game_data['id']] = game
    
    return {
        'season': season,
        'teams': teams_map,
        'players': players_map,
        'games': games_map
    }

def iter_events_from_raw(raw_dir: Path, limit: Optional[int] = None) -> Iterator[Tuple[str, Dict[str, Any]]]:
    """Generator that parses and standardizes events from raw data"""
    
    players_file = raw_dir / 'players.json'
    with open(players_file, 'r') as f:
        players_data = json.load(f)
    
    processed = 0
    
    for player_data in players_data:
        if limit and processed >= limit:
            break
            
        player_id = player_data['player_id']
        team_id = player_data.get('team_id')
        
        # Process shots
        for shot in player_data.get('shots', []):
            if limit and processed >= limit:
                break
                
            action_code = ACTION_MAPPING.get(shot.get('action_type', ''), 'UNKNOWN')
            if action_code == 'UNKNOWN' and shot.get('action_type'):
                logging.warning(f"Unknown action type '{shot.get('action_type')}' mapped to UNKNOWN")
            
            event_data = {
                'source_event_id': shot['id'],
                'player_id': player_id,
                'team_id': team_id,
                'game_id': shot['game_id'],
                'action_code': action_code,
                'event_type': 'shot',
                'x_ft': _safe_float(shot.get('shot_loc_x')),
                'y_ft': _safe_float(shot.get('shot_loc_y')),
                'occurred_at': None,  # Could be derived from game + sequence
                'event_seq': processed,  # Simple sequence number
                # Shot-specific fields
                'points': shot.get('points', 0),
                'shooting_foul_drawn': shot.get('shooting_foul_drawn', False)
            }
            
            yield ('shot', event_data)
            processed += 1
        
        # Process passes
        for pass_data in player_data.get('passes', []):
            if limit and processed >= limit:
                break
                
            action_code = ACTION_MAPPING.get(pass_data.get('action_type', ''), 'UNKNOWN')
            if action_code == 'UNKNOWN' and pass_data.get('action_type'):
                logging.warning(f"Unknown action type '{pass_data.get('action_type')}' mapped to UNKNOWN")
            
            event_data = {
                'source_event_id': pass_data['id'],
                'player_id': player_id,
                'team_id': team_id,
                'game_id': pass_data['game_id'],
                'action_code': action_code,
                'event_type': 'pass',
                'x_ft': _safe_float(pass_data.get('ball_start_loc_x')),
                'y_ft': _safe_float(pass_data.get('ball_start_loc_y')),
                'occurred_at': None,
                'event_seq': processed,
                # Pass-specific fields
                'completed_pass': pass_data.get('completed_pass', True),
                'potential_assist': pass_data.get('potential_assist', False),
                'turnover': pass_data.get('turnover', False),
                'target_player_id': None  # Could be extracted if available
            }
            
            yield ('pass', event_data)
            processed += 1
        
        # Process turnovers
        for turnover in player_data.get('turnovers', []):
            if limit and processed >= limit:
                break
                
            action_code = ACTION_MAPPING.get(turnover.get('action_type', ''), 'UNKNOWN')
            if action_code == 'UNKNOWN' and turnover.get('action_type'):
                logging.warning(f"Unknown action type '{turnover.get('action_type')}' mapped to UNKNOWN")
            
            event_data = {
                'source_event_id': turnover['id'],
                'player_id': player_id,
                'team_id': team_id,
                'game_id': turnover['game_id'],
                'action_code': action_code,
                'event_type': 'turnover',
                'x_ft': _safe_float(turnover.get('tov_loc_x')),
                'y_ft': _safe_float(turnover.get('tov_loc_y')),
                'occurred_at': None,
                'event_seq': processed,
                # Turnover-specific fields
                'turnover_type': 'general'
            }
            
            yield ('turnover', event_data)
            processed += 1

def _safe_float(value) -> Optional[float]:
    """Safely convert to float, return None for invalid values"""
    if value is None:
        return None
    try:
        result = float(value)
        # Basic sanity check for basketball court dimensions
        if abs(result) > 100:
            logging.warning(f"Coordinate value {result} seems unreasonable for basketball court")
        return result
    except (ValueError, TypeError):
        logging.warning(f"Invalid coordinate value: {value}")
        return None

def upsert_events(events_iter: Iterator, dims_map: Dict, actions_map: Dict,
                 batch_size: int = 1000, dry_run: bool = False, 
                 no_update: bool = False, metrics: ETLMetrics = None) -> ETLMetrics:
    """Bulk upsert events with comprehensive error handling"""
    
    if metrics is None:
        metrics = ETLMetrics()
    
    events_batch = []
    
    for event_type, event_data in events_iter:
        events_batch.append((event_type, event_data))
        
        if len(events_batch) >= batch_size:
            _process_batch(events_batch, dims_map, actions_map, 
                          dry_run, no_update, metrics)
            events_batch = []
    
    # Process remaining batch
    if events_batch:
        _process_batch(events_batch, dims_map, actions_map, 
                      dry_run, no_update, metrics)
    
    return metrics

def _process_batch(events_batch: List[Tuple], dims_map: Dict, actions_map: Dict,
                  dry_run: bool, no_update: bool, metrics: ETLMetrics):
    """Process a batch of events with PostgreSQL UPSERT and retry logic"""
    
    if dry_run:
        metrics.events_skipped += len(events_batch)
        return
    
    def _execute_batch():
        with transaction.atomic():
            # Prepare data for bulk operations
            events_to_insert = []
            events_to_update = []
            
            for event_type, event_data in events_batch:
                # Validate required fields
                if not all(k in event_data for k in ['source_event_id', 'player_id', 'game_id']):
                    metrics.errors_parsed += 1
                    logging.error(f"Missing required fields in event: {event_data}")
                    continue
                
                # Check if event exists
                existing_event = Event.objects.filter(
                    source_event_id=event_data['source_event_id']
                ).first()
                
                if existing_event:
                    if no_update:
                        metrics.events_skipped += 1
                        continue
                    else:
                        # Update existing event with whitelisted fields
                        update_data = {
                            'id': existing_event.id,
                            'x_ft': event_data.get('x_ft'),
                            'y_ft': event_data.get('y_ft'),
                            'action_id': actions_map[event_data['action_code']].id,
                            'team_id': dims_map['players'][event_data['player_id']].team_id.id
                        }
                        events_to_update.append((update_data, event_type, event_data))
                        metrics.events_updated += 1
                else:
                    # New event
                    event_record = {
                        'source_event_id': event_data['source_event_id'],
                        'player_id': dims_map['players'][event_data['player_id']].id,
                        'game_id': dims_map['games'][event_data['game_id']].id,
                        'team_id': dims_map['players'][event_data['player_id']].team_id.id,
                        'action_id': actions_map[event_data['action_code']].id,
                        'event_type': event_data['event_type'],
                        'x_ft': event_data.get('x_ft'),
                        'y_ft': event_data.get('y_ft'),
                        'occurred_at': event_data.get('occurred_at'),
                        'created_at': 'NOW()'
                    }
                    events_to_insert.append((event_record, event_type, event_data))
                    metrics.events_inserted += 1
            
            # Bulk insert new events using psycopg2 for performance
            if events_to_insert:
                _bulk_insert_events(events_to_insert, metrics)
            
            # Bulk update existing events
            if events_to_update:
                _bulk_update_events(events_to_update, metrics)
    
    try:
        retry_on_deadlock(_execute_batch)
    except Exception as e:
        logging.error(f"Batch processing failed after retries: {e}")
        raise

def _bulk_insert_events(events_to_insert: List, metrics: ETLMetrics):
    """Use psycopg2 for high-performance bulk inserts"""
    
    with connection.cursor() as cursor:
        # Prepare event records
        event_records = []
        for event_record, event_type, event_data in events_to_insert:
            event_records.append((
                event_record['source_event_id'],
                event_record['player_id'],
                event_record['game_id'], 
                event_record['team_id'],
                event_record['action_id'],
                event_record['event_type'],
                event_record['x_ft'],
                event_record['y_ft'],
                event_record['occurred_at']
            ))
        
        # Bulk insert events with conflict handling
        insert_sql = """
        INSERT INTO app.events 
        (source_event_id, player_id, game_id, team_id, action_id, event_type, x_ft, y_ft, occurred_at, created_at)
        VALUES %s
        ON CONFLICT (source_event_id) DO NOTHING
        RETURNING id, source_event_id
        """
        
        inserted_events = psycopg2.extras.execute_values(
            cursor, insert_sql, event_records, 
            template=None, fetch=True
        )
        
        # Create detail records
        event_id_map = {row[1]: row[0] for row in inserted_events}
        
        for event_record, event_type, event_data in events_to_insert:
            event_id = event_id_map.get(event_record['source_event_id'])
            if not event_id:
                continue
                
            if event_type == 'shot':
                shot_sql = """
                INSERT INTO app.shot_events (event_id, points, shot_result)
                VALUES (%s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """
                cursor.execute(shot_sql, (
                    event_id,
                    event_data.get('points', 0),
                    'make' if event_data.get('points', 0) > 0 else 'miss'
                ))
                metrics.shot_rows += 1
                
            elif event_type == 'pass':
                pass_sql = """
                INSERT INTO app.pass_events 
                (event_id, target_player_id, completed_pass, potential_assist, turnover)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """
                cursor.execute(pass_sql, (
                    event_id,
                    event_data.get('target_player_id'),
                    event_data.get('completed_pass', True),
                    event_data.get('potential_assist', False),
                    event_data.get('turnover', False)
                ))
                metrics.pass_rows += 1
                
            elif event_type == 'turnover':
                turnover_sql = """
                INSERT INTO app.turnover_events (event_id, turnover_type)
                VALUES (%s, %s)
                ON CONFLICT (event_id) DO NOTHING
                """
                cursor.execute(turnover_sql, (
                    event_id,
                    event_data.get('turnover_type', 'general')
                ))
                metrics.turnover_rows += 1

def _bulk_update_events(events_to_update: List, metrics: ETLMetrics):
    """Bulk update existing events with whitelisted fields"""
    with connection.cursor() as cursor:
        for update_data, event_type, event_data in events_to_update:
            update_sql = """
            UPDATE app.events 
            SET x_ft = %(x_ft)s, y_ft = %(y_ft)s, action_id = %(action_id)s, team_id = %(team_id)s
            WHERE id = %(id)s
            """
            cursor.execute(update_sql, update_data)

def summarize_and_print(metrics: ETLMetrics, dry_run: bool = False):
    """Print comprehensive ETL summary"""
    
    print("\n" + "="*60)
    print("ETL SUMMARY")
    print("="*60)
    print(f"Actions created: {metrics.actions_created}")
    print(f"Teams upserted: {metrics.teams_upserted}")
    print(f"Players upserted: {metrics.players_upserted}")
    print(f"Games upserted: {metrics.games_upserted}")
    print(f"Events processed: {metrics.events_inserted + metrics.events_updated + metrics.events_skipped}")
    print(f"Events inserted: {metrics.events_inserted}")
    print(f"Events updated: {metrics.events_updated}")
    print(f"Events skipped: {metrics.events_skipped}")
    print(f"Shot events: {metrics.shot_rows}")
    print(f"Pass events: {metrics.pass_rows}")
    print(f"Turnover events: {metrics.turnover_rows}")
    print(f"Warnings emitted: {metrics.warnings_emitted}")
    print(f"Errors parsed: {metrics.errors_parsed}")
    print(f"Retry attempts: {metrics.retry_attempts}")
    print(f"Total time: {metrics.elapsed_time():.2f} seconds")
    print(f"Events/second: {metrics.events_per_second():.2f}")
    
    if dry_run:
        print(f"Mode: DRY RUN - No data written")
    
    print("="*60)

def main():
    """Main ETL function with comprehensive argument parsing"""
    
    parser = argparse.ArgumentParser(
        description='Idempotent ETL script for basketball data loading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python load_data.py --dry-run                    # Validate data without writing
  python load_data.py --limit 200 --verbose       # Process 200 events with detailed logging
  python load_data.py --batch-size 2000           # Use larger batch size for performance
  python load_data.py --since 2023-11-15          # Only process games since date
  python load_data.py --no-update --verbose       # Only insert new events, don't update existing
        """
    )
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Parse and validate only, do not insert data')
    parser.add_argument('--limit', type=int,
                       help='Limit number of events to process')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for processing (default: 1000)')
    parser.add_argument('--only', choices=['actions', 'teams', 'players', 'games', 'events', 'all'],
                       default='all', help='Only run specific step')
    parser.add_argument('--truncate', action='store_true',
                       help='Clear fact tables before import (dangerous)')
    parser.add_argument('--since', type=str,
                       help='Only process games since YYYY-MM-DD')
    parser.add_argument('--until', type=str,
                       help='Only process games until YYYY-MM-DD')
    parser.add_argument('--resume', action='store_true',
                       help='Resume processing (skip existing events)')
    parser.add_argument('--strict', action='store_true',
                       help='Terminate on first error (default: continue)')
    parser.add_argument('--no-update', action='store_true',
                       help='Do not update existing events, only insert new ones')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    parser.add_argument('--raw-dir', default='raw_data',
                       help='Raw data directory (default: raw_data)')
    
    args = parser.parse_args()
    
    # Setup logging
    level = logging.DEBUG if args.verbose else logging.INFO
    log_format = '%(asctime)s - %(levelname)s - %(message)s'
    
    # Clear any existing handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('etl.log')
        ]
    )
    
    # Parse date filters
    date_filter = None
    if args.since or args.until:
        since = datetime.strptime(args.since, '%Y-%m-%d').date() if args.since else None
        until = datetime.strptime(args.until, '%Y-%m-%d').date() if args.until else None
        date_filter = (since, until)
    
    raw_dir = Path(__file__).parent.parent / args.raw_dir
    
    # Validate raw data directory
    if not raw_dir.exists():
        logging.error(f"Raw data directory not found: {raw_dir}")
        sys.exit(1)
    
    required_files = ['teams.json', 'players.json', 'games.json']
    for file_name in required_files:
        if not (raw_dir / file_name).exists():
            logging.error(f"Required file not found: {raw_dir / file_name}")
            sys.exit(1)
    
    try:
        logging.info("Starting ETL process...")
        logging.info(f"Raw data directory: {raw_dir}")
        logging.info(f"Batch size: {args.batch_size}")
        logging.info(f"Dry run: {args.dry_run}")
        logging.info(f"No update mode: {args.no_update}")
        
        # Initialize actions
        if args.only in ['actions', 'all']:
            actions_map = load_actions()
        else:
            actions_map = {a.code: a for a in Action.objects.all()}
        
        # Load dimension tables
        if args.only in ['teams', 'players', 'games', 'all']:
            dims_map = load_dim_tables(raw_dir, date_filter)
        else:
            dims_map = {}
        
        # Process events
        if args.only in ['events', 'all']:
            events_iter = iter_events_from_raw(raw_dir, args.limit)
            metrics = upsert_events(
                events_iter, dims_map, actions_map,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                no_update=args.no_update
            )
            
            summarize_and_print(metrics, args.dry_run)
        
        logging.info("ETL process completed successfully")
        
    except KeyboardInterrupt:
        logging.info("ETL process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logging.error(f"ETL process failed: {e}")
        if args.strict:
            raise
        sys.exit(1)

if __name__ == '__main__':
    main()
