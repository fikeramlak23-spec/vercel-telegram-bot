import os
import requests
from flask import Flask, request
from google import genai

app = Flask(__name__)

TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or "").strip().strip('"').strip("'")

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Error sending message: {e}")

@app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
@app.route("/<path:path>", methods=["GET", "POST"])
def webhook(path):
    if request.method == "GET":
        return "Bot is active!"

    update = request.get_json(silent=True)
    if not update or "message" not in update:
        return "OK", 200

    chat_id = update["message"]["chat"]["id"]
    user_text = update["message"].get("text", "")

    if user_text.strip().lower() in ["/start", "start"]:
        send_telegram_message(chat_id, "Hello! I am your 24/7 AI bot.")
    elif user_text:
        # Debugging: show key length and start/end characters
        key_len = len(GEMINI_API_KEY)
        key_preview = f"{GEMINI_API_KEY[:4]}...{GEMINI_API_KEY[-4:]}" if key_len > 8 else "EMPTY/TOO_SHORT"
        
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=user_text
            )
            reply_text = response.text
        except Exception as e:
            reply_text = f"Key loaded: {key_preview} (Length: {key_len})\nError: {str(e)}"

        send_telegram_message(chat_id, reply_text)

    return "OK", 200
