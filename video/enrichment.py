### enrichment.py
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

import os
import json
import logging
import re
import google.generativeai as genai

from config.config_loader import load_config_yaml
from video.youtube_downloader import extract_video_id

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY is missing in your environment")
genai.configure(api_key=API_KEY)

config = load_config_yaml()
MODEL_NAME = config.get("gemini", {}).get("video_enrichment_model", "gemini-1.5-pro")
DOWNLOAD_DIR = Path("downloads")
OUTPUT_DIR = Path("data/enriched_video_data")

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

def extract_json_block(text: str) -> str:
    match = re.search(r"```json\s*(.*?)```", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()

def enrich_video_locally(service: str, video_path: Path, title: str):
    logger.info(f"\U0001F4FC Enriching video: {title} ({video_path})")
    model = genai.GenerativeModel(model_name=MODEL_NAME)

    video_bytes = video_path.read_bytes()
    video_part = {
        "mime_type": "video/mp4",
        "data": video_bytes,
    }
    contents = [SYSTEM_ROLE, USER_INSTRUCTION, video_part]

    try:
        response = model.generate_content(contents)
        output = extract_json_block(response.text)
        parsed = json.loads(output)

        parsed["title"] = title
        parsed["service"] = service
        parsed["video_url"] = str(video_path)

        for v in config.get("data_sources", {}).get("videos", []):
            if v.get("title") == title:
                parsed["video_url"] = v.get("url")

        output_path = OUTPUT_DIR / service / f"{video_path.stem}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"✅ Saved enriched output to: {output_path}")
    except Exception as e:
        logger.error(f"❌ Failed to enrich video {video_path.name}: {e}")

def enrich_all_local_videos():
    videos = config.get("data_sources", {}).get("videos", [])
    for video in videos:
        url = video.get("url")
        service = video.get("service")
        title = video.get("title", "Untitled")
        video_id = extract_video_id(url)

        local_path = DOWNLOAD_DIR / service / f"{video_id}.mp4"
        output_path = OUTPUT_DIR / service / f"{video_id}.json"

        if not local_path.exists():
            logger.warning(f"⚠️ Video file not found locally: {local_path}")
            continue

        if output_path.exists():
            logger.info(f"🟡 Skipping already enriched video: {output_path}")
            continue

        enrich_video_locally(service, local_path, title)

if __name__ == "__main__":
    enrich_all_local_videos()