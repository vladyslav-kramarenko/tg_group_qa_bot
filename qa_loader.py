import pandas as pd
import requests
import io
import logging
from sheet_client import get_sheet_client

logger = logging.getLogger(__name__)

def load_qa_from_sheets(sheet_entries):
    if not sheet_entries:
        logger.info("ℹ️ No sheet sources found in config.")
        return []

    all_qa = []
    for entry in sheet_entries:
        url = entry.get("url")
        if not url:
            continue
        try:
            response = requests.get(url)
            response.raise_for_status()
            df = pd.read_csv(io.StringIO(response.text))
            if "question" in df.columns and "answer" in df.columns:
                qa = df[["question", "answer"]].dropna().to_dict(orient="records")
                all_qa.extend(qa)
                logger.info(f"✅ Loaded {len(qa)} Q&A pairs from sheet: {url}")
            else:
                logger.warning(f"⚠️ Missing 'question' or 'answer' columns in: {url}")
        except Exception as e:
            logger.error(f"❌ Error loading from {url}: {e}")
    return all_qa

def load_qa_from_google_sheet(sheet_url: str, sheet_tab: str):
    gc = get_sheet_client()
    sheet = gc.open_by_url(sheet_url).worksheet(sheet_tab)
    records = sheet.get_all_records()
    qa_pairs = []

    for row in records:
        if "question" in row and "answer" in row:
            qa_pairs.append({
                "question": row["question"],
                "answer": row["answer"]
            })

    return qa_pairs