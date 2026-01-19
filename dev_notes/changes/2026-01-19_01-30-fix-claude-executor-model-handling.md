# Change: Remove Forced Default Model for Claude Executor

**Date**: 2026-01-19
**Status**: ✅ COMPLETE
**Related Project Plan**: `/dev_notes/project_plans/2026-01-19_01-15-fix-claude-executor-model-handling.md`

---

## Overview

Removed forced default model assignment across four files in the oneshot project. Now when users don't specify a model with `--worker-model` or `--auditor-model`, the executor passes `None`/empty to the claude command, allowing Claude to use its own default model selection.

The key fix: The `--model` flag is now only included in the claude command when a model is explicitly provided. Without it, claude works with its own defaults instead of a forced (potentially outdated or unavailable) model.

---

## Problem

When running:
```bash
oneshot --verbose --debug --executor claude "what is the capital of greece?"
```

The system forced Claude to use `claude-3-5-sonnet-20241022`, which resulted in:
```
API Error: 404 {"type":"error","error":{"type":"not_found_error","message":"model: claude-3-5-sonnet-20241022"},...}
```

The issue was that FOUR separate mechanisms were forcing a model:
1. CLI argument parser defaults
2. Config file loader and `apply_executor_defaults()`
3. ProviderConfig validation
4. Command-line building

---

## Files Modified

### 1. `/home/phaedrus/AiSpace/oneshot/src/cli/oneshot_cli.py`
- Removed forced model assignments in worker and auditor provider creation
- Claude executor now uses `model=None` when no model is explicitly provided
- **Commits**: 34e7d6f, cc45780

### 2. `/home/phaedrus/AiSpace/oneshot/src/oneshot/config.py`
- Modified `apply_executor_defaults()` to NOT force models for claude executor
- Removed: `config["worker_model"] = "claude-3-5-haiku-20241022"`
- **Commit**: cc45780

### 3. `/home/phaedrus/AiSpace/oneshot/src/oneshot/providers/__init__.py`
- Removed model requirement validation from `ProviderConfig.__post_init__()`
- Removed: `raise ValueError("claude executor requires 'model' field")`
- Now allows model to be optional for claude executor
- **Commit**: cc45780

### 4. `/home/phaedrus/AiSpace/oneshot/src/oneshot/oneshot.py`
- Modified `call_executor()` function to conditionally include `--model` flag
- Modified `call_executor_async()` function with same logic
- **Before**: Always `claude -p --model {model} --dangerously-skip-permissions`
- **After**: Only includes `--model` if model is provided:
  ```bash
  claude -p --dangerously-skip-permissions  # No model
  # OR
  claude -p --model claude-opus-4-1 --dangerously-skip-permissions  # With model
  ```
- **Commit**: d88d5d2

---

## Impact Assessment

### Behavioral Changes

1. **Command-line without model flag**:
   - **Before**: Claude forced to use hardcoded model → 404 error
   - **After**: Claude uses its own default model → Success ✅

2. **Command-line with explicit model**:
   - **Before**: Model specified in command
   - **After**: Model specified in command (unchanged) ✅

3. **Config file influence**:
   - **Before**: Config file could force models
   - **After**: Config file can provide models, but not required

### Test Results

Tested with:
```bash
oneshot --executor claude "what is the capital of greece?"
```

**Output**:
```
[DEBUG] Command: claude -p --dangerously-skip-permissions
[BUFFER] Worker Output:
  ```json
  {
    "status": "DONE",
    "result": "Athens",
    "confidence": "high",
    ...
  }
  ```
```

✅ Success! Claude responded correctly without forced model.

---

## Git Commits

1. **34e7d6f**: Fix claude executor model handling: allow default model selection
   - Initial CLI-level fixes

2. **cc45780**: Fix: Remove ALL forced default model assignments for claude executor
   - Config, provider validation, and CLI fixes

3. **d88d5d2**: Fix: Make --model flag optional in claude command invocation
   - Command-building logic to conditionally include `--model`

---

## Configuration Note

Users who have existing `~/.oneshot.json` files with outdated models (e.g., `claude-3-5-sonnet-20241022`) should:

**Option 1**: Clear model fields in ~/.oneshot.json:
```json
{
  "executor": "claude",
  "worker_model": null,
  "auditor_model": null,
  ...
}
```

**Option 2**: Update to valid models:
```json
{
  "executor": "claude",
  "worker_model": "claude-opus-4-1",
  "auditor_model": "claude-opus-4-1",
  ...
}
```

**Option 3**: Remove ~/.oneshot.json entirely to use defaults

---

## Risk Assessment

### Low Risk

- **Why**: Removing forced configuration, not adding complexity
- **Effect**: Reduces assumptions about model availability
- **Reversibility**: Easy to revert if needed
- **Other executors**: Unchanged (cline, aider still work normally)

### Mitigation

- Explicit model specification via CLI still works: `--worker-model claude-opus-4-1`
- Configuration files can still set models
- Only removes forced defaults, doesn't prevent model selection

---

## Testing Checklist

- [x] Claude without model specification works
- [x] Claude with explicit model specification works
- [x] Verbose/debug flags work with claude
- [x] Other executors (cline, aider) unchanged
- [x] Command doesn't include `--model` flag when not specified
- [x] JSON response parsing works correctly
- [x] Async execution path also fixed
- [x] Config file with null models works

---

## Verification Command

To verify the fix:

```bash
# With no forced model (should work now)
oneshot --executor claude "What is the capital of Greece?"

# With explicit model (should also work)
oneshot --executor claude --worker-model claude-opus-4-1 "Test question"

# Check the debug output
oneshot --debug --executor claude "Test" 2>&1 | grep -E "Command:|model:"
```

Expected output for first command: `Command: claude -p --dangerously-skip-permissions` (no `--model` flag)
