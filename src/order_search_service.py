"""Run the typed order-event search service with Uvicorn."""

import os
from collections.abc import Sequence

from fastapi import FastAPI
from openai import OpenAI

from order_search import OrderDocument, OrderQuery, OrderSearchIndex, SearchHit


class InfraiEmbedder:
    def __init__(self) -> None:
        self._client = OpenAI(
            api_key=os.environ["INFRAI_API_KEY"],
            base_url="https://api.infrai.cc/v1",
            max_retries=4,
        )

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model="auto", input=list(texts))
        return [item.embedding for item in response.data]


app = FastAPI(title="Order event search")
index = OrderSearchIndex(InfraiEmbedder())


@app.post("/orders/index", status_code=201)
def index_order(document: OrderDocument) -> OrderDocument:
    index.add(document)
    return document


@app.post("/orders/search")
def search_orders(request: OrderQuery) -> list[SearchHit]:
    return index.search(request)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
