"""Onyx retrieval client.

The search endpoint and response shape are NOT yet confirmed against a
running Onyx instance -- Stage 0/1 brings Onyx up and indexes Frappe HR
data, at which point this gets wired to the real API. Left raising
NotImplementedError rather than a guessed-at endpoint so it fails loudly
instead of silently returning nothing.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Document:
    object_type: str
    object_id: str
    chunk: str


class OnyxClient:
    def __init__(self, api_url: str, api_key: str = "") -> None:
        self._api_url = api_url.rstrip("/")
        self._headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}

    async def search(self, question: str) -> list[Document]:
        raise NotImplementedError(
            "wire this up against a running Onyx instance (Stage 1) -- "
            "confirm the search endpoint and response shape first"
        )
