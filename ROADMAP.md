# Portfolio Roadmap

A working plan for polishing this PDF RAG app into a portfolio piece for AI Engineer / Forward Deployed Engineer roles.

Reviewers look past "it works" for three things:

1. You can **measure** quality (evals, metrics, experiments).
2. You make **production tradeoffs** deliberately, and can explain them.
3. You can **demo and communicate** the system clearly.

**Suggested order:** bugs + citations → evals → hygiene (compose + CI) → deploy + demo.
**If short on time:** evals + live demo carry the most weight.

---

## Phase 1: Fix real bugs

- [ ] **Batch embeddings.** `embed_texts` sends every chunk in one OpenAI request (`data_loader.py`), so large PDFs fail. Batch them (~100 inputs per request) and add retry/backoff.
- [ ] **Stale chunks on re-ingest.** Re-ingesting a PDF that now has fewer chunks leaves the old extra chunks in Qdrant. Add delete-by-`source` to `QdrantStorage` and call it before upsert.
- [ ] **Silent rate limit.** Re-uploading the same filename within 4 hours is dropped by Inngest, but the UI still says "success". Show the user what actually happened.
- [ ] **Unsafe uploads.** `save_uploaded_pdf` writes `uploads/<file.name>` without sanitizing it. That allows collisions and path traversal. Use `Path(name).name`, restrict to safe characters, and avoid overwrites.
- [ ] **Typing.** `RAGChunkAndSrc.source_id: str = None` should be `str | None = None`.
- [ ] **Client reuse.** `QdrantStorage()` creates a new client on every call. Cache one instance.
- [ ] **Hard-coded URLs.** Read the Qdrant URL and other endpoints from env instead of `localhost`.
- [ ] **Unused code.** Use or remove `RAGQueryResult`.

---

## Phase 2: Retrieval and answer quality

- [ ] **Page-level citations.** `PDFReader` returns one document per page, but `load_and_chunk_pdf` keeps only `.text`, so the page metadata is lost.
  - Store `page` in the Qdrant payload.
  - Return per-chunk citations `{source, page, score, text}`; today `sources` is only a set of filenames.
  - Prompt the model to cite `[source p.N]`.
  - Show citations in the UI with page number, score, and an expandable snippet.
- [ ] **Grounded refusal.** If the top similarity score falls below a threshold, answer "I don't know" instead of letting the model guess.
- [ ] **Hybrid search.** Add Qdrant sparse/BM25 vectors alongside dense vectors.
- [ ] **Reranking.** Add a cross-encoder or Cohere rerank step after retrieval.
- [ ] **Per-document filtering.** Let users ask questions about a single PDF.
- [ ] **(Stretch) Conversation memory and query rewriting** for follow-up questions.

> Prove each retrieval change with numbers from the Phase 3 evals.

---

## Phase 3: Evaluation harness (biggest differentiator)

- [ ] **Golden set:** ~30 Q/A pairs from 2–3 freely licensed public PDFs, with the expected source and page (`evals/data/*.jsonl`).
- [ ] **Separate eval collection** (e.g. `docs_eval`) so your real data stays untouched.
- [ ] **Retrieval metrics:** recall@k and MRR.
- [ ] **Answer metrics:** faithfulness and correctness, scored by an LLM judge (use Claude; the `anthropic` dependency and `CLAUDE_API_KEY` are already in place).
- [ ] **CLI flags for experiments:** `--chunk-size`, `--chunk-overlap`, `--top-k`, `--embed-model`.
- [ ] **Run a sweep**, for example:
  - chunk size 500 vs 1000
  - top-k 3 / 5 / 10
  - `text-embedding-3-small` vs `-large`
  - with and without reranking
- [ ] **Add an "Evaluation" section** to the README with the results table and a short interpretation.

---

## Phase 4: Architecture decision (FDE signal)

Inngest is a good fit for **ingestion** (slow, can fail partway, needs retries). The **query** path, though, polls the Inngest dev-only REST API every 0.5s (`streamlit_app.py`), which won't work in production.

- [ ] Add a FastAPI `POST /query` endpoint that **streams** the answer.
- [ ] Keep Inngest for ingestion only.
- [ ] Point the Streamlit UI at the streaming endpoint.
- [ ] Write a **"Design decisions"** section in the README covering:
  - why Inngest handles ingestion but not queries
  - why deterministic `uuid5` IDs
  - why the throttle and rate-limit values
  - chunk size and embedding model choices, backed by eval results

---

## Phase 5: Engineering hygiene

- [ ] **Config:** use `pydantic-settings` for a single typed config, instead of constants scattered across files.
- [ ] **LLM provider abstraction:** support both OpenAI and Claude, and compare them in the evals.
- [ ] **Tests:** `pytest` with `QdrantClient(":memory:")` and a mocked OpenAI client. Cover chunking, upsert/search, and both pipelines.
- [ ] **Lint and types:** `ruff` + `mypy`.
- [ ] **CI:** a GitHub Actions workflow running lint, type checks and tests. Add a badge to the README.
- [ ] **One-command startup:** a `docker-compose.yml` that runs Qdrant, the API, the Inngest dev server and Streamlit with `docker compose up`.
- [ ] **(Optional) `Makefile`** with `make dev`, `make test`, `make eval`.

---

## Phase 6: Observability

- [ ] Track tokens, cost, and latency per query and per step.
- [ ] Add tracing with Langfuse or OpenTelemetry.
- [ ] Include a screenshot of the Inngest run timeline in the README.

---

## Phase 7: Demo and presentation

- [ ] **Live demo:** Qdrant Cloud (free tier) + Inngest Cloud + Streamlit Community Cloud or Fly.io.
- [ ] **30-second GIF or Loom** at the top of the README.
- [ ] **Screenshots:** UI with citations, Inngest dashboard, eval results.
- [ ] **README polish:** problem statement, demo link, architecture diagram (already done), design decisions, eval results, "What I'd do next".
- [ ] **(Optional) A short write-up or blog post** walking through the eval results and tradeoffs.

---

## Progress log

| Date | Change | Notes |
| --- | --- | --- |
| 2026-10-20 | README with architecture diagrams | Initial commit `a1f9ef3` |
| | | |
