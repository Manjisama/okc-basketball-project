# Basketball Data ETL Scripts

## Overview
Production-ready ETL scripts for loading basketball game data from `raw_data/` into PostgreSQL using Django ORM with idempotent operations and comprehensive error handling.

## Quick Start with Dev Script

The dev scripts provide a convenient one-stop solution for all operations:

**Linux/macOS:**
```bash
cd backend/scripts
chmod +x dev.sh
```

**Windows:**
```powershell
cd backend/scripts
# Use PowerShell version (recommended)
.\dev.ps1 help
# Or use batch version
.\dev.bat help
```

### Basic Usage Examples

**Linux/macOS:**
```bash
# Run ETL with dry-run validation
./dev.sh etl --dry-run

# Process limited events for testing
./dev.sh etl --limit 200 --verbose

# Full ETL import with custom batch size
./dev.sh etl --batch-size 1000 --verbose

# Start Django development server
./dev.sh run

# Export database snapshot
./dev.sh dump

# Quick database health check
./dev.sh check

# Reset and re-import all data (dangerous!)
./dev.sh reset
```

**Windows:**
```powershell
# Run ETL with dry-run validation
.\dev.ps1 etl --dry-run

# Process limited events for testing
.\dev.ps1 etl --limit 200 --verbose

# Full ETL import with custom batch size
.\dev.ps1 etl --batch-size 1000 --verbose

# Start Django development server
.\dev.ps1 run

# Export database snapshot
.\dev.ps1 dump

# Quick database health check
.\dev.ps1 check

# Reset and re-import all data (dangerous!)
.\dev.ps1 reset
```

## Prerequisites & Environment Setup

### PostgreSQL Setup

**1. Install PostgreSQL**
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# macOS (with Homebrew)
brew install postgresql
brew services start postgresql

# Windows
# Download and install from https://www.postgresql.org/download/windows/
```

**2. Create Database and User**
```bash
# Connect to PostgreSQL as superuser
sudo -u postgres psql

# Create database and user
CREATE DATABASE okc;
CREATE USER okcapplicant WITH PASSWORD 'thunder';
GRANT ALL PRIVILEGES ON DATABASE okc TO okcapplicant;

# Create schema
\c okc
CREATE SCHEMA IF NOT EXISTS app;
GRANT ALL ON SCHEMA app TO okcapplicant;
GRANT ALL ON ALL TABLES IN SCHEMA app TO okcapplicant;

# Exit PostgreSQL
\q
```

**3. Verify Setup**
```bash
# Test connection
psql -U okcapplicant -d okc -h localhost -c "SELECT current_database(), current_schema();"

# Check tables (after ETL)
psql -U okcapplicant -d okc -c '\dt app.*'
psql -U okcapplicant -d okc -c '\d app.events'
```

### Python Environment Setup

**Option 1: From backend/ directory**
```bash
cd backend
pip install -r requirements.txt
```

**Option 2: Environment variables**
```bash
export DJANGO_SETTINGS_MODULE=app.settings
export PYTHONPATH=$(pwd)/backend
```

### Database Configuration
- **Database**: okc
- **User**: okcapplicant  
- **Password**: thunder
- **Schema**: app
- **Host**: localhost:5432

If `DATABASE_URL` is not set, the script will use the local defaults above.

## Usage

### ETL Command Examples

**Linux/macOS:**
```bash
# Basic ETL operations
./dev.sh etl --dry-run                    # Validate without writing
./dev.sh etl --limit 100 --verbose       # Process 100 events with logging
./dev.sh etl --batch-size 2000           # Use larger batch size
./dev.sh etl --no-update                 # Only insert new events

# Date filtering
./dev.sh etl --since 2023-11-15          # Only games since date
./dev.sh etl --until 2023-12-01          # Only games until date
./dev.sh etl --since 2023-11-15 --until 2023-12-01  # Date range

# Advanced options
./dev.sh etl --only events --limit 50    # Only process events
./dev.sh etl --strict                    # Terminate on first error
./dev.sh etl --resume                    # Skip existing events
```

**Windows:**
```powershell
# Basic ETL operations
.\dev.ps1 etl --dry-run                   # Validate without writing
.\dev.ps1 etl --limit 100 --verbose      # Process 100 events with logging
.\dev.ps1 etl --batch-size 2000          # Use larger batch size
.\dev.ps1 etl --no-update                # Only insert new events

