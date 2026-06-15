"""
Pipeline utama Supervisor:
1.Cari topik via Tavily (collectors.search)
2.Fallback fetch konten jika perlu (collectors.fetcher)
3.Chunking teks (processing.chunker)
4.Generate embedding (processing.embedder)
5.Simpan ke PostgreSQl pgvector, dengan duplikasi URL
"""

import hashlib
import logging
from datetime import datetime

from psycopg2.extras import execute_batch
from config.settings import TOPICS
from database.connection import get_connection
from collectors.search import search_topic
from collectors.fetcher import fetch_content
from processing.chunker import chunk_text
from processing.embedder import embed_texts

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("supervisor")


#-----Helper Postgres----
def is_url_processed(cur, url: str)->bool:
    cur.execute("SELECT 1 FROM processed_urls WHERE url = %s",(url,))
    return cur.fetchone() is not None

def mark_url_processed(cur, url:str)-> None:
    cur.execute(
        "INSERT INTO processed_urls (url) VALUES (%s) ON CONFLICT DO NOTHING",(url,),
    )

#----Proses satu hasil pencarian------
def process_result(cur, topic: str, result: dict)->int:
    """
    Mengubah satu hasil pencarian menjadi chunk = embedding, lalu menyimpannya ke database.
    Return: 
        Jumlah chunk yang disimpan (0 jika dilewati).
    """
    url = result.get("url")
    title = result.get("title",url)

    if not url or is_url_processed(cur, url):
        return 0
    content = result.get("raw_content") or result.get("content","")

    #Fallback jika Tavily tidak memberi konten lengkap, fetch manual

    if not content or len(content) < 200:
        fetched = fetch_content(url)
        if fetched:
            content = fetched
    
    if not content:
        logger.warning("Tidak ada konten dari %s, dilewati", url)
        return 0
    
    chunks = chunk_text(content)
    if not chunks:
        return 0
    
    embeddings= embed_texts(chunks)

    rows=[]
    now= datetime.utcnow()
    for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        doc_id = hashlib.md5(f"{url}-{i}".encode()).hexdigest()
        rows.append((
            doc_id,
            chunk,
            emb.tolist(),
            url,
            title,
            i,
            len(chunks),
            topic,
            now,
        ))

    execute_batch(cur,"""
        INSERT INTO rag_documents
            (id, text, embedding, source_url, title, chunk_index, total_chunks, query_topic, scraped_at) VALUES (%s, %s, %s,%s,%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING
    """, rows)
    
    mark_url_processed(cur, url)
    return len(rows)

#-----Main job------
def run_supervisor(topics: list[str] | None = None)->int :
    """
    Menjalankan satu siklus pengumpulan data untuk semua topik.
    Returns:
        Totol chunk baru yang disimpan ke database.
    """
    topics = topics or TOPICS
    conn = get_connection()
    cur = conn.cursor()
    
    total_inserted = 0
    
    try:
        for topic in topics:
            logger.info("Mencari topik: %s",topic)
            try:
                results = search_topic(topic)
            except Exception:
                logger.exception("Gagal mencari topik: %s",topic)
                continue
            for r in results:
                try:
                    count= process_result(cur,topic,r)
                    if count:
                        logger.info(" + %d chunk dari %s",count,r.get("url"))
                        total_inserted += count
                except Exception:
                    logger.exception("Gagal memproses %s", r.get("url"))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    logger.info("Selesai. Tota chunk baru: %d", total_inserted)
    return total_inserted

if __name__ == "__main__":
    run_supervisor()
    