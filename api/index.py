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
secretary_modes = {}

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    for chunk in [text[i:i + 4000] for i in range(0, len(text), 4000)]:
        payload = {"chat_id": chat_id, "text": chunk}
        requests.post(url, json=payload)

@app.route("/", methods=["GET", "POST"])
def webhook():
    if request.method == "POST":
        data = request.get_json() or {}
        
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            
            if ALLOWED_USER_IDS and user_id not in ALLOWED_USER_IDS:
                send_telegram_message(chat_id, "Access denied. AXIOM is private.")
                return "OK", 200
            
            user_text = msg.get("text", "")
            
            if user_text.strip().lower() in ["/start", "start"]:
                chat_histories[chat_id] = []
                secretary_modes[chat_id] = False
                send_telegram_message(chat_id, "Hello! I am AXIOM. Send /secretary to toggle Secretary Mode or upload a .txt file!")
                return "OK", 200
            
            if user_text.strip().lower() == "/secretary":
                current_mode = secretary_modes.get(chat_id, False)
                secretary_modes[chat_id] = not current_mode
                status = "ACTIVATED 📋" if secretary_modes[chat_id] else "DEACTIVATED"
                send_telegram_message(chat_id, f"Secretary Mode is now {status}.")
                return "OK", 200

            if "document" in msg:
                doc = msg["document"]
                if doc.get("file_name", "").endswith(".txt"):
                    file_id = doc["file_id"]
                    file_info = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile?file_id={file_id}").json()
                    file_path = file_info.get("result", {}).get("file_path")
                    if file_path:
                        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"
                        file_content = requests.get(file_url).text
                        caption = msg.get("caption", "Analyze and summarize this document.")
                        user_text = f"[Uploaded File Content]:\n{file_content}\n\n[Instruction]: {caption}"
                else:
                    send_telegram_message(chat_id, "Please upload a valid .txt file.")
                    return "OK", 200

            if not user_text:
                return "OK", 200
            
            if not client:
                send_telegram_message(chat_id, "Error: GROQ_API_KEY missing.")
                return "OK", 200

            if chat_id not in chat_histories:
                chat_histories[chat_id] = []

            chat_histories[chat_id].append({"role": "user", "content": user_text})
            
            trimmed_history = []
            total_chars = 0
            for msg_item in reversed(chat_histories[chat_id]):
                if total_chars + len(msg_item["content"]) > 3000:
                    break
                trimmed_history.insert(0, msg_item)
                total_chars += len(msg_item["content"])

            is_secretary = secretary_modes.get(chat_id, False)
            system_instruction = (
                "You are AXIOM's Secretary Mode. Focus on organizing tasks, summarizing text, and drafting professional messages."
                if is_secretary else
                "You are AXIOM, a helpful AI assistant. Be direct and concise."
            )

            messages_payload = [
                {"role": "system", "content": system_instruction}
            ] + trimmed_history

            try:
                chat_completion = client.chat.completions.create(
                    messages=messages_payload,
                    model="openai/gpt-oss-120b",
                    max_tokens=1024
                )
                bot_reply = chat_completion.choices[0].message.content
                chat_histories[chat_id].append({"role": "assistant", "content": bot_reply})
                send_telegram_message(chat_id, bot_reply)
            except Exception as e:
                send_telegram_message(chat_id, f"Error: {e}")

        return "OK", 200
    
    return "AXIOM Bot is running!", 200

if __name__ == "__main__":
    app.run()
