# Change: Fix Pydantic Type Annotation Issues in Tool Classes

**Related Project Plan:** N/A (Trivial fix - adding type annotations)

**Overview:**
Fixed Pydantic validation errors in the STTTool and TTSTool classes by adding proper type annotations to inherited fields. The issue was that these classes overrode BaseTool fields without type annotations, which is required in Pydantic v2.

**Files Modified:**
- `cackle/tools/builtin/stt_tool.py`: Added type annotations to `name: str`, `description: str`, and `return_direct: bool` fields
- `cackle/tools/builtin/tts_tool.py`: Added type annotations to `name: str`, `description: str`, and `return_direct: bool` fields

**Impact Assessment:**
- **Positive:** Eliminates Pydantic INTERNALERROR that prevented test execution
- **Compatibility:** Maintains backward compatibility - no runtime behavior changes
- **Testing:** Tests now run without import/initialization errors, revealing actual test logic issues instead of framework errors