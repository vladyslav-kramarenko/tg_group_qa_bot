### video_qa_extractor.py
import os
import json
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

ENRICHED_DIR = Path("data/enriched_video_data")

def extract_chunks_from_video_json(file_path: Path, service: str) -> List[Dict]:
    chunks = []
    video_id = file_path.stem

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"⚠️ Failed to load JSON: {file_path} → {e}")
        return []

    video_url = data.get("video_url") or f"file://{file_path}"

    if summary := data.get("summary"):
        chunks.append({
            "text": summary,
            "source": "video",
            "service": service,
            "origin": video_id,
            "type": "summary",
            "url": video_url,
            "title": data.get("title")
        })

    if steps := data.get("key_steps"):
        step_text = "\n".join(f"- {step}" for step in steps)
        chunks.append({
            "text": step_text,
            "source": "video",
            "service": service,
            "origin": video_id,
            "type": "steps",
            "url": video_url,
            "title": data.get("title")
        })

    for pair in data.get("common_questions_and_answers", []):
        q = pair.get("question")
        a = pair.get("answer")
        if q and a:
            chunks.append({
                "text": f"Q: {q}\nA: {a}",
                "source": "video",
                "service": service,
                "origin": video_id,
                "type": "faq",
                "url": video_url,
                "title": data.get("title")
            })

    return chunks

def extract_all_video_chunks() -> List[Dict]:
    all_chunks = []
    for service_dir in ENRICHED_DIR.iterdir():
        if not service_dir.is_dir():
            continue
        service = service_dir.name
        for file in service_dir.glob("*.json"):
            chunks = extract_chunks_from_video_json(file, service)
            all_chunks.extend(chunks)
    return all_chunks

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    chunks = extract_all_video_chunks()
    print(f"✅ Extracted {len(chunks)} chunks from videos")
