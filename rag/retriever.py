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


def _strip_markdown_and_urls(text: str) -> str:
    """Remove common markdown artifacts, images and raw URLs to make text model-friendly."""
    if not text:
        return ""
    s = text
    # remove image tags ![alt](url)
    s = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', s)
    # convert markdown links [text](url) -> text
    s = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r"\1", s)
    # remove raw urls
    s = re.sub(r'https?://\S+', '', s)
    # remove markdown header markers anywhere and common list bullets
    s = re.sub(r'\s*#{1,6}\s*', ' ', s)
    s = re.sub(r'\s*[-\*]\s*', ' ', s)
    # remove common noise tokens
    s = re.sub(r'Advertisement', ' ', s, flags=re.IGNORECASE)
    # collapse leftover multiple punctuation or spaces
    s = re.sub(r'[\t\r\n]+', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


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


def _matches_query_keywords(text: str, query: str, threshold: float = 0.3) -> bool:
    """Check if text contains significant keywords from query."""
    query_words = set(query.lower().split())
    text_lower = text.lower()
    matched = sum(1 for word in query_words if len(word) > 2 and word in text_lower)
    return matched / len(query_words) >= threshold if query_words else True


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

def build_context(query: str, top_k: int = 5, max_chars: int = 450, output_format: str = "text"):
    """
    Membangun string context yang lebih ringkas dan fokus pada hasil relevan.
    Prioritaskan hasil yang cocok dengan keyword query.
    """
    results = search_similar(query, top_k * 2)  # fetch lebih banyak untuk filter

    if not results:
        return (
            "Tidak ada konteks relevan yang tersedia saat ini. "
            "Periksa koneksi database atau indeks RAG Anda."
        )

    # Filter dan sort berdasarkan keyword match
    filtered_results = [
        (r, _matches_query_keywords(r.get("text", "") + " " + r.get("title", ""), query))
        for r in results
    ]
    filtered_results.sort(key=lambda x: (-x[1], -x[0].get("similarity", 0)))

    parts = []
    seen_urls = set()
    for r, _ in filtered_results:
        if len(parts) >= top_k:
            break

        url = r.get("source_url") or ""
        if url in seen_urls:
            continue
        seen_urls.add(url)

        raw_text = r.get("text", "")
        cleaned = _strip_markdown_and_urls(raw_text)
        text = _truncate_text(cleaned, max_chars=max_chars)
        score = r.get("similarity", 0.0)
        title = (r.get("title") or "Tanpa judul").strip()
        parts.append({
            "title": _normalize_text(title),
            "url": url,
            "similarity": round(float(score), 4),
            "text": text,
        })

    if output_format == "json":
        return parts

    # default: human-readable numbered text, compact and safe for model input
    out_lines = []
    for i, p in enumerate(parts, start=1):
        out_lines.append(
            f"{i}) {p['title']} — {p['url']}\nRelevansi: {p['similarity']:.2f}\n{p['text']}"
        )
    return "\n\n---\n\n".join(out_lines)

if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "apa itu RAG"
    print(build_context(q))
    