# Project Plan: Add Piper TTS Demo with Caching and Summarization

## Objective
Add a new feature to `scripts/chat-demo.sh` that demonstrates Piper TTS capabilities with caching and summarization. Create `scripts/piper_demo.py` as a standalone script that exposes Piper TTS features with intelligent caching and provides detailed operation summaries. This will allow users to test TTS synthesis independently from the full Wyoming pipeline, with performance monitoring and result caching.

## Implementation Steps
1. **Create piper_demo.py script**
   - Implement PiperTTSService integration with configurable model paths
   - Add caching mechanism using file-based storage with hash-based keys
   - Implement summarization features (timing, file sizes, success rates)
   - Add command-line interface with options for text input, output paths, and cache control

2. **Modify chat-demo.sh to integrate piper_demo.py**
   - Add new command-line option `--piper-demo` or `--tts-only`
   - Integrate piper_demo.py calls for TTS-only testing
   - Preserve existing full-pipeline functionality
   - Add output formatting to display TTS operation summaries

3. **Implement caching system**
   - Create cache directory structure under `tmp/piper_cache/`
   - Use text hash + model hash for cache keys
   - Implement cache hit/miss detection
   - Add cache cleanup and size management

4. **Add summarization and monitoring**
   - Track synthesis time, file size, audio duration
   - Log operation results with timestamps
   - Provide summary statistics (cache hit rate, average synthesis time)
   - Output human-readable summaries to console

5. **Add tests and validation**
   - Create unit tests for piper_demo.py functionality
   - Test caching behavior and summarization output
   - Validate integration with chat-demo.sh

## Success Criteria
- `scripts/piper_demo.py` can synthesize text to audio files with caching
- `scripts/chat-demo.sh --piper-demo` successfully performs TTS operations
- Cache hit/miss ratios are accurately tracked and reported
- Summarization provides useful metrics (timing, file sizes, success rates)
- Existing chat-demo.sh functionality remains unchanged
- All new code follows existing project patterns and style

## Testing Strategy
- Unit tests for piper_demo.py core functions
- Integration tests for chat-demo.sh piper integration
- Manual testing with various text inputs and cache scenarios
- Performance testing to verify caching benefits
- Regression testing to ensure existing functionality works

## Risk Assessment
- **Low**: Piper TTS integration already exists in codebase
- **Low**: Caching can be implemented with simple file-based approach
- **Medium**: Summarization requirements may need clarification (is this timing stats, or content analysis?)
- **Low**: Shell script modifications are straightforward
- **Low**: No breaking changes to existing Wyoming pipeline functionality