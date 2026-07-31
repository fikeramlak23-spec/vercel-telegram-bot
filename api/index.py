\import os
from flask import Flask, request
import google.generativeai as genai

app = Flask(__name__)

TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
GEMINI_API_KEY = (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip().strip('"').strip("'")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

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
            
            if not GEMINI_API_KEY:
                send_telegram_message(chat_id, "Error: GEMINI_API_KEY missing.")
                return "OK", 200

            try:
                model = genai.GenerativeModel("gemini-2.0-flash")
                response = model.generate_content(user_text)
                send_telegram_message(chat_id, response.text)
            except Exception as e:
                send_telegram_message(chat_id, f"Gemini Error: {e}")

        return "OK", 200
    
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run()
