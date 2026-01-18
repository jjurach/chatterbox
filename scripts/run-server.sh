#!/bin/bash
#
# Chatterbox3B Server Runner Script
#
# This script manages the chatterbox3b-server process in the background.
# It uses a PID file for process tracking and logs all output to a dedicated log file.
#
# Usage:
#   ./scripts/run-server.sh status    # Check server status
#   ./scripts/run-server.sh start     # Start server in background
#   ./scripts/run-server.sh stop      # Stop the running server
#   ./scripts/run-server.sh restart   # Restart the server
#   ./scripts/run-server.sh help      # Show this help
#

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
PID_FILE="$PROJECT_ROOT/tmp/chatterbox3b-server.pid"
LOG_FILE="$PROJECT_ROOT/tmp/chatterbox3b-server.log"

# Configuration for venv
VENV_BIN="$PROJECT_ROOT/venv/bin"
PYTHON_BIN="$VENV_BIN/python"

# Check if venv exists
if [[ ! -f "$PYTHON_BIN" ]]; then
    error "Virtual environment not found at $PROJECT_ROOT/venv"
    exit 1
fi

SERVER_CMD="PYTHONPATH=$PROJECT_ROOT $PYTHON_BIN -m src.main"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Create tmp directory if it doesn't exist
mkdir -p tmp

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*" >&2
}

error() {
    echo -e "${RED}ERROR:${NC} $*" >&2
}

success() {
    echo -e "${GREEN}SUCCESS:${NC} $*" >&2
}

warning() {
    echo -e "${YELLOW}WARNING:${NC} $*" >&2
}

# Check if process is running
is_running() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Running
        else
            # Stale PID file
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    fi
    return 1  # Not running
}

# Get process info
get_process_info() {
    if [[ -f "$PID_FILE" ]]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            echo "PID: $pid"
            echo "Command: $(ps -p "$pid" -o comm=)"
            echo "Started: $(ps -p "$pid" -o lstart=)"
            echo "Log file: $LOG_FILE"
            return 0
        fi
    fi
    echo "Server is not running"
    return 1
}

# Status command
cmd_status() {
    log "Checking server status..."
    if is_running; then
        success "Server is running"
        get_process_info
        echo ""
        echo "To view recent logs (last 20 lines):"
        echo "  tail -n 20 $LOG_FILE"
        echo ""
        echo "To follow logs in real-time:"
        echo "  tail -f $LOG_FILE"
        echo ""
        echo "To view logs interactively:"
        echo "  less $LOG_FILE"
    else
        warning "Server is not running"
        echo "Log file: $LOG_FILE"
        echo ""
        echo "To check recent logs (if any exist):"
        echo "  tail -n 20 $LOG_FILE"
    fi
}

# Start command
cmd_start() {
    log "Starting server..."

    if is_running; then
        error "Server is already running"
        get_process_info
        exit 1
    fi

    # Start the server in background
    log "Launching server in background..."
    log "All output will be logged to: $LOG_FILE"

    # Start server with output redirection
    nohup bash -c "$SERVER_CMD" >> "$LOG_FILE" 2>&1 &
    local pid=$!

    # Wait a moment for server to start
    sleep 2

    # Check if process is still running
    if kill -0 "$pid" 2>/dev/null; then
        # Save PID
        echo $pid > "$PID_FILE"
        success "Server started successfully"
        echo "PID: $pid"
        echo "Log file: $LOG_FILE"
        echo ""
        echo "To monitor startup logs:"
        echo "  tail -f $LOG_FILE"
        echo ""
        echo "To check server status:"
        echo "  $0 status"
    else
        error "Server failed to start"
        echo "Check the log file for errors:"
        echo "  tail -n 50 $LOG_FILE"
        exit 1
    fi
}

# Stop command
cmd_stop() {
    log "Stopping server..."

    if ! is_running; then
        warning "Server is not running"
        return 0
    fi

    local pid=$(cat "$PID_FILE")
    log "Sending SIGTERM to process $pid..."

    # Try graceful shutdown first
    kill -TERM "$pid" 2>/dev/null || true

    # Wait up to 30 seconds for graceful shutdown
    local count=0
    while kill -0 "$pid" 2>/dev/null && [[ $count -lt 30 ]]; do
        sleep 1
        ((count++))
    done

    # Force kill if still running
    if kill -0 "$pid" 2>/dev/null; then
        log "Server didn't respond to SIGTERM, sending SIGKILL..."
        kill -KILL "$pid" 2>/dev/null || true
        sleep 1
    fi

    # Clean up
    rm -f "$PID_FILE"
    success "Server stopped"
    echo "Log file remains at: $LOG_FILE"
    echo ""
    echo "To view shutdown logs:"
    echo "  tail -n 20 $LOG_FILE"
}

# Restart command
cmd_restart() {
    log "Restarting server..."
    cmd_stop
    sleep 2
    cmd_start
}

# Help command
cmd_help() {
    cat << EOF
Chatterbox3B Server Runner Script

USAGE:
    $0 <command>

COMMANDS:
    status    Check if server is running and show process info
    start     Start the server in background
    stop      Stop the running server gracefully
    restart   Restart the server (stop then start)
    help      Show this help message

FILES:
    PID file: $PID_FILE
    Log file: $LOG_FILE

EXAMPLES:
    $0 status
    $0 start
    $0 stop
    $0 restart

LOGGING:
    All server output is appended to: $LOG_FILE
    View recent logs: tail -n 20 $LOG_FILE
    Follow logs: tail -f $LOG_FILE
    View interactively: less $LOG_FILE

NOTES:
    - Server must be run from the project root directory
    - Make sure 'chatterbox3b-server' command is available (run 'pip install -e .')
    - Log file will grow over time; consider log rotation for long-term use
EOF
}

# Main command dispatcher
case "${1:-help}" in
    status)
        cmd_status
        ;;
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        error "Unknown command: $1"
        echo ""
        cmd_help
        exit 1
        ;;
esac