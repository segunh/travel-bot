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

# Store user states in memory
user_states = {}

@app.route("/test_firebase")
def test_firebase():
    try:
        test_ref = db.collection("travel_users").document("test_doc")
        test_ref.set({"status": "connected"})
        return "✅ Firestore write success!"
    except Exception as e:
        return f"❌ Firestore error: {e}"


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
    print("Incoming:", data)

    try:
        changes = data.get("entry", [])[0].get("changes", [])[0].get("value", {})
        if "messages" not in changes:
            print("No 'messages' key — likely a status update.")
            return "ok", 200

        message = changes["messages"][0]
        user_number = message["from"]
        user_text = message.get("text", {}).get("body", "").strip()
        print(f"Message from {user_number}: {user_text}")

        # Get or initialize state
        state = user_states.get(user_number, {"step": "start"})

        # Conversation flow
        if state["step"] == "start":
            send_message(user_number, "👋 Hello! Welcome to Libra Travels ✈️\nWhat’s your full name?")
            state["step"] = "name"

        elif state["step"] == "name":
            state["name"] = user_text
            send_message(user_number, f"Nice to meet you, {user_text}! 🌍 Where would you like to travel?")
            state["step"] = "destination"

        elif state["step"] == "destination":
            state["destination"] = user_text
            send_message(user_number, "Great choice! 🗓️ When would you like to travel? (e.g. 2025-11-20)")
            state["step"] = "date"

        elif state["step"] == "date":
            state["date"] = user_text
            save_to_firestore(user_number, state)
            send_message(
                user_number,
                f"✅ Awesome, {state['name']}! Your trip to {state['destination']} on {state['date']} has been recorded.\nWe’ll contact you soon with exciting offers! ✈️"
            )
            # Reset conversation
            user_states.pop(user_number, None)
            return "ok", 200

        user_states[user_number] = state

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
    response = requests.post(url, headers=headers, json=data)
    print("Send message response:", response.text)


def save_to_firestore(user_number, data):
    db.collection("travel_bookings").document(user_number).set({
        "name": data.get("name"),
        "destination": data.get("destination"),
        "date": data.get("date")
    })
    print(f"✅ Saved {user_number} to Firebase")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
