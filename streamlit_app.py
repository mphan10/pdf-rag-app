import hashlib
import re
from pathlib import Path
import time

import streamlit as st
import inngest
from dotenv import load_dotenv
import os
import requests

load_dotenv()

st.set_page_config(page_title="RAG Ingest PDF", page_icon="📄", layout="centered")

UPLOADS_DIR = Path("uploads")


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="pdf_rag_app", is_production=False)


def _inngest_api_base() -> str:
    # Local dev server default; configurable via env
    return os.getenv("INNGEST_API_BASE", "http://127.0.0.1:8288/v1")


def fetch_runs(event_id: str) -> list[dict]:
    url = f"{_inngest_api_base()}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)


def display_name(file) -> str:
    # Browsers send a bare filename, but a crafted request can include directory parts
    return Path(file.name).name or "upload.pdf"


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]", "_", name).lstrip(".")
    return cleaned or "upload.pdf"


def save_uploaded_pdf(file) -> Path:
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    file_bytes = file.getbuffer()
    # Prefix with a content hash so different files with the same name never overwrite each other
    digest = hashlib.sha256(file_bytes).hexdigest()[:12]
    file_path = UPLOADS_DIR / f"{digest}_{safe_filename(display_name(file))}"
    file_path.write_bytes(file_bytes)
    return file_path


# send_sync rather than asyncio.run(client.send(...)): the cached client keeps an async
# HTTP connection bound to the first event loop, so a second asyncio.run fails
def send_rag_ingest_event(pdf_path: Path, source_id: str) -> str:
    client = get_inngest_client()
    result = client.send_sync(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": source_id,
            },
        )
    )
    return result[0]


def ingest_pdf(file) -> tuple[str, str]:
    """Save the upload, trigger ingestion and wait for it. Returns (level, message)."""
    source_id = display_name(file)
    path = save_uploaded_pdf(file)
    event_id = send_rag_ingest_event(path, source_id)

    try:
        output = wait_for_run_output(event_id, timeout_s=300.0)
    except (RuntimeError, TimeoutError) as e:
        return "error", f"Ingestion failed for {source_id}: {e}"
    if output.get("skipped"):
        return "info", f"Skipped {source_id}: this exact file is already ingested."
    return "success", f"Ingested {source_id} ({output.get('ingested', 0)} chunks)."


st.title("Upload a PDF to Ingest")
uploaded = st.file_uploader("Choose a PDF", type=["pdf"], accept_multiple_files=False)

if uploaded is not None:
    # Streamlit reruns the whole script on every interaction (e.g. asking a question),
    # so remember each upload's result instead of re-triggering ingestion.
    results = st.session_state.setdefault("ingest_results", {})
    if uploaded.file_id not in results:
        with st.spinner("Uploading and ingesting..."):
            results[uploaded.file_id] = ingest_pdf(uploaded)
    level, message = results[uploaded.file_id]
    getattr(st, level)(message)
    st.caption("You can upload another PDF if you like.")

st.divider()
st.title("Ask a question about your PDFs")


def send_rag_query_event(question: str, top_k: int) -> str:
    client = get_inngest_client()
    result = client.send_sync(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
            },
        )
    )

    return result[0]


with st.form("rag_query_form"):
    question = st.text_input("Your question")
    top_k = st.number_input("How many chunks to retrieve", min_value=1, max_value=20, value=5, step=1)
    submitted = st.form_submit_button("Ask")

    if submitted and question.strip():
        with st.spinner("Sending event and generating answer..."):
            # Fire-and-forget event to Inngest for observability/workflow
            event_id = send_rag_query_event(question.strip(), int(top_k))
            # Poll the local Inngest API for the run's output
            output = wait_for_run_output(event_id)
            answer = output.get("answer", "")
            sources = output.get("sources", [])

        st.subheader("Answer")
        st.write(answer or "(No answer)")
        if sources:
            st.caption("Sources")
            for s in sources:
                st.write(f"- {s}")
