from flask import Flask, request
import requests, os, firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# WhatsApp API credentials
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
ACCESS_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")

# Initialize Firebase
cred = credentials.Certificate("firebase_config.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Store temporary user state
user_states = {}

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def receive_message():
    data = request.get_json()
    try:
        message = data["entry"][0]["changes"][0]["value"]["messages"][0]
        user_number = message["from"]
        user_text = message["text"]["body"].strip()

        # Get user's current state
        state = user_states.get(user_number, "start")

        if state == "start":
            send_message(user_number, "👋 Hello! Welcome to Libra Travels ✈️\nLet's help plan your trip.\nWhat is your full name?")
            user_states[user_number] = "ask_name"

        elif state == "ask_name":
            user_states[user_number] = {"name": user_text}
            send_message(user_number, "Great, {0}! 🌍 What’s your travel destination?".format(user_text))
            user_states[user_number]["state"] = "ask_destination"

        elif isinstance(user_states[user_number], dict) and user_states[user_number].get("state") == "ask_destination":
            user_states[user_number]["destination"] = user_text
            user_states[user_number]["state"] = "ask_date"
            send_message(user_number, "Got it! 📅 When would you like to travel? (e.g. 2025-11-15)")

        elif isinstance(user_states[user_number], dict) and user_states[user_number].get("state") == "ask_date":
            user_states[user_number]["date"] = user_text
            data_to_save = user_states[user_number]
            save_to_firestore(user_number, data_to_save)
            send_message(user_number, "✅ Perfect! We’ve saved your booking request.\nWe'll contact you shortly with travel package options.")
            user_states.pop(user_number, None)

        else:
            send_message(user_number, "Type 'hello' to start planning your next trip 🌴")

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


def save_to_firestore(user_number, data):
    db.collection("travel_bookings").document(user_number).set({
        "name": data.get("name"),
        "destination": data.get("destination"),
        "date": data.get("date")
    })
    print("Saved to Firebase ✅")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
