import os
import requests
from flask import Flask, request
from groq import Groq

app = Flask(__name__)

# Fetch environment variables from Vercel
TELEGRAM_TOKEN = (os.environ.get("TELEGRAM_TOKEN") or "").strip().strip('"').strip("'")
GROQ_API_KEY = (os.environ.get("GROQ_API_KEY") or "").strip().strip('"').strip("'")

# Parse allowed Telegram IDs from ALLOWED_USERS env variable (comma-separated)
raw_allowed = os.environ.get("ALLOWED_USERS", "")
ALLOWED_USER_IDS = [int(i.strip()) for i in raw_allowed.split(",") if i.strip().isdigit()]

# Initialize Groq client with a 15-second timeout
client = Groq(api_key=GROQ_API_KEY, timeout=15.0) if GROQ_API_KEY else None

# In-memory dictionary for short-term chat context storage
chat_histories = {}

def send_telegram_message(chat_id, text):
    """Chunk and send long outputs to prevent Telegram 4000 character limit failures."""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chunk in [text[i:i + 3900] for i in range(0, len(text), 3900)]:
        requests.post(url, json={"chat_id": chat_id, "text": chunk})

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json() or {}
        
        if "message" in data and "text" in data["message"]:
            chat_id = data["message"]["chat"]["id"]
            user_id = data["message"]["from"]["id"]
            user_text = data["message"]["text"]
            
            # Security Check: Whitelist verification
            if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
                send_telegram_message(chat_id, "Access denied. AXIOM is private.")
                return "OK", 200
            
            # Reset history on /start command
            if user_text.strip().lower() in ["/start", "start"]:
                chat_histories[chat_id] = []
                send_telegram_message(chat_id, "Hello! I am AXIOM, ready to assist.")
                return "OK", 200
            
            if not client:
                send_telegram_message(chat_id, "Error: GROQ_API_KEY missing.")
                return "OK", 200

            if chat_id not in chat_histories:
                chat_histories[chat_id] = []

            # Append current user prompt
            chat_histories[chat_id].append({"role": "user", "content": user_text})
            
            # Keep context trimmed to prevent exceeding token window or timing out
            trimmed_history = []
            total_chars = 0
            for msg in reversed(chat_histories[chat_id]):
                if total_chars + len(msg["content"]) > 3000:
                    break
                trimmed_history.insert(0, msg)
                total_chars += len(msg["content"])

            messages_payload = [
                {"role": "system", "content": "You are AXIOM, a helpful AI assistant. Be concise and direct."}
            ] + trimmed_history

            try:
                # Active high-speed Groq model
                chat_completion = client.chat.completions.create(
                    messages=messages_payload,
                    model="llama-3.1-8b-instant",
                    max_tokens=1000
                )
                bot_reply = chat_completion.choices[0].message.content
                
                chat_histories[chat_id].append({"role": "assistant", "content": bot_reply})
                send_telegram_message(chat_id, bot_reply)
            except Exception as e:
                send_telegram_message(chat_id, f"AXIOM Error: {e}")

        return "OK", 200
    
    return "AXIOM Bot is running!", 200

if __name__ == "__main__":
    app.run()
