"""
Observability and Monitoring Handler for LangChain.

This module provides custom callback handlers for LangChain to capture and log
detailed information about LLM usage, including token counts and estimated costs.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs.llm_result import LLMResult

logger = logging.getLogger(__name__)


class ObservabilityHandler(BaseCallbackHandler):
    """Custom callback handler for observability and monitoring.

    Captures LLM usage metadata and logs detailed information about:
    - Token counts (prompt, completion, total)
    - Estimated costs based on cloud pricing models
    - LLM context and responses

    This handler uses GPT-4o-mini pricing as a reference for virtual cost
    calculations since Ollama is locally run and free.

    Attributes:
        name: Handler name for identification
        raise_error: Whether to raise errors during callback execution
        raise_agg_error: Whether to aggregate and raise errors
    """

    # GPT-4o-mini pricing (per million tokens)
    # https://openai.com/pricing/
    PRICING_PER_MILLION = {
        "input": 0.15,      # $0.15 per 1M input tokens
        "output": 0.60,     # $0.60 per 1M output tokens
    }

    def __init__(self):
        """Initialize the observability handler."""
        super().__init__()
        self.name = "ObservabilityHandler"

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any,
    ) -> None:
        """Handle the start of an LLM call.

        Args:
            serialized: Serialized LLM configuration
            prompts: List of prompts being sent to the LLM
            **kwargs: Additional arguments
        """
        logger.debug(f"[LLM START] Model: {serialized.get('_type', 'unknown')}")
        for i, prompt in enumerate(prompts):
            logger.debug(f"[PROMPT {i}] {prompt[:100]}...")

    def on_llm_end(
        self,
        response: LLMResult,
        **kwargs: Any,
    ) -> None:
        """Handle the end of an LLM call and extract usage metrics.

        Args:
            response: The LLMResult containing model outputs and metadata
            **kwargs: Additional arguments
        """
        try:
            # Extract usage metadata from response
            if hasattr(response, "llm_output") and response.llm_output:
                usage_metadata = response.llm_output.get("usage", {})
            elif hasattr(response, "usage_metadata") and response.usage_metadata:
                usage_metadata = response.usage_metadata
            else:
                usage_metadata = {}

            # Extract token counts
            prompt_tokens = usage_metadata.get("prompt_tokens", 0)
            completion_tokens = usage_metadata.get("completion_tokens", 0)
            total_tokens = usage_metadata.get("total_tokens", 0)

            if not total_tokens and (prompt_tokens or completion_tokens):
                total_tokens = prompt_tokens + completion_tokens

            # Calculate estimated cost based on virtual cloud pricing
            estimated_cost = self._calculate_estimated_cost(
                prompt_tokens, completion_tokens
            )

            # Log detailed usage information
            logger.debug(
                f"[LLM USAGE] Tokens: {total_tokens} "
                f"(prompt: {prompt_tokens}, completion: {completion_tokens})"
            )

            # Log the LLM response text
            if response.generations and len(response.generations) > 0:
                for i, generation in enumerate(response.generations):
                    if generation and len(generation) > 0:
                        output_text = generation[0].text[:200]
                        logger.debug(f"[LLM OUTPUT {i}] {output_text}...")

            # Print summary to stdout
            cost_str = f"${estimated_cost:.6f}"
            print(
                f"[LLM USAGE] Tokens: {total_tokens} | "
                f"Estimated Value: {cost_str}"
            )

            # Log full usage metrics as debug info
            logger.debug(
                f"[LLM METRICS] {json.dumps({
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'total_tokens': total_tokens,
                    'estimated_cost': estimated_cost,
                })}"
            )

        except Exception as e:
            logger.error(f"Error in observability handler: {e}", exc_info=True)

    def on_llm_error(
        self,
        error: Exception,
        **kwargs: Any,
    ) -> None:
        """Handle errors during LLM calls.

        Args:
            error: The exception that occurred
            **kwargs: Additional arguments
        """
        logger.error(f"[LLM ERROR] {str(error)}")

    def _calculate_estimated_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> float:
        """Calculate estimated cost based on token usage.

        Uses GPT-4o-mini pricing as a reference point for estimating costs
        if the service were scaled to a cloud provider.

        Args:
            prompt_tokens: Number of prompt tokens used
            completion_tokens: Number of completion tokens generated

        Returns:
            Estimated cost in USD
        """
        input_cost = (
            prompt_tokens / 1_000_000 * self.PRICING_PER_MILLION["input"]
        )
        output_cost = (
            completion_tokens / 1_000_000 * self.PRICING_PER_MILLION["output"]
        )
        return input_cost + output_cost
