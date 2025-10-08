# Basketball Data ETL & Development Script (PowerShell)
# One-stop script for ETL, server, and database operations

param(
    [Parameter(Position=0)]
    [string]$Command,
    
    [Parameter(ValueFromRemainingArguments=$true)]
    [string[]]$Arguments
)

# Colors for output
$Red = "Red"
$Green = "Green"
$Yellow = "Yellow"
$Blue = "Blue"

# Script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = $ProjectRoot

# Database configuration (matching README)
$DB_USER = "okcapplicant"
$DB_NAME = "okc"
$DB_PASSWORD = "thunder"
$DB_SCHEMA = "app"
$DB_HOST = "localhost"
$DB_PORT = "5432"

# Function to setup environment variables
function Setup-Environment {
    if (-not $env:DJANGO_SETTINGS_MODULE) {
        $env:DJANGO_SETTINGS_MODULE = "app.settings"
        Write-Host "[INFO] Setting DJANGO_SETTINGS_MODULE=app.settings" -ForegroundColor $Blue
    }
    
    if (-not $env:PYTHONPATH -or $env:PYTHONPATH -notlike "*$BackendDir*") {
        $env:PYTHONPATH = "$BackendDir;$env:PYTHONPATH"
        Write-Host "[INFO] Setting PYTHONPATH=$BackendDir" -ForegroundColor $Blue
    }
}

# Function to check if we're connected to a local development database
function Test-LocalDatabase {
    $dbUrl = $env:DATABASE_URL
    $pgHost = if ($env:PGHOST) { $env:PGHOST } else { $DB_HOST }
    
    if ($dbUrl) {
        if ($dbUrl -notlike "*localhost*" -and $dbUrl -notlike "*127.0.0.1*") {
            Write-Host "[ERROR] DATABASE_URL does not point to localhost. This may not be a development database." -ForegroundColor $Red
            Write-Host "[WARNING] Current DATABASE_URL: $dbUrl" -ForegroundColor $Yellow
            Write-Host "[WARNING] For safety, reset operations are only allowed on localhost databases." -ForegroundColor $Yellow
            exit 1
        }
    } elseif ($pgHost -ne "localhost" -and $pgHost -ne "127.0.0.1") {
        Write-Host "[ERROR] PGHOST does not point to localhost. This may not be a development database." -ForegroundColor $Red
        Write-Host "[WARNING] Current PGHOST: $pgHost" -ForegroundColor $Yellow
        Write-Host "[WARNING] For safety, reset operations are only allowed on localhost databases." -ForegroundColor $Yellow
        exit 1
    }
}

# Function to check PostgreSQL connection
function Test-DatabaseConnection {
    Write-Host "[INFO] Checking PostgreSQL connection..." -ForegroundColor $Blue
    
    if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
        Write-Host "[ERROR] psql command not found. Please install PostgreSQL client." -ForegroundColor $Red
        exit 1
    }
    
    $env:PGPASSWORD = $DB_PASSWORD
    $result = & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\q" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Cannot connect to PostgreSQL database." -ForegroundColor $Red
        Write-Host "[WARNING] Please ensure:" -ForegroundColor $Yellow
        Write-Host "  - PostgreSQL is running on $DB_HOST`:$DB_PORT"
        Write-Host "  - Database '$DB_NAME' exists"
        Write-Host "  - User '$DB_USER' exists with password '$DB_PASSWORD'"
        Write-Host "  - Schema '$DB_SCHEMA' exists and user has permissions"
        exit 1
    }
    
    Write-Host "[SUCCESS] PostgreSQL connection successful" -ForegroundColor $Green
}

# Function to show usage
function Show-Usage {
    Write-Host "[INFO] Basketball Data ETL & Development Script" -ForegroundColor $Blue
    Write-Host ""
    Write-Host "Usage: .\dev.ps1 <command> [args...]"
    Write-Host ""
    Write-Host "Commands:"
    Write-Host "  etl [args...]     Run ETL script with arguments"
    Write-Host "  run               Start Django development server"
    Write-Host "  dump              Export database snapshot to dbexport.psql"
    Write-Host "  check             Quick database health check"
    Write-Host "  reset             Reset event tables and run full ETL (dangerous)"
    Write-Host "  help              Show this help message"
    Write-Host ""
    Write-Host "ETL Examples:"
    Write-Host "  .\dev.ps1 etl --dry-run"
    Write-Host "  .\dev.ps1 etl --limit 200 --verbose"
    Write-Host "  .\dev.ps1 etl --batch-size 1000"
    Write-Host "  .\dev.ps1 etl --since 2023-11-15 --until 2023-12-01"
    Write-Host ""
    Write-Host "Other Examples:"
    Write-Host "  .\dev.ps1 run            # Start server on http://localhost:8000"
    Write-Host "  .\dev.ps1 dump           # Export database snapshot"
    Write-Host "  .\dev.ps1 check          # Quick database health check"
    Write-Host "  .\dev.ps1 reset          # Clear tables and re-import all data"
}

# ETL command
function Invoke-ETL {
    Write-Host "[SUCCESS] Running ETL script..." -ForegroundColor $Green
    Setup-Environment
    Test-DatabaseConnection
    
    Set-Location $ScriptDir
    & python load_data.py @Arguments
}

# Run server command
function Start-Server {
    Write-Host "[SUCCESS] Starting Django development server..." -ForegroundColor $Green
    Setup-Environment
    
    Set-Location $BackendDir
    Write-Host "[INFO] Server will be available at: http://localhost:8000/" -ForegroundColor $Blue
    Write-Host "[WARNING] Press Ctrl+C to stop the server" -ForegroundColor $Yellow
    & python manage.py runserver
}

