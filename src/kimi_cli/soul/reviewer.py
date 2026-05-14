from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from kosong import generate
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


class Reviewer:
    """Reviews the agent's final response before presenting it to the user."""

    def __init__(self, runtime: Runtime) -> None:
        self._runtime = runtime

    async def review(self, context: Context, final_message: Message) -> ReviewResult | None:
        """Review the final assistant message.

        Returns None when disabled or the review call fails (fail-open).
        """
        llm = self._runtime.llm
        if llm is None:
            logger.warning("Reviewer skipped: no LLM available")
            return None

        history_text = "\n\n".join(
            f"{msg.role}: {msg.extract_text(' ')}" for msg in context.history
        )
        final_text = final_message.extract_text(" ")

        review_prompt = REVIEWER.format(history_text=history_text, final_text=final_text)

        logger.info("Reviewer starting review for turn")
        write_file_log("REVIEWER_PROMPT", review_prompt)

        messages = [Message(role="user", content=[TextPart(text=review_prompt)])]

        try:
            result = await generate(
                llm.chat_provider,
                "You are a helpful code reviewer. Respond only with valid JSON.",
                [],
                messages,
            )
            raw = result.message.extract_text(" ").strip()
            logger.info("Reviewer raw response: {raw!r}", raw=raw)
            write_file_log("REVIEWER_RAW_RESPONSE", raw)

            # Strip markdown code fences if present
            if raw.startswith("```"):
                import re

                raw = re.sub(r"^```(?:json)?\s*", "", raw)
                raw = re.sub(r"\s*```$", "", raw)
                raw = raw.strip()

            parsed = json.loads(raw)
            review_result = ReviewResult(
                need_changes=bool(parsed.get("need_changes", False)),
                feedback=str(parsed.get("feedback", "")),
                refined_response=str(parsed.get("refined_response", "")),
            )
            logger.info(
                "Reviewer decision: need_changes={need_changes} "
                "has_feedback={has_feedback} has_refined={has_refined}",
                need_changes=review_result.need_changes,
                has_feedback=bool(review_result.feedback),
                has_refined=bool(review_result.refined_response),
            )
            write_file_log(
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
        except Exception as exc:
            logger.warning("Reviewer failed: {error}", error=exc)
            write_file_log("REVIEWER_ERROR", str(exc))
            return None
