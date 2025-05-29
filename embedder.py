import logging
from sentence_transformers import SentenceTransformer
from config.config_loader import load_config_yaml

logger = logging.getLogger(__name__)

# Load config and model name
config = load_config_yaml()
MODEL_NAME = config.get("embedding", {}).get("model", "all-MiniLM-L6-v2")

_model = None

def get_embedder():
    global _model
    if _model is None:
        logger.info(f"🧠 Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

def embed_texts(texts):
    model = get_embedder()
    logger.info(f"📐 Embedding {len(texts)} texts")
    return model.encode(texts, show_progress_bar=True)
