#!/bin/bash
#
# Wyoming Voice Assistant Demo Script
#
# This script tests the Wyoming voice assistant by running the pipeline
# against an already-running server.
#
# PREREQUISITES:
#   - Server must already be running (start it separately with: bash scripts/run-server.sh start)
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

VENV_DIR=$SCRIPT_DIR/../venv
test -d "$VENV_DIR/bin" && . "$VENV_DIR/bin/activate"

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
PIPER_DEMO_MODE=false
PIPER_TEXT="Hello, this is a test of the Piper text-to-speech system with caching."

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
        --piper-demo)
            PIPER_DEMO_MODE=true
            shift
            ;;
        --piper-text)
            PIPER_TEXT="$2"
            shift 2
            ;;
        --help|-h)
            echo "Wyoming Voice Assistant Demo Script"
            echo ""
            echo "USAGE:"
            echo "    $0 [OPTIONS]"
            echo ""
            echo "PREREQUISITES (for Wyoming pipeline):"
            echo "    Server must be running. Start it with:"
            echo "      bash scripts/run-server.sh start"
            echo ""
            echo "OPTIONS:"
            echo "    -u, --uri URI          Wyoming server URI (default: $DEFAULT_URI)"
            echo "    -f, --file FILE        Test WAV file path (default: $DEFAULT_FILE)"
            echo "    --piper-demo           Run Piper TTS demo instead of Wyoming pipeline"
            echo "    --piper-text TEXT      Text to synthesize for Piper demo (default: test message)"
            echo "    -h, --help             Show this help message"
            echo ""
            echo "EXAMPLES:"
            echo "    $0"
            echo "    $0 --file my_test.wav"
            echo "    $0 --uri tcp://192.168.1.100:10700"
            echo "    $0 --piper-demo"
            echo "    $0 --piper-demo --piper-text 'Custom message to synthesize'"
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

# Check if we're in Piper demo mode
if [[ "$PIPER_DEMO_MODE" == "true" ]]; then
    header "Piper TTS Demo with Caching"
    echo "Text: $PIPER_TEXT"
    echo ""

    # Set up default Piper model paths
    PIPER_MODEL_DIR="$PROJECT_ROOT/tmp/piper-voices-model"
    MODEL_NAME="en_US-amy-medium"
    MODEL_PATH="$PIPER_MODEL_DIR/en/en_US/amy/medium/${MODEL_NAME}.onnx"
    CONFIG_PATH="$PIPER_MODEL_DIR/en/en_US/amy/medium/${MODEL_NAME}.onnx.json"

    # Check if Piper model exists
    if [[ ! -f "$MODEL_PATH" ]]; then
        error "Piper model not found: $MODEL_PATH"
        echo ""
        echo "To download Piper models, run the download script or check tmp/piper-voices-model/"
        exit 1
    fi

    if [[ ! -f "$CONFIG_PATH" ]]; then
        error "Piper config not found: $CONFIG_PATH"
        echo ""
        echo "To download Piper models, run the download script or check tmp/piper-voices-model/"
        exit 1
    fi

    success "Piper model found: $MODEL_NAME"
    echo ""

    # Run Piper demo
    header "Running Piper TTS Demo"
    log "Synthesizing text with caching..."
    echo ""

    if python "$SCRIPT_DIR/piper_demo.py" "$PIPER_TEXT" \
        --model-path "$MODEL_PATH" \
        --config-path "$CONFIG_PATH"; then
        success "Piper TTS demo completed successfully"
    else
        error "Piper TTS demo failed"
        exit 1
    fi

    echo ""
    success "Piper demo script finished successfully"
    exit 0
fi

# Wyoming pipeline mode (original functionality)
# Validate test file exists
if [[ ! -f "$TEST_FILE" ]]; then
    error "Test file does not exist: $TEST_FILE"
    exit 1
fi

header "Wyoming Voice Assistant Demo"
echo "Server URI: $SERVER_URI"
echo "Test File:  $TEST_FILE"
echo ""

# Check if server is running
header "Checking Server"
log "Verifying server is accessible at $SERVER_URI..."

# Extract host and port from URI
if [[ $SERVER_URI =~ tcp://([^:]+):([0-9]+) ]]; then
    HOST="${BASH_REMATCH[1]}"
    PORT="${BASH_REMATCH[2]}"
else
    error "Invalid server URI format: $SERVER_URI"
    echo "Expected format: tcp://host:port"
    exit 1
fi

# Check if server is listening
if ! nc -z -w 2 "$HOST" "$PORT" 2>/dev/null; then
    error "Server is not running at $HOST:$PORT"
    echo ""
    echo "To start the server, run:"
    echo "  bash scripts/run-server.sh start"
    exit 1
fi

success "Server is running and accessible"
echo ""

# Run test
header "Testing Wyoming Pipeline"
log "Testing STT → LLM → TTS pipeline with audio file..."
echo ""

if python -m wyoming_tester.cli --uri "$SERVER_URI" --file "$TEST_FILE" --verbose; then
    success "Pipeline test completed successfully"
else
    error "Pipeline test failed"
    exit 1
fi

echo ""
success "Demo script finished successfully"