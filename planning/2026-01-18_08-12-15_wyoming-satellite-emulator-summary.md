# Wyoming Satellite Emulator - Implementation Summary

**Plan:** `planning/2026-01-18_08-12-15_wyoming-satellite-emulator-plan-plan.md`
**Changes Doc:** `dev_notes/changes/2026-01-18_14-35-00_wyoming-satellite-emulation-fix.md`
**Status:** ✓ Implemented
**Date:** 2026-01-18

## Implementation Details



## Overview

Fixed the Wyoming test client to properly emulate ESP32 satellite behavior by removing incorrect protocol usage (Transcribe event) and implementing auto-transcription on the server side when AudioStop is received. This resolves "Unhandled event type" protocol errors and enables the full voice assistant pipeline (STT → LLM → TTS) to work correctly.



---
*Summary generated from dev_notes/changes/ documentation*
