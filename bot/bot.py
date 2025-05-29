from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import os
import logging
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config_loader import load_config_yaml
# from sheets.qa_loader import load_qa_from_google_sheet
from sheets.update_feedback import increment_feedback
# from sentence_transformers import SentenceTransformer
# import faiss
# import numpy as np
from sheets.staging_qa import log_staging_qa
from search import search, format_result  # ✅ use unified search pipeline

# === LOGGING SETUP ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram.bot").setLevel(logging.WARNING)

# === BOT CONFIG ===
BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
BOT_USERNAME = os.getenv("TG_BOT_USERNAME")

if not BOT_TOKEN or not BOT_USERNAME:
    raise ValueError("Missing required env vars: TG_BOT_TOKEN, TG_BOT_USERNAME")

# === LOAD CONFIG ===
config = load_config_yaml()
CONFIDENCE_THRESHOLD = float(config.get("confidence_threshold", 0.75))

staging_cfg = config.get("data_sources", {}).get("google_sheets", {}).get("staging", {})
STAGING_SHEET_URL = staging_cfg.get("url")
STAGING_SHEET_TAB = staging_cfg.get("tab", "staging_qa")

if not STAGING_SHEET_URL:
    raise ValueError("❌ STAGING_SHEET_URL not found in config. Please check config.yaml")

# # === LOAD Q&A DATA FROM GOOGLE SHEET ===
# qa_cfg = config.get("data_sources", {}).get("google_sheets", {}).get("qa", {})
# QA_SHEET_URL = qa_cfg.get("url")
# QA_SHEET_TAB = qa_cfg.get("tab", "QandA")
# if not QA_SHEET_URL:
#     raise ValueError("❌ Sheet URL not found in config.yaml under data_sources → google_sheets → qa → url")
# qa_pairs = load_qa_from_google_sheet(QA_SHEET_URL, QA_SHEET_TAB)

# if not qa_pairs:
#     logger.warning("⚠️ No Q&A data loaded — bot will not respond meaningfully.")

# # === EMBEDDINGS + FAISS ===
# model = SentenceTransformer("all-MiniLM-L6-v2")
# questions = [q["question"] for q in qa_pairs]
# embeddings = model.encode(questions)

# index = faiss.IndexFlatL2(embeddings.shape[1])
# index.add(np.array(embeddings))

# === TELEGRAM BOT ===
app = ApplicationBuilder().token(BOT_TOKEN).build()

def clean_query(text: str) -> str:
    # Remove bot mention and excess whitespace
    return text.replace(f"@{BOT_USERNAME}", "").strip()

def is_mentioned(update: Update) -> bool:
    if not update.message or not update.message.text:
        return False
    return f"@{BOT_USERNAME.lower()}" in update.message.text.lower()

# def is_confident_match(query: str, index, model, threshold=0.7):
#     query_vec = model.encode([query])
#     D, I = index.search(np.array(query_vec).reshape(1, -1), k=1)
#     distance = D[0][0]
#     logger.info(f"🔎 Match distance: {distance:.4f} (threshold: {threshold})")
#     return distance < threshold, I[0][0]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    raw_text = update.message.text.strip()
    text = clean_query(raw_text)
    logger.info(f"🔍 Cleaned query: {text}")
    user = update.effective_user.username
    chat = update.effective_chat.title

    logger.info(f"📩 Received: {text} from {update.effective_user.username} in chat {update.effective_chat.title} ({update.effective_chat.id})")

    # confident = False
    # answer_index = None

    # if qa_pairs:
    #     confident, idx = is_confident_match(text, index, model, threshold=CONFIDENCE_THRESHOLD)
    #     answer_index = int(idx) if confident else None

    is_tagged = is_mentioned(update)
    start_time = time.time()
    results = search(text)
    elapsed = time.time() - start_time

    if not results:
        logger.warning("⚠️ No search results found.")
        await update.message.reply_text("❓ Sorry, I couldn’t find a relevant answer. Want to rephrase or clarify?")
        log_staging_qa(question=raw_text, answer=None, user=user, chat=chat)
        return

    top_group = results[0]
    top_score = top_group["score"]
    confident = top_score < CONFIDENCE_THRESHOLD

    should_respond = is_tagged or confident

    if not should_respond:
        return  # stay silent if not tagged and no confident match
    
    messages = [format_result(top_group) + f"\n⏱️ _Response time: {elapsed:.2f}s_" for _ in range(1)]

    for idx, msg in enumerate(messages):
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍", callback_data=f"feedback|{idx}|positive_feedback"),
                InlineKeyboardButton("👎", callback_data=f"feedback|{idx}|negative_feedback")
            ]
        ])
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=buttons)
  

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, index_str, feedback_type = query.data.split("|", 2)

        index = int(index_str)
        question = "(untracked)"
        # answer_index = int(index_str)
        # matched_question = qa_pairs[answer_index]["question"]

        increment_feedback(STAGING_SHEET_URL, STAGING_SHEET_TAB, question, feedback_type)

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ Thanks for your feedback ({'👍' if 'positive' in feedback_type else '👎'})!")
    except Exception as e:
        logger.error(f"❌ Failed to handle feedback: {e}")
        await query.message.reply_text("⚠️ Sorry, something went wrong when processing your feedback.")

# === HANDLERS ===
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_feedback))

app.run_polling()