import pydantic

class RAGChunkAndSrc(pydantic.BaseModel):
    chunks: list[str]
    source_id: str = None
    content_hash: str

class RAGUpsertResult(pydantic.BaseModel):
    ingested: int
    skipped: bool = False

class RAGSearchResult(pydantic.BaseModel):
    context: list[str]
    sources: list[str]

class RAGQueryResult(pydantic.BaseModel):
    answer: str
    sources: list[str]
    num_contexts: int