# Date filtering
.\dev.ps1 etl --since 2023-11-15         # Only games since date
.\dev.ps1 etl --until 2023-12-01         # Only games until date
.\dev.ps1 etl --since 2023-11-15 --until 2023-12-01  # Date range

# Advanced options
.\dev.ps1 etl --only events --limit 50   # Only process events
.\dev.ps1 etl --strict                   # Terminate on first error
.\dev.ps1 etl --resume                   # Skip existing events
```

### Database Operations

**Linux/macOS:**
```bash
# Quick health check
./dev.sh check

# Export database snapshot
./dev.sh dump

# Verify export file
wc -c backend/scripts/dbexport.psql
head -20 backend/scripts/dbexport.psql

# Reset and re-import (dangerous!)
./dev.sh reset
```

**Windows:**
```powershell
# Quick health check
.\dev.ps1 check

# Export database snapshot
.\dev.ps1 dump

# Verify export file
Get-ChildItem backend/scripts/dbexport.psql
Get-Content backend/scripts/dbexport.psql | Select-Object -First 20

# Reset and re-import (dangerous!)
.\dev.ps1 reset
```

### Manual Usage (Alternative to dev.sh)

If you prefer to run commands manually:

```bash
cd backend/scripts

# Dry run - validate data without writing
python load_data.py --dry-run

# Process limited events for testing
python load_data.py --limit 200 --verbose

# Full import with custom batch size
python load_data.py --batch-size 2000

# Full import with verbose logging
python load_data.py --verbose
```

### Idempotent Verification

**Linux/macOS:**
```bash
# First run - should insert all data
./dev.sh etl --verbose

# Second run - should show 0 inserts, mostly skips
./dev.sh etl --verbose

# Third run with no-update mode - should show 0 updates
./dev.sh etl --no-update --verbose
```

**Windows:**
```powershell
# First run - should insert all data
.\dev.ps1 etl --verbose

# Second run - should show 0 inserts, mostly skips
.\dev.ps1 etl --verbose

# Third run with no-update mode - should show 0 updates
.\dev.ps1 etl --no-update --verbose
```

### Advanced Usage

```bash
# Date range filtering
python load_data.py --since 2023-11-15 --until 2023-12-01

# Resume processing (skip existing events)
python load_data.py --resume

# Strict mode (terminate on first error)
python load_data.py --strict

# No update mode (only insert new events)
python load_data.py --no-update

# Clear and reload fact tables (dangerous!)
python load_data.py --truncate

