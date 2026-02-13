#!/bin/bash

##############################################################################
# Watch Firmware Script
#
# Monitors firmware/voice-assistant.yaml for changes and automatically
# restarts the ESPHome compilation/upload process.
#
# Usage:
#   ./scripts/watch_firmware.sh                    # Default: /dev/ttyACM0
#   ./scripts/watch_firmware.sh /dev/ttyUSB0      # Use specific device
#   ./scripts/watch_firmware.sh --ota              # Use OTA (mDNS)
#
# Press Ctrl-C to stop watching and clean up processes
#
##############################################################################

set -e

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIRMWARE_FILE="$PROJECT_ROOT/firmware/voice-assistant.yaml"
ESPHOME_PID=""

# Parse device argument (default to /dev/ttyACM0 for serial, or --ota for OTA)
DEVICE_ARG="${1:---device /dev/ttyACM0}"
if [ "$DEVICE_ARG" = "--ota" ]; then
    DEVICE_ARG=""
    UPLOAD_METHOD="OTA"
else
    UPLOAD_METHOD="Serial: $DEVICE_ARG"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

##############################################################################
# Cleanup function - called on script exit or Ctrl-C
##############################################################################
cleanup() {
    echo -e "\n${YELLOW}=== Cleaning up ===${NC}"

    # Kill ESPHome process if it's still running
    if [ -n "$ESPHOME_PID" ] && kill -0 "$ESPHOME_PID" 2>/dev/null; then
        echo -e "${YELLOW}Stopping ESPHome (PID: $ESPHOME_PID)...${NC}"
        kill "$ESPHOME_PID" 2>/dev/null || true

        # Wait a bit for graceful shutdown
        sleep 1

        # Force kill if still running
        if kill -0 "$ESPHOME_PID" 2>/dev/null; then
            echo -e "${RED}Force killing ESPHome...${NC}"
            kill -9 "$ESPHOME_PID" 2>/dev/null || true
        fi
    fi

    # Check for any orphaned esphome processes
    ORPHANED=$(pgrep -f "esphome run" 2>/dev/null || true)
    if [ -n "$ORPHANED" ]; then
        echo -e "${RED}Found orphaned ESPHome processes, cleaning up: $ORPHANED${NC}"
        for pid in $ORPHANED; do
            kill -9 "$pid" 2>/dev/null || true
        done
    fi

    echo -e "${GREEN}Cleanup complete${NC}"
}

# Set up trap to call cleanup on exit or Ctrl-C
trap cleanup EXIT INT TERM

##############################################################################
# Start ESPHome process
##############################################################################
start_esphome() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}▶ Starting ESPHome ($(date '+%H:%M:%S'))${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Start esphome in background and capture PID
    cd "$PROJECT_ROOT"
    if [ -z "$DEVICE_ARG" ]; then
        # OTA mode
        esphome run firmware/voice-assistant.yaml &
    else
        # Serial mode
        esphome run firmware/voice-assistant.yaml $DEVICE_ARG &
    fi
    ESPHOME_PID=$!

    echo -e "${BLUE}Process ID: $ESPHOME_PID${NC}"
}

##############################################################################
# Stop ESPHome process
##############################################################################
stop_esphome() {
    if [ -n "$ESPHOME_PID" ] && kill -0 "$ESPHOME_PID" 2>/dev/null; then
        echo -e "\n${YELLOW}⏹  Stopping ESPHome (PID: $ESPHOME_PID)${NC}"
        kill "$ESPHOME_PID" 2>/dev/null || true

        # Wait for process to exit
        for i in {1..10}; do
            if ! kill -0 "$ESPHOME_PID" 2>/dev/null; then
                echo -e "${GREEN}✓ ESPHome stopped${NC}"
                return 0
            fi
            sleep 0.5
        done

        # Force kill if needed
        echo -e "${RED}Force killing ESPHome${NC}"
        kill -9 "$ESPHOME_PID" 2>/dev/null || true
    fi
    ESPHOME_PID=""
}

##############################################################################
# Watch for file changes
##############################################################################
watch_files() {
    echo -e "\n${GREEN}👁️  Watching for changes...${NC}"
    echo -e "${BLUE}Files being monitored:${NC}"
    echo "  • $FIRMWARE_FILE"
    echo "  • $PROJECT_ROOT/firmware/secrets.yaml (if exists)"
    echo ""
    echo -e "${YELLOW}Press Ctrl-C to stop watching${NC}"
    echo ""

    # Create list of files to watch
    WATCH_FILES="$FIRMWARE_FILE"
    if [ -f "$PROJECT_ROOT/firmware/secrets.yaml" ]; then
        WATCH_FILES="$WATCH_FILES:$PROJECT_ROOT/firmware/secrets.yaml"
    fi

    # Use inotifywait to monitor file changes
    # Falls back to polling if inotifywait not available
    if command -v inotifywait &> /dev/null; then
        # Use inotifywait for efficient file monitoring
        while inotifywait -e modify,close_write $FIRMWARE_FILE "$PROJECT_ROOT/firmware/secrets.yaml" 2>/dev/null; do
            echo -e "\n${YELLOW}📝 File changed! Restarting ESPHome...${NC}"
            stop_esphome
            sleep 1
            start_esphome
        done
    else
        # Fallback to polling if inotifywait not available
        echo -e "${YELLOW}⚠️  inotifywait not found, using polling mode (1 second interval)${NC}"
        LAST_MTIME=$(stat -c %Y "$FIRMWARE_FILE" 2>/dev/null || stat -f %m "$FIRMWARE_FILE" 2>/dev/null || echo 0)

        while true; do
            sleep 1
            CURRENT_MTIME=$(stat -c %Y "$FIRMWARE_FILE" 2>/dev/null || stat -f %m "$FIRMWARE_FILE" 2>/dev/null || echo 0)

            if [ "$CURRENT_MTIME" != "$LAST_MTIME" ]; then
                echo -e "\n${YELLOW}📝 File changed! Restarting ESPHome...${NC}"
                stop_esphome
                sleep 1
                LAST_MTIME=$CURRENT_MTIME
                start_esphome
            fi
        done
    fi
}

##############################################################################
# Main
##############################################################################
main() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}        ${GREEN}Chatterbox Firmware Watch Script${NC}              ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}Project root:${NC}   $PROJECT_ROOT"
    echo -e "${BLUE}Config file:${NC}    $FIRMWARE_FILE"
    echo -e "${BLUE}Upload method:${NC}  $UPLOAD_METHOD"
    echo ""

    # Check if firmware file exists
    if [ ! -f "$FIRMWARE_FILE" ]; then
        echo -e "${RED}✗ Error: Firmware file not found: $FIRMWARE_FILE${NC}"
        exit 1
    fi

    # Check if esphome is installed
    if ! command -v esphome &> /dev/null; then
        echo -e "${RED}✗ Error: ESPHome not found. Install with: pip install esphome${NC}"
        exit 1
    fi

    # For serial mode, check if device exists
    if [[ "$UPLOAD_METHOD" == Serial* ]]; then
        DEVICE_PATH=$(echo "$UPLOAD_METHOD" | sed 's/Serial: //')
        if [ ! -e "$DEVICE_PATH" ]; then
            echo -e "${YELLOW}⚠️  Warning: Device $DEVICE_PATH not found yet${NC}"
            echo -e "${YELLOW}   Waiting for device to be connected...${NC}"
            echo ""
        fi
    fi

    # Start the initial esphome process
    start_esphome

    # Start watching for file changes
    watch_files
}

# Run main function
main
