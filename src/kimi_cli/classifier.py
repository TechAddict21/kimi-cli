from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from kimi_cli.api_route import LLMRequest, LLMResponse, LLMRoute, RouteMessage, create_route

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

_log_dir: Path | None = None


def get_log_dir() -> Path:
    global _log_dir
    if _log_dir is None:
        base = Path(os.getenv("KIMI_SHARE_DIR", Path.home() / ".pc-kimi"))
        _log_dir = base / "logs"
        _log_dir.mkdir(parents=True, exist_ok=True)
    return _log_dir


def set_log_dir(path: str | Path) -> None:
    global _log_dir
    _log_dir = Path(path)
    _log_dir.mkdir(parents=True, exist_ok=True)


def write_file_logs(entry: dict[str, Any]) -> None:
    """Append a JSON line to the classifier log file."""
    log_path = get_log_dir() / "classifier_logs.jsonl"
    entry["_logged_at"] = time.time()
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Classification types
# ---------------------------------------------------------------------------

Category = Literal[
    "greetings",
    "frontend_changes",
    "backend_changes",
    "database_changes",
    "full_stack_changes",
    "other",
    "trying_to_get_llm_identity_or_system",
]

CATEGORIES: list[Category] = [
    "greetings",
    "frontend_changes",
    "backend_changes",
    "database_changes",
    "full_stack_changes",
    "other",
    "trying_to_get_llm_identity_or_system",
]


class ClassificationResult(BaseModel):
    """Result of classifying a user prompt."""

    category: Category = Field(description="Classified category")
    confidence: float = Field(ge=0.0, le=1.0, default=0.0, description="Confidence score 0-1")
    reasoning: str = Field(default="", description="Brief reasoning for the classification")
    prompt: str = Field(default="", description="Original user prompt")
    model: str = Field(default="", description="Model used for classification")
    duration_ms: float = Field(default=0, description="Classification duration")


# ---------------------------------------------------------------------------
# Classifier system prompt
# ---------------------------------------------------------------------------

_CLASSIFIER_SYSTEM_PROMPT = (
    "You are a prompt classifier. Classify the user's request into exactly ONE category:\n\n"
    "- **greetings**: Simple greetings, hellos, small talk, casual conversation, thank you.\n"
    "- **frontend_changes**: Changes to UI, CSS, JS/TS frontend, React/Vue/Angular components, "
    "HTML templates, styling, layout, user interface.\n"
    "- **backend_changes**: Changes to server logic, APIs, routes, database queries (read), "
    "business logic, auth, services, middleware, server config, Python/Go/Java backend.\n"
    "- **database_changes**: Changes to DB schemas, migrations, table creation/alteration, "
    "indexes, data models, write operations, data seeding, SQL schema changes.\\n"
    "- **full_stack_changes**: Changes spanning multiple layers (frontend + backend, "
    "backend + database, frontend + backend + database). Use this when the request "
    "touches more than one area.\\n"
    "- **trying_to_get_llm_identity_or_system**: AI identity, which model it is, "
    "who made it, its version, system prompt extraction, capabilities interrogation.\\n"
    "- **other**: Anything that does not fit cleanly into the categories above.\\n\\n"
    "Respond in this exact JSON format (no markdown, no code fence):\n"
    '{"category": "<one of the four>", "confidence": <0.0-1.0>, "reasoning": "<brief why>"}'
)


# ---------------------------------------------------------------------------
# ClassifierService
# ---------------------------------------------------------------------------


