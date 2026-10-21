from openai import OpenAI
from llama_index.readers.file import PDFReader
from llama_index.core.node_parser import SentenceSplitter
from dotenv import load_dotenv

load_dotenv()

# The SDK retries rate-limit (429), timeout and 5xx errors with exponential backoff
client = OpenAI(max_retries=5)
EMBED_MODEL = "text-embedding-3-large"
EMBED_DIM = 3072
# OpenAI caps a single embeddings request at 2048 inputs and 300k tokens;
# 100 chunks of ~1000 tokens stays well under both
EMBED_BATCH_SIZE = 100

splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=200)

def load_and_chunk_pdf(path: str):
    docs = PDFReader().load_data(file=path)
    texts = [d.text for d in docs if getattr(d, "text", None)]
    chunks = []
    for t in texts:
        chunks.extend(splitter.split_text(t))
    return chunks

def embed_texts(texts: list[str]) -> list[list[float]]:
    embeddings = []
    for start in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[start:start + EMBED_BATCH_SIZE]
        response = client.embeddings.create(
            model=EMBED_MODEL,
            input=batch
        )
        # Sort by index so vectors always line up with their input chunks
        embeddings.extend(item.embedding for item in sorted(response.data, key=lambda d: d.index))
    return embeddings