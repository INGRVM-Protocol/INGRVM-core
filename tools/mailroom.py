import sys
import os
import json
import time
import requests

HUB_IP = "192.168.68.51" # The PC Master Hub (Corrected)
HUB_PORT = 8000
INBOX_FILE = "laptop_inbox.json"

def send_mail(sender, body):
    """ Sends a high-signal message to the Master Hub. """
    url = f"http://{HUB_IP}:{HUB_PORT}/api/mailroom/send"
    payload = {
        "sender": sender,
        "timestamp": time.time(),
        "body": body
    }
    try:
        resp = requests.post(url, json=payload, timeout=2)
        if resp.status_code == 200:
            print(f"✅ Mail dispatched to Hub: {body[:30]}...")
        else:
            print(f"❌ Hub rejected mail (is Task #25 done on PC?)")
    except Exception as e:
        print(f"⚠️ Could not reach Hub Mailroom: {e}")

def check_mail():
    """ Fetches new mail from the Hub. """
    url = f"http://{HUB_IP}:{HUB_PORT}/api/mailroom/inbox/LAPTOP_RELAY"
    try:
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            mail = resp.json()
            with open(INBOX_FILE, "w") as f:
                json.dump(mail, f, indent=4)
            print(f"📩 Synced {len(mail)} letters from Hub.")
        else:
            print(f"❌ Hub Mailroom unreachable.")
    except Exception:
        print("⚠️ Hub Offline. Using last cached inbox.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mailroom.py send 'your message'")
        print("  python mailroom.py check")
    elif sys.argv[1] == "send":
        send_mail("LAPTOP_RELAY", sys.argv[2])
    elif sys.argv[1] == "check":
        check_mail()
