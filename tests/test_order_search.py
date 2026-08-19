from collections.abc import Sequence

from order_search import OrderDocument, OrderQuery, OrderSearchIndex


class IntentEmbedder:
    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            lowered = text.lower()
            vectors.append([1.0, 0.0] if "where" in lowered or "warehouse" in lowered else [0.0, 1.0])
        return vectors


def test_shipping_question_selects_fulfillment_update() -> None:
    index = OrderSearchIndex(IntentEmbedder())
    index.add(
        OrderDocument(
            document_id="receipt-1042",
            order_id="ord-1042",
            kind="receipt",
            text="Receipt for order 1042, paid by card.",
        )
    )
    index.add(
        OrderDocument(
            document_id="shipment-1042",
            order_id="ord-1042",
            kind="fulfillment",
            text="Order 1042 left the warehouse and arrives Friday.",
        )
    )

    results = index.search(OrderQuery(query="Where is order 1042?", limit=1))

    assert results[0].document_id == "shipment-1042"
    assert results[0].kind == "fulfillment"
    assert results[0].score == 1.0
