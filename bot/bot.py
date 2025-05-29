from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from config.config_loader import load_config_yaml
from sheets.qa_loader import load_qa_from_google_sheet
from sheets.update_feedback import increment_feedback
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import os
import logging
from sheets.staging_qa import log_staging_qa

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
config = load_config_yaml("config.yaml")
CONFIDENCE_THRESHOLD = float(config.get("confidence_threshold", 0.75))

staging_cfg = config.get("data_sources", {}).get("google_sheets", {}).get("staging", {})
STAGING_SHEET_URL = staging_cfg.get("url")
STAGING_SHEET_TAB = staging_cfg.get("tab", "staging_qa")

# === LOAD Q&A DATA FROM GOOGLE SHEET ===
qa_cfg = config.get("data_sources", {}).get("google_sheets", {}).get("qa", {})
QA_SHEET_URL = qa_cfg.get("url")
QA_SHEET_TAB = qa_cfg.get("tab", "QandA")
if not QA_SHEET_URL:
    raise ValueError("❌ Sheet URL not found in config.yaml under data_sources → google_sheets → qa → url")
qa_pairs = load_qa_from_google_sheet(QA_SHEET_URL, QA_SHEET_TAB)

if not qa_pairs:
    logger.warning("⚠️ No Q&A data loaded — bot will not respond meaningfully.")

# === EMBEDDINGS + FAISS ===
model = SentenceTransformer("all-MiniLM-L6-v2")
questions = [q["question"] for q in qa_pairs]
embeddings = model.encode(questions)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(np.array(embeddings))

# === TELEGRAM BOT ===
app = ApplicationBuilder().token(BOT_TOKEN).build()

def is_mentioned(update: Update) -> bool:
    if not update.message or not update.message.text:
        return False
    return f"@{BOT_USERNAME.lower()}" in update.message.text.lower()

def is_confident_match(query: str, index, model, threshold=0.7):
    query_vec = model.encode([query])
    D, I = index.search(np.array(query_vec).reshape(1, -1), k=1)
    distance = D[0][0]
    logger.info(f"🔎 Match distance: {distance:.4f} (threshold: {threshold})")
    return distance < threshold, I[0][0]

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    logger.info(f"📩 Received: {text} from {update.effective_user.username} in chat {update.effective_chat.title} ({update.effective_chat.id})")

    confident = False
    answer_index = None

    if qa_pairs:
        confident, idx = is_confident_match(text, index, model, threshold=CONFIDENCE_THRESHOLD)
        answer_index = int(idx) if confident else None

    is_tagged = is_mentioned(update)
    should_respond = is_tagged or confident

    if not should_respond:
        return  # stay silent if not tagged and no confident match

    if confident and answer_index is not None:
        best_answer = qa_pairs[answer_index]["answer"]
        matched_question = qa_pairs[answer_index]["question"]

        response = f"💬 *Answer:*\n{best_answer}"
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("👍", callback_data=f"feedback|{answer_index}|positive_feedback"),
                InlineKeyboardButton("👎", callback_data=f"feedback|{answer_index}|negative_feedback")
            ]
        ])
        await update.message.reply_text(response, parse_mode="Markdown", reply_markup=buttons)
    else:
        await update.message.reply_text(
            "🤔 I appreciate the tag, but I’m not sure how to help with that yet. Could you rephrase or provide more detail?"
        )
        # 📝 Log the tagged but unmatched question
        log_staging_qa(
            question=text,
            answer=None,
            user=update.effective_user.username,
            chat=update.effective_chat.title
        )

async def handle_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    try:
        _, index_str, feedback_type = query.data.split("|", 2)
        answer_index = int(index_str)
        matched_question = qa_pairs[answer_index]["question"]

        increment_feedback(SHEET_URL, SHEET_TAB, matched_question, feedback_type)

        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(f"✅ Thanks for your feedback ({'👍' if 'positive' in feedback_type else '👎'})!")
    except Exception as e:
        logger.error(f"❌ Failed to handle feedback: {e}")
        await query.message.reply_text("⚠️ Sorry, something went wrong when processing your feedback.")

# === HANDLERS ===
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_feedback))

app.run_polling()