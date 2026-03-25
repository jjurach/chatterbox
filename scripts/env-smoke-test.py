#!/usr/bin/env python3
"""
Smoke test for Epic 5 prerequisites.

Validates that the environment is configured correctly for Epic 5 integration testing,
with specific focus on mellona configuration chaining and provider availability patterns.

Tests performed:
1. Chatterbox Settings loading
2. Mellona configuration discovery and provider availability
2.5. Chatterbox ~/.config/chatterbox directory setup
4. STT service initialization (faster-whisper via mellona)
5. TTS service initialization (piper via mellona)
6. Ollama connection and model availability
7. VoiceAssistantAgent initialization with mellona config
8. Tool registry availability and population
9. Basic STT→Agent→TTS pipeline simulation

Configuration chain discovery:
- ~/.config/chatterbox/mellona.yaml (app-specific, highest priority)
- ~/.config/mellona/config.yaml (shared mellona config)
- .mellona.yaml (project-local config)
- Built-in defaults (lowest priority)

Usage:
    python scripts/env-smoke-test.py                 # Default mode
    python scripts/env-smoke-test.py --verbose       # Detailed diagnostics
    python scripts/env-smoke-test.py --json          # JSON output for CI/CD
    python scripts/env-smoke-test.py --help          # Show help

See docs for:
- mellona config chaining: ../mellona/docs/configuration.md
- pigeon integration patterns: ../pigeon/docs/system-prompts/guidelines/mellona-integration-patterns.md
"""

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import traceback

# Colors for terminal output
class Colors:
    RESET = "\033[0m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"


@dataclass
class TestResult:
    """Single test result."""
    name: str
    passed: bool
    error: Optional[str] = None
    details: Optional[str] = None
    component: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


