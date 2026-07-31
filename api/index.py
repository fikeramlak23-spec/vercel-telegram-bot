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

            # Valid model fallbacks in case one hits rate limits
            models_to_try = ["gemini-2.0-flash", "gemini-2.0-flash-lite"]
            response_text = None
            last_error = None

            for model_name in models_to_try:
                try:
                    res = client.models.generate_content(
                        model=model_name,
                        contents=user_text,
                    )
                    response_text = res.text
                    if response_text:
                        break
                except Exception as e:
                    last_error = e

            if response_text:
                send_telegram_message(chat_id, response_text)
            else:
                send_telegram_message(chat_id, f"Gemini Error: {last_error}")

        return "OK", 200
    
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run()
