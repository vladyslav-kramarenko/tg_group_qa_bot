import os
import logging
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

logger = logging.getLogger(__name__)

def get_drive_client():
    scopes = ["https://www.googleapis.com/auth/drive"]
    creds_path = os.getenv("GOOGLE_CREDS_FILE")

    if not creds_path or not os.path.exists(creds_path):
        raise FileNotFoundError(f"❌ Credential file not found at path: {creds_path}")

    creds = Credentials.from_service_account_file(creds_path, scopes=scopes)
    logger.info(f"🔐 Loaded Drive client from: {creds_path}")
    return build("drive", "v3", credentials=creds)