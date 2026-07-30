from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
from google import genai

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

def send_telegram_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        urllib.request.urlopen(req)
    except Exception as e:
        print("Error sending message to Telegram:", e)

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length)

        try:
            update = json.loads(post_data.decode("utf-8"))

            if "message" in update and "text" in update["message"]:
                chat_id = update["message"]["chat"]["id"]
                user_text = update["message"]["text"]

                # Handle start command vs standard message
                if user_text.strip().lower() in ["/start", "start"]:
                    send_telegram_message(chat_id, "Hello! I am your 24/7 AI bot.")
                else:
                    try:
                        client = genai.Client(api_key=GEMINI_API_KEY)
                        response = client.models.generate_content(
                            model="gemini-2.5-flash",
                            contents=user_text
                        )
                        reply_text = response.text
                    except Exception as e:
                        reply_text = f"Gemini Error: {str(e)}"

                    send_telegram_message(chat_id, reply_text)

        except Exception as e:
            print("Handler error:", e)

        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"OK")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot service running.")
