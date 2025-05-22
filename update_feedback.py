from sheet_client import get_sheet_client
import logging

logger = logging.getLogger(__name__)

def increment_feedback(sheet_url: str, worksheet_name: str, matched_question: str, feedback_type: str):
    assert feedback_type in ["positive_feedback", "negative_feedback"], "Invalid feedback type"

    gc = get_sheet_client()
    sheet = gc.open_by_url(sheet_url).worksheet(worksheet_name)

    records = sheet.get_all_records()
    headers = sheet.row_values(1)

    try:
        feedback_col_index = headers.index(feedback_type) + 1  # gspread is 1-based
    except ValueError as e:
        raise ValueError("❌ Missing required columns in sheet") from e

    for row_index, row in enumerate(records):
        if row.get("question", "").strip() == matched_question.strip():
            current = row.get(feedback_type, 0)
            try:
                new_value = int(current) + 1
            except ValueError:
                new_value = 1
            sheet.update_cell(row_index + 2, feedback_col_index, new_value)
            logger.info(f"✅ Feedback updated: '{matched_question}' → {feedback_type} = {new_value}")
            return

    logger.warning(f"⚠️ Question not found in sheet: {matched_question}")