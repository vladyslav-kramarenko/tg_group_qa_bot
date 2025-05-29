import logging
from typing import List, Dict
from sheets.sheet_client import get_sheet_client
from config.config_loader import load_config_yaml

logger = logging.getLogger(__name__)


def extract_chunks_from_sheet(sheet_url: str, sheet_tab: str, service: str = "general") -> List[Dict]:
    gc = get_sheet_client()
    sheet = gc.open_by_url(sheet_url).worksheet(sheet_tab)
    records = sheet.get_all_records()
    chunks = []

    for row in records:
        q = row.get("question")
        a = row.get("answer")
        if q and a:
            chunks.append({
                "text": f"Q: {q}\nA: {a}",
                "source": "sheet",
                "service": service,
                "origin": sheet_tab,
                "type": "faq"
            })

    logger.info(f"✅ Extracted {len(chunks)} Q&A chunks from {sheet_tab}")
    return chunks


def extract_all_sheet_chunks() -> List[Dict]:
    config = load_config_yaml()
    sheets_cfg = config.get("data_sources", {}).get("google_sheets", {})
    chunks = []

    for name, entry in sheets_cfg.items():
        url = entry.get("url")
        tab = entry.get("tab")
        if not url or not tab:
            continue
        chunks.extend(extract_chunks_from_sheet(url, tab, service=name))

    return chunks


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    all_chunks = extract_all_sheet_chunks()
    print(f"✅ Total sheet chunks extracted: {len(all_chunks)}")
