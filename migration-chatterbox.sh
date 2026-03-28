#!/bin/bash
# Auto-generated migration script - REVIEW BEFORE EXECUTION
# Project: chatterbox

set -e

# Create safety tag before migration
git tag -a -m 'pre-dev_notes-cleanup' pre-dev_notes-cleanup

# Move untracked files to tmp/ for review
mkdir -p tmp
mv dev_notes/specs/spec-wyoming-protocol-llm-integration-20260218.md tmp/spec-wyoming-protocol-llm-integration-20260218.md.untracked
mv dev_notes/project_plans/2026-01-18_17-12-51_add-piper-tts-demo-with-caching.md tmp/2026-01-18_17-12-51_add-piper-tts-demo-with-caching.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-8-receiving-audio-playback.md tmp/2026-03-24_epic-8-receiving-audio-playback.md.untracked
mv dev_notes/project_plans/2026-03-25_epic-6-ha-integration-addendum.md tmp/2026-03-25_epic-6-ha-integration-addendum.md.untracked
mv dev_notes/project_plans/2026-03-25_epic2-phase2-assessment.md tmp/2026-03-25_epic2-phase2-assessment.md.untracked
mv dev_notes/project_plans/2026-01-18_21-00-00_approach-a-batch-processing-enhancement.md tmp/2026-01-18_21-00-00_approach-a-batch-processing-enhancement.md.untracked
mv dev_notes/project_plans/2026-01-18_20-55-00_whisper-integration-streaming-stt.md tmp/2026-01-18_20-55-00_whisper-integration-streaming-stt.md.untracked
mv dev_notes/project_plans/2026-01-18_21-15-00_migrate-aider-config-to-commandline.md tmp/2026-01-18_21-15-00_migrate-aider-config-to-commandline.md.untracked
mv dev_notes/project_plans/2026-01-19_14-30-00_tts_stt_wyoming_implementation.md tmp/2026-01-19_14-30-00_tts_stt_wyoming_implementation.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-7-recording-pcm-streaming.md tmp/2026-03-24_epic-7-recording-pcm-streaming.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-12-documentation-maintenance.md tmp/2026-03-24_epic-12-documentation-maintenance.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-2-observability-monitoring.md tmp/2026-03-24_epic-2-observability-monitoring.md.untracked
mv dev_notes/project_plans/2026-01-19_01-15-fix-claude-executor-model-handling.md tmp/2026-01-19_01-15-fix-claude-executor-model-handling.md.untracked
mv dev_notes/project_plans/2026-03-24_clarifications-summary.md tmp/2026-03-24_clarifications-summary.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-9-touchscreen-integration.md tmp/2026-03-24_epic-9-touchscreen-integration.md.untracked
mv dev_notes/project_plans/2026-01-18_22-52-run-server-restart-fix.md tmp/2026-01-18_22-52-run-server-restart-fix.md.untracked
mv dev_notes/project_plans/master-plan.md tmp/master-plan.md.untracked
mv dev_notes/project_plans/2026-02-19_05-44-53_task-3-6-validate-whisper-stt-service.md tmp/2026-02-19_05-44-53_task-3-6-validate-whisper-stt-service.md.untracked
mv dev_notes/project_plans/2026-03-25_epic-5-6-implementation-status.md tmp/2026-03-25_epic-5-6-implementation-status.md.untracked
mv dev_notes/project_plans/2026-01-18_08-12-15_wyoming-satellite-emulator.md tmp/2026-01-18_08-12-15_wyoming-satellite-emulator.md.untracked
mv dev_notes/project_plans/2026-01-18_14-30-00_wyoming-satellite-emulation-fix.md tmp/2026-01-18_14-30-00_wyoming-satellite-emulation-fix.md.untracked
mv dev_notes/project_plans/2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md tmp/2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-6-backend-deployment-ha-connection.md tmp/2026-03-24_epic-6-backend-deployment-ha-connection.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-10-continuous-conversation-wake-word.md tmp/2026-03-24_epic-10-continuous-conversation-wake-word.md.untracked
mv dev_notes/project_plans/2026-02-20_00-20-16_task-4.2-agentic-framework-evaluation.md tmp/2026-02-20_00-20-16_task-4.2-agentic-framework-evaluation.md.untracked
mv dev_notes/project_plans/2026-02-25_mellona-migration-project-plan.md tmp/2026-02-25_mellona-migration-project-plan.md.untracked
mv dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md tmp/2026-02-18_epic-3-4-wyoming-llm-project-plan.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-5-persistent-conversation-context.md tmp/2026-03-24_epic-5-persistent-conversation-context.md.untracked
mv dev_notes/project_plans/2026-03-24_epic-11-reliability-llm-fallback.md tmp/2026-03-24_epic-11-reliability-llm-fallback.md.untracked
mv dev_notes/inbox/un-cackle.md tmp/un-cackle.md.untracked
mv dev_notes/inbox/prompt-01.md tmp/prompt-01.md.untracked

# Create planning directory structure
mkdir -p planning/inbox

