### search.py
import json
import logging
from pathlib import Path
from typing import List, Tuple

import faiss
from embedder import get_embedder
from config.config_loader import load_config_yaml

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

config = load_config_yaml()
index_config = config.get("index", {})
INDEX_DIR = Path(index_config.get("dir", "index"))
INDEX_FILE = INDEX_DIR / index_config.get("name", "qa_index.faiss")
META_FILE = INDEX_DIR / index_config.get("metadata", "qa_metadata.json")

if not INDEX_FILE.exists() or not META_FILE.exists():
    raise FileNotFoundError("❌ FAISS index or metadata file not found. Please run the indexer first.")

logger.info("📦 Loading FAISS index and metadata...")
index = faiss.read_index(str(INDEX_FILE))
with open(META_FILE, "r", encoding="utf-8") as f:
    metadata = json.load(f)

embedder = get_embedder()

def search(query: str, top_k: int = 5) -> List[Tuple[str, dict]]:
    logger.info(f"🔍 Searching for: {query}")
    embedding = embedder.encode([query])
    D, I = index.search(embedding, top_k)

    results = []
    for i, idx in enumerate(I[0]):
        if idx < len(metadata):
            result = metadata[idx]
            result_score = float(D[0][i])
            results.append((result_score, result))

    if not results:
        logger.warning("🚫 No matching results found.")

    return results

def format_result(result: dict, score: float) -> str:
    title = result.get("title") or result.get("origin", "N/A")
    service = result.get("service", "unknown")
    src = result.get("source")
    rtype = result.get("type")
    text = result.get("text")
    url = result.get("url")

    display = f"\n📌 Source: {src.upper()} ({service})\n🔎 Type: {rtype}\n🧠 Score: {score:.4f}\n📝 Content:\n{text}"
    if url:
        display += f"\n🔗 Watch video: {url}"
    return display

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python search.py \"your question here\"")
        exit(1)

    query = sys.argv[1]
    results = search(query)
    for score, r in results:
        print(format_result(r, score))
