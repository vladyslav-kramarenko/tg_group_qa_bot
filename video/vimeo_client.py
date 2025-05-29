import logging

logger = logging.getLogger(__name__)

def fetch_vimeo_transcript(video: dict):
    """
    Placeholder for Vimeo transcript loader.
    Logs the video info and skips actual processing for now.
    """
    url = video.get("url")
    title = video.get("title", "Untitled")
    service = video.get("service", "vimeo")

    logger.info(f"📼 [Vimeo] Skipping transcript fetch for: {title} ({url})")