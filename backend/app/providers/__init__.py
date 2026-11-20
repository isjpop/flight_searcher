from __future__ import annotations

from .. import config
from ..airlines import AIRLINES
from .base import AwardFare, Provider, Route, cheapest_per_day
from .live import LIVE_PROVIDERS
from .mock import MockProvider

__all__ = ["AwardFare", "MockProvider", "Provider", "Route", "build_providers", "cheapest_per_day", "provider_mode"]


def provider_mode(code: str) -> str:
    return "live" if code in config.LIVE_AIRLINES else "mock"


def build_providers(codes: list[str] | None = None) -> list[Provider]:
    selected = codes or list(AIRLINES)
    return [
        LIVE_PROVIDERS[code]() if provider_mode(code) == "live" else MockProvider(code)
        for code in selected
    ]
