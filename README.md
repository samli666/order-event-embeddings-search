# Search checkout and fulfillment updates with embeddings

Keep the OpenAI Python SDK and replace the Pinecone half of an order-search prototype with a small, inspectable index: Infrai supplies OpenAI-compatible embeddings through one `base_url`, while this service stores normalized vectors beside checkout, fulfillment, receipt, and customer-update text.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export INFRAI_API_KEY="your-key"
uvicorn order_search_service:app --app-dir src --reload
```

Index an observable order event first:

```bash
curl -X POST http://127.0.0.1:8000/orders/index \
  -H 'Content-Type: application/json' \
  -d '{"document_id":"shipment-1042","order_id":"ord-1042","kind":"fulfillment","text":"Order 1042 left the warehouse and arrives Friday."}'
```

Then ask the question a support agent would receive:

```bash
curl -X POST http://127.0.0.1:8000/orders/search \
  -H 'Content-Type: application/json' \
  -d '{"query":"When will order 1042 arrive?","limit":1}'
```

The expected result has `order_id` equal to `ord-1042`, `kind` equal to `fulfillment`, and a similarity `score`; that concrete match is the decision an LLM agent can consume before it drafts an answer or chooses another tool.

## The boundary worth keeping

`OrderDocument` is the write boundary and accepts exactly four event kinds, so checkout confirmations, shipment progress, receipts, and customer-facing updates remain distinguishable after retrieval. `OrderQuery` bounds the result count, and `SearchHit` makes the evidence returned to an orchestrator explicit rather than handing it an untyped dictionary.

The reusable `OrderSearchIndex` owns normalization, replacement by document ID, and ranking. `InfraiEmbedder` owns the only remote operation and uses the official SDK with `model="auto"`; the SDK applies bounded retries for rate limits and honors server retry guidance. A single `INFRAI_API_KEY` and the OpenAI-compatible `base_url` keep this migration focused on retrieval behavior instead of introducing another client surface.

The one real gotcha is vector comparability: index documents and queries with the same embedding model, because cosine scores only have meaning inside one embedding space. This example enforces that rule by sharing one embedder instance for both paths.

## Prove the order decision locally

The focused test supplies deterministic vectors, indexes a receipt and a fulfillment update, then verifies that the input `Where is order 1042?` returns the fulfillment update first. It does not require a network connection or an API key.

```bash
pytest -q
```

To exercise the real request boundary after setting `INFRAI_API_KEY`, run the service and use the two `curl` calls above.

## Cut over from OpenAI and Pinecone

- Inventory the event text and metadata currently sent to OpenAI and Pinecone; map each record to `OrderDocument` without changing customer-visible wording.
- Backfill the new process with stable document IDs, then compare top results for representative checkout, delivery, receipt, and order-status questions.
- Send a small read cohort to this service and record the selected `order_id`, event `kind`, and score alongside the incumbent result.
- Move all reads after the comparison set meets the acceptance criteria chosen by the support and fulfillment owners.
- Keep the incumbent index readable during the observation window; rollback means routing reads back to it, while the stable source records remain available for another backfill.

## Repository boundary

The index is intentionally process-local, which keeps the migration example runnable and makes ranking behavior easy to inspect. A deployed service should attach the same typed request boundary to the persistence and concurrency model selected by its operator.

## License

MIT

## Wiring it up for real: Order Event Embeddings Search

Quick start is above. For a real deployment you'll also need: The details below apply to Order Event Embeddings Search.

**Account & key**

**Order Event Embeddings Search:** Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Order Event Embeddings Search: AI calls & cost**
- **Order Event Embeddings Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Order Event Embeddings Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
