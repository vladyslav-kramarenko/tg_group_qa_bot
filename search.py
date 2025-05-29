### search.py
import json
import logging
import re
from pathlib import Path
from typing import List, Tuple, Dict

import faiss
from embedder import get_embedder
from config.config_loader import load_config_yaml
from collections import defaultdict

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

config = load_config_yaml()
search_config = config.get("search", {})
DISTANCE_THRESHOLD = float(search_config.get("distance_threshold", 1.0))
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

def search(query: str, top_k: int = 10) -> List[dict]:
    logger.info(f"🔍 Searching for: {query}")
    embedding = embedder.encode([query])
    D, I = index.search(embedding, top_k)

    raw_results = []
    for i, idx in enumerate(I[0]):
        if idx < len(metadata):
            distance = float(D[0][i])
            if distance <= DISTANCE_THRESHOLD:
                raw_results.append((distance, metadata[idx]))

    if not raw_results:
        logger.warning("🚫 No matching results found under threshold.")
        return []

    # Group by origin + source
    grouped = {}
    for distance, chunk in raw_results:
        key = (chunk["origin"], chunk["source"])
        if key not in grouped:
            grouped[key] = {
                "source": chunk["source"],
                "origin": chunk["origin"],
                "score": distance,
                "chunks": [chunk]
            }
        else:
            grouped[key]["chunks"].append(chunk)
            if distance < grouped[key]["score"]:
                grouped[key]["score"] = distance  # keep best score

    sorted_groups = sorted(grouped.values(), key=lambda x: x["score"])
    return sorted_groups

def format_result(group: dict) -> str:
    title = group["chunks"][0].get("title", group["origin"])
    service = group["chunks"][0].get("service", "unknown")
    url = group["chunks"][0].get("url")
    top_score = group["score"]

    display = f"\n📌 Source: {group['source'].upper()} ({service})\n🎬 Title: {title}\n🧠 Top Score: {top_score:.4f}"
    if url:
        display += f"\n🔗 Watch video: {url}"

    for chunk in group["chunks"]:
        if chunk["type"] == "summary":
            display += f"\n\n📝 Summary:\n{chunk['text']}"
        elif chunk["type"] == "steps":
            lines = chunk["text"].split("\n")
            formatted_steps = []
            for i, line in enumerate(lines, 1):
                # Try to extract just the value from a string like "- {'step': 'Do something'}"
                match = re.search(r"'step':\s*['\"](.+?)['\"]", line)
                if match:
                    step_text = match.group(1)
                else:
                    # fallback: just clean hyphens or whitespace
                    step_text = line.strip("- ").strip()
                formatted_steps.append(f"{i}. {step_text}")
            display += f"\n\n🪜 Steps:\n" + "\n".join(formatted_steps)
        elif chunk["type"] == "faq":
            display += f"\n\n❓ Q&A:\n{chunk['text']}"

    return display

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python search.py \"your question here\"")
        exit(1)

    query = sys.argv[1]
    results = search(query)
    for group in results:
        print(format_result(group))
