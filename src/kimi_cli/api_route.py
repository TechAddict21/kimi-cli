# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false

from __future__ import annotations

import asyncio
import json
import pathlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal, cast

from openai import AsyncOpenAI
from pydantic import BaseModel, Field

from kimi_cli.constant import USER_AGENT

# ---------------------------------------------------------------------------
# Request / Response models (OpenAPI-friendly)
# ---------------------------------------------------------------------------


class ContentPartDef(BaseModel):
    """A single content part in a message (text, thinking, etc.)."""

    type: Literal["text", "think", "refusal", "image_url", "audio_url", "video_url"] = "text"
    text: str | None = None
    think: str | None = None
    encrypted: str | None = None
    refusal: str | None = None
    image_url: dict[str, Any] | None = None
    audio_url: dict[str, Any] | None = None
    video_url: dict[str, Any] | None = None


class ToolCallDef(BaseModel):
    """A tool call embedded in an assistant message."""

    id: str
    type: str = "function"
    function: dict[str, Any]  # {name: str, arguments: str}


class RouteMessage(BaseModel):
    """A single message in the conversation history."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str | list[ContentPartDef] | None = None
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[ToolCallDef] | None = None


class ToolDefinition(BaseModel):
    """Schema for a tool the model can call."""

    name: str
    description: str = ""
    parameters: dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class LLMRequest(BaseModel):
    """Request payload for an LLM generation."""

    model: str = "MiniMax-M2.7-highspeed"
    system_prompt: str | None = None
    messages: list[RouteMessage] = []
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    thinking: bool | None = None
    reasoning_split: bool | None = None
    tools: list[ToolDefinition] | None = None
    base_url: str | None = None
    api_key: str | None = None
    extra_headers: dict[str, str] | None = None
    extra_body: dict[str, Any] | None = None


class ContentPartOut(BaseModel):
    """A content part in the response."""

    type: str
    text: str | None = None
    think: str | None = None
    encrypted: str | None = None
    refusal: str | None = None


class ToolCallOut(BaseModel):
    """A tool call in the response."""

    id: str
    name: str
    arguments: str


class TokenUsageOut(BaseModel):
    """Token usage information."""

    input: int = 0
    output: int = 0
    input_cache_read: int = 0
    input_cache_creation: int = 0

    @property
    def total(self) -> int:
        return self.input + self.output


class LLMResponse(BaseModel):
    """Structured response from an LLM generation."""

    content: str = ""
    content_parts: list[ContentPartOut] = []
    tool_calls: list[ToolCallOut] = []
    token_usage: TokenUsageOut | None = None
    model: str = ""
    message_id: str | None = None
    duration_ms: float = 0
    finish_reason: str | None = None
    tps: float = 0


# ---------------------------------------------------------------------------
# LLMRoute — the main class
# ---------------------------------------------------------------------------


@dataclass
class LLMRoute:
    """A reusable route for making OpenAI-compatible LLM calls (default: MiniMax).

    Wraps the OpenAI SDK with proper error handling, streaming support,
    thinking-content extraction, MiniMax ``reasoning_split`` support,
    and structured response types.

    Usage::

        route = LLMRoute(api_key="your-key")
        resp = await route.generate(
            LLMRequest(system_prompt="You are a helpful assistant.")
        )
        print(resp.content)

    Without arguments, the default model is ``MiniMax-M2.7-highspeed``
    pointed at ``https://api.minimax.io/v1``. Use environment variables
    ``MINIMAX_API_KEY``, ``MINIMAX_BASE_URL``, ``MINIMAX_MODEL`` to
    configure silently.
    """

    base_url: str = "https://api.minimax.io/v1"
    api_key: str = ""
    model: str = "MiniMax-M2.7-highspeed"
    max_tokens: int = 32000
    temperature: float | None = None
    top_p: float | None = None
    extra_headers: dict[str, str] | None = None
    stream: bool = False
    reasoning_split: bool | None = None

    _client: AsyncOpenAI | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not self.base_url:
            self.base_url = "https://api.minimax.io/v1"
        if not self.model:
            self.model = "MiniMax-M2.7-highspeed"
        self.api_key = self.api_key.strip()

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            headers = {"User-Agent": USER_AGENT}
            if self.extra_headers:
                headers.update(self.extra_headers)
            self._client = AsyncOpenAI(
                base_url=self.base_url,
                api_key=self.api_key,
                default_headers=headers,
            )
        return self._client

    def clone(self, **overrides: Any) -> LLMRoute:
        """Return a copy with overridden attributes."""
        kwargs = {
            "base_url": self.base_url,
            "api_key": self.api_key,
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "extra_headers": self.extra_headers,
            "stream": self.stream,
            "reasoning_split": self.reasoning_split,
        }
        kwargs.update(overrides)
        return LLMRoute(**cast(dict[str, Any], kwargs))

    async def generate(self, request: LLMRequest | None = None, **kwargs: Any) -> LLMResponse:
        """Send a completion request and return the structured response.

        Accepts either an ``LLMRequest`` object or keyword arguments
        that will be merged into the request.
        """
        if not self.api_key:
            return LLMResponse(
                content="Error: API key not set. Set MINIMAX_API_KEY or pass api_key=.",
                model=self.model,
                finish_reason="error",
            )

        req = self._build_request(request, kwargs)
        start = time.monotonic()

        messages = self._build_messages(req)
        tools = self._build_tools(req)
        body = self._build_body(req, messages, tools)

        try:
            response = await self.client.chat.completions.create(**body)
        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            return LLMResponse(
                content=f"Error: {exc}",
                model=self.model,
                duration_ms=round(duration_ms, 1),
                finish_reason="error",
            )

        duration_ms = (time.monotonic() - start) * 1000

        return self._parse_non_streaming(response, duration_ms)

    async def generate_stream(
        self, request: LLMRequest | None = None, **kwargs: Any
    ) -> AsyncIterator[ContentPartOut | ToolCallOut | LLMResponse]:
        """Stream response parts as they arrive.

        Yields ``ContentPartOut`` (text/think) and ``ToolCallOut`` chunks
        during streaming, then yields a final ``LLMResponse`` with the
        complete assembled result.
        """
        if not self.api_key:
            yield LLMResponse(
                content="Error: API key not set. Set MINIMAX_API_KEY or pass api_key=.",
                model=self.model,
                finish_reason="error",
            )
            return

        req = self._build_request(request, kwargs)
        start = time.monotonic()

        messages = self._build_messages(req)
        tools = self._build_tools(req)
        body = self._build_body(req, messages, tools)
        body["stream"] = True

        collected_parts: list[ContentPartOut] = []
        collected_tool_calls: dict[int, tuple[str, str, str]] = {}
        content_buffer = ""
        finish_reason: str | None = None
        final_model = self.model
        usage: TokenUsageOut | None = None

        try:
            stream = await self.client.chat.completions.create(**body)
            async for chunk in stream:
                delta = chunk.choices[0].delta if chunk.choices else None
                if delta is None:
                    continue

                if chunk.usage:
                    u = chunk.usage
                    usage = TokenUsageOut(
                        input=(u.prompt_tokens or 0),
                        output=(u.completion_tokens or 0),
                    )

                if chunk.model:
                    final_model = chunk.model
                if chunk.choices and chunk.choices[0].finish_reason:
                    finish_reason = chunk.choices[0].finish_reason

                if delta.refusal:
                    part = ContentPartOut(type="refusal", refusal=delta.refusal)
                    collected_parts.append(part)
                    yield part

                if delta.reasoning_content:
                    part = ContentPartOut(type="think", think=delta.reasoning_content)
                    collected_parts.append(part)
                    yield part

                if delta.content:
                    part = ContentPartOut(type="text", text=delta.content)
                    collected_parts.append(part)
                    content_buffer += delta.content
                    yield part

                if delta.tool_calls:
                    for tc in delta.tool_calls:
                        idx = tc.index
                        if idx not in collected_tool_calls:
                            cid_ = tc.id or ""
                            cname_ = tc.function.name or ""
                            cargs_ = tc.function.arguments or ""
                            collected_tool_calls[idx] = (cid_, cname_, cargs_)
                        else:
                            cid, cname, cargs = collected_tool_calls[idx]
                            cargs += tc.function.arguments or ""
                            collected_tool_calls[idx] = (cid, cname, cargs)

                if chunk.usage:
                    u = chunk.usage
                    usage = TokenUsageOut(
                        input=(u.prompt_tokens or 0),
                        output=(u.completion_tokens or 0),
                    )

        except Exception as exc:
            duration_ms = (time.monotonic() - start) * 1000
            yield LLMResponse(
                content=f"Error: {exc}",
                model=self.model,
                duration_ms=round(duration_ms, 1),
                finish_reason="error",
            )
            return

        duration_ms = (time.monotonic() - start) * 1000
        tool_calls_out = [
            ToolCallOut(id=cid, name=cname, arguments=cargs)
            for cid, cname, cargs in collected_tool_calls.values()
        ]

        tps = 0.0
        if usage and usage.output > 0 and duration_ms > 0:
            tps = usage.output / (duration_ms / 1000)

        yield LLMResponse(
            content=content_buffer,
            content_parts=collected_parts,
            tool_calls=tool_calls_out,
            token_usage=usage,
            model=final_model,
            duration_ms=round(duration_ms, 1),
            finish_reason=finish_reason,
            tps=round(tps, 1),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_request(self, request: LLMRequest | None, overrides: dict[str, Any]) -> LLMRequest:
        if request is None:
            request = LLMRequest(model=self.model)
        merged = request.model_dump(exclude_none=True)
        merged.update((k, v) for k, v in overrides.items() if v is not None)
        merged.setdefault("model", self.model)
        return LLMRequest(**merged)

    def _build_messages(self, req: LLMRequest) -> list[dict[str, Any]]:
        msgs: list[dict[str, Any]] = []

        if req.system_prompt:
            msgs.append({"role": "system", "content": req.system_prompt})

        for m in req.messages:
            entry: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                if isinstance(m.content, str):
                    entry["content"] = m.content
                else:
                    entry["content"] = [p.model_dump(exclude_none=True) for p in m.content]
            if m.name:
                entry["name"] = m.name
            if m.tool_call_id:
                entry["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                entry["tool_calls"] = [tc.model_dump(exclude_none=True) for tc in m.tool_calls]
            msgs.append(entry)

        return msgs

    def _build_tools(self, req: LLMRequest) -> list[dict[str, Any]] | None:
        if not req.tools:
            return None
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description,
                    "parameters": t.parameters,
                },
            }
            for t in req.tools
        ]

    def _build_body(
        self,
        req: LLMRequest,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": req.model or self.model,
            "messages": messages,
            "max_tokens": req.max_tokens or self.max_tokens,
            "stream": False,
        }
        if req.temperature is not None:
            body["temperature"] = req.temperature
        elif self.temperature is not None:
            body["temperature"] = self.temperature
        if req.top_p is not None:
            body["top_p"] = req.top_p
        elif self.top_p is not None:
            body["top_p"] = self.top_p
        if tools:
            body["tools"] = tools
        if req.thinking is True:
            body.setdefault("extra_body", {})["thinking"] = {"type": "enabled"}
        use_rs = req.reasoning_split
        if use_rs is None and self.reasoning_split is not None:
            use_rs = self.reasoning_split
        if use_rs is True:
            body.setdefault("extra_body", {})["reasoning_split"] = True
        if req.extra_body:
            existing = body.get("extra_body", {})
            existing.update(req.extra_body)
            body["extra_body"] = existing
        return body

    def _parse_non_streaming(self, response: Any, duration_ms: float) -> LLMResponse:
        choice = response.choices[0] if response.choices else None
        if not choice:
            return LLMResponse(
                content="",
                model=response.model or self.model,
                duration_ms=round(duration_ms, 1),
            )

        msg = choice.message
        raw_content = msg.content or ""
        finish_reason = choice.finish_reason

        parts: list[ContentPartOut] = []

        # 1. MiniMax reasoning_details (when reasoning_split=True)
        rdetails = getattr(msg, "reasoning_details", None)
        if rdetails and isinstance(rdetails, list):
            for rd in rdetails:
                if isinstance(rd, dict) and rd.get("type") == "thinking":
                    think_text = rd.get("text") or rd.get("thinking") or ""
                    if think_text:
                        parts.append(ContentPartOut(type="think", think=think_text))

        # 2. OpenAI-style reasoning_content
        rc = getattr(msg, "reasoning_content", None)
        if rc:
            parts.append(ContentPartOut(type="think", think=rc))

        # 3. MiniMax inline <think> tags (when reasoning_split is off)
        clean_content = raw_content
        if not rdetails and not rc:
            think_blocks = _extract_think_tags(raw_content)
            for tb in think_blocks:
                parts.append(ContentPartOut(type="think", think=tb))
                clean_content = clean_content.replace(f"<think>{tb}</think>", "", 1)

        # 4. Remaining text content
        if clean_content:
            parts.append(ContentPartOut(type="text", text=clean_content))

        tool_calls: list[ToolCallOut] = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(
                    ToolCallOut(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=tc.function.arguments,
                    )
                )

        usage = None
        if response.usage:
            usage = TokenUsageOut(
                input=response.usage.prompt_tokens or 0,
                output=response.usage.completion_tokens or 0,
            )

        tps = 0.0
        if usage and usage.output > 0 and duration_ms > 0:
            tps = usage.output / (duration_ms / 1000)

        return LLMResponse(
            content=clean_content,
            content_parts=parts,
            tool_calls=tool_calls,
            token_usage=usage,
            model=response.model or self.model,
            message_id=getattr(response, "id", None),
            duration_ms=round(duration_ms, 1),
            finish_reason=finish_reason,
            tps=round(tps, 1),
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


# ---------------------------------------------------------------------------
# MiniMax helpers
# ---------------------------------------------------------------------------


_THINK_TAG_RE = __import__("re").compile(r"<think>(.*?)</think>", __import__("re").DOTALL)


def _extract_think_tags(text: str) -> list[str]:
    """Extract all ``<think>...</think>`` blocks from *text*."""
    return _THINK_TAG_RE.findall(text)


# ---------------------------------------------------------------------------
# Factory helpers
# ---------------------------------------------------------------------------


def create_route(
    base_url: str | None = None,
    api_key: str | None = None,
    model: str | None = None,
    config: Any | None = None,
    **kwargs: Any,
) -> LLMRoute:
    """Create an ``LLMRoute`` from config, with config file and env var fallback.

    Resolution order (first wins):
    - Base URL: explicit arg > ``config.secondary_llm_base_url`` > env var
    - API key:  explicit arg > ``config.secondary_llm_api_key`` > env var
    - Model:    explicit arg > env var

    Supported env vars (in priority):
    - Base URL: ``MINIMAX_BASE_URL`` > ``LLM_BASE_URL`` > ``KIMI_BASE_URL`` > ``OPENAI_BASE_URL``
    - API key:  ``MINIMAX_API_KEY`` > ``LLM_API_KEY`` > ``KIMI_API_KEY`` > ``OPENAI_API_KEY``
    - Model:    ``MINIMAX_MODEL`` > ``LLM_MODEL`` > ``KIMI_MODEL_NAME``
    """
    import os

    # Resolve config-level values
    cfg_key: str | None = None
    cfg_base: str | None = None
    if config is not None:
        if hasattr(config, "secondary_llm_api_key") and config.secondary_llm_api_key is not None:
            cfg_key = config.secondary_llm_api_key.get_secret_value()
        if hasattr(config, "secondary_llm_base_url") and config.secondary_llm_base_url is not None:
            cfg_base = config.secondary_llm_base_url

    resolved_base = (
        base_url
        or cfg_base
        or os.getenv("MINIMAX_BASE_URL")
        or os.getenv("LLM_BASE_URL")
        or os.getenv("KIMI_BASE_URL")
        or os.getenv("OPENAI_BASE_URL")
        or "https://api.minimax.io/v1"
    )
    resolved_key = (
        api_key
        or cfg_key
        or os.getenv("MINIMAX_API_KEY")
        or os.getenv("LLM_API_KEY")
        or os.getenv("KIMI_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or ""
    )
    resolved_model = (
        model
        or os.getenv("MINIMAX_MODEL")
        or os.getenv("LLM_MODEL")
        or os.getenv("KIMI_MODEL_NAME")
        or "MiniMax-M2.7-highspeed"
    )

    return LLMRoute(
        base_url=resolved_base,
        api_key=resolved_key,
        model=resolved_model,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# CLI — independent test entry point
# ---------------------------------------------------------------------------


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="LLMRoute — standalone LLM API caller (default: MiniMax M2.7 HighSpeed)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  uv run python -m kimi_cli.api_route --prompt 'Hello!'\n"
            "  uv run python -m kimi_cli.api_route --system 'You are a poet'\n"
            "  uv run python -m kimi_cli.api_route --prompt 'Write a haiku'\n"
            "  uv run python -m kimi_cli.api_route --prompt 'Hi' --model gpt-4o\n"
            "  uv run python -m kimi_cli.api_route --base-url https://api.openai.com/v1\n"
            "  uv run python -m kimi_cli.api_route --prompt 'What is 2+2?' --stream\n"
            "  uv run python -m kimi_cli.api_route --prompt 'Think step by step'\n"
            "  uv run python -m kimi_cli.api_route --thinking --reasoning-split\n"
            '  uv run python -m kimi_cli.api_route --json \'{"system_prompt":"..."}\'\n'
        ),
    )
    parser.add_argument("--prompt", "-p", help="Single user message")
    parser.add_argument("--system", "-s", help="System prompt")
    parser.add_argument("--model", "-m", help="Model name (env: MINIMAX_MODEL, LLM_MODEL)")
    parser.add_argument("--base-url", help="API base URL (env: MINIMAX_BASE_URL, LLM_BASE_URL)")
    parser.add_argument("--api-key", help="API key (env: MINIMAX_API_KEY, LLM_API_KEY)")
    parser.add_argument("--temperature", type=float, help="Sampling temperature")
    parser.add_argument("--max-tokens", type=int, default=32000, help="Max tokens")
    parser.add_argument("--stream", action="store_true", help="Enable streaming output")
    parser.add_argument("--thinking", action="store_true", help="Enable thinking/reasoning")
    parser.add_argument(
        "--reasoning-split",
        action="store_true",
        help="MiniMax: separate thinking into reasoning_details",
    )
    parser.add_argument("--json", "-j", help="JSON file or string with full LLMRequest")
    parser.add_argument("--tool", "-t", action="append", help="Tool JSON")

    args = parser.parse_args()

    if args.json:
        raw = args.json
        p = pathlib.Path(raw)
        if p.exists():
            raw = p.read_text(encoding="utf-8")
        try:
            request_data = json.loads(raw)
        except json.JSONDecodeError as e:
            print(f"Invalid JSON: {e}")
            raise SystemExit(1) from e
    else:
        request_data = {}
        if args.system:
            request_data["system_prompt"] = args.system
        if args.prompt:
            request_data["messages"] = [{"role": "user", "content": args.prompt}]
        if args.temperature is not None:
            request_data["temperature"] = args.temperature
        if args.max_tokens is not None:
            request_data["max_tokens"] = args.max_tokens
        if args.thinking:
            request_data["thinking"] = True
        if args.reasoning_split:
            request_data["reasoning_split"] = True
        if args.tool:
            tools = []
            for t_str in args.tool:
                t_path = pathlib.Path(t_str)
                if t_path.exists():
                    t_str = t_path.read_text(encoding="utf-8")
                tools.append(json.loads(t_str))
            if tools:
                request_data["tools"] = tools

    request_data.setdefault("model", args.model) if args.model else None
    request_data.setdefault("base_url", args.base_url) if args.base_url else None
    request_data.setdefault("api_key", args.api_key) if args.api_key else None

    # Load config so secondary_llm_* fields feed into create_route
    try:
        from kimi_cli.config import load_config

        _cfg = load_config()
    except Exception:
        _cfg = None

    route = create_route(
        base_url=request_data.pop("base_url", None),
        api_key=request_data.pop("api_key", None),
        model=request_data.pop("model", None),
        config=_cfg,
    )

    req = LLMRequest(**request_data)

    async def run() -> None:
        if args.stream:
            async for part in route.generate_stream(req):
                if isinstance(part, LLMResponse):
                    usage = part.token_usage
                    ustr = f" | {usage.input} in / {usage.output} out" if usage else ""
                    tps_str = f" | {part.tps} tps" if part.tps > 0 else ""
                    print(f"\n\n--- Done ({part.duration_ms:.0f}ms{ustr}{tps_str}) ---")
                    if part.finish_reason:
                        print(f"Finish reason: {part.finish_reason}")
                elif isinstance(part, ContentPartOut):
                    if part.type == "think":
                        print(f"\n[thinking] {part.think}", end="", flush=True)
                    elif part.type == "text":
                        print(part.text, end="", flush=True)
            print()
        else:
            resp = await route.generate(req)
            usage = resp.token_usage
            ustr = f" | {usage.input} in / {usage.output} out" if usage else ""
            tps_str = f" | {resp.tps} tps" if resp.tps > 0 else ""
            print(f"--- Response ({resp.duration_ms:.0f}ms{ustr}{tps_str}) ---")

            if resp.content_parts:
                for p in resp.content_parts:
                    if p.type == "think":
                        print(f"\n[thinking]\n{p.think}\n[/thinking]")
                    elif p.type == "text":
                        print(p.text)
            else:
                print(resp.content or "(empty)")

            if resp.tool_calls:
                print("\n--- Tool Calls ---")
                for tc in resp.tool_calls:
                    try:
                        pretty_args = json.dumps(json.loads(tc.arguments), indent=2)
                    except Exception:
                        pretty_args = tc.arguments
                    print(f"  {tc.name}(id={tc.id[:16]}):")
                    print(f"    {pretty_args}")

            if resp.finish_reason:
                print(f"\nFinish reason: {resp.finish_reason}")

        await route.close()

    asyncio.run(run())


if __name__ == "__main__":
    _main()

__all__ = [
    "LLMRoute",
    "LLMRequest",
    "LLMResponse",
    "ContentPartDef",
    "ContentPartOut",
    "ToolCallDef",
    "ToolCallOut",
    "ToolDefinition",
    "TokenUsageOut",
    "RouteMessage",
    "create_route",
    "_extract_think_tags",
]
