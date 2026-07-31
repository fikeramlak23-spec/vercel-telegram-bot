import os
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
GROQ_API_KEY = (os.environ.get("GROQ_API_KEY") or "").strip().strip('"').strip("'")

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

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
                send_telegram_message(chat_id, "Hello! I am your 24/7 AI bot powered by Groq.")
                return "OK", 200
            
            if not client:
                send_telegram_message(chat_id, "Error: GROQ_API_KEY is missing in environment variables.")
                return "OK", 200

            try:
                chat_completion = client.chat.completions.create(
                    messages=[{"role": "user", "content": user_text}],
                    model="llama-3.3-70b-versatile",
                )
                send_telegram_message(chat_id, chat_completion.choices[0].message.content)
            except Exception as e:
                send_telegram_message(chat_id, f"Groq Error: {e}")

        return "OK", 200
    
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run()
