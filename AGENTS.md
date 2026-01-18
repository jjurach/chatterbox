# MANDATORY AI Agent Instructions (Condensed)

**CRITICAL:** This document contains the essential, non-negotiable rules for all development tasks. You are responsible for knowing and following every rule here. Detailed explanations, full templates, and non-critical best practices are located in the `/docs` directory.

---

## 1. The Core Workflow

**MANDATORY:** For any request that involves creating or modifying code or infrastructure, you MUST follow this workflow.

**Step A: Analyze the Request & Declare Intent**
1.  **Is it a simple question?** → Answer it directly.
2.  **Is it a Trivial Change?** → Make the change directly. No documentation required.
3.  **Is it anything else?** → Announce you will create a **Project Plan**.

> **Trivial Change Definition:** Non-functional changes like fixing typos in comments or code formatting. The full definition and examples are in `docs/01_overview.md`.

**Step B: Create a Project Plan (If Required)**
- Use the `Project Plan` structure defined in Section 3.
- The plan must be detailed enough for another agent to execute.
- Save the plan to `dev_notes/project_plans/YYYY-MM-DD_HH-MM-SS_description.md`.

**Step C: AWAIT DEVELOPER APPROVAL**
- **NEVER EXECUTE A PLAN WITHOUT EXPLICIT APPROVAL.**
- Present the full Project Plan to the developer.
- "Approved", "proceed", "go ahead", "ok", or "yes" mean you can start.
- If the developer asks questions or provides feedback, answer them and then **return to a waiting state** until you receive a new, explicit approval.
- **If approval is ambiguous** (e.g., "maybe", "I think so", "probably"): Ask a follow-up clarifying question such as "I want to confirm: should I proceed with this Project Plan? Please respond with 'yes' or 'no'."

**Step D: Implement & Document Concurrently**
- Execute the approved plan step-by-step.
- After each logical change, create or update a **Change Documentation** entry in `dev_notes/changes/`. Use the structure from Section 3.

---

## 2. Project Component & Skill Routing Guide

**MANDATORY:** Use this guide to locate project components.

- **`infrastructure/`**: Terraform for AWS ECS deployment.
- **`api/openapi.yaml`**: **The API's single source of truth.** Changes here are critical and must be planned carefully as they impact all frontends and the backend.
- **`docs/`**: Detailed documentation (architecture, conventions, full templates).
- **`dev_notes/`**: All AI-generated Project Plans and Change Documentation.

---

## 2.1. Documentation Index & Quick Reference

**This project is a Home Assistant Voice Assist management CLI tool.** Use this keyword-indexed reference to quickly locate relevant documentation and commands.

### Home Assistant Management Commands

| Keyword | Document | Command | Purpose |
|---------|----------|---------|---------|
| **Conversation** | `dev_notes/DIAGNOSTICS.md` | `manage-ha assist text "query"` | Send text to voice assistant |
| **Configuration** | `docs/overview.md` | `manage-ha config view` | View full Home Assistant config |
| **Status Check** | `docs/overview.md` | `manage-ha status` | Check system health and components |
| **Services** | `docs/overview.md` | `manage-ha assist services` | List available conversation agents |
| **Error Logs** | `dev_notes/DIAGNOSTICS.md` | `manage-ha logs view --lines 100` | View error log entries |
| **Log Tail** | `dev_notes/DIAGNOSTICS.md` | `manage-ha logs tail --lines 50` | View recent error log snapshot |
| **Debug Mode** | `dev_notes/DIAGNOSTICS.md` | `manage-ha --debug assist text "query"` | Full response debugging |
| **Continue Conversation** | `dev_notes/DIAGNOSTICS.md` | `manage-ha assist continue <ID> "text"` | Resume previous conversation |
| **Retrieve State** | `dev_notes/DIAGNOSTICS.md` | `manage-ha assist continue <ID> ""` | Get conversation context |
| **Connection Test** | `docs/overview.md` | `manage-ha test-connection` | Verify Home Assistant connectivity |

### Diagnostic & Troubleshooting

| Issue | Document | Solution/Guide |
|-------|----------|----------------|
| **"2:25 PM" instead of "Copenhagen"** | `dev_notes/DIAGNOSTICS.md` (Step 1-8) + `dev_notes/project_plans/2026-01-17_assist-configuration-guide.md` | Root cause analysis decision tree; configure OpenAI/Ollama agent |
| **Understanding response types** | `dev_notes/DIAGNOSTICS.md` (Step 7) | `query_answer`, `action_done`, `error` explained with examples |
| **Complete diagnostic procedure** | `dev_notes/DIAGNOSTICS.md` | 8-step diagnostic workflow + automated script |
| **Automated diagnostics** | `scripts/diagnose_assist.sh` | Run full diagnostic suite: `./scripts/diagnose_assist.sh` |
| **Intent routing issues** | `dev_notes/DIAGNOSTICS.md` (Issue 1, Step 8) | Check logs for routing decisions |
| **Conversation agent selection** | `dev_notes/project_plans/2026-01-17_assist-configuration-guide.md` (Step 2) | Built-in vs OpenAI vs Ollama comparison |
| **Enable debug logging** | `dev_notes/project_plans/2026-01-17_assist-configuration-guide.md` (Step 4) | Add conversation logger config to YAML |

