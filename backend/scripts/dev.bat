@echo off
REM Basketball Data ETL & Development Script (Windows)
REM One-stop script for ETL, server, and database operations

setlocal enabledelayedexpansion

REM Colors for output (Windows doesn't support colors in batch, but we'll use echo)
set "RED=[ERROR]"
set "GREEN=[SUCCESS]"
set "YELLOW=[WARNING]"
set "BLUE=[INFO]"

REM Script directory
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%..\"
set "BACKEND_DIR=%PROJECT_ROOT%"

REM Database configuration (matching README)
set "DB_USER=okcapplicant"
set "DB_NAME=okc"
set "DB_PASSWORD=thunder"
set "DB_SCHEMA=app"
set "DB_HOST=localhost"
set "DB_PORT=5432"

REM Function to setup environment variables
:setup_env
if "%DJANGO_SETTINGS_MODULE%"=="" (
    set "DJANGO_SETTINGS_MODULE=app.settings"
    echo %BLUE% Setting DJANGO_SETTINGS_MODULE=app.settings
)

echo %PYTHONPATH% | findstr /C:"%BACKEND_DIR%" >nul
if errorlevel 1 (
    set "PYTHONPATH=%BACKEND_DIR%;%PYTHONPATH%"
    echo %BLUE% Setting PYTHONPATH=%BACKEND_DIR%
)
goto :eof

REM Function to check if we're connected to a local development database
:check_local_db
if not "%DATABASE_URL%"=="" (
    echo %DATABASE_URL% | findstr /C:"localhost" >nul
    if errorlevel 1 (
        echo %DATABASE_URL% | findstr /C:"127.0.0.1" >nul
        if errorlevel 1 (
            echo %RED% Error: DATABASE_URL does not point to localhost. This may not be a development database.
            echo %YELLOW% Current DATABASE_URL: %DATABASE_URL%
            echo %YELLOW% For safety, reset operations are only allowed on localhost databases.
            exit /b 1
        )
    )
) else (
    if not "%PGHOST%"=="localhost" (
        if not "%PGHOST%"=="127.0.0.1" (
            echo %RED% Error: PGHOST does not point to localhost. This may not be a development database.
            echo %YELLOW% Current PGHOST: %PGHOST%
            echo %YELLOW% For safety, reset operations are only allowed on localhost databases.
            exit /b 1
        )
    )
)
goto :eof

REM Function to check PostgreSQL connection
:check_db_connection
echo %BLUE% Checking PostgreSQL connection...

where psql >nul 2>&1
if errorlevel 1 (
    echo %RED% Error: psql command not found. Please install PostgreSQL client.
    exit /b 1
)

set "PGPASSWORD=%DB_PASSWORD%"
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\q" >nul 2>&1
if errorlevel 1 (
    echo %RED% Error: Cannot connect to PostgreSQL database.
    echo %YELLOW% Please ensure:
    echo   - PostgreSQL is running on %DB_HOST%:%DB_PORT%
    echo   - Database '%DB_NAME%' exists
    echo   - User '%DB_USER%' exists with password '%DB_PASSWORD%'
    echo   - Schema '%DB_SCHEMA%' exists and user has permissions
    exit /b 1
)

echo %GREEN% PostgreSQL connection successful
goto :eof

REM Function to show usage
:show_usage
echo %BLUE% Basketball Data ETL ^& Development Script
echo.
echo Usage: %~nx0 ^<command^> [args...]
echo.
echo Commands:
echo   etl [args...]     Run ETL script with arguments
echo   run               Start Django development server
echo   dump              Export database snapshot to dbexport.psql
echo   check             Quick database health check
echo   reset             Reset event tables and run full ETL ^(dangerous^)
echo   help              Show this help message
echo.
echo ETL Examples:
echo   %~nx0 etl --dry-run
echo   %~nx0 etl --limit 200 --verbose
echo   %~nx0 etl --batch-size 1000
echo   %~nx0 etl --since 2023-11-15 --until 2023-12-01
echo.
echo Other Examples:
echo   %~nx0 run            # Start server on http://localhost:8000
echo   %~nx0 dump           # Export database snapshot
echo   %~nx0 check          # Quick database health check
echo   %~nx0 reset          # Clear tables and re-import all data
goto :eof

REM ETL command
:cmd_etl
echo %GREEN% Running ETL script...
call :setup_env
call :check_db_connection

cd /d "%SCRIPT_DIR%"
python load_data.py %*
goto :eof

REM Run server command
:cmd_run
echo %GREEN% Starting Django development server...
call :setup_env

cd /d "%BACKEND_DIR%"
echo %BLUE% Server will be available at: http://localhost:8000/
echo %YELLOW% Press Ctrl+C to stop the server
python manage.py runserver
goto :eof

