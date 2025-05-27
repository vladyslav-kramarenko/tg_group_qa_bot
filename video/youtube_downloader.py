import os
import logging
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import subprocess
import sys
from pathlib import Path

# ✅ Add the project root to sys.path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config_loader import load_config_yaml

logger = logging.getLogger(__name__)

DOWNLOAD_DIR = Path("downloads")


def extract_video_id(url: str) -> str:
    query = parse_qs(urlparse(url).query)
    return query.get("v", [None])[0]


def download_youtube_video(url: str, service: str, video_id: str) -> Path:
    service_dir = DOWNLOAD_DIR / service
    service_dir.mkdir(parents=True, exist_ok=True)
    
    output_path = service_dir / f"{video_id}.mp4"
    if output_path.exists():
        logger.info(f"🟡 Video already downloaded: {output_path}")
        return output_path

    logger.info(f"⬇️ Downloading YouTube video: {url} → {output_path}")
    try:
        subprocess.run([
            "yt-dlp",
            "-f", "mp4",
            "-o", str(output_path),
            url
        ], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Failed to download {url}: {e}")
        return None

    return output_path


def download_all_youtube_videos():
    config = load_config_yaml()
    video_sources = config.get("data_sources", {}).get("videos", [])

    downloaded = {}
    for video in video_sources:
        if video.get("source") != "youtube":
            continue

        url = video.get("url")
        service = video.get("service")
        title = video.get("title")
        video_id = extract_video_id(url)

        local_path = download_youtube_video(url, service, video_id)
        if local_path:
            downloaded[video_id] = str(local_path)

    return downloaded


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    paths = download_all_youtube_videos()
    print("Downloaded:", paths)