# Migrate specs → planning/*-prompt.md
git mv dev_notes/specs/spec-wyoming-protocol-llm-integration-20260218.md planning/spec-wyoming-protocol-llm-integration-20260218-prompt.md

# Migrate project_plans → planning/*-plan.md
git mv dev_notes/project_plans/2026-01-18_08-12-15_wyoming-satellite-emulator.md planning/2026-01-18_08-12-15_wyoming-satellite-emulator-plan.md
git mv dev_notes/project_plans/2026-01-18_14-30-00_wyoming-satellite-emulation-fix.md planning/2026-01-18_14-30-00_wyoming-satellite-emulation-fix-plan.md
git mv dev_notes/project_plans/2026-01-18_17-12-51_add-piper-tts-demo-with-caching.md planning/2026-01-18_17-12-51_add-piper-tts-demo-with-caching-plan.md
git mv dev_notes/project_plans/2026-01-18_20-55-00_whisper-integration-streaming-stt.md planning/2026-01-18_20-55-00_whisper-integration-streaming-stt-plan.md
git mv dev_notes/project_plans/2026-01-18_21-00-00_approach-a-batch-processing-enhancement.md planning/2026-01-18_21-00-00_approach-a-batch-processing-enhancement-plan.md
git mv dev_notes/project_plans/2026-01-18_21-15-00_migrate-aider-config-to-commandline.md planning/2026-01-18_21-15-00_migrate-aider-config-to-commandline-plan.md
git mv dev_notes/project_plans/2026-01-18_22-52-run-server-restart-fix.md planning/2026-01-18_22-52-run-server-restart-fix-plan.md
git mv dev_notes/project_plans/2026-01-19_01-15-fix-claude-executor-model-handling.md planning/2026-01-19_01-15-fix-claude-executor-model-handling-plan.md
git mv dev_notes/project_plans/2026-01-19_14-30-00_tts_stt_wyoming_implementation.md planning/2026-01-19_14-30-00_tts_stt_wyoming_implementation-plan.md
git mv dev_notes/project_plans/2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan.md planning/2026-02-13_10-00-00_epic-1-ota-and-foundation-project-plan-plan.md
git mv dev_notes/project_plans/2026-02-18_epic-3-4-wyoming-llm-project-plan.md planning/2026-02-18_epic-3-4-wyoming-llm-project-plan-plan.md
git mv dev_notes/project_plans/2026-02-19_05-44-53_task-3-6-validate-whisper-stt-service.md planning/2026-02-19_05-44-53_task-3-6-validate-whisper-stt-service-plan.md
git mv dev_notes/project_plans/2026-02-20_00-20-16_task-4.2-agentic-framework-evaluation.md planning/2026-02-20_00-20-16_task-4.2-agentic-framework-evaluation-plan.md
git mv dev_notes/project_plans/2026-02-25_mellona-migration-project-plan.md planning/2026-02-25_mellona-migration-project-plan-plan.md
git mv dev_notes/project_plans/2026-03-24_clarifications-summary.md planning/2026-03-24_clarifications-summary-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-10-continuous-conversation-wake-word.md planning/2026-03-24_epic-10-continuous-conversation-wake-word-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-11-reliability-llm-fallback.md planning/2026-03-24_epic-11-reliability-llm-fallback-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-12-documentation-maintenance.md planning/2026-03-24_epic-12-documentation-maintenance-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-2-observability-monitoring.md planning/2026-03-24_epic-2-observability-monitoring-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-5-persistent-conversation-context.md planning/2026-03-24_epic-5-persistent-conversation-context-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-6-backend-deployment-ha-connection.md planning/2026-03-24_epic-6-backend-deployment-ha-connection-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-7-recording-pcm-streaming.md planning/2026-03-24_epic-7-recording-pcm-streaming-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-8-receiving-audio-playback.md planning/2026-03-24_epic-8-receiving-audio-playback-plan.md
git mv dev_notes/project_plans/2026-03-24_epic-9-touchscreen-integration.md planning/2026-03-24_epic-9-touchscreen-integration-plan.md
git mv dev_notes/project_plans/2026-03-25_epic-5-6-implementation-status.md planning/2026-03-25_epic-5-6-implementation-status-plan.md
git mv dev_notes/project_plans/2026-03-25_epic-6-ha-integration-addendum.md planning/2026-03-25_epic-6-ha-integration-addendum-plan.md
git mv dev_notes/project_plans/2026-03-25_epic2-phase2-assessment.md planning/2026-03-25_epic2-phase2-assessment-plan.md
git mv dev_notes/project_plans/master-plan.md planning/master-plan-plan.md

# Migrate inbox → planning/inbox/
git mv dev_notes/inbox/prompt-01.md planning/inbox/prompt-01.md
git mv dev_notes/inbox/un-cackle.md planning/inbox/un-cackle.md

mkdir -p planning/inbox-archive
# Migrate inbox-archive → planning/inbox-archive/

# Remove empty directories
rmdir dev_notes/specs 2>/dev/null || true
rmdir dev_notes/project_plans 2>/dev/null || true
rmdir dev_notes/inbox 2>/dev/null || true

echo '✓ Migration complete for chatterbox'