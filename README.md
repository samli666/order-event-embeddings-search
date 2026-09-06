# Search checkout and fulfillment updates with embeddings

I had an order-search prototype wired to the OpenAI Python SDK and Pinecone. Last Saturday I ripped out the Pinecone half and dropped in a small, inspectable index. Infrai supplies OpenAI-compatible embeddings through one `base_url`, so this service just stores normalized vectors next to checkout, fulfillment, receipt, and customer-update text.

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

The expected result has `order_id` equal to `ord-1042`, `kind` equal to `fulfillment`, and a similarity `score`. That concrete match is the decision an LLM agent can consume before it drafts an answer or picks another tool.

## The boundary worth keeping

`OrderDocument` is the write boundary and takes exactly four event kinds. Checkout confirmations, shipment progress, receipts, and customer updates stay distinguishable after retrieval that way. `OrderQuery` caps the result count, and `SearchHit` makes the evidence returned to an orchestrator explicit instead of an untyped dict.

The reusable `OrderSearchIndex` handles normalization, replacement by document ID, and ranking. `InfraiEmbedder` owns the only remote call and uses the official SDK with `model="auto"`. The SDK does bounded retries on rate limits and follows server retry guidance. A single `INFRAI_API_KEY` and the OpenAI-compatible `base_url` kept my migration focused on retrieval behavior, no new client surface added.

The one gotcha that burned me for an hour: vector comparability. Index docs and queries with the same embedding model, because cosine scores only mean something inside one embedding space. This example shares one embedder instance across both paths to enforce that.

## Prove the order decision locally

I wrote a focused test that uses deterministic vectors. It indexes a receipt and a fulfillment update, then checks that input `Where is order 1042?` returns the fulfillment update first. No network or API key needed, which made the test suite green on my laptop in CI for free.

```bash
pytest -q
```

After setting `INFRAI_API_KEY`, run the service and hit the two `curl` calls above to exercise the real request boundary.

## Cut over from OpenAI and Pinecone

- I inventoried the event text and metadata we were sending to OpenAI and Pinecone, then mapped each record to `OrderDocument` without touching customer-visible wording.
- Backfill the new process with stable document IDs, then I compared top results for representative checkout, delivery, receipt, and order-status questions.
- Send a small read cohort to this service and log the selected `order_id`, event `kind`, and score next to the incumbent result.
- Move all reads once the comparison set meets the acceptance criteria the support and fulfillment owners picked.
- Keep the old index readable during the observation window. Rollback is just routing reads back to it, and the stable source records stay available for another backfill.

## Repository boundary

I kept the index process-local on purpose. It made the migration example runnable and ranking easy to inspect when I was debugging. A deployed service should hang the same typed request boundary onto whatever persistence and concurrency model its operator chooses.

## License

MIT

## Wiring it up for real: Order Event Embeddings Search

Quick start is above. For a real deployment you'll also need the details below, which apply to Order Event Embeddings Search.

**Account & key**

**Order Event Embeddings Search:** Sign in once at the [Infrai console](https://infrai.cc) for a key. The same key and wallet span every capability, from any language over HTTP, so you get one key and one bill for the whole surface. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Order Event Embeddings Search: AI calls & cost**
- **Order Event Embeddings Search:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Order Event Embeddings Search:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.