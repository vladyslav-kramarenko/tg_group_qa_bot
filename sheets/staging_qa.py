from sheets.sheet_client import get_sheet_client
from datetime import datetime
import logging

# === SETUP LOGGER ===
logger = logging.getLogger(__name__)

# === CONFIG ===
from config.config_loader import load_config_yaml

config = load_config_yaml()
staging_cfg = config.get("data_sources", {}).get("google_sheets", {}).get("staging", {})
SHEET_URL = staging_cfg.get("url")
SHEET_TAB = staging_cfg.get("tab", "staging_qa")

# === LOGGING FUNCTION ===
def log_staging_qa(question: str, answer: str = None, user: str = None, chat: str = None):
    gc = get_sheet_client()
    sheet = gc.open_by_url(SHEET_URL).worksheet(SHEET_TAB)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sheet.append_row([now, chat, user, question, answer or "", "", ""])
    logger.info(f"📝 Staged new Q&A: {question} → {answer}")