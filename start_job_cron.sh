#!/bin/bash
#
# Startup script for the Job Cron Processor
#
# This script provides easy management of the job cron processor with
# different deployment options:
#
# 1. Development mode - runs in foreground with detailed logging
# 2. Production mode - runs as systemd service
# 3. Background mode - runs as background process with nohup
# 4. Docker mode - runs in container environment
#
# Usage:
#     ./start_job_cron.sh [mode] [options]
#     
# Modes:
#     dev         - Development mode (foreground, detailed logging)
#     prod        - Production mode (systemd service)
#     bg          - Background mode (nohup)
#     docker      - Docker container mode
#     stop        - Stop running processes
#     status      - Show status of running processes
#     
# Examples:
#     ./start_job_cron.sh dev                    # Development mode
#     ./start_job_cron.sh dev --interval 10      # Dev mode, 10s interval
#     ./start_job_cron.sh prod                   # Production systemd service
#     ./start_job_cron.sh bg --max-jobs 100      # Background, max 100 jobs
#     ./start_job_cron.sh stop                   # Stop all processes
#     ./start_job_cron.sh status                 # Show status
#

set -e  # Exit on any error

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JOB_CRON_SCRIPT="$SCRIPT_DIR/job_cron.py"
SERVICE_NAME="job_cron"
PID_FILE="/tmp/job_cron.pid"
LOG_FILE="$SCRIPT_DIR/logs/job_cron.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_debug() {
    echo -e "${BLUE}[DEBUG]${NC} $1"
}

# Check if Python script exists
check_script() {
    if [[ ! -f "$JOB_CRON_SCRIPT" ]]; then
        log_error "Job cron script not found: $JOB_CRON_SCRIPT"
        exit 1
    fi
}

# Check environment variables
check_environment() {
    if [[ -z "$DATABASE_URL" && -z "$POSTGRES_URL" ]]; then
        log_error "DATABASE_URL or POSTGRES_URL environment variable required"
        exit 1
    fi
    
    # Load .env file if it exists
    if [[ -f "$SCRIPT_DIR/.env" ]]; then
        log_info "Loading environment from .env file"
        set -a  # automatically export all variables
        source "$SCRIPT_DIR/.env"
        set +a
    fi
}

# Create necessary directories
setup_directories() {
    mkdir -p "$SCRIPT_DIR/logs"
    mkdir -p "$SCRIPT_DIR/temp"
}

# Get process ID if running
get_pid() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "$pid"
            return 0
        else
            rm -f "$PID_FILE"
        fi
    fi
    
    # Also check for processes by name
    pgrep -f "job_cron.py" | head -1 || true
}

# Check if service is running
is_running() {
    local pid=$(get_pid)
    [[ -n "$pid" ]]
}

# Stop running processes
stop_processes() {
    log_info "Stopping job cron processes..."
    
    # Stop systemd service if running
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        log_info "Stopping systemd service: $SERVICE_NAME"
        sudo systemctl stop "$SERVICE_NAME"
    fi
    
    # Stop background processes
    local pid=$(get_pid)
    if [[ -n "$pid" ]]; then
        log_info "Stopping process with PID: $pid"
        kill -TERM "$pid" 2>/dev/null || true
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "Force killing process $pid"
            kill -KILL "$pid" 2>/dev/null || true
        fi
        
        rm -f "$PID_FILE"
    fi
    
    # Kill any remaining processes
    pkill -f "job_cron.py" 2>/dev/null || true
    
    log_info "All job cron processes stopped"
}

# Show status
show_status() {
    log_info "Job Cron Processor Status:"
    echo
    
    # Check systemd service
    if systemctl list-unit-files --type=service | grep -q "$SERVICE_NAME"; then
        echo "📋 Systemd Service:"
        systemctl status "$SERVICE_NAME" --no-pager -l || true
        echo
    fi
    
    # Check background processes
    local pid=$(get_pid)
    if [[ -n "$pid" ]]; then
        echo "🔄 Background Process:"
        echo "   PID: $pid"
        echo "   Status: Running"
        ps -p "$pid" -o pid,ppid,cmd --no-headers || true
        echo
    else
        echo "🔄 Background Process: Not running"
        echo
    fi
    
    # Check log files
    if [[ -f "$LOG_FILE" ]]; then
        echo "📋 Recent Log Entries:"
        tail -10 "$LOG_FILE" || true
        echo
    fi
    
    # Show database connection
    echo "🗄️  Database Connection:"
    python3 -c "
import os
import sys
# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
sys.path.insert(0, '$SCRIPT_DIR/app')
try:
    from app.database import DatabaseManager
    db = DatabaseManager()
    with db.get_connection() as conn:
        print('   Status: Connected')
        with conn.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) as pending FROM processing_jobs WHERE status = %s', ('pending',))
            result = cursor.fetchone()
            print(f'   Pending Jobs: {result[\"pending\"]}')
