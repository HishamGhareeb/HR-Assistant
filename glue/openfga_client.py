"""OpenFGA authorization filtering: given a user and a list of candidate
documents, keep only the ones the user is an authorized viewer of. This is
the actual access-control enforcement point -- nothing downstream of this
should be trusted to re-derive permissions."""
from __future__ import annotations

import asyncio

from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest

from .onyx_client import Document


class OpenFgaFilter:
    def __init__(self, api_url: str, store_id: str, model_id: str = "") -> None:
        self._config = ClientConfiguration(
            api_url=api_url,
            store_id=store_id,
            authorization_model_id=model_id or None,
        )

    async def filter_authorized(self, user_id: str, documents: list[Document]) -> list[Document]:
        if not documents:
            return []
        async with OpenFgaClient(self._config) as client:
            results = await asyncio.gather(
                *[
                    client.check(
                        ClientCheckRequest(
                            user=f"user:{user_id}",
                            relation="viewer",
                            object=f"{doc.object_type}:{doc.object_id}",
                        )
                    )
                    for doc in documents
                ]
            )
        return [doc for doc, result in zip(documents, results) if result.allowed]