REM Database health check command
:cmd_check
echo %GREEN% Running database health check...
call :check_db_connection

echo %BLUE% Database Statistics:
echo %BLUE% Schema tables:
set "PGPASSWORD=%DB_PASSWORD%"
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "\dt app.*"

echo %BLUE% Event counts:
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "SELECT 'events' as table_name, COUNT(*) as count FROM app.events UNION ALL SELECT 'shot_events', COUNT(*) FROM app.shot_events UNION ALL SELECT 'pass_events', COUNT(*) FROM app.pass_events UNION ALL SELECT 'turnover_events', COUNT(*) FROM app.turnover_events ORDER BY table_name;"

echo %GREEN% Health check completed
goto :eof

REM Database dump command
:cmd_dump
echo %GREEN% Exporting database snapshot...
call :check_db_connection

set "DUMP_FILE=%SCRIPT_DIR%dbexport.psql"

echo %BLUE% Exporting database '%DB_NAME%' to %DUMP_FILE%

if exist "%DUMP_FILE%" (
    echo %YELLOW% Warning: %DUMP_FILE% already exists. It will be overwritten.
    set /p "continue=Continue? (y/N): "
    if /i not "!continue!"=="y" (
        echo %YELLOW% Export cancelled
        exit /b 0
    )
)

REM Export with optimized parameters for portability
set "PGPASSWORD=%DB_PASSWORD%"
set "PGUSER=%DB_USER%"
set "PGDATABASE=%DB_NAME%"
pg_dump --host=%DB_HOST% --port=%DB_PORT% --schema=%DB_SCHEMA% --no-owner --no-privileges --verbose > "%DUMP_FILE%" 2>nul
if errorlevel 1 (
    echo %RED% Error: Failed to export database snapshot
    echo %YELLOW% Please check database connection and permissions
    exit /b 1
)

echo %GREEN% Database snapshot exported successfully to: %DUMP_FILE%

REM Show file size
for %%A in ("%DUMP_FILE%") do echo %BLUE% File size: %%~zA bytes

REM Show export summary
echo %BLUE% Export summary:
echo   Database: %DB_NAME%
echo   Schema: %DB_SCHEMA%
echo   User: %DB_USER%
echo   Output: %DUMP_FILE%

echo %BLUE% Verification commands:
echo   dir "%DUMP_FILE%"
echo   more +1 "%DUMP_FILE%" ^| head -20
goto :eof

REM Reset command (dangerous)
:cmd_reset
echo %RED% DANGER: This will clear all event data and re-import everything!
echo %YELLOW% This operation will:
echo   1. Clear all event tables ^(Event, ShotEvent, PassEvent, TurnoverEvent^)
echo   2. Re-import all data from raw_data/
echo   3. This action cannot be undone!
echo.

REM Check if we're on a local development database
call :check_local_db

REM Require exact phrase confirmation
echo %RED% To confirm, please type exactly: RESET-EVENTS
set /p "confirmation=Confirmation: "
if not "!confirmation!"=="RESET-EVENTS" (
    echo %YELLOW% Reset cancelled ^(incorrect confirmation phrase^)
    exit /b 0
)

echo %GREEN% Proceeding with reset...
call :setup_env
call :check_db_connection

cd /d "%SCRIPT_DIR%"

REM Clear event tables using direct SQL for better performance
echo %BLUE% Clearing event tables...
set "PGPASSWORD=%DB_PASSWORD%"
psql -h %DB_HOST% -p %DB_PORT% -U %DB_USER% -d %DB_NAME% -c "TRUNCATE app.turnover_events, app.pass_events, app.shot_events, app.events RESTART IDENTITY CASCADE;"

echo %GREEN% Event tables cleared successfully

REM Run full ETL import
echo %BLUE% Running full ETL import...
python load_data.py --verbose

echo %GREEN% Reset completed successfully

REM Show final stats
echo %BLUE% Final database state:
call :cmd_check
goto :eof

REM Main script logic
:main
if "%~1"=="" (
    call :show_usage
    exit /b 0
)

if "%~1"=="etl" (
    shift
    call :cmd_etl %*
    goto :eof
)

if "%~1"=="run" (
    call :cmd_run
    goto :eof
)

if "%~1"=="check" (
    call :cmd_check
    goto :eof
)

if "%~1"=="dump" (
    call :cmd_dump
    goto :eof
)

if "%~1"=="reset" (
    call :cmd_reset
    goto :eof
)

if "%~1"=="help" (
    call :show_usage
    goto :eof
)

if "%~1"=="-h" (
    call :show_usage
    goto :eof
)

if "%~1"=="--help" (
    call :show_usage
    goto :eof
)

echo %RED% Error: Unknown command '%~1'
echo.
call :show_usage
exit /b 1

REM Run main function with all arguments
call :main %*
exit /b %errorlevel%
