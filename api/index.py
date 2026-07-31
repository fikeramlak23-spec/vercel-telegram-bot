import os
from flask import Flask, request
from google import genai

app = Flask(__name__)

TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

def send_telegram_message(chat_id, text):
    import requests
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json() or {}
        
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            user_text = data["message"]["text"]
            
            if user_text.strip().lower() in ["/start", "start"]:
                send_telegram_message(chat_id, "Hello! I am your 24/7 AI bot.")
                return "OK", 200
            
            if not client:
                send_telegram_message(chat_id, "Error: GEMINI_API_KEY is missing in environment variables.")
                return "OK", 200

            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash-lite",
                    contents=user_text,
                )
                send_telegram_message(chat_id, response.text)
            except Exception as e:
                send_telegram_message(chat_id, f"Gemini Error: {e}")

        return "OK", 200
    
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run()