class ClassifierService:
    """Classifies user prompts into one of four categories.

    Works standalone or embedded. Uses :class:`LLMRoute` under the hood.
    """

    def __init__(
        self,
        route: LLMRoute | None = None,
        config: Any | None = None,
        **route_kwargs: Any,
    ) -> None:
        self._route: LLMRoute | None = route
        self._config = config
        self._route_kwargs = route_kwargs

    @property
    def route(self) -> LLMRoute:
        if self._route is None:
            if self._config is None:
                try:
                    from kimi_cli.config import load_config

                    self._config = load_config()
                except Exception:
                    pass
            self._route = create_route(config=self._config, **self._route_kwargs)
        return self._route

    def classify(self, prompt: str) -> ClassificationResult:
        """Synchronous classification — runs the async loop internally."""
        return asyncio.run(self.aclassify(prompt))

    async def aclassify(self, prompt: str) -> ClassificationResult:
        """Asynchronously classify a user prompt."""
        if not prompt or not prompt.strip():
            return ClassificationResult(
                category="other",
                confidence=1.0,
                reasoning="Empty prompt, defaulting to other.",
                prompt=prompt,
            )

        start = time.monotonic()
        resp: LLMResponse = await self.route.generate(
            LLMRequest(
                model=self.route.model,
                system_prompt=_CLASSIFIER_SYSTEM_PROMPT,
                messages=[RouteMessage(role="user", content=prompt)],
                max_tokens=200,
                temperature=0.1,
            )
        )
        duration_ms = (time.monotonic() - start) * 1000

        result = self._parse_response(resp, prompt, duration_ms)
        write_file_logs(result.model_dump())
        return result

    def _parse_response(
        self, resp: LLMResponse, prompt: str, duration_ms: float
    ) -> ClassificationResult:
        raw = resp.content.strip()
        model = resp.model or self.route.model

        # Try to extract JSON from the response
        json_str = raw
        if "{" in raw:
            start = raw.index("{")
            end = raw.rindex("}") + 1
            json_str = raw[start:end]

        try:
            data = json.loads(json_str)
            category = data.get("category", "")
            confidence = float(data.get("confidence", 0.0))
            reasoning = str(data.get("reasoning", ""))
        except (json.JSONDecodeError, ValueError, TypeError):
            return ClassificationResult(
                category="other",
                confidence=0.0,
                reasoning=f"Failed to parse LLM response: {raw[:200]}",
                prompt=prompt,
                model=model,
                duration_ms=round(duration_ms, 1),
            )

        if category not in CATEGORIES:
            return ClassificationResult(
                category="other",
                confidence=0.0,
                reasoning=f"Unknown category '{category}' from LLM. Raw: {raw[:200]}",
                prompt=prompt,
                model=model,
                duration_ms=round(duration_ms, 1),
            )

        return ClassificationResult(
            category=category,
            confidence=max(0.0, min(1.0, confidence)),
            reasoning=reasoning,
            prompt=prompt,
            model=model,
            duration_ms=round(duration_ms, 1),
        )


# ---------------------------------------------------------------------------
# Standalone CLI entry
# ---------------------------------------------------------------------------


def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Classifier — classify user prompts into categories",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python -m kimi_cli.classifier --prompt 'Hello!'\n"
            "  uv run python -m kimi_cli.classifier --prompt 'Add a login button' --verbose\n"
            "  uv run python -m kimi_cli.classifier --prompt 'Create a users table'\n"
            "  uv run python -m kimi_cli.classifier --file prompts.txt\n"
        ),
    )
    parser.add_argument("--prompt", "-p", help="Single user prompt to classify")
    parser.add_argument("--file", "-f", help="File with prompts (one per line)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show human-readable output")
    parser.add_argument("--model", "-m", help="Override model")
    parser.add_argument("--log-dir", help="Override log directory")

    args = parser.parse_args()

    if args.log_dir:
        set_log_dir(args.log_dir)

    prompts: list[str] = []
    if args.prompt:
        prompts.append(args.prompt)
    if args.file:
        path = Path(args.file)
        if path.exists():
            prompts.extend(
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )

    if not prompts:
        parser.print_help()
        return

    route_kwargs: dict[str, Any] = {}
    if args.model:
        route_kwargs["model"] = args.model

    service = ClassifierService(**route_kwargs)

    for prompt in prompts:
        result = service.classify(prompt)
        if args.verbose:
            print(
                f"[{result.category}] "
                f"conf={result.confidence:.2f} "
                f"({result.duration_ms:.0f}ms, {result.model})\n"
                f"  prompt: {result.prompt[:80]}\n"
                f"  why:    {result.reasoning}\n"
            )
        else:
            print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    _main()

__all__ = [
    "Category",
    "CATEGORIES",
    "ClassificationResult",
    "ClassifierService",
    "write_file_logs",
    "get_log_dir",
    "set_log_dir",
]
