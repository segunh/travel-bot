from flask import Flask, request
import requests
import os
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    else:
        return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()

    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        user_number = message["from"]
        user_text = message["text"]["body"].lower()

        # Basic travel bot logic
        if "hello" in user_text or "hi" in user_text:
            reply = "🌍 Welcome to Libra Travels! ✈️\n\nChoose an option:\n1️⃣ View travel deals\n2️⃣ Book a trip\n3️⃣ Talk to an agent"
        elif user_text == "1":
            reply = "Here are our top deals this week 🌴:\n- Dubai: $899\n- Paris: $999\n- Nairobi: $650\n\nReply 'book' to reserve a spot!"
        elif user_text == "2" or "book" in user_text:
            reply = "Awesome! Please share your destination and travel date 📅."
        else:
            reply = "I'm here to assist you. Type 'hello' to start 😊"

        send_message(user_number, reply)
    except Exception as e:
        print("Error:", e)
    return "ok", 200

def send_message(to, message):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    requests.post(url, headers=headers, json=data)

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000)