### API Client Features

| Feature | Document | Details |
|---------|----------|---------|
| **Polling responses** | `docs/api-client.md` | `poll_conversation_response()` for async responses |
| **Conversation continuity** | `docs/api-client.md` | `process_conversation(text, conversation_id)` |
| **Error log access** | `docs/api-client.md` | `get_error_log()` via `/api/error_log` endpoint |
| **Response parsing** | `docs/api-client.md` | `get_response_text()`, `is_error_response()` helpers |
| **Configuration loading** | `docs/api-client.md` | `get_config()`, `get_states()` for introspection |

### Project Architecture

| Component | Document | Purpose |
|-----------|----------|---------|
| **Package structure** | `docs/overview.md` | `ha_tools/` package with CLI entry point |
| **CLI commands** | `docs/overview.md` | `status`, `config`, `assist`, `logs`, `test-connection` |
| **Configuration** | `docs/overview.md` | API key, Home Assistant URL via secrets.json |
| **Polling feature** | `docs/api-client.md` | Automatic polling for `action_in_progress` responses |
| **Error handling** | `docs/api-client.md` | `HAApiError`, `ConfigError` exceptions |

### Configuration & Setup

| Task | Document | Instructions |
|------|----------|--------------|
| **Installation** | `docs/overview.md` | `pip install -e .` in project root |
| **Configure secrets** | `docs/overview.md` | Create `secrets.json` with API key |
| **Set Home Assistant URL** | `docs/overview.md` | Environment variable or interactive prompt |
| **Conversation agent setup** | `dev_notes/project_plans/2026-01-17_assist-configuration-guide.md` | Step 2: Configure built-in, OpenAI, or Ollama |

### Development & Testing

| Activity | Document | Process |
|----------|----------|---------|
| **Running tests** | `docs/overview.md` | Manual testing commands provided |
| **Code structure** | `docs/api-client.md`, `docs/overview.md` | Module organization and imports |
| **Adding new commands** | `docs/overview.md` | CLI pattern using Click framework |
| **Debugging responses** | `dev_notes/DIAGNOSTICS.md` | Use `--debug` flag for full output |

### Common Keywords to File Mappings

- **"polling"** → `docs/api-client.md`, `dev_notes/DIAGNOSTICS.md` (Step 7)
- **"response type"** → `dev_notes/DIAGNOSTICS.md` (Step 7), `docs/api-client.md`
- **"conversation ID"** → `dev_notes/DIAGNOSTICS.md` (Step 5-6), `docs/api-client.md`
- **"error log"** → `dev_notes/DIAGNOSTICS.md` (Step 4, 8), manage-ha logs commands
- **"debug output"** → `dev_notes/DIAGNOSTICS.md`, use `manage-ha --debug`
- **"conversation agent"** → `dev_notes/project_plans/2026-01-17_assist-configuration-guide.md` (Step 2, 3)
- **"intent routing"** → `dev_notes/DIAGNOSTICS.md` (Issue 1), Project Plan Step 1
- **"async response"** → `docs/api-client.md` (polling section), `dev_notes/DIAGNOSTICS.md`
- **"configuration"** → `docs/overview.md`, Step 3 of diagnostics
- **"services"** → `docs/overview.md`, `dev_notes/DIAGNOSTICS.md` Step 2

---

## 3. Documentation Structures (Checklists)

**MANDATORY:** All Project Plans and Change Documentation you create must include these sections. Full, detailed templates are in `docs/templates.md`.

### Project Plan Structure
- `# Project Plan: [Project Name]`
- `Objective`
- `Implementation Steps` (Detailed list of actions)
- `Success Criteria`
- `Testing Strategy`
- `Risk Assessment`

### Change Documentation Structure
- `# Change: [Brief Description]`
- `Related Project Plan`
- `Overview` of the change.
- `Files Modified` with a summary of what changed in each.
- `Impact Assessment`

---

## 4. The Unbreakable Rules

1.  **Approval is Mandatory:** This is the most important rule. Never act on a Project Plan without explicit developer approval.
2.  **Quality is Mandatory:** You MUST follow the existing code patterns, conventions, style, and typing of the files you are editing. New code should look like the old code.
3.  **Uncertainty Requires a Full Stop:** If you encounter any error, are confused by a requirement, or are unsure how to proceed, you MUST **STOP** immediately. Document the issue and ask the developer for guidance. Do not try to solve novel problems alone.
4.  **File Naming is Mandatory:** All Project Plans and Change Documentation in `dev_notes/` MUST use the `YYYY-MM-DD_HH-MM-SS_description.md` format.
5.  **Slack Notification (If Supported):** Notify using the slack-notifications MCP service each time you commit to the local git repo. See `docs/06_tools_and_integrations.md` for setup instructions. **Note:** This rule applies only to agents with MCP support (e.g., Claude Code). Agents without MCP capabilities may skip this step.

This condensed file preserves all mandatory instructions while significantly reducing the token count, making it suitable for models with smaller context windows.
