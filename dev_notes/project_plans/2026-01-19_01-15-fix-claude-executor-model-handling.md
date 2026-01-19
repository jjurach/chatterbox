# Project Plan: Fix Claude Executor Model Handling

**Date Created**: 2026-01-19
**Status**: Awaiting Approval

---

## Objective

Remove forced default model assignment when invoking the claude executor via `oneshot`. If the user does not specify a model for claude, the oneshot command should **not** force claude to use a default hardcoded value (e.g., `claude-3-5-sonnet-20241022`). Instead, when no model is given, the executor should call claude without a model parameter, allowing Claude to use its own default behavior.

---

## Problem Summary

Currently, when `oneshot --verbose --debug --executor claude "what is the capital of france?"` is executed without an explicit model parameter, the system fails with:

```
API Error: 404 {"type":"error","error":{"type":"not_found_error","message":"model: claude-3-5-sonnet-20241022"},...}
```

This indicates that:
1. A default model `claude-3-5-sonnet-20241022` is being forced onto the claude executor
2. This model may be outdated, unavailable, or invalid in the user's API configuration
3. Claude would work fine if called **without** a specific model parameter, allowing the API to use its default model

---

## Implementation Steps

### Step 1: Identify Configuration Source
- **Action**: Locate where the claude executor's default model is being set
- **Search locations**:
  - Claude Code's built-in configuration or hooks
  - Any `.claude_code` config files or environment variables
  - Configuration files in the project root (e.g., `claude.json`, `.clauderc`, etc.)
  - Python configuration files that may be invoking oneshot
- **Deliverable**: Document the exact location and mechanism for model defaults

### Step 2: Understand Current Behavior
- **Action**: Trace how `--executor claude` is invoked and where the model parameter is added
- **Details to document**:
  - How the default model `claude-3-5-sonnet-20241022` is selected
  - Whether it's a constant or derived from configuration
  - The execution flow when `--executor claude` is used without `--model`
- **Deliverable**: Detailed flow diagram or code annotations showing the current invocation pattern

### Step 3: Modify Model Assignment Logic
- **Action**: Update the executor configuration to conditionally assign the model parameter
- **Key change**:
  - If the user provides a `--model` flag, use that model
  - If the user does **not** provide a `--model` flag, **omit** the model parameter entirely when calling claude
- **Files likely affected**:
  - Configuration loading mechanism
  - Executor invocation code
  - Command-line argument parsing (if applicable)
- **Deliverable**: Code changes with clear before/after comments

### Step 4: Verify Alternative Configurations
- **Action**: Ensure that when a user explicitly provides a model, it still works correctly
- **Test cases**:
  - `oneshot --executor claude "question"` → Claude called without model
  - `oneshot --executor claude --model claude-opus-4-1 "question"` → Claude called with specified model
  - `oneshot --verbose --debug --executor claude "question"` → Verbose/debug flags work without default model forcing
- **Deliverable**: Test execution results

### Step 5: Document the Change
- **Action**: Create a Change Documentation entry explaining:
  - What was broken (forced default model causing 404 errors)
  - How it was fixed (conditional model assignment)
  - Why this is better (allows Claude to use its own defaults)
  - Impact on existing workflows
- **File**: `dev_notes/changes/[TIMESTAMP]_claude-executor-model-fix.md`

---

## Success Criteria

1. ✅ `oneshot --verbose --debug --executor claude "what is the capital of france?"` executes **without** throwing a 404 error
2. ✅ Claude responds with correct output (e.g., "Paris")
3. ✅ Users can still explicitly specify a model with `--model` and it works correctly
4. ✅ Verbose and debug flags continue to function as expected
5. ✅ No breaking changes to other executor types (non-claude executors remain unaffected)

---

## Testing Strategy

### Phase 1: Reproduction Test
- Run `oneshot --verbose --debug --executor claude "what is the capital of france?"`
- **Expected**: No 404 error; claude responds normally
- **Current**: API Error 404 with `claude-3-5-sonnet-20241022` not found

### Phase 2: Explicit Model Test
- Run `oneshot --executor claude --model claude-opus-4-1 "what is 2+2?"`
- **Expected**: Claude responds using the specified model

### Phase 3: Edge Case Tests
- Run with various flag combinations:
  - `--verbose` without `--debug`
  - `--debug` without `--verbose`
  - `--executor claude` as last vs. first argument
- **Expected**: All variations work without model-related errors

### Phase 4: Non-Regression Tests
- Verify other executors still work (if applicable)
- Confirm no side effects on configuration or environment

---

## Risk Assessment

### Low Risk
- **Reason**: This change is **removing** a forced configuration, not adding new complexity
- **Impact**: Reduces forced assumptions about model availability
- **Reversibility**: Changes are non-destructive and easy to revert if needed

### Potential Issues
1. **Configuration Location Unknown**: The source of the forced default model hasn't been fully pinpointed in this codebase
   - **Mitigation**: May require investigation of Claude Code's own configuration files or external tool settings
   - **Action**: If not found in this repo, search Claude Code documentation or `~/.claude_code/` directories

2. **API Default Behavior Change**: Removing the model parameter might cause Claude to use a different model by default
   - **Mitigation**: This is actually the desired behavior—let Claude choose its own default
   - **Verification**: Confirm API response indicates which model was used

3. **Existing Scripts/Automation**: If users have workflows that depend on the specific model being used, this changes behavior
   - **Mitigation**: Users can still explicitly specify the model with `--model` flag
   - **Communication**: Document this change in release notes

---

## Files Likely to Be Modified

- Configuration loading/initialization code (location TBD upon investigation)
- Executor invocation logic (location TBD upon investigation)
- Command-line argument parsing (if applicable)
- Test/example files demonstrating the new behavior

---

## Notes for Implementation

1. **Investigation Required**: The exact source of the forced model assignment needs to be identified first. This may involve:
   - Checking Claude Code's internal configuration
   - Searching environment variables
   - Looking at any `.claude_code` or similar config files
   - Reviewing Claude Code documentation

2. **Scope Limitation**: This plan focuses on the claude executor. Other executors should not be affected.

3. **User Communication**: Once implemented, users should be informed that they no longer need to specify a model unless they want a specific Claude model version.

---

## Approval Gate

This plan is ready for developer review and approval. Please confirm whether to proceed with implementation.