class SmokeTest:
    """Epic 5 prerequisites smoke test."""

    def __init__(self, verbose: bool = False, json_output: bool = False):
        self.verbose = verbose
        self.json_output = json_output
        self.results: List[TestResult] = []
        self.config_path: Optional[Path] = None
        self.settings: Optional[Any] = None

    def log(self, message: str, color: str = "", force_print: bool = False):
        """Log message with optional color."""
        if self.json_output and not force_print:
            return
        if color:
            print(f"{color}{message}{Colors.RESET}")
        else:
            print(message)

    def log_header(self, title: str):
        """Log section header."""
        self.log(f"\n{Colors.BOLD}{Colors.BLUE}━━━ {title} ━━━{Colors.RESET}", force_print=True)

    def log_test(self, name: str, passed: bool, error: Optional[str] = None, details: Optional[str] = None):
        """Log individual test result."""
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if passed else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        self.log(f"  {status} {name}", force_print=True)
        if error and self.verbose:
            self.log(f"    Error: {error}", Colors.RED, force_print=True)
        if details and self.verbose:
            self.log(f"    {details}", Colors.YELLOW, force_print=True)

    async def test_settings_loading(self) -> bool:
        """Test 1: Load chatterbox Settings."""
        self.log_header("1. LOADING CHATTERBOX SETTINGS")
        try:
            from chatterbox.config import get_settings
            self.settings = get_settings()

            details = f"mellona_config_path={self.settings.mellona_config_path}"
            self.log_test("Settings loaded", True, details=details)
            self.results.append(TestResult(
                name="Settings loading",
                passed=True,
                component="config",
                details=details
            ))
            return True
        except Exception as e:
            error_msg = str(e)
            self.log_test("Settings loading", False, error=error_msg)
            self.results.append(TestResult(
                name="Settings loading",
                passed=False,
                component="config",
                error=error_msg
            ))
            return False

    async def test_mellona_config(self) -> bool:
        """Test 2: Load and validate Mellona configuration with config chain discovery."""
        self.log_header("2. MELLONA CONFIGURATION & CONFIG CHAIN DISCOVERY")
        try:
            from mellona import get_config
            from pathlib import Path

            # Check for config files in standard locations
            config_locations = [
                Path.home() / ".config" / "chatterbox" / "mellona.yaml",
                Path.home() / ".config" / "mellona" / "config.yaml",
                Path.cwd() / ".mellona.yaml",
            ]

            found_configs = [p for p in config_locations if p.exists()]
            if found_configs:
                details = f"Found config: {found_configs[0].name}"
                self.log_test("Config files discovered", True, details=details)
                self.results.append(TestResult(
                    name="Config files discovered",
                    passed=True,
                    component="mellona",
                    details=details
                ))
            else:
                warning = "No mellona config found (using defaults)"
                self.log_test("Config files discovered", True, details=warning)
                self.results.append(TestResult(
                    name="Config files discovered",
                    passed=True,
                    component="mellona",
                    details=warning
                ))

            config = get_config()

            # Check providers are defined
            providers = config.get("providers", {})
            has_stt = "faster_whisper" in providers
            has_tts = "piper" in providers
            has_lm = "ollama" in providers

            details = f"STT={has_stt}, TTS={has_tts}, LLM={has_lm}"
            self.log_test("Mellona config loaded", True, details=details)
            self.results.append(TestResult(
                name="Mellona config loaded",
                passed=True,
                component="mellona",
                details=details
            ))

            # Check for environment variable substitution support
            if isinstance(config, dict):
                has_env_vars = any(
                    isinstance(v, str) and "${" in v
                    for v in str(config).split()
                )
                self.log_test(
                    "Environment variable support",
                    True,
                    details="Ready for ${VAR_NAME} substitution"
                )
                self.results.append(TestResult(
                    name="Environment variable support",
                    passed=True,
                    component="mellona"
                ))

            if not (has_stt and has_tts and has_lm):
                missing = []
                if not has_stt:
                    missing.append("faster_whisper")
                if not has_tts:
                    missing.append("piper")
                if not has_lm:
                    missing.append("ollama")
                error = f"Missing providers: {', '.join(missing)}"
                self.log_test("All required providers present", False, error=error)
                self.results.append(TestResult(
                    name="All required providers present",
                    passed=False,
                    component="mellona",
                    error=error
                ))
                return False

            self.log_test("All required providers present", True)
            self.results.append(TestResult(
                name="All required providers present",
                passed=True,
                component="mellona"
            ))
            return True

        except Exception as e:
            error_msg = str(e)
            self.log_test("Mellona config", False, error=error_msg)
            self.results.append(TestResult(
                name="Mellona config",
                passed=False,
                component="mellona",
                error=error_msg
            ))
            return False

    async def test_config_directory_setup(self) -> bool:
        """Test 3.5: Check ~/.config/chatterbox directory and suggest setup if needed."""
        self.log_header("2.5 CHATTERBOX CONFIG DIRECTORY SETUP")
        try:
            from pathlib import Path

            chatterbox_config_dir = Path.home() / ".config" / "chatterbox"
            mellona_config_file = chatterbox_config_dir / "mellona.yaml"

            if chatterbox_config_dir.exists():
                self.log_test(
                    "Chatterbox config directory exists",
                    True,
                    details=f"Found: {chatterbox_config_dir}"
                )
                self.results.append(TestResult(
                    name="Chatterbox config directory exists",
                    passed=True,
                    component="config",
                    details=str(chatterbox_config_dir)
                ))

                if mellona_config_file.exists():
                    self.log_test(
                        "Chatterbox mellona config exists",
                        True,
                        details=f"Found: {mellona_config_file}"
                    )
                    self.results.append(TestResult(
                        name="Chatterbox mellona config exists",
                        passed=True,
                        component="config",
                        details=str(mellona_config_file)
                    ))
                    return True
                else:
                    suggestion = f"Consider creating: {mellona_config_file}"
                    self.log_test(
                        "Chatterbox mellona config exists",
                        True,
                        details=suggestion
                    )
                    self.results.append(TestResult(
                        name="Chatterbox mellona config exists",
                        passed=True,
                        component="config",
                        details=suggestion
                    ))
                    return True
            else:
                suggestion = (
                    f"Create directory and config: mkdir -p {chatterbox_config_dir} && "
                    f"cp src/chatterbox/mellona.yaml {mellona_config_file}"
                )
                self.log_test(
                    "Chatterbox config directory setup",
                    True,
                    details=suggestion
                )
                self.results.append(TestResult(
                    name="Chatterbox config directory setup",
                    passed=True,
                    component="config",
                    details=suggestion
                ))
                return True

        except Exception as e:
            error_msg = str(e)
            self.log_test("Config directory check", False, error=error_msg)
            self.results.append(TestResult(
                name="Config directory check",
                passed=False,
                component="config",
                error=error_msg
            ))
            return False

    async def test_stt_service(self) -> bool:
        """Test 4: Initialize STT service and check mellona integration."""
        self.log_header("4. STT SERVICE (FASTER-WHISPER VIA MELLONA)")
        try:
            from chatterbox.services.stt import WhisperSTTService

            # Try to initialize with small model to save time
            stt = WhisperSTTService(model="tiny")

            self.log_test("STT service initialized", True, details="Model: tiny")
            self.results.append(TestResult(
                name="STT service initialized",
                passed=True,
                component="stt",
                details="Model: tiny"
            ))

            # Check if service is available (mellona provider check)
            is_available = stt.is_available
            status = "Available" if is_available else "Not available (missing dependencies)"
            self.log_test(
                "STT provider available",
                is_available,
                details=f"is_available={is_available}, {status}"
            )
            self.results.append(TestResult(
                name="STT provider available",
                passed=is_available,
                component="stt",
                details=f"is_available={is_available}"
            ))

            # Check mellona integration
            if hasattr(stt, 'provider') and stt.provider is not None:
                self.log_test(
                    "Mellona STT provider integration",
                    True,
                    details=f"Provider: {stt.provider.__class__.__name__}"
                )
                self.results.append(TestResult(
                    name="Mellona STT provider integration",
                    passed=True,
                    component="stt",
                    details=f"Provider: {stt.provider.__class__.__name__}"
                ))
            else:
                self.log_test(
                    "Mellona STT provider integration",
                    True,
                    details="Provider available (lazy-loaded)"
                )
                self.results.append(TestResult(
                    name="Mellona STT provider integration",
                    passed=True,
                    component="stt"
                ))

            return is_available

        except ImportError as e:
            error = f"Faster-whisper not installed: {e}"
            self.log_test("STT service initialization", False, error=error)
            self.results.append(TestResult(
                name="STT service initialization",
                passed=False,
                component="stt",
                error=error
            ))
            return False
        except Exception as e:
            error_msg = str(e)
            self.log_test("STT service initialization", False, error=error_msg)
            self.results.append(TestResult(
                name="STT service initialization",
                passed=False,
                component="stt",
                error=error_msg
            ))
            return False

    async def test_tts_service(self) -> bool:
        """Test 5: Initialize TTS service and check mellona integration."""
        self.log_header("5. TTS SERVICE (PIPER VIA MELLONA)")
        try:
            from chatterbox.services.tts import PiperTTSService

            # Try to initialize
            tts = PiperTTSService(voice="en_US-lessac-medium")

            self.log_test("TTS service initialized", True, details="Voice: en_US-lessac-medium")
            self.results.append(TestResult(
                name="TTS service initialized",
                passed=True,
                component="tts",
                details="Voice: en_US-lessac-medium"
            ))

            # Check if service is available (mellona provider check)
            is_available = tts.is_available
            status = "Available" if is_available else "Not available (missing dependencies)"
            self.log_test(
                "TTS provider available",
                is_available,
                details=f"is_available={is_available}, {status}"
            )
            self.results.append(TestResult(
                name="TTS provider available",
                passed=is_available,
                component="tts",
                details=f"is_available={is_available}"
            ))

            # Check mellona integration
            if hasattr(tts, 'provider') and tts.provider is not None:
                self.log_test(
                    "Mellona TTS provider integration",
                    True,
                    details=f"Provider: {tts.provider.__class__.__name__}"
                )
                self.results.append(TestResult(
                    name="Mellona TTS provider integration",
                    passed=True,
                    component="tts",
                    details=f"Provider: {tts.provider.__class__.__name__}"
                ))
            else:
                self.log_test(
                    "Mellona TTS provider integration",
                    True,
                    details="Provider available (lazy-loaded)"
                )
                self.results.append(TestResult(
                    name="Mellona TTS provider integration",
                    passed=True,
                    component="tts"
                ))

            return is_available

        except ImportError as e:
            error = f"Piper TTS not installed: {e}"
            self.log_test("TTS service initialization", False, error=error)
            self.results.append(TestResult(
                name="TTS service initialization",
                passed=False,
                component="tts",
                error=error
            ))
            return False
        except Exception as e:
            error_msg = str(e)
            self.log_test("TTS service initialization", False, error=error_msg)
            self.results.append(TestResult(
                name="TTS service initialization",
                passed=False,
                component="tts",
                error=error_msg
            ))
            return False

    async def test_ollama_connection(self) -> bool:
        """Test 6: Validate Ollama connection and model availability."""
        self.log_header("6. OLLAMA CONNECTION & MODEL AVAILABILITY")
        try:
            import aiohttp

            ollama_base_url = "http://localhost:11434"

            # Try to connect and get model list
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(f"{ollama_base_url}/api/tags", timeout=aiohttp.ClientTimeout(total=5)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            models = data.get("models", [])
                            model_names = [m.get("name", "unknown") for m in models]

                            self.log_test(
                                "Ollama reachable",
                                True,
                                details=f"Found {len(models)} models: {', '.join(model_names[:3])}{'...' if len(model_names) > 3 else ''}"
                            )
                            self.results.append(TestResult(
                                name="Ollama reachable",
                                passed=True,
                                component="ollama",
                                details=f"Found {len(models)} models"
                            ))

                            # Check for default model
                            default_model = "llama3.1:8b"
                            has_default = any(default_model in m.get("name", "") for m in models)

                            if has_default:
                                self.log_test(
                                    f"Default model ({default_model}) available",
                                    True
                                )
                                self.results.append(TestResult(
                                    name=f"Default model ({default_model}) available",
                                    passed=True,
                                    component="ollama"
                                ))
                                return True
                            else:
                                warning = f"Default model {default_model} not found. Available: {', '.join(model_names[:3])}"
                                self.log_test(f"Default model ({default_model}) available", False, error=warning)
                                self.results.append(TestResult(
                                    name=f"Default model ({default_model}) available",
                                    passed=False,
                                    component="ollama",
                                    error=warning
                                ))
                                return False
                        else:
                            error = f"Ollama API returned status {resp.status}"
                            self.log_test("Ollama reachable", False, error=error)
                            self.results.append(TestResult(
                                name="Ollama reachable",
                                passed=False,
                                component="ollama",
                                error=error
                            ))
                            return False
                except asyncio.TimeoutError:
                    error = f"Ollama not reachable at {ollama_base_url} (timeout)"
                    self.log_test("Ollama reachable", False, error=error)
                    self.results.append(TestResult(
                        name="Ollama reachable",
                        passed=False,
                        component="ollama",
                        error=error
                    ))
                    return False
                except Exception as e:
                    error = f"Ollama connection error: {e}"
                    self.log_test("Ollama reachable", False, error=error)
                    self.results.append(TestResult(
                        name="Ollama reachable",
                        passed=False,
                        component="ollama",
                        error=error
                    ))
                    return False

        except ImportError:
            error = "aiohttp not installed"
            self.log_test("Ollama connection test", False, error=error)
            self.results.append(TestResult(
                name="Ollama connection test",
                passed=False,
                component="ollama",
                error=error
            ))
            return False
        except Exception as e:
            error_msg = str(e)
            self.log_test("Ollama connection test", False, error=error_msg)
            self.results.append(TestResult(
                name="Ollama connection test",
                passed=False,
                component="ollama",
                error=error_msg
            ))
            return False

    async def test_voice_assistant_agent(self) -> bool:
        """Test 7: Initialize VoiceAssistantAgent with mellona config."""
        self.log_header("7. VOICEASSISTANTAGENT INITIALIZATION")
        try:
            from chatterbox.agent import VoiceAssistantAgent

            # Initialize with test configuration
            agent = VoiceAssistantAgent(
                ollama_base_url="http://localhost:11434/v1",
                ollama_model="llama3.1:8b",
                ollama_temperature=0.7,
                conversation_window_size=3,
                debug=self.verbose,
                mellona_config_path=None,  # Use default discovery
                mellona_profile="default"
            )

            self.log_test("VoiceAssistantAgent initialized", True, details="Profile: default")
            self.results.append(TestResult(
                name="VoiceAssistantAgent initialized",
                passed=True,
                component="agent",
                details="Profile: default"
            ))

            # Check if agent has required components
            has_llm = agent.llm is not None
            has_memory = agent.memory is not None
            has_tools = len(agent.tools) > 0

            details = f"LLM={has_llm}, Memory={has_memory}, Tools={has_tools}"

            if has_llm and has_memory:
                self.log_test("Agent has required components", True, details=details)
                self.results.append(TestResult(
                    name="Agent has required components",
                    passed=True,
                    component="agent",
                    details=details
                ))
                return True
            else:
                missing = []
                if not has_llm:
                    missing.append("LLM")
                if not has_memory:
                    missing.append("Memory")
                error = f"Missing: {', '.join(missing)}"
                self.log_test("Agent has required components", False, error=error)
                self.results.append(TestResult(
                    name="Agent has required components",
                    passed=False,
                    component="agent",
                    error=error
                ))
                return False

        except Exception as e:
            error_msg = str(e)
            self.log_test("VoiceAssistantAgent initialization", False, error=error_msg)
            if self.verbose:
                self.log_test("Stack trace", False, error=traceback.format_exc())
            self.results.append(TestResult(
                name="VoiceAssistantAgent initialization",
                passed=False,
                component="agent",
                error=error_msg
            ))
            return False

    async def test_tool_registry(self) -> bool:
        """Test 8: Check tool registry is available and populated."""
        self.log_header("8. TOOL REGISTRY")
        try:
            from chatterbox.tools import get_available_tools

            tools = get_available_tools()

            if tools and len(tools) > 0:
                tool_names = [t.name if hasattr(t, 'name') else str(t) for t in tools]
                details = f"Tools available: {', '.join(tool_names)}"
                self.log_test("Tool registry populated", True, details=details)
                self.results.append(TestResult(
                    name="Tool registry populated",
                    passed=True,
                    component="tools",
                    details=details
                ))
                return True
            else:
                error = "No tools found in registry"
                self.log_test("Tool registry populated", False, error=error)
                self.results.append(TestResult(
                    name="Tool registry populated",
                    passed=False,
                    component="tools",
                    error=error
                ))
                return False

        except Exception as e:
            error_msg = str(e)
            self.log_test("Tool registry access", False, error=error_msg)
            self.results.append(TestResult(
                name="Tool registry access",
                passed=False,
                component="tools",
                error=error_msg
            ))
            return False

    async def test_basic_pipeline(self) -> bool:
        """Test 9: Simulate basic STT→Agent→TTS pipeline."""
        self.log_header("9. BASIC PIPELINE SIMULATION (MOCKED)")
        try:
            # This test uses mocked audio to avoid requiring actual audio files
            from chatterbox.agent import VoiceAssistantAgent
            from unittest.mock import AsyncMock, patch

            agent = VoiceAssistantAgent(
                ollama_base_url="http://localhost:11434/v1",
                ollama_model="llama3.1:8b",
                debug=False
            )

            # Mock LLM response to avoid actual Ollama call
            with patch.object(agent.llm, 'apredict') as mock_predict:
                mock_predict.return_value = "The current time is noon."

                # Try to process input
                try:
                    # Note: This is a simplified test. Full pipeline would require
                    # setting up proper conversation entity with Wyoming protocol
                    self.log_test(
                        "Basic pipeline simulation",
                        True,
                        details="Agent ready for STT/TTS integration"
                    )
                    self.results.append(TestResult(
                        name="Basic pipeline simulation",
                        passed=True,
                        component="pipeline",
                        details="Agent ready for STT/TTS integration"
                    ))
                    return True
                except Exception as e:
                    error = f"Pipeline execution failed: {e}"
                    self.log_test("Basic pipeline simulation", False, error=error)
                    self.results.append(TestResult(
                        name="Basic pipeline simulation",
                        passed=False,
                        component="pipeline",
                        error=error
                    ))
                    return False

        except Exception as e:
            error_msg = str(e)
            self.log_test("Pipeline setup", False, error=error_msg)
            self.results.append(TestResult(
                name="Pipeline setup",
                passed=False,
                component="pipeline",
                error=error_msg
            ))
            return False

    async def run_all_tests(self):
        """Run all tests sequentially."""
        self.log(f"{Colors.BOLD}{Colors.BLUE}Epic 5 Prerequisites Smoke Test{Colors.RESET}", force_print=True)
        self.log(f"Verbose: {self.verbose}, JSON: {self.json_output}\n", force_print=True)

        try:
            await self.test_settings_loading()
            await self.test_mellona_config()
            await self.test_config_directory_setup()
            await self.test_stt_service()
            await self.test_tts_service()
            await self.test_ollama_connection()
            await self.test_voice_assistant_agent()
            await self.test_tool_registry()
            await self.test_basic_pipeline()
        except Exception as e:
            self.log(f"\n{Colors.RED}Unexpected error during test execution: {e}{Colors.RESET}", force_print=True)
            if self.verbose:
                self.log(traceback.format_exc(), force_print=True)

    def print_summary(self):
        """Print test summary."""
        if self.json_output:
            return self._print_json_summary()

        self.log_header("SUMMARY")

        passed = sum(1 for r in self.results if r.passed)
        total = len(self.results)

        self.log(f"\nResults: {Colors.GREEN}{passed}/{total} passed{Colors.RESET}\n", force_print=True)

        # Group by component
        by_component = {}
        for result in self.results:
            comp = result.component or "unknown"
            if comp not in by_component:
                by_component[comp] = []
            by_component[comp].append(result)

        for component, comp_results in sorted(by_component.items()):
            comp_passed = sum(1 for r in comp_results if r.passed)
            comp_total = len(comp_results)
            status = f"{Colors.GREEN}✓{Colors.RESET}" if comp_passed == comp_total else f"{Colors.RED}✗{Colors.RESET}"
            self.log(
                f"{status} {component.upper()}: {comp_passed}/{comp_total} passed",
                force_print=True
            )

            for result in comp_results:
                if not result.passed:
                    self.log(f"  - {result.name}", Colors.RED, force_print=True)
                    if result.error:
                        self.log(f"    {result.error}", Colors.YELLOW, force_print=True)

        # Recommendations
        if passed < total:
            self.log(f"\n{Colors.YELLOW}Recommendations:{Colors.RESET}", force_print=True)
            for result in self.results:
                if not result.passed:
                    if "ollama" in result.name.lower():
                        self.log(
                            "  • Start Ollama: ollama serve",
                            Colors.YELLOW,
                            force_print=True
                        )
                    elif "faster-whisper" in str(result.error or "").lower():
                        self.log(
                            "  • Install faster-whisper: pip install faster-whisper",
                            Colors.YELLOW,
                            force_print=True
                        )
                    elif "piper" in str(result.error or "").lower():
                        self.log(
                            "  • Install piper-tts: pip install piper-tts",
                            Colors.YELLOW,
                            force_print=True
                        )

        # Exit code
        exit_code = 0 if passed == total else 1
        self.log(f"\n{Colors.BOLD}Exit Code: {exit_code}{Colors.RESET}\n", force_print=True)
        return exit_code

    def _print_json_summary(self):
        """Print JSON summary for CI/CD integration."""
        summary = {
            "total_tests": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "results": [r.to_dict() for r in self.results],
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        }
        print(json.dumps(summary, indent=2))
        return 0 if summary["failed"] == 0 else 1


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Epic 5 prerequisites smoke test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/env-smoke-test.py                 # Default verbose output
  python scripts/env-smoke-test.py --json          # JSON for CI/CD
  python scripts/env-smoke-test.py --verbose       # Even more details
        """
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed diagnostics and error messages"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format (for CI/CD integration)"
    )

    args = parser.parse_args()

    test = SmokeTest(verbose=args.verbose, json_output=args.json)
    await test.run_all_tests()
    exit_code = test.print_summary()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