except Exception as e:
    print(f'   Status: Error - {e}')
"
}

# Development mode
run_dev() {
    log_info "Starting job cron in development mode..."
    
    # Parse additional arguments
    local args=("$@")
    
    # Default development settings
    if [[ ! " ${args[*]} " =~ " --interval " ]]; then
        args+=(--interval 10)  # Faster polling in dev
    fi
    
    if [[ ! " ${args[*]} " =~ " --log-level " ]]; then
        args+=(--log-level DEBUG)  # More verbose logging in dev
    fi
    
    log_info "Running: python3 $JOB_CRON_SCRIPT ${args[*]}"
    exec python3 "$JOB_CRON_SCRIPT" "${args[@]}"
}

# Production mode (systemd)
run_prod() {
    log_info "Starting job cron in production mode (systemd)..."
    
    # Check if systemd service exists
    if [[ ! -f "/etc/systemd/system/$SERVICE_NAME.service" ]]; then
        log_warn "Systemd service file not found. Installing..."
        
        if [[ -f "$SCRIPT_DIR/$SERVICE_NAME.service" ]]; then
            sudo cp "$SCRIPT_DIR/$SERVICE_NAME.service" "/etc/systemd/system/"
            sudo systemctl daemon-reload
            log_info "Service file installed"
        else
            log_error "Service file not found: $SCRIPT_DIR/$SERVICE_NAME.service"
            exit 1
        fi
    fi
    
    # Enable and start service
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
    
    log_info "Production service started. Use 'systemctl status $SERVICE_NAME' to check status"
    log_info "Logs: 'journalctl -u $SERVICE_NAME -f'"
}

# Background mode
run_bg() {
    log_info "Starting job cron in background mode..."
    
    # Parse additional arguments
    local args=("$@")
    
    # Add daemon flag
    if [[ ! " ${args[*]} " =~ " --daemon " ]]; then
        args+=(--daemon)
    fi
    
    # Start in background
    nohup python3 "$JOB_CRON_SCRIPT" "${args[@]}" > "$LOG_FILE" 2>&1 &
    local pid=$!
    
    echo "$pid" > "$PID_FILE"
    
    log_info "Job cron started in background with PID: $pid"
    log_info "Log file: $LOG_FILE"
    log_info "Use './start_job_cron.sh stop' to stop"
}

# Docker mode
run_docker() {
    log_info "Starting job cron in Docker mode..."
    
    # Parse additional arguments
    local args=("$@")
    
    # Docker-specific settings
    if [[ ! " ${args[*]} " =~ " --daemon " ]]; then
        args+=(--daemon)
    fi
    
    # Run directly (Docker handles process management)
    exec python3 "$JOB_CRON_SCRIPT" "${args[@]}"
}

# Main function
main() {
    local mode="${1:-dev}"
    shift || true
    
    # Setup
    check_script
    setup_directories
    
    case "$mode" in
        "dev"|"development")
            check_environment
            if is_running; then
                log_error "Job cron is already running. Use 'stop' first."
                exit 1
            fi
            run_dev "$@"
            ;;
        "prod"|"production")
            check_environment
            run_prod "$@"
            ;;
        "bg"|"background")
            check_environment
            if is_running; then
                log_error "Job cron is already running. Use 'stop' first."
                exit 1
            fi
            run_bg "$@"
            ;;
        "docker")
            check_environment
            run_docker "$@"
            ;;
        "stop")
            stop_processes
            ;;
        "status")
            show_status
            ;;
        "restart")
            stop_processes
            sleep 2
            run_bg "$@"
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [mode] [options]"
            echo
            echo "Modes:"
            echo "  dev      - Development mode (foreground)"
            echo "  prod     - Production mode (systemd service)"
            echo "  bg       - Background mode (nohup)"
            echo "  docker   - Docker container mode"
            echo "  stop     - Stop running processes"
            echo "  status   - Show status"
            echo "  restart  - Restart in background mode"
            echo "  help     - Show this help"
            echo
            echo "Options are passed through to job_cron.py"
            echo "Run 'python3 job_cron.py --help' for available options"
            ;;
        *)
            log_error "Unknown mode: $mode"
            echo "Use '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
