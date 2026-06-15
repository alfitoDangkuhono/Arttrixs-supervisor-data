# RAG Supervisor

Pipeline otomatis yang mencari informasi terbaru dari internet (via Tavily
Search API), mengubahnya menjadi embedding, dan menyimpannya ke PostgreSQL
(pgvector) untuk digunakan sebagai knowledge base RAG oleh LLM lokal.

## Struktur Project

```
rag-supervisor/
├── config/         konfigurasi (.env, topik, model embedding, dll)
├── database/       schema SQL & koneksi Postgres
├── collectors/     pencarian (Tavily) & fetch konten web
├── processing/     chunking & embedding teks
├── supervisor/     pipeline utama: search -> chunk -> embed -> simpan
├── scheduler/      menjalankan supervisor secara berkala
├── rag/            retriever untuk LLM lokal (similarity search)
└── scripts/        utility (init database)
```

## Setup

1. Buat virtual environment & install dependency

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Pastikan PostgreSQL sudah terinstall extension `pgvector`.

3. Copy `.env.example` menjadi `.env`, lalu isi:
   - `TAVILY_API_KEY` (daftar gratis di tavily.com)
   - kredensial database (`DB_HOST`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, dll)

   ```bash
   cp .env.example .env
   ```

4. Inisialisasi database (membuat extension, tabel, index):

   ```bash
   python scripts/init_db.py
   ```

## Konfigurasi Topik

Edit `config/settings.py`, ubah list `TOPICS` sesuai topik yang ingin
dipantau supervisor:

```python
TOPICS = [
    "perkembangan AI lokal terbaru",
    "framework RAG terbaru",
]
```

## Menjalankan

### Sekali jalan (manual)

```bash
python -m supervisor.pipeline
```

### Berkala (scheduler bawaan)

```bash
python scheduler/scheduler.py
```

Akan jalan sekali saat start, lalu berulang setiap `SCHEDULE_INTERVAL_HOURS`
jam (default 1 jam, atur di `.env`).

### Berkala via cron (alternatif)

```bash
# tambahkan ke crontab -e, contoh tiap jam:
0 * * * * cd /path/to/rag-supervisor && /path/to/venv/bin/python -m supervisor.pipeline >> logs/supervisor.log 2>&1
```

## Menggunakan untuk RAG (LLM lokal)

```python
from rag.retriever import build_context

context = build_context("apa itu RAG", top_k=5)

prompt = f"""Berdasarkan informasi berikut:

{context}

Jawab pertanyaan: apa itu RAG"""

# kirim prompt ke LLM lokal (Ollama, llama.cpp, dll)
```

Atau jalankan langsung dari terminal untuk uji coba:

```bash
python -m rag.retriever "apa itu RAG"
```

## Catatan

- Model embedding default: `all-MiniLM-L6-v2` (384 dimensi, ringan, jalan
  di CPU). Jika ganti model dengan dimensi berbeda, update juga
  `EMBEDDING_DIM` di `.env` dan `VECTOR(...)` di `database/schema.sql`.
- Deduplikasi URL disimpan di tabel `processed_urls` agar tidak
  diproses ulang.
- Free tier Tavily: ~1000 request/bulan — sesuaikan jumlah topik dan
  interval scheduler agar tidak melebihi kuota.