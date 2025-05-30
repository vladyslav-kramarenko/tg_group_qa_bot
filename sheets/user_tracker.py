from datetime import datetime
from sheets.sheet_client import get_sheet_client
from config.config_loader import load_config_yaml
import logging

logger = logging.getLogger(__name__)

# === CONFIG LOAD ===
config = load_config_yaml()
user_cfg = config.get("data_sources", {}).get("google_sheets", {}).get("users", {})
USER_SHEET_URL = user_cfg.get("url")
USER_SHEET_TAB = user_cfg.get("tab", "users")

if not USER_SHEET_URL:
    raise ValueError("❌ USER_SHEET_URL not found in config.yaml")

# === USER TRACKING ===
def log_user_if_new(user):
    """
    Append Telegram user metadata to sheet if not already present.
    """
    try:
        sheet = get_sheet_client().open_by_url(USER_SHEET_URL).worksheet(USER_SHEET_TAB)
        existing_ids = sheet.col_values(1)
        if str(user.id) in existing_ids:
            return
        sheet.append_row([
            str(user.id),
            user.username or "",
            user.first_name or "",
            user.last_name or "",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ""  # Email (to be filled manually)
        ])
        logger.info(f"✅ Logged new user: {user.id} ({user.username})")
    except Exception as e:
        logger.error(f"❌ Failed to log user: {e}")

def get_email_by_user_id(user_id: str) -> str:
    """
    Lookup email using Telegram user ID.
    """
    try:
        sheet = get_sheet_client().open_by_url(USER_SHEET_URL).worksheet(USER_SHEET_TAB)
        for row in sheet.get_all_records():
            if str(row.get("user_id")).strip() == str(user_id).strip():
                return row.get("email", "").strip()
    except Exception as e:
        logger.error(f"❌ Failed to get email by user ID {user_id}: {e}")
    return None

def get_email_by_username(username: str) -> str:
    """
    Lookup email using Telegram username.
    """
    try:
        sheet = get_sheet_client().open_by_url(USER_SHEET_URL).worksheet(USER_SHEET_TAB)
        for row in sheet.get_all_records():
            if row.get("username") == username and row.get("Email"):
                return row["Email"]
    except Exception as e:
        logger.error(f"❌ Failed to retrieve email for username {username}: {e}")
    return None