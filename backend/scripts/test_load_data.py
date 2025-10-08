#!/usr/bin/env python3
"""
Smoke tests for ETL script - comprehensive validation
"""

import os
import sys
import subprocess
import json
from pathlib import Path

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
sys.path.append(str(Path(__file__).parent.parent))

import django
django.setup()

from django.db import connection
from django.db.models import Max, Min
from app.dbmodels.models import (
    Event, ShotEvent, PassEvent, TurnoverEvent, Action, 
    Team, Player, Game
)

def test_dry_run_execution():
    """Test dry run execution with limited events"""
    print("Testing dry run execution...")
    
    result = subprocess.run([
        sys.executable, 'load_data.py', '--dry-run', '--limit', '50'
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    assert result.returncode == 0, f"Dry run failed: {result.stderr}"
    
    # Parse output for statistics
    output = result.stdout
    assert "Events processed: 50" in output, "Expected 50 events in dry run"
    assert "Mode: DRY RUN - No data written" in output, "Should indicate dry run mode"
    assert "Events inserted: 0" in output, "Dry run should not insert events"
    
    print("  ✅ Dry run executed successfully")
    print("  ✅ Processed expected number of events")
    print("  ✅ Correctly indicated dry run mode")
    print("✅ Dry run test passed")

def test_action_dictionary():
    """Test that all required action types are created"""
    print("Testing action dictionary...")
    
    required_actions = ['PNR', 'ISO', 'POST', 'OFFBALL', 'UNKNOWN']
    
    for code in required_actions:
        action = Action.objects.filter(code=code).first()
        assert action is not None, f"Action {code} not found"
        print(f"  ✅ Found action: {code} - {action.name}")
    
    # Test action mapping functionality
    from load_data import ACTION_MAPPING
    assert 'pickAndRoll' in ACTION_MAPPING, "pickAndRoll mapping not found"
    assert ACTION_MAPPING['pickAndRoll'] == 'PNR', "pickAndRoll should map to PNR"
    assert ACTION_MAPPING['isolation'] == 'ISO', "isolation should map to ISO"
    
    print("  ✅ All action mappings are correct")
    print("✅ Action dictionary test passed")

def test_idempotent_behavior():
    """Test that running ETL twice produces expected results"""
    print("Testing idempotent behavior...")
    
    # Get initial counts
    initial_events = Event.objects.count()
    initial_shots = ShotEvent.objects.count()
    initial_passes = PassEvent.objects.count()
    initial_turnovers = TurnoverEvent.objects.count()
    
    print(f"  Initial counts - Events: {initial_events}, Shots: {initial_shots}, Passes: {initial_passes}, Turnovers: {initial_turnovers}")
    
    # Run ETL with limit
    result = subprocess.run([
        sys.executable, 'load_data.py', '--limit', '100', '--verbose'
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    assert result.returncode == 0, f"ETL run failed: {result.stderr}"
    
    # Check output for expected behavior
    output = result.stdout
    if initial_events == 0:
        # First run - should insert events
        assert "Events inserted:" in output and "Events skipped: 0" in output, "First run should insert events"
        print("  ✅ First run - events inserted as expected")
    else:
        # Subsequent run - should skip existing events
        assert "Events skipped:" in output, "Subsequent run should skip events"
        print("  ✅ Subsequent run - events skipped as expected")
    
    # Verify final counts
    final_events = Event.objects.count()
    final_shots = ShotEvent.objects.count()
    final_passes = PassEvent.objects.count()
    final_turnovers = TurnoverEvent.objects.count()
    
    print(f"  Final counts - Events: {final_events}, Shots: {final_shots}, Passes: {final_passes}, Turnovers: {final_turnovers}")
    
    # Counts should be reasonable
    assert final_events >= initial_events, "Event count should not decrease"
    assert final_shots + final_passes + final_turnovers <= final_events, "Detail records should not exceed events"
    
    print("✅ Idempotent behavior test passed")

def test_no_update_mode():
    """Test that --no-update mode prevents updates"""
    print("Testing no-update mode...")
    
    # Run with no-update mode
    result = subprocess.run([
        sys.executable, 'load_data.py', '--limit', '10', '--no-update', '--verbose'
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    assert result.returncode == 0, f"No-update mode failed: {result.stderr}"
    
    output = result.stdout
    assert "Events updated: 0" in output, "No-update mode should not update events"
    assert "No update mode: True" in output, "Should indicate no-update mode"
    
    print("  ✅ No-update mode prevented updates")
    print("  ✅ Correctly indicated no-update mode")
    print("✅ No-update mode test passed")

def test_data_integrity():
    """Test data integrity and relationships"""
    print("Testing data integrity...")
    
    # Test 1: Event relationships
    total_events = Event.objects.count()
    events_with_details = (
        ShotEvent.objects.count() + 
        PassEvent.objects.count() + 
        TurnoverEvent.objects.count()
    )
    
    assert total_events >= events_with_details, "Some events missing detail records"
    print(f"  ✅ Event relationships: {total_events} events, {events_with_details} detail records")
    
    # Test 2: Coordinate validation
    events_with_coords = Event.objects.filter(x_ft__isnull=False, y_ft__isnull=False)
    if events_with_coords.exists():
        coord_stats = events_with_coords.aggregate(
            max_x=Max('x_ft'), min_x=Min('x_ft'),
            max_y=Max('y_ft'), min_y=Min('y_ft')
        )
        
        print(f"  ✅ Coordinate ranges - X: {coord_stats['min_x']:.1f} to {coord_stats['max_x']:.1f}, Y: {coord_stats['min_y']:.1f} to {coord_stats['max_y']:.1f}")
        
        # Sanity check for basketball court dimensions
        assert abs(coord_stats['min_x']) < 100 and abs(coord_stats['max_x']) < 100, "X coordinates seem unreasonable"
        assert abs(coord_stats['min_y']) < 100 and abs(coord_stats['max_y']) < 100, "Y coordinates seem unreasonable"
    else:
        print("  ✅ No coordinate data found (expected for dry run)")
    
    # Test 3: Action code validation
    invalid_actions = Event.objects.exclude(
        action_id__code__in=['PNR', 'ISO', 'POST', 'OFFBALL', 'UNKNOWN']
    ).count()
    assert invalid_actions == 0, f"Found {invalid_actions} events with invalid action codes"
    print("  ✅ All events have valid action codes")
    
    # Test 4: Event type validation
    invalid_types = Event.objects.exclude(
        event_type__in=['shot', 'pass', 'turnover']
    ).count()
    assert invalid_types == 0, f"Found {invalid_types} events with invalid event types"
    print("  ✅ All events have valid event types")
    
    # Test 5: Source event ID uniqueness
    if total_events > 0:
        unique_source_ids = Event.objects.values('source_event_id').distinct().count()
        assert unique_source_ids == total_events, "Source event IDs should be unique"
        print("  ✅ All source event IDs are unique")
    
    print("✅ Data integrity test passed")

def test_performance_metrics():
    """Test that performance metrics are reasonable"""
    print("Testing performance metrics...")
    
    result = subprocess.run([
        sys.executable, 'load_data.py', '--limit', '100', '--batch-size', '50'
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    assert result.returncode == 0, f"Performance test failed: {result.stderr}"
    
    output = result.stdout
    assert "Events/second:" in output, "Should report events per second"
    assert "Total time:" in output, "Should report total time"
    
    # Extract and validate performance metrics
    lines = output.split('\n')
    for line in lines:
        if "Events/second:" in line:
            events_per_sec = float(line.split(':')[1].strip())
            assert events_per_sec > 0, "Events per second should be positive"
            print(f"  ✅ Events per second: {events_per_sec:.2f}")
        elif "Total time:" in line:
            total_time = float(line.split(':')[1].strip().split()[0])
            assert total_time > 0, "Total time should be positive"
            print(f"  ✅ Total time: {total_time:.2f} seconds")
    
    print("✅ Performance metrics test passed")

def test_error_handling():
    """Test error handling and logging"""
    print("Testing error handling...")
    
    # Test with invalid limit (should still work)
    result = subprocess.run([
        sys.executable, 'load_data.py', '--limit', '0'
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    assert result.returncode == 0, f"Zero limit should not cause failure: {result.stderr}"
    print("  ✅ Zero limit handled gracefully")
    
    # Test verbose logging
    result = subprocess.run([
        sys.executable, 'load_data.py', '--limit', '10', '--verbose'
    ], capture_output=True, text=True, cwd=Path(__file__).parent)
    
    assert result.returncode == 0, f"Verbose mode failed: {result.stderr}"
    output = result.stdout
    assert "Starting ETL process..." in output, "Should show startup message"
    assert "Batch size:" in output, "Should show batch size in verbose mode"
    print("  ✅ Verbose logging works correctly")
    
    print("✅ Error handling test passed")

def test_batch_processing():
    """Test batch processing functionality"""
    print("Testing batch processing...")
    
    # Test with different batch sizes
    batch_sizes = [50, 100, 500]
    
    for batch_size in batch_sizes:
        result = subprocess.run([
            sys.executable, 'load_data.py', '--limit', '150', '--batch-size', str(batch_size)
        ], capture_output=True, text=True, cwd=Path(__file__).parent)
        
        assert result.returncode == 0, f"Batch size {batch_size} failed: {result.stderr}"
        output = result.stdout
        assert f"Batch size: {batch_size}" in output, f"Should show batch size {batch_size}"
        print(f"  ✅ Batch size {batch_size} processed successfully")
    
    print("✅ Batch processing test passed")

def test_dimension_tables():
    """Test dimension table loading"""
    print("Testing dimension tables...")
    
    # Test teams
    teams_count = Team.objects.count()
    assert teams_count > 0, "Should have teams loaded"
    print(f"  ✅ Teams loaded: {teams_count}")
    
    # Test players
    players_count = Player.objects.count()
    assert players_count > 0, "Should have players loaded"
    print(f"  ✅ Players loaded: {players_count}")
    
    # Test games
    games_count = Game.objects.count()
    assert games_count > 0, "Should have games loaded"
    print(f"  ✅ Games loaded: {games_count}")
    
    # Test relationships
    players_with_teams = Player.objects.filter(team_id__isnull=False).count()
    assert players_with_teams == players_count, "All players should have teams"
    print("  ✅ All players have valid team relationships")
    
    print("✅ Dimension tables test passed")

def main():
    """Run all smoke tests"""
    print("Running ETL smoke tests...\n")
    
    try:
        test_dry_run_execution()
        print()
        
        test_action_dictionary()
        print()
        
        test_idempotent_behavior()
        print()
        
        test_no_update_mode()
        print()
        
        test_data_integrity()
        print()
        
        test_performance_metrics()
        print()
        
        test_error_handling()
        print()
        
        test_batch_processing()
        print()
        
        test_dimension_tables()
        print()
        
        print("🎉 All smoke tests passed!")
        print("\nETL script is ready for production use.")
        
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
