# Chatterbox Project Plan

## Overview

This document outlines the implementation strategy for the **Chatterbox** project, specifically focusing on the device state machine, OTA updates, and the 12-Epic structure.

## Goals from Inbox

### 1. Device State Machine & Visuals
The Chatterbox device (Espressif Box 3B) must implement a robust state machine with distinct visual indicators (screens) for each state. These states will be validated using Python-based OCR.

| State | Color  | Screen Letter | Description |
| :--- | :--- | :--- | :--- |
| **N** | Orange | N | Before Wi-Fi (Non-functional) |
| **H** | Purple | H | Connected to Wi-Fi, waiting for Home Assistant |
| **S** | Blue | S | Sleeping / Waiting for wake word (Puppy metaphor: Sleeping) |
| **A** | Red | A | Active recording / Listening (Puppy metaphor: Attentive) |
| **W** | Yellow | W | Waiting for Home Assistant response |
| **P** | Green | P | Playing / Rendering response |

**Key Features:**
- **Wake Word & Button:** Support both audio wake word and button press. Configuration to disable audio wake word.
- **Stop/Silence:** Stop button or 20s silence threshold to end recording.
- **Audio Streaming:** Stream PCM data to Home Assistant; send end-of-transmission packet.
- **OCR Validation:** Scripts to validate the displayed screen letter matches the expected state.

#### Epic 1: OTA & Foundation
- **State Machine MVP:** Implement the basic state machine cycling through the 6 screens (N, H, S, A, W, P) to verify the display and OCR logic.
- **OCR Validator:** Implement ocr-validation tool to read /dev/video0 and to detect the letter on the screen.
- **Autonomous Deployment:** Agents must be able to deploy new builds to devices autonomously.
- **Deployment Tool:** Create a tool to push selected images to specific devices.
- **OTA Cadence:** Establish a reliable Over-The-Air update process.

# Notes:

- Add a large letter to each of the 6 cycled screens.
- We will use these letters with OCR to verify that the screen is cycling correctly.
- Create OCR validator tool based on /dev/video0 and a python, cpu-based ocr library to read that single letter.
- Agent will use this OCR validator tool in subsequent iterations of this project.
- Arduino 1.8.19 is installed on the system

