"""
Retriever: digunakan oleh LLM lokal untuk mengambil konteks relevan dari Postgres pgvector bedasarkan query similiraty search.
"""

import logging
import re

import psycopg2

from database.connection import get_connection
from processing.embedder import embed_texts

logger = logging.getLogger("rag.retriever")


def _normalize_text(text: str) -> str:
    """Bersihkan whitespace agar output lebih rapi."""
    text = re.sub(r"\s+", " ", text or "")
    return text.strip()


def _truncate_text(text: str, max_chars: int = 500) -> str:
    """Potong teks dengan aman di batas kalimat agar tetap ringkas."""
    clean = _normalize_text(text)
    if len(clean) <= max_chars:
        return clean

    cut = clean[:max_chars]
    for marker in (". ", "\n", " - ", " | "):
        pos = cut.rfind(marker)
        if pos > int(max_chars * 0.7):
            cut = cut[: pos + len(marker)]
            break
    return cut.strip() + "..."


def search_similar(query: str, top_k:int = 5)->list[dict]:
    """
    Mencari chunk dokumen paling relevan dengan query menggunakan cosine similarity di pgvector.
    Returns:
        List of dict: {text, source_url, title, similarity}
    """
    try:
        query_embedding = embed_texts([query])[0].tolist()

        conn = get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                        SELECT text, source_url, title, 1 - (embedding <=> %s::vector) AS similarity
                        FROM rag_documents
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                        """, (query_embedding, query_embedding, top_k))
            rows = cur.fetchall()
        finally:
            cur.close()
            conn.close()
    except psycopg2.Error as exc:
        logger.warning("Gagal mengakses database untuk query %r: %s", query, exc)
        return []

    return [{"text": text, "source_url": url, "title": title, "similarity": float(sim)}
            for text, url, title, sim in rows]

def build_context(query: str, top_k: int = 5, max_chars: int = 450)->str:
    """
    Membangun string context yang lebih ringkas dan fokus pada hasil relevan.
    """
    results = search_similar(query, top_k)

    if not results:
        return (
            "Tidak ada konteks relevan yang tersedia saat ini. "
            "Periksa koneksi database atau indeks RAG Anda."
        )

    parts = []
    seen_urls = set()
    for r in results:
        url = r.get("source_url") or ""
        if url in seen_urls:
            continue
        seen_urls.add(url)

        text = _truncate_text(r.get("text", ""), max_chars=max_chars)
        score = r.get("similarity", 0.0)
        title = (r.get("title") or "Tanpa judul").strip()
        parts.append(
            f"Sumber: {title} ({url})\n"
            f"Relevansi: {score:.2f}\n"
            f"{text}"
        )
    return "\n---\n".join(parts)

if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "apa itu RAG"
    print(build_context(q))
    