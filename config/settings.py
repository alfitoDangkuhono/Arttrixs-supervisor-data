"""
konfigurasi terpusat untuk RAG supervisor.
semua nilai dibaca dari environment variable (.env)
"""
import os
from dotenv import load_dotenv

load_dotenv()

#-------------Tavily Search--------
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY")
MAX_RESULTS_PER_TOPIC = int(
    os.environ.get("MAX_RESULTS_PER_TOPIC")
    or os.environ.get("MAX_RESULT_PER_TOPIC", 5)
)


#-------------PostgresSQL----------
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT",5432)),
    "dbname":os.environ.get("DB_NAME","ragdb"),
    "user":os.environ.get("DB_USER","postgres"),
    "password":os.environ.get("DB_PASSWORD","strongpassword123")
}

#---Embedding---
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL","all-MiniLM-L6-v2")
EMBEDDING_DIM = int(os.environ.get("EMBEDDING_DIM", 384))

#---Chunking---
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", 400))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP",50))

#---Scheduler---
SCHEDULE_INTERVAL_HOURS = int(os.environ.get("SCHEDULE_INTERVAL_HOURS", 1))

#---Topics yang di pantau supervisor-----
#bisa di ubah sesuai kebutuhan, atau nanti diganti generator otomatis (LLM)
TOPICS = [
    "perkembangan AI terbaru",
    "framework RAG terbaru",
    "model embedding open source terbaru"
]