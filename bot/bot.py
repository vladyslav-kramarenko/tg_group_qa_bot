from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes

import os
import logging
import sys
import time
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from config.config_loader import load_config_yaml
from sheets.update_feedback import increment_feedback
from sheets.staging_qa import log_staging_qa
from sheets.user_tracker import log_user_if_new, get_email_by_username, get_email_by_user_id
from search import search, format_result
from zammad.zammad_client import create_ticket

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

# === TELEGRAM BOT ===
app = ApplicationBuilder().token(BOT_TOKEN).build()

def clean_query(text: str) -> str:
    return text.replace(f"@{BOT_USERNAME}", "").strip()

def is_mentioned(update: Update) -> bool:
    if not update.message or not update.message.text:
        return False
    return f"@{BOT_USERNAME.lower()}" in update.message.text.lower()

def build_user_info(user) -> dict:
    username = user.username or f"user{user.id}"

    email = (
        get_email_by_username(username)
        or get_email_by_user_id(user.id)
        or f"{username}@telegram.bot"
    )

    logger.debug(f"📧 Using email for {username} (ID {user.id}): {email}")

    return {
        "email": email,
        "firstname": user.first_name or "",
        "lastname": user.last_name or ""
    }

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    raw_text = update.message.text.strip()
    text = clean_query(raw_text)
    user = update.effective_user
    chat = update.effective_chat.title

    logger.info(f"📩 Received: {raw_text} from {user.username} in chat {chat} ({update.effective_chat.id})")

    is_tagged = is_mentioned(update)
    start_time = time.time()
    results = search(text)
    elapsed = time.time() - start_time

    # Track user every time
    log_user_if_new(user)

    if not results:
        logger.warning("⚠️ No search results found.")
        if is_tagged:
            await update.message.reply_text("❓ Sorry, I couldn’t find a relevant answer. Want to rephrase or clarify?")
        log_staging_qa(question=raw_text, answer=None, user=user.username, chat=chat)

        # ⛑ Send to Zammad as unanswered
        user_info = build_user_info(user)
        create_ticket(
            subject=f"[Unanswered] {text[:40]}",
            body=f"*Question:* {text}\n\n_No answer found._",
            user_info=user_info
        )
        return

    top_group = results[0]
    top_score = top_group["score"]
    confident = top_score < CONFIDENCE_THRESHOLD

    if not (is_tagged or confident):
        return

    formatted = format_result(top_group) + f"\n⏱️ _Response time: {elapsed:.2f}s_"

    # 📨 Log to Zammad
    user_info = build_user_info(user)
    create_ticket(
        subject=f"[QA] {text[:40]}",
        body=f"*Question:* {text}\n\n*Answer:*\n{formatted}",
        user_info=user_info
    )

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👍", callback_data="feedback|0|positive_feedback"),
            InlineKeyboardButton("👎", callback_data="feedback|0|negative_feedback")
        ]
    ])
    await update.message.reply_text(formatted, parse_mode="Markdown", reply_markup=buttons)

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    try:
        _, index_str, feedback_type = query.data.split("|", 2)
        increment_feedback(STAGING_SHEET_URL, STAGING_SHEET_TAB, "(untracked)", feedback_type)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ Thanks for your feedback ({'👍' if 'positive' in feedback_type else '👎'})!")
    except Exception as e:
        logger.error(f"❌ Failed to handle feedback: {e}")
        await query.message.reply_text("⚠️ Something went wrong recording your feedback.")

# === START BOT ===
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_feedback))
app.run_polling()
