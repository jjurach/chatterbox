# Chatterbox Implementation in Gastown

## Overview

This document outlines the strategy for implementing the **Chatterbox** project using the **Gastown** multi-agent orchestration system. The implementation will follow the goals defined in the project inbox, specifically focusing on the device state machine, OTA updates, and the 12-Epic structure.

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

### 2. Epic Structure & Orchestration
The project is divided into **12 Epics**.
- **Management:** Use `@beads/bd` for task dependency management.
- **Parallelism:** Execute unrelated epics (e.g., device firmware vs. backend) in parallel using multiple agents.

#### Epic 1: OTA & Foundation
- **OTA Cadence:** Establish a reliable Over-The-Air update process.
- **Deployment Tool:** Create a tool to push selected images to specific devices.
- **Autonomous Deployment:** Agents must be able to deploy new builds to devices autonomously.
- **State Machine MVP:** Implement the basic state machine cycling through the 6 screens (N, H, S, A, W, P) to verify the display and OCR logic.

## Gastown Implementation Strategy

### 1. The Mayor's Role
The **Mayor** (`~/gt/mayor/`) will serve as the central coordinator for the Chatterbox project.
- **Responsibility:** Manage the high-level roadmap (the 12 Epics).
- **Orchestration:** Break down Epics into Convoys and Beads.
- **Oversight:** Monitor progress via `gt convoy list` and handle escalations from Witnesses/Polecats.

### 2. Work Breakdown (Beads & Convoys)

We will map the inbox goals to Gastown entities:

*   **Epics** $\rightarrow$ **Convoys** (or parent Beads)
    *   *Example:* `gt convoy create "Chatterbox Epic 1" --owner mayor/`
*   **Stories/Tasks** $\rightarrow$ **Beads**
    *   *Example:* `bd create "Implement 'N' (Orange) Screen" --tag firmware`
    *   *Example:* `bd create "Develop Python OCR Validator" --tag test --tag tools`
    *   *Example:* `bd create "Setup OTA Server" --tag infra`

### 3. Agent Workforce (Polecats)
We will utilize **Polecats** (ephemeral worker agents) for parallel execution:
- **Firmware Crew:** Agents assigned beads tagged `firmware` (e.g., ESPHome YAML, C++ logic).
- **Backend Crew:** Agents assigned beads tagged `infra` or `backend` (e.g., OTA server, HA integration).
- **QA/Tools Crew:** Agents building the OCR validator and test scripts.

### 4. Verification (Witnesses)
**Witnesses** can be deployed to run validation loops:
- **OCR Witness:** Continuously monitors the device video feed, running the OCR script to verify the physical device state matches the reported firmware state.
- **Escalation:** If the screen doesn't match the state (e.g., Red screen but state is "Sleeping"), the Witness escalates to the Mayor via `gt mail`.

## The "Living Roadmap" Strategy

Instead of manually prescribing every task, we will leverage the Mayor's ability to maintain a high-level master plan while dynamically dispatching work. The plan does **not** need to be complete before work begins.

### 1. Ingest & Analyze (The "Whole Plan")
The Mayor will ingest the full context (all 12 Epics and Device State requirements) to build a dependency graph.
*   **Input:** Provide the Mayor with the "Epic Structure" and "Screen Details" notes.
*   **Goal:** Mayor creates a top-level tracking Bead for "Chatterbox Master Plan" and child Beads for the 12 Epics.

### 2. Initialization Script & Smoke Test

Use this workflow to bootstrap the system and verify the Mayor-Polecat connection before beginning Epic 1.

#### Phase A: System Bootstrap
Run these commands in your terminal to set up the environment and the "Living Roadmap."

```bash
# 1. Initialize the Gas Town Headquarters (HQ)
# This creates the necessary town-level structure (CLAUDE.md, mayor/, .beads/) 
# in the current directory so that Gas Town knows this is your "Town."
gt install .

# 2. Initialize the Chatterbox Rig (and friends)
# Run these commands to register your repositories as Rigs in Gastown.
# This allows the Mayor to orchestrate across the entire fleet if needed.

# PRIMARY RIG:
gt rig add chatterbox git@github.com:jjurach/chatterbox.git

# SUPPORTING RIGS:
gt rig add cackle git@github.com:jjurach/cackle.git
gt rig add chatvault git@github.com:jjurach/chatvault.git
gt rig add google-personal-mcp git@github.com:jjurach/google-personal-mcp.git
gt rig add logist git@github.com:jjurach/logist.git
gt rig add oneshot git@github.com:jjurach/oneshot.git
gt rig add pigeon git@github.com:jjurach/pigeon.git
gt rig add second_voice git@github.com:jjurach/second_voice.git
gt rig add slack-agent-mcp git@github.com:jjurach/slack-agent-mcp.git
gt rig add whisper git@github.com:jjurach/whisper.git

# 3. Start the Mayor
# This launches the Mayor agent in the background/interactive session.
gt mayor attach
```

**Mayor Prompt (Copy & Paste this to the Mayor):**
> "I am initializing the Chatterbox project.
>
> **Context:**
> I have a set of inbox notes detailing 12 Epics and specific device state requirements.
>
> **Your Mission:**
> 1. Ingest these notes (I will paste them next).
> 2. Create a 'Living Roadmap' in `docs/specs/chatterbox-roadmap.md`.
> 3. Do NOT create Beads yet. Just draft the Markdown plan so I can review your understanding of the dependencies.
> 4. Once I approve the Markdown, I will authorize you to generate the Beads and start slinging work.
>
> Ready for the notes?"

*(After the Mayor confirms, paste the content of your Inbox notes)*

#### Phase B: Smoke Test ("The 2+2 Check")
Before we start complex coding, verify the orchestration pipeline.

1.  **Ask the Mayor:**
    > "Run a smoke test. I want you to spin up a Polecat agent and ask it: 'What is 2 + 2?'.
    >
    > Report back when the Polecat successfully returns the answer. This confirms our 'Sling' capability is functional."

2.  **Verify:**
    *   Did the Mayor dispatch a task?
    *   Did a generic/polecat agent pick it up?
    *   Did the answer (4) get back to the Mayor?

If this passes, the system is ready for Epic 1.

### 3. Execution Phase

Once the smoke test passes and you have approved `docs/specs/chatterbox-roadmap.md`:

**Mayor Prompt:**
> "The roadmap is approved.
> 1. Initialize the project in Beads (create the structure).
> 2. Spin up the 'Living Convoy' for Epic 1.
> 3. Identify the first 3 non-blocking tasks (e.g., Firmware scaffolding, OTA infra setup).
> 4. Sling them to agents immediately."

