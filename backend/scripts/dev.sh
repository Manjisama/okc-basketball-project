#!/bin/bash
# Basketball Data ETL & Development Script
# One-stop script for ETL, server, and database operations

set -euo pipefail  # Exit on any error, undefined variables, or pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_ROOT"

# Database configuration (matching README)
DB_USER="okcapplicant"
DB_NAME="okc"
DB_PASSWORD="thunder"
DB_SCHEMA="app"
DB_HOST="localhost"
DB_PORT="5432"

# Function to setup environment variables
setup_env() {
    if [[ -z "${DJANGO_SETTINGS_MODULE:-}" ]]; then
        export DJANGO_SETTINGS_MODULE=app.settings
        echo -e "${BLUE}Setting DJANGO_SETTINGS_MODULE=app.settings${NC}"
    fi
    
    if [[ -z "${PYTHONPATH:-}" ]] || [[ "$PYTHONPATH" != *"$BACKEND_DIR"* ]]; then
        export PYTHONPATH="$BACKEND_DIR:$PYTHONPATH"
        echo -e "${BLUE}Setting PYTHONPATH=$BACKEND_DIR${NC}"
    fi
}

# Function to check if we're connected to a local development database
check_local_db() {
    local db_url="${DATABASE_URL:-}"
    local pg_host="${PGHOST:-$DB_HOST}"
    
    if [[ -n "$db_url" ]]; then
        if [[ "$db_url" != *"localhost"* ]] && [[ "$db_url" != *"127.0.0.1"* ]]; then
            echo -e "${RED}Error: DATABASE_URL does not point to localhost. This may not be a development database.${NC}"
            echo -e "${YELLOW}Current DATABASE_URL: $db_url${NC}"
            echo -e "${YELLOW}For safety, reset operations are only allowed on localhost databases.${NC}"
            exit 1
        fi
    elif [[ "$pg_host" != "localhost" ]] && [[ "$pg_host" != "127.0.0.1" ]]; then
        echo -e "${RED}Error: PGHOST does not point to localhost. This may not be a development database.${NC}"
        echo -e "${YELLOW}Current PGHOST: $pg_host${NC}"
        echo -e "${YELLOW}For safety, reset operations are only allowed on localhost databases.${NC}"
        exit 1
    fi
}

# Function to check PostgreSQL connection
check_db_connection() {
    echo -e "${BLUE}Checking PostgreSQL connection...${NC}"
    
    if ! command -v psql &> /dev/null; then
        echo -e "${RED}Error: psql command not found. Please install PostgreSQL client.${NC}"
        exit 1
    fi
    
    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; then
        echo -e "${RED}Error: Cannot connect to PostgreSQL database.${NC}"
        echo -e "${YELLOW}Please ensure:${NC}"
        echo -e "  - PostgreSQL is running on $DB_HOST:$DB_PORT"
        echo -e "  - Database '$DB_NAME' exists"
        echo -e "  - User '$DB_USER' exists with password '$DB_PASSWORD'"
        echo -e "  - Schema '$DB_SCHEMA' exists and user has permissions"
        exit 1
    fi
    
    echo -e "${GREEN}PostgreSQL connection successful${NC}"
}

# Function to show usage
show_usage() {
    echo -e "${BLUE}Basketball Data ETL & Development Script${NC}"
    echo ""
    echo "Usage: $0 <command> [args...]"
    echo ""
    echo "Commands:"
    echo "  etl [args...]     Run ETL script with arguments"
    echo "  run               Start Django development server"
    echo "  dump              Export database snapshot to dbexport.psql"
    echo "  check             Quick database health check"
    echo "  reset             Reset event tables and run full ETL (dangerous)"
    echo "  help              Show this help message"
    echo ""
    echo "ETL Examples:"
    echo "  $0 etl --dry-run"
    echo "  $0 etl --limit 200 --verbose"
    echo "  $0 etl --batch-size 1000"
    echo "  $0 etl --since 2023-11-15 --until 2023-12-01"
    echo ""
    echo "Other Examples:"
    echo "  $0 run            # Start server on http://localhost:8000"
    echo "  $0 dump           # Export database snapshot"
    echo "  $0 check          # Quick database health check"
    echo "  $0 reset          # Clear tables and re-import all data"
}

# ETL command
cmd_etl() {
    echo -e "${GREEN}Running ETL script...${NC}"
    setup_env
    check_db_connection
    
    cd "$SCRIPT_DIR"
    python load_data.py "$@"
}

# Run server command
cmd_run() {
    echo -e "${GREEN}Starting Django development server...${NC}"
    setup_env
    
    cd "$BACKEND_DIR"
    echo -e "${BLUE}Server will be available at: http://localhost:8000/${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
    python manage.py runserver
}

