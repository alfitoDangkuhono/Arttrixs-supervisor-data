import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from rag.retriever import build_context, search_similar

app = FastAPI(
    title="RAG Supervisor API",
    description="API untuk query konteks RAG dari database pgvector",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "rag-supervisor"}


@app.get("/api/search")
async def search(
    query: str = Query(..., min_length=1, description="Kata kunci pencarian"),
    top_k: int = Query(5, ge=1, le=10, description="Jumlah hasil teratas"),
    context_format: str = Query("text", description="Format konteks: 'text' atau 'json'"),
):
    """Mengembalikan hasil pencarian RAG dalam format JSON."""
    results = search_similar(query, top_k=top_k)
    context = build_context(query, top_k=top_k, output_format=context_format)

    return {
        "query": query,
        "top_k": top_k,
        "count": len(results),
        "context": context,
        "results": results,
    }


@app.get("/")
async def root():
    return {
        "message": "RAG Supervisor API siap.",
        "docs": "/docs",
        "health": "/health",
    }
