from __future__ import annotations

from contextlib import asynccontextmanager

from app.bootstrap.container import AppContainer, build_container


@asynccontextmanager
async def app_lifespan():
    container: AppContainer = build_container()
    try:
        yield container
    finally:
        return
