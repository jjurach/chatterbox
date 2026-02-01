# Definition of Done - Cackle

**Referenced from:** [AGENTS.md](../AGENTS.md)

This document defines the "Done" criteria for the Cackle project. It extends the universal Agent Kernel Definition of Done with project-specific requirements.

## Agent Kernel Definition of Done

This project follows the Agent Kernel Definition of Done. **You MUST review these documents first:**

### Universal Requirements

See **[Universal Definition of Done](../docs/system-prompts/principles/definition-of-done.md)** for:
- Plan vs Reality Protocol
- Verification as Data
- Codebase State Integrity
- Agent Handoff
- Status tracking in project plans
- dev_notes/ change documentation requirements

### Python Requirements

See **[Python Definition of Done](../docs/system-prompts/languages/python/definition-of-done.md)** for:
- Python environment & dependencies
- Testing requirements (pytest)
- Code quality standards
- File organization
- Coverage requirements

## Project-Specific Extensions

### 1. Audio Processing Integrity

**Mandatory Checks:**
- [ ] Audio buffers are correctly handled and cleared
- [ ] Sample rates match (default 16000Hz)
- [ ] No large audio files committed to repository (use `tests/data/audio/` for small test samples)

### 2. Wyoming Protocol Compliance

**Mandatory Checks:**
- [ ] Wyoming events are correctly serialized/deserialized
- [ ] Server handles client disconnects gracefully
- [ ] Protocol version compatibility is maintained

## Pre-Commit Checklist

Before committing, verify:

**Code Quality:**
- [ ] Python formatting applied: `black .`
- [ ] Linting passes: `ruff check .`
- [ ] Type hints present
- [ ] Docstrings present

**Testing:**
- [ ] All unit tests pass: `pytest`
- [ ] Integration tests pass: `pytest tests/integration/`
- [ ] No regressions in Wyoming tester: `pytest tests/test_wyoming_tester.py`

**Documentation:**
- [ ] README updated for new features
- [ ] Architecture docs updated for design changes
- [ ] Change log created in `dev_notes/changes/`

## See Also

- [AGENTS.md](../AGENTS.md) - Core A-E workflow
- [Architecture](architecture.md) - System design
- [Implementation Reference](implementation-reference.md) - Code patterns
- [Workflows](workflows.md) - Development workflows

---
Last Updated: 2026-02-01