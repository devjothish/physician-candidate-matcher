"""Claude API client with retry logic, cost tracking, and structured logging."""

import json
import time
from dataclasses import dataclass

import anthropic
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.config import get_settings
from app.db.repositories.metrics import MetricsRepository
from app.utils.exceptions import ClaudeAPIError
from app.utils.logging import get_logger
from app.utils.tokens import calculate_cost

logger = get_logger(__name__)

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 529}


@dataclass
class LLMResult:
    parsed: dict | list
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


def _is_retryable(exc: BaseException) -> bool:
    return isinstance(exc, anthropic.APIStatusError) and exc.status_code in RETRYABLE_STATUS_CODES


class ClaudeService:

    def __init__(self, request_id: str) -> None:
        settings = get_settings()
        self.request_id = request_id
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.metrics_repo = MetricsRepository()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception(_is_retryable),
        reraise=True,
    )
    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int,
    ) -> anthropic.types.Message:
        """Raw API call with retry on transient errors only (429, 5xx)."""
        return self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        max_tokens: int = 2048,
        prompt_type: str = "matching",
    ) -> LLMResult:
        start_time = time.time()
        input_tokens = 0
        output_tokens = 0

        try:
            response = self._call_api(system_prompt, user_prompt, model, max_tokens)

            input_tokens = response.usage.input_tokens
            output_tokens = response.usage.output_tokens
            latency_ms = (time.time() - start_time) * 1000
            cost = calculate_cost(input_tokens, output_tokens, model)

            raw_text = ""
            for block in response.content:
                if block.type == "text":
                    raw_text = block.text
                    break

            if not raw_text:
                raise ClaudeAPIError(detail="Empty response from Claude API")

            cleaned = raw_text.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines)

            parsed = json.loads(cleaned)

            self.metrics_repo.log_llm_call(
                request_id=self.request_id,
                model=model,
                prompt_type=prompt_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                cost_usd=cost,
                success=True,
            )

            logger.info(
                "claude_call_complete",
                request_id=self.request_id,
                model=model,
                prompt_type=prompt_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=round(latency_ms, 1),
                cost_usd=cost,
            )

            return LLMResult(
                parsed=parsed,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost,
                latency_ms=latency_ms,
            )

        except json.JSONDecodeError as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_failure(model, prompt_type, input_tokens, output_tokens, latency_ms, f"JSON parse error: {e}")
            raise ClaudeAPIError(detail="Failed to parse LLM response as JSON") from e

        except anthropic.APIStatusError as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_failure(model, prompt_type, input_tokens, output_tokens, latency_ms, str(e))
            raise ClaudeAPIError(detail=f"Claude API error (status {e.status_code})") from e

        except anthropic.APIError as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_failure(model, prompt_type, input_tokens, output_tokens, latency_ms, str(e))
            raise ClaudeAPIError(detail="Claude API connection error") from e

    def _log_failure(
        self,
        model: str,
        prompt_type: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        error_message: str,
    ) -> None:
        cost = calculate_cost(input_tokens, output_tokens, model)
        self.metrics_repo.log_llm_call(
            request_id=self.request_id,
            model=model,
            prompt_type=prompt_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            cost_usd=cost,
            success=False,
            error_message=error_message[:500],
        )
        logger.error(
            "claude_call_failed",
            request_id=self.request_id,
            model=model,
            error=error_message[:200],
        )