# Process only specific steps
python load_data.py --only actions
python load_data.py --only events --limit 100
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--dry-run` | Parse and validate only, do not insert data | False |
| `--limit N` | Process only first N events (for debugging) | None |
| `--batch-size N` | Batch size for processing | 1000 |
| `--only {actions,teams,players,games,events,all}` | Only run specific step | all |
| `--truncate` | Clear fact tables before import (dangerous) | False |
| `--since YYYY-MM-DD` | Only process games since date | None |
| `--until YYYY-MM-DD` | Only process games until date | None |
| `--resume` | Resume processing (skip existing events) | False |
| `--strict` | Terminate on first error (default: continue) | False |
| `--no-update` | Do not update existing events | False |
| `--verbose` | Enable detailed logging | False |
| `--raw-dir` | Specify raw data directory | raw_data |

## Data Flow

### 1. Action Dictionary Initialization
Creates standardized action codes with the following mapping:

| Raw Data | Standardized Code | Description |
|----------|-------------------|-------------|
| pickAndRoll, pick_and_roll | PNR | Pick & Roll |
| isolation | ISO | Isolation |
| postUp, post_up | POST | Post-up |
| offBallScreen, off_ball_screen | OFFBALL | Off-Ball Screen |
| (unknown/other) | UNKNOWN | Unknown Action |

- Uses `get_or_create` for idempotent operations
- Logs warnings for unknown action types mapped to UNKNOWN

### 2. Dimension Table Loading
- **Seasons**: Creates default 2023-2024 season
- **Teams**: Loads from teams.json with team_id as natural key
- **Players**: Loads from players.json with player_id as natural key
- **Games**: Loads from games.json with optional date filtering

All dimension tables use `get_or_create` to ensure idempotent operations.

### 3. Event Processing
Parses events from players.json with three event types:

#### Shot Events
- Maps `shot_loc_x`/`shot_loc_y` to `x_ft`/`y_ft`
- Extracts `points` (0, 2, 3) and `shooting_foul_drawn`
- Determines shot result: 'make' if points > 0, 'miss' otherwise

#### Pass Events  
- Maps `ball_start_loc_x`/`ball_start_loc_y` to `x_ft`/`y_ft`
- Extracts `completed_pass`, `potential_assist`, `turnover`
- `target_player_id` set to NULL (not available in raw data)

#### Turnover Events
- Maps `tov_loc_x`/`tov_loc_y` to `x_ft`/`y_ft`  
- Sets `turnover_type` to 'general'

### 4. Bulk Upsert Operations
- Uses PostgreSQL `ON CONFLICT` for idempotent inserts
- Processes events in configurable batches (default: 1000)
- Creates detail records (ShotEvent, PassEvent, TurnoverEvent)
- Maintains referential integrity

#### Update Whitelist
When updating existing events (conflict resolution), only these fields are updated:
- `x_ft`, `y_ft` - coordinate updates
- `occurred_at` - timestamp updates  
- `action_id` - action type corrections
- `team_id` - team assignment corrections

## Performance Features

- **Bulk Operations**: Process events in configurable batches
- **Memory Mapping**: Pre-load dimension tables to avoid N+1 queries
- **PostgreSQL UPSERT**: Uses `ON CONFLICT` for optimal performance
- **Transaction Safety**: Atomic operations with rollback on errors
- **Deadlock Retry**: Automatic retry with exponential backoff for transient errors
- **Parallel Processing**: Batch-level transactions for better throughput

## Data Quality & Validation

### Coordinate Handling
- Maintains feet as unit (no conversion)
- Invalid coordinates → NULL with warning
- Records coordinate ranges for validation
- Basic sanity check: coordinates > 100 feet trigger warnings

### Error Handling
- **Missing Fields**: Logs error and skips record
- **Invalid Data**: Converts to NULL with warning
- **Constraint Violations**: Logs error and continues processing
- **Batch Failures**: Rolls back batch, continues with next batch
- **Deadlock/Connection Issues**: Automatic retry (max 3 attempts with exponential backoff)

### Logging & Monitoring
- Comprehensive logging to console and file (`etl.log`)
- Performance metrics (events/second, elapsed time)
- Detailed statistics (inserts, updates, skips, errors, retries)
- Warning tracking for data quality issues

## Troubleshooting

### Common Issues

**PostgreSQL Connection Failed**
```bash
# Check if PostgreSQL is running
pg_ctl status

# Verify connection settings
psql -U okcapplicant -d okc -h localhost -p 5432

# Check schema exists
psql -U okcapplicant -d okc -c "SELECT schema_name FROM information_schema.schemata WHERE schema_name='app';"
```

**Schema/Permission Issues**
```bash
# Create schema if missing
psql -U okcapplicant -d okc -c "CREATE SCHEMA IF NOT EXISTS app;"

# Grant permissions
psql -U okcapplicant -d okc -c "GRANT ALL ON SCHEMA app TO okcapplicant;"
psql -U okcapplicant -d okc -c "GRANT ALL ON ALL TABLES IN SCHEMA app TO okcapplicant;"
```

**Data Validation Issues**
```bash
# Check for invalid coordinates
python load_data.py --dry-run --verbose

# Validate action mapping
python -c "from load_data import ACTION_MAPPING; print(ACTION_MAPPING)"
```

**Performance Issues**
```bash
# Use larger batch size for better performance
python load_data.py --batch-size 2000

