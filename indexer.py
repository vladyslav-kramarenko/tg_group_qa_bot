import logging
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import faiss

from config.config_loader import load_config_yaml
from video.video_qa_extractor import extract_all_video_chunks
from sheets.sheet_qa_extractor import extract_all_sheet_chunks

# === Logging Setup ===
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# === Load Config ===
config = load_config_yaml()
MODEL_NAME = config.get("embedding", {}).get("model", "all-MiniLM-L6-v2")
index_config = config.get("index", {})

INDEX_DIR = Path(index_config.get("dir", "index"))
INDEX_FILE = INDEX_DIR / index_config.get("name", "qa_index.faiss")
META_FILE = INDEX_DIR / index_config.get("metadata", "qa_metadata.json")

INDEX_DIR.mkdir(exist_ok=True)


def build_index():
    logger.info("📦 Starting index build...")

    # Step 1: Load data chunks
    video_chunks = extract_all_video_chunks()
    logger.info(f"🎥 Extracted {len(video_chunks)} chunks from enriched video data")

    sheet_chunks = extract_all_sheet_chunks()
    logger.info(f"📄 Extracted {len(sheet_chunks)} chunks from Google Sheets")

    all_chunks = video_chunks + sheet_chunks
    logger.info(f"🧱 Total chunks to index: {len(all_chunks)}")

    if not all_chunks:
        logger.error("❌ No chunks available for indexing. Exiting.")
        return

    # Step 2: Validate chunk structure
    for i, chunk in enumerate(all_chunks):
        if "text" not in chunk:
            logger.warning(f"⚠️ Missing 'text' field in chunk {i}: {chunk}")

    texts = [chunk["text"] for chunk in all_chunks if "text" in chunk]

    # Step 3: Embeddings
    logger.info(f"🧠 Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    embeddings = model.encode(texts, show_progress_bar=True)
    logger.info(f"📐 Generated {len(embeddings)} embeddings of dimension {embeddings.shape[1]}")

    # Step 4: FAISS index
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    if index.ntotal != len(texts):
        logger.warning(f"⚠️ FAISS index count mismatch: index={index.ntotal}, embeddings={len(texts)}")
    else:
        logger.info("✅ FAISS index built successfully")

    faiss.write_index(index, str(INDEX_FILE))
    logger.info(f"💾 FAISS index saved to: {INDEX_FILE}")

    # Step 5: Metadata
    with open(META_FILE, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    logger.info(f"📝 Metadata saved to: {META_FILE}")


if __name__ == "__main__":
    build_index()