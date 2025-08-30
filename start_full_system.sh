#!/bin/bash
#
# Complete system startup script for Business Insights AI
#
# This script starts both the FastAPI server and the job processing cron system.
#
# Usage:
#     ./start_full_system.sh [mode] [cron-options]
#     
# Modes:
#     dev         - Development mode (both services in separate terminals)
#     bg          - Background mode (both services as background processes)
#     prod        - Production mode (systemd services)
#     stop        - Stop all services
#     status      - Show status of all services
#     
# Examples:
#     ./start_full_system.sh dev                    # Development mode
#     ./start_full_system.sh bg --interval 10       # Background with custom interval
#     ./start_full_system.sh prod                   # Production systemd services
#     ./start_full_system.sh stop                   # Stop everything
#     ./start_full_system.sh status                 # Show status
#

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_PID_FILE="/tmp/fastapi_server.pid"
CRON_PID_FILE="/tmp/job_cron.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if server is running
is_server_running() {
    if [[ -f "$SERVER_PID_FILE" ]]; then
        local pid=$(cat "$SERVER_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$SERVER_PID_FILE"
        fi
    fi
    
    # Also check for uvicorn processes
    pgrep -f "uvicorn.*app.main:app" > /dev/null 2>&1
}

# Check if cron is running
is_cron_running() {
    local pid
    if [[ -f "$CRON_PID_FILE" ]]; then
        pid=$(cat "$CRON_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0
        else
            rm -f "$CRON_PID_FILE"
        fi
    fi
    
    # Also check for processes by name
    pgrep -f "job_cron.py" > /dev/null 2>&1
}

# Get server PID
get_server_pid() {
    if [[ -f "$SERVER_PID_FILE" ]]; then
        local pid=$(cat "$SERVER_PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "$pid"
            return 0
        else
            rm -f "$SERVER_PID_FILE"
        fi
    fi
    
    pgrep -f "uvicorn.*app.main:app" | head -1 || true
}

# Stop all services
stop_all() {
    log_info "Stopping all Business Insights AI services..."
    
    # Stop job cron
    log_info "Stopping job processing cron..."
    "$SCRIPT_DIR/start_job_cron.sh" stop || true
    
    # Stop FastAPI server
    local server_pid=$(get_server_pid)
    if [[ -n "$server_pid" ]]; then
        log_info "Stopping FastAPI server (PID: $server_pid)..."
        kill -TERM "$server_pid" 2>/dev/null || true
        
        # Wait for graceful shutdown
        for i in {1..10}; do
            if ! ps -p "$server_pid" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Force kill if still running
        if ps -p "$server_pid" > /dev/null 2>&1; then
            log_warn "Force killing server process $server_pid"
            kill -KILL "$server_pid" 2>/dev/null || true
        fi
        
        rm -f "$SERVER_PID_FILE"
    fi
    
    # Kill any remaining processes
    pkill -f "uvicorn.*app.main:app" 2>/dev/null || true
    pkill -f "start_server.py" 2>/dev/null || true
    
    log_info "All services stopped"
}

# Show status of all services
show_status() {
    log_info "Business Insights AI - System Status"
    echo
    
    # FastAPI Server Status
    echo "🌐 FastAPI Server:"
    if is_server_running; then
        local server_pid=$(get_server_pid)
        echo "   Status: Running (PID: $server_pid)"
        echo "   URL: http://localhost:8000"
        echo "   Health: http://localhost:8000/health"
    else
        echo "   Status: Not running"
    fi
    echo
    
    # Job Cron Status
    echo "⚡ Job Processing Cron:"
    "$SCRIPT_DIR/start_job_cron.sh" status
    echo
    
    # Quick system check
    echo "🔧 System Check:"
    if [[ -n "${DATABASE_URL:-}${POSTGRES_URL:-}" ]]; then
        echo "   Database: Configured ✅"
    else
        echo "   Database: Not configured ❌"
    fi
    
    if [[ -n "${AZURE_OPENAI_API_KEY:-}" ]]; then
        echo "   Azure OpenAI: Configured ✅"
    else
        echo "   Azure OpenAI: Not configured ❌"
    fi
}

# Development mode - start both in separate terminals
start_dev() {
    log_info "Starting Business Insights AI in development mode..."
    
    # Check if services are already running
    if is_server_running; then
        log_error "FastAPI server is already running. Use 'stop' first."
        exit 1
    fi
    
    if is_cron_running; then
        log_error "Job cron is already running. Use 'stop' first."
        exit 1
    fi
    
    log_info "This will open two terminal windows:"
    log_info "1. FastAPI Server (http://localhost:8000)"
    log_info "2. Job Processing Cron"
    echo
    
    # Parse cron arguments
    local cron_args=("$@")
    if [[ ! " ${cron_args[*]} " =~ " --interval " ]]; then
        cron_args+=(--interval 10)  # Faster polling in dev
    fi
    
    # Start server in new terminal
    if command -v gnome-terminal > /dev/null 2>&1; then
        gnome-terminal --title="FastAPI Server" -- bash -c "cd '$SCRIPT_DIR' && python start_server.py; read -p 'Press Enter to close...'"
        gnome-terminal --title="Job Cron" -- bash -c "cd '$SCRIPT_DIR' && ./start_job_cron.sh dev ${cron_args[*]}; read -p 'Press Enter to close...'"
    elif command -v xterm > /dev/null 2>&1; then
        xterm -title "FastAPI Server" -e "cd '$SCRIPT_DIR' && python start_server.py; read -p 'Press Enter to close...'" &
        xterm -title "Job Cron" -e "cd '$SCRIPT_DIR' && ./start_job_cron.sh dev ${cron_args[*]}; read -p 'Press Enter to close...'" &
    else
        log_warn "No terminal emulator found. Starting in background mode instead."
        start_bg "$@"
        return
    fi
    
    sleep 2
    log_info "Development services started in separate terminals"
    log_info "FastAPI Server: http://localhost:8000"
    log_info "Use './start_full_system.sh status' to check status"
    log_info "Use './start_full_system.sh stop' to stop all services"
}

# Background mode - start both as background processes
start_bg() {
    log_info "Starting Business Insights AI in background mode..."
    
    # Check if services are already running
    if is_server_running; then
        log_error "FastAPI server is already running. Use 'stop' first."
        exit 1
    fi
    
    if is_cron_running; then
        log_error "Job cron is already running. Use 'stop' first."
        exit 1
    fi
    
    # Create logs directory
    mkdir -p "$SCRIPT_DIR/logs"
    
    # Start FastAPI server in background
    log_info "Starting FastAPI server in background..."
    nohup python "$SCRIPT_DIR/start_server.py" > "$SCRIPT_DIR/logs/server.log" 2>&1 &
    local server_pid=$!
    echo "$server_pid" > "$SERVER_PID_FILE"
    
    # Wait a moment for server to start
    sleep 3
    
    # Start job cron in background
    log_info "Starting job cron in background..."
    "$SCRIPT_DIR/start_job_cron.sh" bg "$@"
    
    # Verify both are running
    sleep 2
    if is_server_running && is_cron_running; then
        log_info "✅ All services started successfully"
        log_info "FastAPI Server: http://localhost:8000 (PID: $server_pid)"
        log_info "Server logs: $SCRIPT_DIR/logs/server.log"
        log_info "Cron logs: $SCRIPT_DIR/logs/job_cron.log"
        echo
        log_info "Use './start_full_system.sh status' to check status"
        log_info "Use './start_full_system.sh stop' to stop all services"
    else
        log_error "Failed to start one or more services"
        stop_all
        exit 1
    fi
}

# Production mode - systemd services
start_prod() {
    log_info "Starting Business Insights AI in production mode..."
    
    # This would set up systemd services for both
    log_warn "Production mode setup:"
    log_info "1. FastAPI server should be managed by your process manager (PM2, systemd, etc.)"
    log_info "2. Starting job cron as systemd service..."
    
    "$SCRIPT_DIR/start_job_cron.sh" prod
    
    log_info "✅ Job processing cron started as systemd service"
    log_info "💡 Make sure to also start your FastAPI server with your process manager"
    log_info "Example: systemctl start fastapi-server"
}

# Main function
main() {
    local mode="${1:-dev}"
    shift || true
    
    case "$mode" in
        "dev"|"development")
            start_dev "$@"
            ;;
        "bg"|"background")
            start_bg "$@"
            ;;
        "prod"|"production")
            start_prod "$@"
            ;;
        "stop")
            stop_all
            ;;
        "status")
            show_status
            ;;
        "restart")
            stop_all
            sleep 2
            start_bg "$@"
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [mode] [cron-options]"
            echo
            echo "Modes:"
            echo "  dev      - Development mode (separate terminals)"
            echo "  bg       - Background mode (background processes)"
            echo "  prod     - Production mode (systemd services)"
            echo "  stop     - Stop all services"
            echo "  status   - Show status of all services"
            echo "  restart  - Restart in background mode"
            echo "  help     - Show this help"
            echo
            echo "Cron options are passed through to start_job_cron.sh"
            echo "Example: $0 dev --interval 5 --max-jobs 10"
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
