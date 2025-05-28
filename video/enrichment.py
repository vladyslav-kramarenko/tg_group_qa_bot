

import sys
from pathlib import Path
# ✅ Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))
import os
import json
import logging
import google.generativeai as genai
from config.config_loader import load_config_yaml
from video.youtube_downloader import extract_video_id

# === LOGGING ===
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# === CONFIG ===
API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY is missing in your environment")

genai.configure(api_key=API_KEY)

MODEL_NAME = load_config_yaml().get("gemini", {}).get("video_enrichment", "gemini-1.5-pro")
# MODEL_NAME = os.getenv("GEMINI_VIDEO_MODEL", "gemini-1.5-pro")
DOWNLOAD_DIR = Path("downloads")
OUTPUT_DIR = Path("data/enriched_video_data")

# === ENRICHMENT PROMPT ===
SYSTEM_ROLE = """
You are an expert assistant trained to understand videos and extract useful insights.
Your task is to analyze the content and provide:
1. A short summary
2. A list of key steps shown
3. Common questions answered by this video and their answers
Respond in structured JSON.
"""

USER_INSTRUCTION = """
Please analyze this instructional video. What does it explain?
Extract key steps and user-relevant Q&A based only on its visual and audio content.
"""

def enrich_video_locally(service: str, video_path: Path, title: str):
    logger.info(f"📼 Enriching video: {title} ({video_path})")

    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    model = genai.GenerativeModel(model_name=MODEL_NAME)

    video_bytes = video_path.read_bytes()
    video_part = {
        "mime_type": "video/mp4",
        "data": video_bytes,
    }

    contents = [SYSTEM_ROLE, USER_INSTRUCTION, video_part]

    try:
        response = model.generate_content(contents)
        output = response.text

        output_dir = OUTPUT_DIR / service
        output_dir.mkdir(parents=True, exist_ok=True)

        out_path = output_dir / f"{video_path.stem}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(output)

        logger.info(f"✅ Saved enriched output to: {out_path}")
    except Exception as e:
        logger.error(f"❌ Failed to enrich video {video_path.name}: {e}")

def enrich_all_local_videos():
    config = load_config_yaml()
    videos = config.get("data_sources", {}).get("videos", [])

    for video in videos:
        if video.get("source") != "youtube":
            continue

        url = video.get("url")
        service = video.get("service")
        title = video.get("title", "Untitled")
        video_id = extract_video_id(url)

        local_path = DOWNLOAD_DIR / service / f"{video_id}.mp4"
        if not local_path.exists():
            logger.warning(f"⚠️ Video file not found locally: {local_path}")
            continue

        enrich_video_locally(service, local_path, title)

if __name__ == "__main__":
    enrich_all_local_videos()