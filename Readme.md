# RAG Supervisor - Automated Knowledge Base Pipeline

Pipeline otomatis pengumpulan data untuk RAG (Retrieval-Augmented Generation). Mencari informasi terbaru dari internet via **Tavily Search API** (dengan fallback **Brave Search**), membersihkan hasil, mengubahnya menjadi embedding, dan menyimpannya ke **PostgreSQL + pgvector** untuk digunakan sebagai knowledge base RAG. Project ini dilengkapi dengan **API FastAPI** untuk query dan integrasi dengan LLM lokal.

## ✨ Fitur Utama

- 🔍 **Pencarian Multi-Sumber**: Tavily Search dengan fallback Brave Search
- 🧹 **Pembersihan Otomatis**: Menghapus Markdown, URL, noise dari hasil pencarian
- 📊 **31 Topik Terpantau**: Mencakup berita, AI/ML, programming, cloud, DevOps, security, mobile, dan open source
- 🚀 **API FastAPI**: Query dan format output fleksibel (text/json)
- 💾 **PostgreSQL + pgvector**: Similarity search berbasis vector embedding
- ⏰ **Scheduler Berkala**: Otomatis update knowledge base
- 🤖 **LLM-Ready Output**: Context terformat khusus untuk model lokal

## 📁 Struktur Project

```
arttrixs-supervisor-data/
├── app.py                    # API FastAPI untuk query RAG
├── Readme.md                 # dokumentasi ini
├── requirements.txt          # Python dependencies
├── config/
│   └── settings.py          # konfigurasi terpusat (ENV, topik, model)
├── database/
│   ├── connection.py        # koneksi PostgreSQL
│   └── schema.sql           # schema tabel RAG + pgvector
├── collectors/
│   ├── fetcher.py           # HTML fetcher fallback
│   ├── search.py            # Tavily + Brave Search dengan cleaning
│   └── __init__.py
├── processing/
│   ├── chunker.py           # text chunking
│   ├── embedder.py          # sentence-transformers embedding
│   └── __init__.py
├── supervisor/
│   ├── pipeline.py          # pipeline utama: search → chunk → embed → save
│   └── __init__.py
├── rag/
│   └── retriever.py         # similarity search & context building
├── scheduler/
│   └── scheduler.py         # APScheduler untuk eksekusi berkala
└── scripts/
    └── init_db.py           # setup database schema
```

## 🔧 Setup

### 1. Clone & Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Setup PostgreSQL + pgvector

Pastikan PostgreSQL terinstall dengan extension `pgvector`. Inisialisasi schema:

```bash
python scripts/init_db.py
```

### 3. Setup Environment Variables

Buat file `.env` di root project:

```env
# Tavily Search API
TAVILY_API_KEY=your_tavily_api_key_here

# Brave Search API (opsional, sebagai fallback)
BRAVE_API_KEY=your_brave_api_key_here

# Database PostgreSQL
DB_HOST=localhost
DB_PORT=5432
DB_NAME=ragdb
DB_USER=postgres
DB_PASSWORD=strongpassword123

# Embedding Model
EMBEDDING_MODEL=all-MiniLM-L6-v2
EMBEDDING_DIM=384

# Search Results
MAX_RESULTS_PER_TOPIC=5

# Scheduler
SCHEDULE_INTERVAL_HOURS=1
```

### 4. Konfigurasi Topik Pencarian

Edit `config/settings.py` untuk menyesuaikan topik. Default sudah include 31 topik:

**Kategori topics yang tersedia:**
- 📰 **Berita**: piala dunia, teknologi, bisnis/startup
- 🤖 **AI/ML**: AI trends, LLM, Generative AI
- 💻 **Programming**: Laravel, JavaScript, Python, Golang, Rust
- ☁️ **Web/Cloud**: AWS/GCP/Azure, Docker, Kubernetes, Microservices
- 📊 **Data/Database**: PostgreSQL, pgvector, design patterns
- 🔧 **DevOps**: CI/CD, Git, testing, DevOps tools
- 🔒 **Security**: cybersecurity, web security, API auth
- 📱 **Mobile**: React Native, Flutter
- 🌟 **Open Source**: trending projects

