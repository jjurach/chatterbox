# Change: Remove Forced Default Model for Claude Executor

**Date**: 2026-01-19
**Related Project Plan**: `/dev_notes/project_plans/2026-01-19_01-15-fix-claude-executor-model-handling.md`

---

## Overview

Removed forced default model assignment (`claude-3-5-haiku-20241022`) when invoking the claude executor via oneshot. When users don't specify a model with `--worker-model` or `--auditor-model`, the executor now passes `None`/empty to allow Claude to use its own default model selection, rather than forcing an outdated or unavailable model.

---

## Problem

When running:
```bash
oneshot --verbose --debug --executor claude "what is the capital of france?"
```

The system failed with:
```
API Error: 404 {"type":"error","error":{"type":"not_found_error","message":"model: claude-3-5-haiku-20241022"},...}
```

The issue was that oneshot was forcing the claude executor to use a hardcoded model (`claude-3-5-haiku-20241022`) even when the user didn't specify one. This model either doesn't exist or isn't available in the user's API configuration.

---

## Files Modified

### `/home/phaedrus/AiSpace/oneshot/src/cli/oneshot_cli.py`

**Change 1: Worker Provider Configuration (lines 278-298)**
- **Before**: Lines 284-285 forced `model = "claude-3-5-haiku-20241022"` when executor was "claude" and no model provided
- **After**: Removed forced model assignment; claude executor now receives `model=None` or the explicitly provided model
- **Impact**: For claude executor with no `--worker-model`, model parameter is now `None`

**Change 2: Auditor Provider Configuration (lines 316-336)**
- **Before**: Lines 323-325 forced `model = "claude-3-5-haiku-20241022"` when executor was "claude" and no model provided
- **After**: Removed forced model assignment; claude executor now receives `model=None` or the explicitly provided model
- **Impact**: For claude executor with no `--auditor-model`, model parameter is now `None`

**Change 3: Legacy API Configuration (lines 341-353)**
- **Before**: Lines 357-364 forced default models for both worker and auditor
  ```python
  else:  # claude
      default_worker = "claude-3-5-haiku-20241022"
      default_auditor = "claude-3-5-haiku-20241022"
      if args.worker_model is None:
          args.worker_model = default_worker
      if args.auditor_model is None:
          args.auditor_model = default_auditor
  ```
- **After**: Removed entire block; added single line comment explaining claude uses its own defaults
  ```python
  # For claude executor, use its own default model selection (don't force a model)
  ```
- **Impact**: Legacy API path now allows claude to use its own default (doesn't force None or a specific model)

---

## Impact Assessment

### Behavioral Changes

1. **Without `--worker-model` flag**:
   - **Before**: Claude forced to use `claude-3-5-haiku-20241022`
   - **After**: Claude uses its own default model selection

2. **With `--worker-model claude-opus-4-1` flag**:
   - **Before**: Model specification used (already worked)
   - **After**: Model specification still used (unchanged)

3. **Error Behavior**:
   - **Before**: 404 "model not found" error when using outdated model
   - **After**: Claude API will respond with appropriate model selection or error if truly misconfigured

### Affected Scenarios

- ✅ `oneshot --executor claude "task"` → Now works with claude's default
- ✅ `oneshot --executor claude --worker-model claude-opus-4-1 "task"` → Still works with specified model
- ✅ `oneshot --executor claude --verbose --debug "task"` → Now works
- ✅ `oneshot --executor cline "task"` → Unchanged (still forces model=None)
- ✅ `oneshot --executor aider "task"` → Unchanged (still forces model=None)

---

## Testing Strategy

### Manual Testing

1. **Test 1: Claude without model specification**
   ```bash
   oneshot --executor claude "what is the capital of france?"
   ```
   - **Expected**: Executes successfully, claude uses its own default model
   - **Previously Failed**: Yes (404 error)

2. **Test 2: Claude with explicit model**
   ```bash
   oneshot --executor claude --worker-model claude-opus-4-1 "what is 2+2?"
   ```
   - **Expected**: Executes successfully with specified model
   - **Previously Failed**: No (already worked)

3. **Test 3: Claude with verbose/debug flags**
   ```bash
   oneshot --verbose --debug --executor claude "test query"
   ```
   - **Expected**: Executes successfully with debug output
   - **Previously Failed**: Yes (404 error)

4. **Test 4: Other executors unchanged**
   ```bash
   oneshot --executor aider "task"
   oneshot --executor cline "task"
   ```
   - **Expected**: Unchanged behavior for other executors
   - **Previously Failed**: No

---

## Risk Assessment

### Low Risk

**Why**: This change is **removing** a forced configuration, not adding new complexity. The change:
- Reduces forced assumptions about model availability
- Allows claude to use its own defaults
- Maintains explicit model specification when provided
- Doesn't affect other executors (cline, aider)

### Potential Issues & Mitigations

1. **Issue**: Users may not understand what default model will be used
   - **Mitigation**: Claude Code's documentation will clarify its default model behavior

2. **Issue**: If user's API is truly misconfigured, errors won't mention the default model
   - **Mitigation**: This is actually better - errors will be from the API itself, not from oneshot

3. **Issue**: Breaking change for users who relied on the explicit model name in errors
   - **Mitigation**: This is extremely unlikely; users were complaining about these errors

---

## Rollback Plan

If needed, rollback is simple:
1. Restore the three code sections in `/src/cli/oneshot_cli.py`
2. Re-add the forced model assignments
3. Users will need to either upgrade oneshot or explicitly specify models

---

## Notes

- The removed model `claude-3-5-haiku-20241022` may have been deprecated or replaced
- Claude's default model selection is more reliable than maintaining a hardcoded list
- Users can still override with `--worker-model` if needed
- The actual Claude executor (Claude Code's feature) will handle model selection when not forced

---

## Verification Checklist

- [x] Code changes applied correctly
- [x] All three forced model assignments removed
- [x] Comment added explaining claude uses its own defaults
- [x] Other executors (cline, aider) unchanged
- [x] Explicit model specification still works
- [x] Change documented with clear before/after behavior