# Database health check command
function Test-DatabaseHealth {
    Write-Host "[SUCCESS] Running database health check..." -ForegroundColor $Green
    Test-DatabaseConnection
    
    Write-Host "[INFO] Database Statistics:" -ForegroundColor $Blue
    Write-Host "[INFO] Schema tables:" -ForegroundColor $Blue
    $env:PGPASSWORD = $DB_PASSWORD
    & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "\dt app.*"
    
    Write-Host "[INFO] Event counts:" -ForegroundColor $Blue
    $query = @"
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
"@
    & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c $query
    
    Write-Host "[SUCCESS] Health check completed" -ForegroundColor $Green
}

# Database dump command
function Export-Database {
    Write-Host "[SUCCESS] Exporting database snapshot..." -ForegroundColor $Green
    Test-DatabaseConnection
    
    $DumpFile = Join-Path $ScriptDir "dbexport.psql"
    
    Write-Host "[INFO] Exporting database '$DB_NAME' to $DumpFile" -ForegroundColor $Blue
    
    if (Test-Path $DumpFile) {
        Write-Host "[WARNING] $DumpFile already exists. It will be overwritten." -ForegroundColor $Yellow
        $continue = Read-Host "Continue? (y/N)"
        if ($continue -ne "y" -and $continue -ne "Y") {
            Write-Host "[WARNING] Export cancelled" -ForegroundColor $Yellow
            return
        }
    }
    
    # Export with optimized parameters for portability
    $env:PGPASSWORD = $DB_PASSWORD
    $env:PGUSER = $DB_USER
    $env:PGDATABASE = $DB_NAME
    & pg_dump --host=$DB_HOST --port=$DB_PORT --schema=$DB_SCHEMA --no-owner --no-privileges --verbose | Out-File -FilePath $DumpFile -Encoding UTF8
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[SUCCESS] Database snapshot exported successfully to: $DumpFile" -ForegroundColor $Green
        
        # Show file size
        $fileSize = (Get-Item $DumpFile).Length
        Write-Host "[INFO] File size: $fileSize bytes" -ForegroundColor $Blue
        
        # Show export summary
        Write-Host "[INFO] Export summary:" -ForegroundColor $Blue
        Write-Host "  Database: $DB_NAME"
        Write-Host "  Schema: $DB_SCHEMA"
        Write-Host "  User: $DB_USER"
        Write-Host "  Output: $DumpFile"
        
        # Quick verification
        Write-Host "[INFO] Verification commands:" -ForegroundColor $Blue
        Write-Host "  Get-ChildItem '$DumpFile'"
        Write-Host "  Get-Content '$DumpFile' | Select-Object -First 20"
    } else {
        Write-Host "[ERROR] Failed to export database snapshot" -ForegroundColor $Red
        Write-Host "[WARNING] Please check database connection and permissions" -ForegroundColor $Yellow
        exit 1
    }
}

# Reset command (dangerous)
function Reset-Database {
    Write-Host "[ERROR] DANGER: This will clear all event data and re-import everything!" -ForegroundColor $Red
    Write-Host "[WARNING] This operation will:" -ForegroundColor $Yellow
    Write-Host "  1. Clear all event tables (Event, ShotEvent, PassEvent, TurnoverEvent)"
    Write-Host "  2. Re-import all data from raw_data/"
    Write-Host "  3. This action cannot be undone!"
    Write-Host ""
    
    # Check if we're on a local development database
    Test-LocalDatabase
    
    # Require exact phrase confirmation
    Write-Host "[ERROR] To confirm, please type exactly: RESET-EVENTS" -ForegroundColor $Red
    $confirmation = Read-Host "Confirmation"
    if ($confirmation -ne "RESET-EVENTS") {
        Write-Host "[WARNING] Reset cancelled (incorrect confirmation phrase)" -ForegroundColor $Yellow
        return
    }
    
    Write-Host "[SUCCESS] Proceeding with reset..." -ForegroundColor $Green
    Setup-Environment
    Test-DatabaseConnection
    
    Set-Location $ScriptDir
    
    # Clear event tables using direct SQL for better performance
    Write-Host "[INFO] Clearing event tables..." -ForegroundColor $Blue
    $env:PGPASSWORD = $DB_PASSWORD
    & psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "TRUNCATE app.turnover_events, app.pass_events, app.shot_events, app.events RESTART IDENTITY CASCADE;"
    
    Write-Host "[SUCCESS] Event tables cleared successfully" -ForegroundColor $Green
    
    # Run full ETL import
    Write-Host "[INFO] Running full ETL import..." -ForegroundColor $Blue
    & python load_data.py --verbose
    
    Write-Host "[SUCCESS] Reset completed successfully" -ForegroundColor $Green
    
    # Show final stats
    Write-Host "[INFO] Final database state:" -ForegroundColor $Blue
    Test-DatabaseHealth
}

# Main script logic
switch ($Command) {
    "etl" { Invoke-ETL }
    "run" { Start-Server }
    "check" { Test-DatabaseHealth }
    "dump" { Export-Database }
    "reset" { Reset-Database }
    "help" { Show-Usage }
    "-h" { Show-Usage }
    "--help" { Show-Usage }
    "" { Show-Usage }
    default {
        Write-Host "[ERROR] Unknown command '$Command'" -ForegroundColor $Red
        Write-Host ""
        Show-Usage
        exit 1
    }
}
