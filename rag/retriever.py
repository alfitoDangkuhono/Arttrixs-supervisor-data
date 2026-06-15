"""
Retriever: digunakan oleh LLM lokal untuk mengambil konteks relevan dari Postgres pgvector bedasarkan query similiraty search.
"""

from database.connection import get_connection
from processing.embedder import embed_texts



def search_similar(query: str, top_k:int = 5)->list[dict]:
    """
    Mencari chunk dokumen paling relevan dengan query menggunakan cosine similarity di pgvector.
    Returns:
        List of dict: {text, source_url, title, similarity}
    """
    query_embedding=embed_texts([query])[0].tolist()
    
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
    return [{"text": text, "source_url": url, "title": title, "similarity": float(sim)}
            for text,url,title,sim in rows]

def build_context(query: str, top_k: int = 5)->str:
    """
    Membangun string context (siap dimasukkan ke promp LLM)
    dari hasil similiraty search.
    """
    results = search_similar(query,top_k)
    
    if not results:
        return ""
    
    parts= []
    for r in results:
        parts.append(
            f"Sumber: {r['title']} ({r['source_url']})\n{r['text']}"
        )
    return "\n---\n".join(parts)

if __name__ == "__main__":
    import sys

    q = " ".join(sys.argv[1:]) or "apa itu RAG"
    print(build_context(q))
    