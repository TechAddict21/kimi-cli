from __future__ import annotations

import socket
from pathlib import Path
from typing import Any, cast

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from analytics_web.api import (
    aggregate_router,
    cost_router,
    latency_router,
    messages_router,
    sessions_router,
    timeline_router,
    tokens_router,
    tools_router,
)
from analytics_web.config import DEFAULT_PORT

STATIC_DIR = Path(__file__).parent.parent.parent / "frontend" / "dist"
GZIP_MINIMUM_SIZE = 1024
GZIP_COMPRESSION_LEVEL = 6


def get_address_family(host: str) -> socket.AddressFamily:
    return socket.AF_INET6 if ":" in host else socket.AF_INET


def find_available_port(host: str, start_port: int, max_attempts: int = 10) -> int:
    if max_attempts <= 0:
        raise ValueError("max_attempts must be positive")
    if start_port < 1 or start_port > 65535:
        raise ValueError("start_port must be between 1 and 65535")
    family = get_address_family(host)
    for offset in range(max_attempts):
        port = start_port + offset
        with socket.socket(family, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise RuntimeError(
        f"Cannot find available port in range {start_port}-{start_port + max_attempts - 1}"
    )


def create_app() -> FastAPI:
    application = FastAPI(
        title="Kimi Analytics Dashboard",
        docs_url=None,
        separate_input_output_schemas=False,
    )

    application.add_middleware(
        cast(Any, GZipMiddleware),
        minimum_size=GZIP_MINIMUM_SIZE,
        compresslevel=GZIP_COMPRESSION_LEVEL,
    )

    application.add_middleware(
        cast(Any, CORSMiddleware),
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(sessions_router)
    application.include_router(timeline_router)
    application.include_router(tokens_router)
    application.include_router(tools_router)
    application.include_router(latency_router)
    application.include_router(cost_router)
    application.include_router(messages_router)
    application.include_router(aggregate_router)

    @application.get("/healthz")
    async def health_probe() -> dict[str, Any]:
        return {"status": "ok"}

    if STATIC_DIR.exists():
        application.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

    return application


def run_server(
    host: str = "127.0.0.1",
    port: int = DEFAULT_PORT,
    reload: bool = False,
    open_browser: bool = True,
) -> None:
    import threading
    import webbrowser

    import uvicorn

    actual_port = find_available_port(host, port)
    if actual_port != port:
        print(f"\nPort {port} is in use, using port {actual_port} instead")

    browser_url = f"http://localhost:{actual_port}"

    banner = f"""
+================================================+
|          KIMI ANALYTICS DASHBOARD              |
|                                                |
|  -> Local  {browser_url}
|                                                |
|  Session analytics and performance metrics     |
+================================================+
"""
    print(banner)

    if open_browser:

        def open_browser_after_delay() -> None:
            import time

            time.sleep(1.5)
            webbrowser.open(browser_url)

        thread = threading.Thread(target=open_browser_after_delay, daemon=True)
        thread.start()

    uvicorn.run(
        "analytics_web.app:create_app",
        factory=True,
        host=host,
        port=actual_port,
        reload=reload,
        log_level="info",
        timeout_graceful_shutdown=3,
    )


if __name__ == "__main__":
    run_server()
