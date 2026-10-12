import os
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
GROQ_API_KEY = (os.environ.get("GROQ_API_KEY") or "").strip().strip('"').strip("'")

raw_allowed = os.environ.get("ALLOWED_USERS", "")
ALLOWED_USER_IDS = [int(i.strip()) for i in raw_allowed.split(",") if i.strip().isdigit()]

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Temporary memory storage (chat_id -> list of messages)
chat_histories = {}

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
            user_id = data["message"]["from"]["id"]
            user_text = data["message"]["text"]
            
            if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
                send_telegram_message(chat_id, "Access denied. AXIOM is private.")
                return "OK", 200
            
            if user_text.strip().lower() in ["/start", "start"]:
                chat_histories[chat_id] = []
                send_telegram_message(chat_id, "Hello! I am AXIOM, your AI assistant with memory.")
                return "OK", 200
            
            if not client:
                send_telegram_message(chat_id, "Error: GROQ_API_KEY missing.")
                return "OK", 200

            # Initialize history for this chat if needed
            if chat_id not in chat_histories:
                chat_histories[chat_id] = []

            # Append user message
            chat_histories[chat_id].append({"role": "user", "content": user_text})
            
            # Keep only the last 10 messages to avoid token overload
            chat_histories[chat_id] = chat_histories[chat_id][-10:]

            try:
                chat_completion = client.chat.completions.create(
                    messages=chat_histories[chat_id],
                    model="openai/gpt-oss-120b",
                )
                bot_reply = chat_completion.choices[0].message.content
                
                # Append assistant reply to history
                chat_histories[chat_id].append({"role": "assistant", "content": bot_reply})
                
                send_telegram_message(chat_id, bot_reply)
            except Exception as e:
                send_telegram_message(chat_id, f"Groq Error: {e}")

        return "OK", 200
    
    return "Bot is running!", 200

if __name__ == "__main__":
    app.run()