# Database health check command
cmd_check() {
    echo -e "${GREEN}Running database health check...${NC}"
    check_db_connection
    
    echo -e "${BLUE}Database Statistics:${NC}"
    
    # Check tables exist
    echo -e "${BLUE}Schema tables:${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\dt app.*'
    
    # Count events
    echo -e "${BLUE}Event counts:${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT 
            'events' as table_name, COUNT(*) as count FROM app.events
        UNION ALL
        SELECT 
            'shot_events', COUNT(*) FROM app.shot_events
        UNION ALL
        SELECT 
            'pass_events', COUNT(*) FROM app.pass_events
        UNION ALL
        SELECT 
            'turnover_events', COUNT(*) FROM app.turnover_events
        ORDER BY table_name;
    "
    
    # Show recent events
    echo -e "${BLUE}Recent events (last 5):${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT event_id, event_type, source_event_id, created_at 
        FROM app.events 
        ORDER BY created_at DESC 
        LIMIT 5;
    "
    
    # Show action distribution
    echo -e "${BLUE}Action type distribution:${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        SELECT a.code, a.name, COUNT(e.event_id) as event_count
        FROM app.actions a
        LEFT JOIN app.events e ON a.action_id = e.action_id
        GROUP BY a.action_id, a.code, a.name
        ORDER BY event_count DESC;
    "
    
    echo -e "${GREEN}Health check completed${NC}"
}

# Database dump command
cmd_dump() {
    echo -e "${GREEN}Exporting database snapshot...${NC}"
    check_db_connection
    
    DUMP_FILE="$SCRIPT_DIR/dbexport.psql"
    
    echo -e "${BLUE}Exporting database '$DB_NAME' to $DUMP_FILE${NC}"
    
    if [[ -f "$DUMP_FILE" ]]; then
        echo -e "${YELLOW}Warning: $DUMP_FILE already exists. It will be overwritten.${NC}"
        read -p "Continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Export cancelled${NC}"
            exit 0
        fi
    fi
    
    # Export with optimized parameters for portability
    if PGUSER="$DB_USER" PGPASSWORD="$DB_PASSWORD" PGDATABASE="$DB_NAME" \
       pg_dump \
       --host="$DB_HOST" \
       --port="$DB_PORT" \
       --schema="$DB_SCHEMA" \
       --no-owner \
       --no-privileges \
       --verbose \
       > "$DUMP_FILE" 2>/dev/null; then
        
        echo -e "${GREEN}Database snapshot exported successfully to: $DUMP_FILE${NC}"
        
        # Show file size
        if command -v wc &> /dev/null; then
            FILE_SIZE=$(wc -c < "$DUMP_FILE")
            if command -v numfmt &> /dev/null; then
                FILE_SIZE_HUMAN=$(numfmt --to=iec "$FILE_SIZE")
                echo -e "${BLUE}File size: $FILE_SIZE_HUMAN ($FILE_SIZE bytes)${NC}"
            else
                echo -e "${BLUE}File size: $FILE_SIZE bytes${NC}"
            fi
        fi
        
        # Show export summary
        echo -e "${BLUE}Export summary:${NC}"
        echo -e "  Database: $DB_NAME"
        echo -e "  Schema: $DB_SCHEMA"
        echo -e "  User: $DB_USER"
        echo -e "  Output: $DUMP_FILE"
        
        # Quick verification
        echo -e "${BLUE}Verification commands:${NC}"
        echo -e "  wc -c $DUMP_FILE"
        echo -e "  head -20 $DUMP_FILE"
        
    else
        echo -e "${RED}Error: Failed to export database snapshot${NC}"
        echo -e "${YELLOW}Please check database connection and permissions${NC}"
        exit 1
    fi
}

# Reset command (dangerous)
cmd_reset() {
    echo -e "${RED}DANGER: This will clear all event data and re-import everything!${NC}"
    echo -e "${YELLOW}This operation will:${NC}"
    echo -e "  1. Clear all event tables (Event, ShotEvent, PassEvent, TurnoverEvent)"
    echo -e "  2. Re-import all data from raw_data/"
    echo -e "  3. This action cannot be undone!"
    echo ""
    
    # Check if we're on a local development database
    check_local_db
    
    # Require exact phrase confirmation
    echo -e "${RED}To confirm, please type exactly: RESET-EVENTS${NC}"
    read -p "Confirmation: " -r
    if [[ $REPLY != "RESET-EVENTS" ]]; then
        echo -e "${YELLOW}Reset cancelled (incorrect confirmation phrase)${NC}"
        exit 0
    fi
    
    echo -e "${GREEN}Proceeding with reset...${NC}"
    setup_env
    check_db_connection
    
    cd "$SCRIPT_DIR"
    
    # Clear event tables using direct SQL for better performance
    echo -e "${BLUE}Clearing event tables...${NC}"
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "
        TRUNCATE app.turnover_events, app.pass_events, app.shot_events, app.events 
        RESTART IDENTITY CASCADE;
    "
    
    echo -e "${GREEN}Event tables cleared successfully${NC}"
    
    # Run full ETL import
    echo -e "${BLUE}Running full ETL import...${NC}"
    python load_data.py --verbose
    
    echo -e "${GREEN}Reset completed successfully${NC}"
    
    # Show final stats
    echo -e "${BLUE}Final database state:${NC}"
    cmd_check
}

# Main script logic
main() {
    if [[ $# -eq 0 ]]; then
        show_usage
        exit 0
    fi
    
    case "$1" in
        "etl")
            shift
            cmd_etl "$@"
            ;;
        "run")
            cmd_run
            ;;
        "check")
            cmd_check
            ;;
        "dump")
            cmd_dump
            ;;
        "reset")
            cmd_reset
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            echo -e "${RED}Error: Unknown command '$1'${NC}"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