## 🚀 Menjalankan

### Pipeline Supervisor (Indexing)

Jalankan sekali untuk mengindex semua topik:

```bash
python -m supervisor.pipeline
```

**Reindex semua URL (abaikan processed_urls):**

```bash
# Windows PowerShell
$env:FORCE_REINDEX='1'
python -m supervisor.pipeline

# Windows Command Prompt
set FORCE_REINDEX=1
python -m supervisor.pipeline

# Linux/Mac
FORCE_REINDEX=1 python -m supervisor.pipeline
```

### API Server

Jalankan FastAPI server untuk query RAG:

```bash
python -m uvicorn app:app --host 127.0.0.1 --port 8000
```

Akses dokumentasi API:
- 📖 **Swagger UI**: http://127.0.0.1:8000/docs
- 🔍 **ReDoc**: http://127.0.0.1:8000/redoc
- 💚 **Health Check**: http://127.0.0.1:8000/health

### Scheduler (Berkala)

Jalankan untuk eksekusi pipeline secara otomatis sesuai interval:

```bash
python scheduler/scheduler.py
```

Interval default: 1 jam (atur `SCHEDULE_INTERVAL_HOURS` di `.env`)

## 📡 API Endpoints

### `/api/search`

Query similarity search dengan output context terformat:

```http
GET /api/search?query=piala+dunia&top_k=5&context_format=text
```

**Query Parameters:**
- `query` (required): kata kunci pencarian
- `top_k` (optional, default=5): jumlah hasil teratas (1-10)
- `context_format` (optional, default='text'): format output ('text' atau 'json')

**Response Format (text):**

```
1) Judul Artikel 1 — https://example.com/article1
Relevansi: 0.92
Ringkasan artikel berkaitan dengan piala dunia...

---

2) Judul Artikel 2 — https://example.com/article2
Relevansi: 0.87
Penjelasan lengkap tentang piala dunia terbaru...
```

**Response Format (json):**

```json
[
  {
    "title": "Judul Artikel",
    "url": "https://example.com",
    "similarity": 0.92,
    "text": "Ringkasan artikel dibersihkan dari noise..."
  }
]
```

### `/health`

Health check endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Response:
```json
{"status": "ok", "service": "rag-supervisor"}
```

## 🤖 Integrasi dengan LLM Lokal

### Contoh: Menggunakan Ollama

```python
import requests
from rag.retriever import build_context

# Query ke RAG API
response = requests.get(
    "http://127.0.0.1:8000/api/search",
    params={
        "query": "Apa itu artificial intelligence",
        "top_k": 5,
        "context_format": "text"
    }
)

context = response.json()["context"]

# Siapkan prompt untuk LLM
prompt = f"""Berdasarkan konteks berikut:

{context}

Jawab pertanyaan dengan detail dan mudah dipahami:
Apa itu artificial intelligence dan aplikasinya?
"""

# Send ke Ollama (local LLM)
llm_response = requests.post(
    "http://127.0.0.1:11434/api/generate",
    json={
        "model": "mistral",
        "prompt": prompt,
        "stream": False
    }
)

print(llm_response.json()["response"])
```

### Python Library Integration

```python
from rag.retriever import build_context, search_similar

# Text format (model-friendly)
context_text = build_context("framework RAG", top_k=5, output_format="text")

# JSON format (structured data)
context_json = build_context("framework RAG", top_k=5, output_format="json")

# Raw search results
results = search_similar("framework RAG", top_k=5)
```

### CLI Retriever

Test langsung dari terminal:

```bash
python -m rag.retriever "apa itu RAG"
python -m rag.retriever "machine learning terbaru" 3
```

## 🧹 Data Cleaning & Preprocessing

### Tavily Result Cleaning
- ✅ HTML tag stripping (BeautifulSoup)
- ✅ URL removal
- ✅ Markdown artifact removal
- ✅ Whitespace normalization
- ✅ Duplicate URL deduplication
- ✅ Content truncation (smart sentence boundary)