# Process in smaller chunks for memory-constrained environments
python load_data.py --batch-size 500 --limit 1000
```

### Expected Output Examples

**Dry Run Example:**
```
2024-01-15 10:30:00 - INFO - Starting ETL process...
2024-01-15 10:30:00 - INFO - Raw data directory: /path/to/raw_data
2024-01-15 10:30:00 - INFO - Batch size: 1000
2024-01-15 10:30:00 - INFO - Dry run: True
2024-01-15 10:30:00 - INFO - Created action: PNR - Pick & Roll
2024-01-15 10:30:00 - INFO - Created action: ISO - Isolation
2024-01-15 10:30:01 - INFO - Processing batch of 1000 events...
============================================================
ETL SUMMARY
============================================================
Actions created: 4
Teams upserted: 10
Players upserted: 10
Games upserted: 39
Events processed: 1000
Events inserted: 0
Events updated: 0
Events skipped: 1000
Shot events: 0
Pass events: 0
Turnover events: 0
Warnings emitted: 0
Errors parsed: 0
Retry attempts: 0
Total time: 2.45 seconds
Events/second: 408.16
Mode: DRY RUN - No data written
============================================================
```

**Full Import Example:**
```
2024-01-15 10:35:00 - INFO - Starting ETL process...
2024-01-15 10:35:01 - INFO - Processing batch of 1000 events...
2024-01-15 10:35:02 - INFO - Inserted 1000 events
2024-01-15 10:35:03 - INFO - Processing batch of 847 events...
2024-01-15 10:35:04 - INFO - Inserted 847 events
============================================================
ETL SUMMARY
============================================================
Actions created: 5
Teams upserted: 10
Players upserted: 10
Games upserted: 39
Events processed: 1847
Events inserted: 1847
Events updated: 0
Events skipped: 0
Shot events: 892
Pass events: 723
Turnover events: 232
Warnings emitted: 15
Errors parsed: 0
Retry attempts: 2
Total time: 8.23 seconds
Events/second: 224.42
============================================================
```

**Idempotent Run Example (Second Execution):**
```
2024-01-15 10:40:00 - INFO - Starting ETL process...
2024-01-15 10:40:01 - INFO - Processing batch of 1000 events...
2024-01-15 10:40:02 - INFO - Inserted 0 events
2024-01-15 10:40:03 - INFO - Processing batch of 847 events...
2024-01-15 10:40:04 - INFO - Inserted 0 events
============================================================
ETL SUMMARY
============================================================
Actions created: 0
Teams upserted: 10
Players upserted: 10
Games upserted: 39
Events processed: 1847
Events inserted: 0
Events updated: 0
Events skipped: 1847
Shot events: 0
Pass events: 0
Turnover events: 0
Warnings emitted: 0
Errors parsed: 0
Retry attempts: 0
Total time: 4.12 seconds
Events/second: 448.30
============================================================
```

**No-Update Mode Example:**
```
2024-01-15 10:45:00 - INFO - Starting ETL process...
2024-01-15 10:45:00 - INFO - No update mode: True
2024-01-15 10:45:01 - INFO - Processing batch of 1847 events...
2024-01-15 10:45:02 - INFO - Inserted 0 events
============================================================
ETL SUMMARY
============================================================
Actions created: 0
Teams upserted: 10
Players upserted: 10
Games upserted: 39
Events processed: 1847
Events inserted: 0
Events updated: 0
Events skipped: 1847
Shot events: 0
Pass events: 0
Turnover events: 0
Warnings emitted: 0
Errors parsed: 0
Retry attempts: 0
Total time: 2.18 seconds
Events/second: 847.25
============================================================
```

**Database Export Example:**
```
Exporting database 'okc' to backend/scripts/dbexport.psql
Database snapshot exported successfully to: backend/scripts/dbexport.psql
File size: 2.1M (2,097,152 bytes)
Export summary:
  Database: okc
  Schema: app
  User: okcapplicant
  Output: backend/scripts/dbexport.psql
Verification commands:
  wc -c backend/scripts/dbexport.psql
  head -20 backend/scripts/dbexport.psql
```

**Database Health Check Example:**
```
Database Statistics:
Schema tables:
                List of relations
 Schema |     Name      | Type  |  Owner   
--------+---------------+-------+----------
 app    | actions       | table | okcapplicant
 app    | events        | table | okcapplicant
 app    | games         | table | okcapplicant
 app    | players       | table | okcapplicant
 app    | shot_events   | table | okcapplicant
 app    | teams         | table | okcapplicant

Event counts:
 table_name      | count 
-----------------+-------
 events          |  1847
 pass_events     |   723
 shot_events     |   892
 turnover_events |   232
```

## Integration with Next Steps

After successful ETL completion, export database snapshot:

**Linux/macOS:**
```bash
# Using dev script (recommended)
./dev.sh dump

# Or manually
pg_dump -U okcapplicant okc > backend/scripts/dbexport.psql
```

**Windows:**
```powershell
# Using dev script (recommended)
.\dev.ps1 dump

# Or manually
pg_dump -U okcapplicant okc > backend/scripts/dbexport.psql
```

This creates a complete database backup for deployment or analysis.

## Testing

Run the included smoke tests to validate ETL functionality:

```bash
python test_load_data.py
```

The smoke tests verify:
- Dry run execution works correctly
- All required action types are created
- Idempotent behavior (second run shows mostly skips)
- Data integrity and relationships
- Update behavior with no-update mode
- Performance metrics are reasonable
