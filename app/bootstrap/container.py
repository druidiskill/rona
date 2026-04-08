from __future__ import annotations

from dataclasses import dataclass

from app.bootstrap.settings import AppSettings, load_settings


@dataclass(frozen=True)
class AppContainer:
    settings: AppSettings


def build_container() -> AppContainer:
    return AppContainer(settings=load_settings())
