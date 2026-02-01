# Project Guidelines: Cackle

This document provides project-specific guidelines for Cackle (Chatterbox).

## Project Overview

Cackle is a conversational AI agent framework with STT, TTS, and Wyoming protocol support.

## Project Structure

- `cackle/`: Core library code
- `src/`: Application entry points
- `tests/`: Test suite
- `docs/`: Documentation
- `dev_notes/`: Planning and change logs

## Development Guidelines

- **Language:** Python 3.11+
- **Style:** Follow PEP 8 (use `black` and `ruff`)
- **Testing:** Mandatory `pytest` for all new features
- **Type Hints:** Required for all new code

## Prohibited Actions

- Do NOT hardcode API keys or secrets
- Do NOT commit large audio files to the repository
- Do NOT modify files in `docs/system-prompts/`

## Stopping and Asking for Help

Stop and ask for help if:
- You encounter an architectural conflict
- You are unsure about a security implication
- A tool is behaving unexpectedly

## See Also

- [AGENTS.md](../AGENTS.md) - Core workflow
- [Quickstart](quickstart.md) - Getting started
- [Architecture](architecture.md) - System design
- [Definition of Done](definition-of-done.md) - Quality standards

---
Last Updated: 2026-02-01