### Context Building
- ✅ Keyword filtering (prioritas hasil relevan)
- ✅ Similarity score sorting
- ✅ Redundancy removal
- ✅ Safe truncation untuk model input

## 📊 Database Schema

### `rag_documents`
```sql
id              TEXT PRIMARY KEY         -- md5(url-chunk_index)
text            TEXT                     -- chunk teks
embedding       VECTOR(384)              -- sentence-transformers embedding
source_url      TEXT                     -- URL sumber
title           TEXT                     -- judul halaman
chunk_index     INT                      -- nomor chunk
total_chunks    INT                      -- total chunks dalam dokumen
query_topic     TEXT                     -- topik yang dicari
scraped_at      TIMESTAMP                -- waktu scraping
```

### `processed_urls`
```sql
url             TEXT PRIMARY KEY         -- URL yang sudah diproses
processed_at    TIMESTAMP                -- waktu processing
```

## ⚙️ Konfigurasi Lanjutan

### Mengubah Embedding Model

Edit `config/settings.py` dan `database/schema.sql`:

```python
# config/settings.py
EMBEDDING_MODEL = "all-mpnet-base-v2"  # 768 dimensi
EMBEDDING_DIM = 768
```

```sql
-- database/schema.sql (ubah VECTOR dimension)
embedding VECTOR(768),  -- sesuaikan dimensi
```

Re-run `python scripts/init_db.py` untuk apply schema baru.

### Mengubah Chunk Size

```env
# .env
CHUNK_SIZE=400          # ukuran chunk (tokens)
CHUNK_OVERLAP=50        # overlap antar chunks
```

### Scheduler: Cron Schedule (Alternatif)

Ubah `scheduler/scheduler.py` untuk menggunakan cron trigger:

```python
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
import zoneinfo

tz_jakarta = zoneinfo.ZoneInfo("Asia/Jakarta")

scheduler.add_job(
    run_supervisor,
    trigger=CronTrigger(hour=0, minute=0, timezone=tz_jakarta),
    id="rag_supervisor_job",
)
```

## 📝 Catatan Penting

- **Embedding Model**: Default `all-MiniLM-L6-v2` (ringan, CPU-friendly, 384 dim). Ganti model → update `EMBEDDING_DIM` & schema.
- **API Key Quotas**: 
  - Tavily free tier: ~1000 request/bulan
  - Brave free tier: terbatas
  - Sesuaikan jumlah topik & interval scheduler agar tidak melebihi kuota.
- **URL Deduplication**: Disimpan di `processed_urls` untuk hindari reprocessing.
- **Force Reindex**: Gunakan `FORCE_REINDEX=1` untuk reprocess semua URL (abaikan `processed_urls`).
- **Performance**: Gunakan `pgvector` index (HNSW) untuk fast similarity search pada dataset besar.

## 🐛 Troubleshooting

### Database Connection Error

```
psycopg2.OperationalError: could not connect to server
```

**Solusi:**
- Pastikan PostgreSQL running: `pg_isready -h localhost -p 5432`
- Cek kredensial di `.env`
- Pastikan database sudah dibuat: `createdb ragdb -U postgres`

### pgvector Extension Not Found

```
psycopg2.ProgrammingError: permission denied to create extension
```

**Solusi:**
```bash
# Run sebagai superuser
psql -U postgres -d ragdb -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### Tavily API Not Configured

```
ValueError: TAVILY_API_KEY not set. Add on file .env
```

**Solusi:**
- Daftar gratis di https://tavily.com
- Copy API key ke `.env`: `TAVILY_API_KEY=your_key`

## 📚 Resources

- **Tavily Search**: https://tavily.com
- **Brave Search**: https://api.search.brave.com
- **pgvector**: https://github.com/pgvector/pgvector
- **sentence-transformers**: https://sbert.net
- **FastAPI**: https://fastapi.tiangolo.com
- **APScheduler**: https://apscheduler.readthedocs.io