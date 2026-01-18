#!/bin/bash
#
# Wyoming Voice Assistant Demo Script
#
# This script demonstrates the complete Wyoming voice assistant workflow:
# 1. Restart the server
# 2. Verify it's running
# 3. Test Wyoming endpoints with the specified WAV file
#
# Usage:
#   ./scripts/chat-demo.sh                    # Use defaults (localhost:10700, test_audio.wav)
#   ./scripts/chat-demo.sh --file my_test.wav # Use custom test file
#   ./scripts/chat-demo.sh --uri tcp://192.168.1.100:10700  # Use custom server URI
#

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEFAULT_URI="tcp://localhost:10700"
DEFAULT_FILE="$PROJECT_ROOT/tests/data/audio/test_audio.wav"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Ensure we're in the project root
cd "$PROJECT_ROOT"

# Logging functions
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $*" >&2
}

success() {
    echo -e "${GREEN}✓${NC} $*" >&2
}

error() {
    echo -e "${RED}✗${NC} $*" >&2
}

warning() {
    echo -e "${YELLOW}⚠${NC} $*" >&2
}

info() {
    echo -e "${CYAN}ℹ${NC} $*" >&2
}

header() {
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════${NC}" >&2
    echo -e "${PURPLE}$*${NC}" >&2
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════${NC}" >&2
}

# Parse command line arguments
SERVER_URI="$DEFAULT_URI"
TEST_FILE="$DEFAULT_FILE"

while [[ $# -gt 0 ]]; do
    case $1 in
        --uri|-u)
            SERVER_URI="$2"
            shift 2
            ;;
        --file|-f)
            TEST_FILE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Wyoming Voice Assistant Demo Script"
            echo ""
            echo "USAGE:"
            echo "    $0 [OPTIONS]"
            echo ""
            echo "OPTIONS:"
            echo "    -u, --uri URI          Wyoming server URI (default: $DEFAULT_URI)"
            echo "    -f, --file FILE         Test WAV file path (default: $DEFAULT_FILE)"
            echo "    -h, --help              Show this help message"
            echo ""
            echo "EXAMPLES:"
            echo "    $0"
            echo "    $0 --file my_test.wav"
            echo "    $0 --uri tcp://192.168.1.100:10700 --file custom_test.wav"
            echo ""
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate test file exists
if [[ ! -f "$TEST_FILE" ]]; then
    error "Test file does not exist: $TEST_FILE"
    exit 1
fi

header "Wyoming Voice Assistant Demo"
echo "Server URI: $SERVER_URI"
echo "Test File:  $TEST_FILE"
echo ""

# Step 1: Restart the server
header "Step 1: Restarting Server"
log "Restarting chatterbox3b-server..."

if "$SCRIPT_DIR/run-server.sh" restart; then
    success "Server restart initiated"
else
    error "Failed to restart server"
    exit 1
fi

# Wait a moment for server to fully start
log "Waiting for server to initialize..."
sleep 3

# Step 2: Verify server is running
header "Step 2: Verifying Server Status"
log "Checking server status..."

if "$SCRIPT_DIR/run-server.sh" status >/dev/null 2>&1; then
    success "Server is running"
    # Show the status output
    "$SCRIPT_DIR/run-server.sh" status 2>/dev/null || true
else
    error "Server is not running"
    echo "Check the server logs for errors:"
    echo "  $SCRIPT_DIR/run-server.sh status"
    exit 1
fi

# Step 3: Test Wyoming endpoints
header "Step 3: Testing Wyoming Endpoints"
log "Testing Wyoming pipeline with audio file..."

# Test 1: Full STT + TTS pipeline
info "Running full STT → Intent → TTS pipeline test..."
echo ""

if python -m wyoming_tester.cli --uri "$SERVER_URI" --file "$TEST_FILE" --verbose; then
    success "Full pipeline test completed successfully"
else
    error "Full pipeline test failed"
    exit 1
fi

echo ""
log "Demo completed successfully!"
echo ""
echo "Next steps you can try:"
echo "  • Run additional tests with different WAV files"
echo "  • Test with conversation context: wyoming-tester -u $SERVER_URI -f $TEST_FILE -c abc123"
echo "  • Monitor server logs: $SCRIPT_DIR/run-server.sh status"
echo "  • Check server logs: tail -f tmp/chatterbox3b-server.log"
echo ""

success "Demo script finished successfully"