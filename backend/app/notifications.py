import os
from twilio.rest import Client
from firebase_admin import messaging

TWILIO_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE = os.getenv("TWILIO_PHONE_NUMBER")

def send_notification(category: str, person_id: int = None):
    if category == "Random":
        # Send SMS alert
        if TWILIO_SID and TWILIO_TOKEN:
            client = Client(TWILIO_SID, TWILIO_TOKEN)
            message = client.messages.create(
                body="Unknown person detected!",
                from_=TWILIO_PHONE,
                to="+your_phone_number"  # Change to real
            )
            print(f"SMS sent: {message.sid}")
    
    # Push via Firebase (mock)
    print(f"Notification for {category} (person {person_id})")