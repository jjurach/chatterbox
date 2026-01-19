# Project Plan: Migrate Aider Configuration from Environment Variables to Commandline Arguments

## Objective

Successfully migrate all aider-related configuration from environment variables in `.env` to commandline arguments, allowing the `.env` file to contain only `CHATTERBOX_` configuration variables. This provides better separation of concerns and makes aider behavior more explicit and testable.

## Current State

**Current `.env` contents:**
```
AIDER2_MODEL=ollama_chat/qwen2.5-coder:7b
AIDER_EDITOR2_MODEL=ollama_chat/qwen2.5-coder:7b
AIDER_MODEL=ollama_chat/llama-pro
AIDER_EDITOR_MODEL=ollama_chat/llama-pro
AIDER_ARCHITECT=true
OLLAMA_API_BASE=http://localhost:11434
AIDER_EDIT_FORMAT=whole
```

**`.env.orig` contents (target state):**
```
# Only CHATTERBOX_ variables
CHATTERBOX_HOST=0.0.0.0
CHATTERBOX_PORT=10700
CHATTERBOX_OLLAMA_BASE_URL=http://localhost:11434/v1
CHATTERBOX_OLLAMA_MODEL=llama3.1:8b
CHATTERBOX_OLLAMA_TEMPERATURE=0.7
CHATTERBOX_CONVERSATION_WINDOW_SIZE=3
CHATTERBOX_LOG_LEVEL=DEBUG
CHATTERBOX_SERVER_MODE=stt_only
```

## Implementation Steps

### Phase 1: Baseline Testing
1. **Test the current aider command** with all environment variables present:
   - Run: `aider --message "What is the capital of france?" --chat-mode ask --yes-always --no-stream --no-pretty`
   - Verify successful execution with current `.env`
   - Document the baseline behavior

2. **Identify the complete set of aider commandline equivalents:**
   - `AIDER2_MODEL` → `--model` or similar flag
   - `AIDER_EDITOR2_MODEL` → editor model flag
   - `AIDER_MODEL` → model selection flag
   - `AIDER_EDITOR_MODEL` → editor model flag
   - `AIDER_ARCHITECT` → `--architect` flag
   - `OLLAMA_API_BASE` → base URL flag (may be API-specific)
   - `AIDER_EDIT_FORMAT` → `--edit-format` flag

3. **Document commandline equivalents** by checking aider help/docs or testing

### Phase 2: Iterative Migration (One Variable at a Time)
For each environment variable below, execute these steps:

**Variables to migrate (in order):**
1. `AIDER_EDIT_FORMAT`
2. `AIDER_ARCHITECT`
3. `AIDER_MODEL`
4. `AIDER_EDITOR_MODEL`
5. `AIDER2_MODEL`
6. `AIDER_EDITOR2_MODEL`
7. `OLLAMA_API_BASE`

**For each variable:**

a. **Create test command:**
   - Take the working aider command
   - Add commandline argument equivalent of the environment variable
   - Comment out or temporarily remove the environment variable from `.env`

b. **Test the updated command:**
   - Execute the command with the new commandline argument
   - Verify it works identically to the previous version
   - Document success or any issues

c. **Commit the progress:**
   - Update `.env` to remove the migrated variable
   - Document the change in `dev_notes/changes/`
   - Create appropriate git commit

d. **Verify baseline still works:**
   - Re-run the full aider command with all migrated variables as flags
   - Ensure no regressions

### Phase 3: Final Verification & Cleanup
1. **Verify `.env` contains only CHATTERBOX_ variables:**
   - All AIDER_ variables removed
   - OLLAMA_API_BASE removed (if it's aider-specific)
   - Only chatterbox configuration remains

2. **Create final working command template:**
   - Document the complete aider commandline that works without environment variables
   - Include all required flags

3. **Update documentation:**
   - Update relevant scripts or READMEs with new commandline format
   - Document why this separation was made

4. **Final test:**
   - Run the command with fresh shell (no env vars) using commandline args only
   - Verify all functionality works as expected

## Success Criteria

- ✓ Aider command executes successfully with all configuration passed via commandline arguments
- ✓ `.env` file contains only `CHATTERBOX_` environment variables
- ✓ No AIDER_ or OLLAMA_API_BASE variables in `.env`
- ✓ All migration steps documented with test results
- ✓ No functionality lost in the migration
- ✓ Each step tested and verified before moving to next

## Testing Strategy

1. **Baseline test:** Confirm current command works with existing `.env`
2. **Incremental tests:** After each variable migration, verify aider command still functions
3. **Regression tests:** After all migrations, run full command to ensure no breakage
4. **Clean environment test:** Run final command with minimal environment setup

## Risk Assessment

**Low Risk:**
- Each step is incremental and reversible
- Changes are localized to `.env` and command invocation
- Testing occurs after each change before proceeding

**Potential Issues:**
- Aider commandline arguments may have different syntax than expected → Mitigate by consulting aider help/documentation first
- Some environment variables may not have direct commandline equivalents → Mitigate by researching aider options thoroughly

**Mitigation:**
- Keep `.env` in git so changes can be easily reverted
- Test each step independently before committing
- Document findings about commandline equivalents before making changes
