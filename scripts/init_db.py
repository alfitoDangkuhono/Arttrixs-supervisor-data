"""
Script sekali pakai: menjalankan database/schema.sql untuk membuat extension, tabel, dan index yang diperlukan.

Cara pakai:
    python scripts/init_db.py
"""

import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from database.connection import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..","database","schema.sql")

def main():
    with open(SCHEMA_PATH,"r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    conn = get_connection()
    cur = conn.cursor()
    
    try:
        cur.execute(schema_sql)
        conn.commit()
        logger.info("Schema berhasil diterapkan.")
    finally:
        cur.close()
        conn.close()
    
if __name__ == "__main__":
    main()