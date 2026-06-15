"""
Generate embedding vector dari teks menggunakan
sentence-transformers (model berjalan lokal, tidak perlu API KEY)
"""

import logging
import os
import warnings

from sentence_transformers import SentenceTransformer

from config.settings import EMBEDDING_MODEL

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TQDM_DISABLE", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

warnings.filterwarnings("ignore")

logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

_model = None

def get_model():
    """
    Lazy-load model agar hanya dimuat sekali(model cukup besar).
    """

    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL)
    return _model
    
def embed_texts(texts: list[str]):

    """
    Generate embedding untuk list teks.
    Return: 
        numpy.ndarray dengan shape (len(texts), EMBEDDING_DIM)
    """
    model = get_model()
    return model.encode(texts, show_progress_bar=False)