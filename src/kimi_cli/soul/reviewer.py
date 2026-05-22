from __future__ import annotations

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from kosong import generate
from kosong.chat_provider import (
    APIConnectionError,
    APIEmptyResponseError,
    APIStatusError,
    APITimeoutError,
    ChatProviderError,
)
from kosong.message import Message, TextPart
from kosong.utils.test_logger import write_file_log

from kimi_cli.prompts import REVIEWER
from kimi_cli.utils.logging import logger

if TYPE_CHECKING:
    from kimi_cli.soul.agent import Runtime
    from kimi_cli.soul.context import Context


@dataclass
class ReviewResult:
    """Result of reviewing the agent's final response."""

    need_changes: bool
    """True if the response needs to be revised."""

    feedback: str
    """Specific feedback to send back to the LLM when need_changes is True."""

    refined_response: str
    """A refined version of the response when only minor fixes are needed."""


type LogFunc = Callable[[str, str], None]


class Reviewer:
    """Reviews the agent's final response before presenting it to the user."""

    def __init__(self, runtime: Runtime, *, log_func: LogFunc | None = None) -> None:
        self._runtime = runtime
        self._log_func = log_func or write_file_log

    async def review(self, context: Context, final_message: Message) -> ReviewResult | None:
        """Review the final assistant message.

        Returns None when disabled or the review call fails (fail-open).
        """
        llm = self._runtime.llm
        if llm is None:
            logger.warning("Reviewer skipped: no LLM available")
            return None

        # Only the last few turns matter for identity-rule checks; strip tool content
        recent = [m for m in context.history if m.role in ("user", "assistant")][-4:]
        history_text = "\n\n".join(f"{msg.role}: {msg.extract_text(' ')[:500]}" for msg in recent)
        final_text = final_message.extract_text(" ")

        review_prompt = REVIEWER.format(history_text=history_text, final_text=final_text)

        logger.info("Reviewer starting review for turn")
        self._log_func("REVIEWER_PROMPT", review_prompt)

        messages = [Message(role="user", content=[TextPart(text=review_prompt)])]

        # Build review provider: use reviewer_model if configured, else disable thinking on primary
        review_provider = llm.chat_provider
        reviewer_model_alias = self._runtime.config.reviewer_model
        if reviewer_model_alias:
            model_cfg = self._runtime.config.models.get(reviewer_model_alias)
            if model_cfg:
                provider_cfg = self._runtime.config.providers.get(model_cfg.provider)
                if provider_cfg:
                    from kimi_cli.llm import create_llm

                    fast_llm = create_llm(provider_cfg, model_cfg, thinking=False, stream=True)
                    if fast_llm:
                        review_provider = fast_llm.chat_provider
        else:
            # Reviewer task is simple identity-rule checking — no reasoning needed
            review_provider = llm.chat_provider.with_thinking("off")

        try:
            result = await asyncio.wait_for(
                generate(
                    review_provider,
                    "You are a helpful code reviewer. Respond only with valid JSON.",
                    [],
                    messages,
                ),
                timeout=60.0,
            )
        except TimeoutError:
            logger.warning("Reviewer timed out after 60s")
            self._log_func("REVIEWER_ERROR", "timeout after 60s")
            return None
        except APITimeoutError as exc:
            logger.warning("Reviewer API timeout: {error}", error=exc)
            self._log_func("REVIEWER_ERROR", f"api_timeout: {exc}")
            return None
        except APIConnectionError as exc:
            logger.warning("Reviewer API connection error: {error}", error=exc)
            self._log_func("REVIEWER_ERROR", f"api_connection: {exc}")
            return None
        except APIStatusError as exc:
            logger.warning("Reviewer API status error: {error}", error=exc)
            self._log_func("REVIEWER_ERROR", f"api_status: {exc}")
            return None
        except APIEmptyResponseError as exc:
            logger.info("Reviewer got empty response: {error}", error=exc)
            self._log_func("REVIEWER_ERROR", f"empty_response: {exc}")
            return None
        except ChatProviderError as exc:
            logger.warning("Reviewer chat provider error: {error}", error=exc)
            self._log_func("REVIEWER_ERROR", f"chat_provider: {exc}")
            return None

        raw = result.message.extract_text(" ").strip()
        logger.info("Reviewer raw response: {raw!r}", raw=raw)
        self._log_func("REVIEWER_RAW_RESPONSE", raw)

        parsed = _extract_json_object(raw)
        if parsed is None:
            logger.warning("Reviewer response had no parseable JSON object")
            self._log_func("REVIEWER_ERROR", "no_json_object_found")
            return None
        if not isinstance(parsed, dict):
            kind = type(parsed).__name__
            logger.warning("Reviewer JSON was not an object: type={type}", type=kind)
            self._log_func("REVIEWER_ERROR", f"json_not_object: {kind}")
            return None

        parsed = cast(dict[str, object], parsed)

        try:
            need_changes_raw: object = parsed.get("need_changes", False)
            feedback_raw: object = parsed.get("feedback", "")
            refined_response_raw: object = parsed.get("refined_response", "")
            review_result = ReviewResult(
                need_changes=_coerce_bool(need_changes_raw),
                feedback=str(feedback_raw),
                refined_response=str(refined_response_raw),
            )
        except (TypeError, ValueError) as exc:
            logger.warning("Reviewer result coercion failed: {error}", error=exc)
            self._log_func("REVIEWER_ERROR", f"coercion: {exc}")
            return None

        logger.info(
            "Reviewer decision: need_changes={need_changes} "
            "has_feedback={has_feedback} has_refined={has_refined}",
            need_changes=review_result.need_changes,
            has_feedback=bool(review_result.feedback),
            has_refined=bool(review_result.refined_response),
        )
        self._log_func(
            "REVIEWER_RESULT",
            json.dumps(
                {
                    "need_changes": review_result.need_changes,
                    "feedback": review_result.feedback,
                    "refined_response": review_result.refined_response,
                },
                ensure_ascii=False,
            ),
        )
        return review_result


def _extract_json_object(text: str) -> object | None:
    """Extract the first JSON value from text, tolerating preamble/fences/trailing prose."""
    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "{[":
            continue
        try:
            obj, _ = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            continue
        return obj
    return None


def _coerce_bool(value: object) -> bool:
    """Coerce a JSON-decoded value to bool. Treats stringy 'false'/'0'/'' as False."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() not in {"", "false", "0", "no", "null", "none"}
    return bool(value)
