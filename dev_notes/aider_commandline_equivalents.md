# Aider Environment Variables to Commandline Arguments Mapping

## Baseline Test Results

**Baseline Command (Working):**
```bash
aider --message "What is the capital of france?" --chat-mode ask --yes-always --no-stream --no-pretty
```

**Output:**
```
Model: ollama_chat/llama-pro with ask edit format
The capital of France is Paris.
Tokens: 5.1k sent, 8 received.
```

✓ **Status:** WORKING

---

## Environment Variable Mappings

### Current `.env` Configuration
```
AIDER2_MODEL=ollama_chat/qwen2.5-coder:7b
AIDER_EDITOR2_MODEL=ollama_chat/qwen2.5-coder:7b
AIDER_MODEL=ollama_chat/llama-pro
AIDER_EDITOR_MODEL=ollama_chat/llama-pro
AIDER_ARCHITECT=true
OLLAMA_API_BASE=http://localhost:11434
AIDER_EDIT_FORMAT=whole
```

### Mapping Details

| Env Variable | Commandline Option | Status | Notes |
|---|---|---|---|
| `AIDER_EDIT_FORMAT=whole` | `--edit-format whole` or `--chat-mode whole` | ✓ Found | Specifies edit format (whole, diff, etc) |
| `AIDER_ARCHITECT=true` | `--architect` | ✓ Found | Boolean flag for architect mode |
| `AIDER_MODEL=...` | `--model <model>` | ✓ Found | Main model specification |
| `AIDER_EDITOR_MODEL=...` | `--editor-model <model>` | ✓ Found | Editor model specification |
| `AIDER2_MODEL=...` | ❌ Not found | Legacy/Unknown | No equivalent in aider help |
| `AIDER_EDITOR2_MODEL=...` | ❌ Not found | Legacy/Unknown | No equivalent in aider help |
| `OLLAMA_API_BASE=http://localhost:11434` | `--openai-api-base http://localhost:11434` | ✓ Found | Maps to `AIDER_OPENAI_API_BASE` env var |

### Not Currently Used in Baseline Test
- `AIDER2_MODEL` - Not referenced in baseline
- `AIDER_EDITOR2_MODEL` - Not referenced in baseline
- `AIDER_EDITOR_MODEL` - Not set (uses AIDER_MODEL as default)
- `OLLAMA_API_BASE` - Not needed for the baseline test with ollama_chat model
- `AIDER_ARCHITECT` - Not needed for ask mode (--chat-mode ask)

---

## Migration Strategy

### Variables Actually Used in Current `.env`
1. `AIDER_MODEL=ollama_chat/llama-pro` → `--model ollama_chat/llama-pro`
2. `AIDER_EDIT_FORMAT=whole` → `--edit-format whole`
3. `AIDER_ARCHITECT=true` → `--architect` (only if needed)

### Variables to Investigate/Remove
- `AIDER2_MODEL` - Check if actually used anywhere
- `AIDER_EDITOR2_MODEL` - Check if actually used anywhere
- `AIDER_EDITOR_MODEL` - Keep in .env if used elsewhere, or migrate
- `OLLAMA_API_BASE` - Check if used with non-ollama_chat models

