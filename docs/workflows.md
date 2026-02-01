# Project Workflows

This document describes development workflows specific to Cackle.

## Core Agent Workflow

All AI agents working on this project must follow the **A-E workflow** defined in [AGENTS.md](../AGENTS.md):

- **A: Analyze** - Understand the request and declare intent
- **B: Build** - Create project plan
- **C: Code** - Implement the plan
- **D: Document** - Update documentation
- **E: Evaluate** - Verify against Definition of Done

For complete workflow documentation, see the [Agent Kernel Workflows](../docs/system-prompts/workflows/).

## Testing Workflow

### Running Unit Tests
```bash
pytest tests/core/
pytest tests/services/
```

### Running Integration Tests
```bash
pytest tests/integration/
```

### Testing Wyoming Protocol
Use the `wyoming-tester` utility:
```bash
pytest tests/test_wyoming_tester.py
```

## See Also

- [AGENTS.md](../AGENTS.md) - Core A-E workflow
- [Definition of Done](definition-of-done.md) - Quality checklist
- [Architecture](architecture.md) - System design
- [Implementation Reference](implementation-reference.md) - Code patterns

---
Last Updated: 2026-02-01