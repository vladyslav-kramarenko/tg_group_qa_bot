import os
import json  # ✅ Needed for debug log
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ZAMMAD_API = os.getenv("ZAMMAD_API_URL", "http://localhost:8080/api/v1")
ZAMMAD_TOKEN = os.getenv("ZAMMAD_API_TOKEN")

HEADERS = {
    "Authorization": f"Token token={ZAMMAD_TOKEN}",
    "Content-Type": "application/json"
}

def find_user_by_email(email: str):
    try:
        res = requests.get(f"{ZAMMAD_API}/users/search?query={email}", headers=HEADERS)
        res.raise_for_status()
        users = res.json()
        return users[0] if users else None
    except Exception as e:
        logger.error(f"❌ Failed to search user in Zammad: {e}")
        return None

def create_user(email: str, firstname: str = "", lastname: str = ""):
    try:
        payload = {
            "email": email,
            "firstname": firstname,
            "lastname": lastname,
            "login": email
        }
        print("==== ZAMMAD PAYLOAD ====")
        print(json.dumps(payload, indent=2))
        print("========================")
        res = requests.post(f"{ZAMMAD_API}/users", json=payload, headers=HEADERS)
        res.raise_for_status()
        logger.info(f"👤 Created Zammad user: {email}")
        return res.json()
    except Exception as e:
        logger.error(f"❌ Failed to create user in Zammad: {e}")
        return None

def ensure_user(email: str, firstname: str, lastname: str):
    email = email.lower().strip()
    logger.debug(f"🔍 Ensuring user exists: {email} ({firstname} {lastname})")
    user = find_user_by_email(email)
    if user:
        logger.debug(f"✅ Found existing Zammad user: {user['id']} ({email})")
    else:
        logger.debug(f"👤 No user found, creating new user: {email}")
    return user or create_user(email, firstname, lastname)

def create_ticket(subject: str, body: str, user_info: dict):
    user = ensure_user(user_info["email"], user_info.get("firstname", ""), user_info.get("lastname", ""))
    if not user:
        logger.warning("⚠️ Ticket skipped — user not found/created")
        return

    payload = {
        "title": subject,
        "group": "Users",  # ⚠️ Make sure this group exists in Zammad
        "customer_id": user["id"],
        "article": {
            "subject": subject,
            "body": body,
            "type": "note",
            "internal": False
        }
    }

    try:
        logger.debug(f"🧾 Zammad payload: {json.dumps(payload, indent=2)}")
        res = requests.post(f"{ZAMMAD_API}/tickets", json=payload, headers=HEADERS)
        res.raise_for_status()
        logger.info(f"🎟️ Created Zammad ticket: {res.json().get('id')}")
    except requests.exceptions.HTTPError as e:
        if e.response is not None:
            logger.error(f"❌ Zammad error details: {e.response.text}")
        logger.error(f"❌ Failed to create Zammad ticket: {e}")
    
def update_ticket_feedback(ticket_id: int, feedback: str):
    """
    Updates the Zammad ticket with answer_feedback custom field.
    """
    try:
        payload = {
            "custom_fields": {
                "answer_feedback": feedback
            }
        }
        res = requests.put(f"{ZAMMAD_API}/tickets/{ticket_id}", json=payload, headers=HEADERS)
        res.raise_for_status()
        logger.info(f"✅ Ticket {ticket_id} updated with feedback: {feedback}")
    except Exception as e:
        logger.error(f"❌ Failed to update ticket feedback: {e}")