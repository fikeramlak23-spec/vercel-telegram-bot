import os
import requests
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
GROQ_API_KEY = (os.environ.get("GROQ_API_KEY") or "").strip().strip('"').strip("'")

raw_allowed = os.environ.get("ALLOWED_USERS", "")
ALLOWED_USER_IDS = [int(i.strip()) for i in raw_allowed.split(",") if i.strip().isdigit()]

client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

chat_histories = {}

def send_telegram_message(chat_id, text):
    """Splits messages longer than 4000 characters to prevent Telegram API errors."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    
    # Split long responses into chunks of 4000 characters
    for chunk in [text[i:i + 4000] for i in range(0, len(text), 4000)]:
        payload = {"chat_id": chat_id, "text": chunk}
        requests.post(url, json=payload)

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json() or {}
        
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            user_id = data["message"]["from"]["id"]
            user_text = data["message"]["text"]
            
            # Whitelist check
            if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
                send_telegram_message(chat_id, "Access denied. AXIOM is private.")
                return "OK", 200
            
            if user_text.strip().lower() in ["/start", "start"]:
                chat_histories[chat_id] = []
                send_telegram_message(chat_id, "Hello! I am AXIOM, ready to assist.")
                return "OK", 200
            
            if not client:
                send_telegram_message(chat_id, "Error: GROQ_API_KEY missing.")
                return "OK", 200

            if chat_id not in chat_histories:
                chat_histories[chat_id] = []

            # Append user message
            chat_histories[chat_id].append({"role": "user", "content": user_text})
            
            # Keep history under ~3000 characters total to avoid exceeding token/timeout limits
            trimmed_history = []
            total_chars = 0
            for msg in reversed(chat_histories[chat_id]):
                if total_chars + len(msg["content"]) > 3000:
                    break
                trimmed_history.insert(0, msg)
                total_chars += len(msg["content"])

            # System prompt to ensure concise responses within Vercel's execution window
            messages_payload = [
                {"role": "system", "content": "You are AXIOM, a helpful AI assistant. Provide direct, concise responses without unnecessary fluff."}
            ] + trimmed_history

            try:
                chat_completion = client.chat.completions.create(
                    messages=messages_payload,
                    model="openai/gpt-oss-120b",
                    max_tokens=1024  # Prevents long generations from timing out
                )
                bot_reply = chat_completion.choices[0].message.content
                
                # Save reply to history
                chat_histories[chat_id].append({"role": "assistant", "content": bot_reply})
                
                send_telegram_message(chat_id, bot_reply)
            except Exception as e:
                send_telegram_message(chat_id, f"Error: {e}")

        return "OK", 200
    
    return "AXIOM Bot is running!", 200

if __name__ == "__main__":
    app.run()
