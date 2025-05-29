import gspread
from google.oauth2.service_account import Credentials
import os

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

def get_sheet_client():
    creds_file = os.getenv("GOOGLE_CREDS_FILE")
    if not creds_file:
        raise ValueError("GOOGLE_CREDS_FILE not set in .env")
    creds = Credentials.from_service_account_file(creds_file, scopes=SCOPES)
    return gspread.authorize(creds)