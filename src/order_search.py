"""Embedding-backed retrieval for customer order events."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Sequence

from pydantic import BaseModel, Field


class OrderDocument(BaseModel):
    document_id: str = Field(min_length=1)
    order_id: str = Field(min_length=1)
    kind: str = Field(pattern="^(checkout|fulfillment|receipt|customer_update)$")
    text: str = Field(min_length=1)


class OrderQuery(BaseModel):
    query: str = Field(min_length=1)
    limit: int = Field(default=3, ge=1, le=20)


class SearchHit(BaseModel):
    document_id: str
    order_id: str
    kind: str
    text: str
    score: float


@dataclass(frozen=True)
class _IndexedOrder:
    document: OrderDocument
    embedding: tuple[float, ...]


def _normalized(values: Sequence[float]) -> tuple[float, ...]:
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        raise ValueError("Embedding vectors must have non-zero magnitude")
    return tuple(value / magnitude for value in values)


class OrderSearchIndex:
    def __init__(self, embedder: Any) -> None:
        self._embedder = embedder
        self._orders: dict[str, _IndexedOrder] = {}

    def add(self, document: OrderDocument) -> None:
        vector = self._embedder.embed([document.text])[0]
        self._orders[document.document_id] = _IndexedOrder(
            document=document,
            embedding=_normalized(vector),
        )

    def search(self, request: OrderQuery) -> list[SearchHit]:
        query_vector = _normalized(self._embedder.embed([request.query])[0])
        ranked = sorted(
            self._orders.values(),
            key=lambda item: sum(
                left * right for left, right in zip(query_vector, item.embedding, strict=True)
            ),
            reverse=True,
        )
        return [
            SearchHit(
                **item.document.model_dump(),
                score=sum(
                    left * right
                    for left, right in zip(query_vector, item.embedding, strict=True)
                ),
            )
            for item in ranked[: request.limit]
        ]
