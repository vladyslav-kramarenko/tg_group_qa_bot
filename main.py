import argparse
import logging
from video.transcript_loader import fetch_all_transcripts
from video.chunker import process_all_cached_transcripts
# from video.embedder import build_all_faiss_indexes  # Future
# from bot.bot import run_bot                         # Optional integration

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Telegram Support Bot Utilities")
    parser.add_argument("--task", type=str, required=True, help="Task to run", choices=[
        "fetch_transcripts",
        "chunk_transcripts",
        # "build_indexes",
        # "run_bot"
    ])
    args = parser.parse_args()

    if args.task == "fetch_transcripts":
        logger.info("📥 Fetching video transcripts...")
        fetch_all_transcripts()

    elif args.task == "chunk_transcripts":
        logger.info("🧩 Chunking cached transcripts...")
        process_all_cached_transcripts()

    elif args.task == "enrich_videos":
        from video.enrichment import enrich_all_local_videos
        enrich_all_local_videos()

    # elif args.task == "build_indexes":
    #     logger.info("🔧 Building FAISS indexes...")
    #     build_all_faiss_indexes()

    # elif args.task == "run_bot":
    #     logger.info("🤖 Starting the bot...")
    #     run_bot()

if __name__ == "__main__":
    main()