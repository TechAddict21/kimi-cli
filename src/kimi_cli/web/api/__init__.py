"""API routes."""

from kimi_cli.web.api import analytics, config, open_in, sessions

analytics_router = analytics.router
config_router = config.router
sessions_router = sessions.router
work_dirs_router = sessions.work_dirs_router
open_in_router = open_in.router

__all__ = [
    "analytics_router",
    "config_router",
    "open_in_router",
    "sessions_router",
    "work_dirs_router",
]
