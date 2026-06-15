"""

Fallback fetcher: digunakan jika hasil dari Tavily (raw_content) kosong
atau kurang lengkap, sehingga perlu mengambil langsung dari halaman web.
"""

import requests
from bs4 import BeautifulSoup


def  fetch_content(url: str, max_chars: int = 5000)-> str:

    """
    Mengambil dan membersihkan teks utama dari sebuah halama web.
    Returns:
        Teks bersih (tanpa script/style/nav/footer), dipotong sampai max_chars.
        String kosong jika gagal
    """
    try: 
        headers= {"User-Agent":"Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script","style","nav","header"]):
            tag.decompose()
        text = " ".join(soup.get_text(separator=" ").split())
        return text[:max_chars]
    except Exception:
        return ""