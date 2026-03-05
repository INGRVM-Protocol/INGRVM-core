import sys
import os
import json
import time
import requests

HUB_IP = "192.168.68.51" # The PC Master Hub (Corrected)
HUB_PORT = 8000
INBOX_FILE = "laptop_inbox.json"

def send_mail(sender, recipient, body):
    """ Sends a high-signal message to the Master Hub. """
    url = f"http://{HUB_IP}:{HUB_PORT}/api/mailroom/send"
    payload = {
        "sender": sender,
        "recipient": recipient,
        "timestamp": time.time(),
        "body": body
    }
    try:
        resp = requests.post(url, json=payload, timeout=2)
        if resp.status_code == 200:
            print(f"✅ Mail dispatched to {recipient}: {body[:30]}...")
        else:
            print(f"❌ Hub rejected mail")
    except Exception as e:
        print(f"⚠️ Could not reach Hub Mailroom: {e}")

def check_mail():
    """ Fetches new mail from the Hub. """
    node_id = os.getenv("CALYX_NODE_ID", "LAPTOP_RELAY")
    url = f"http://{HUB_IP}:{HUB_PORT}/api/mailroom/inbox/{node_id}"
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

def acknowledge_mail():
    """ Task #22: Sends a read receipt to the Hub. """
    node_id = os.getenv("CALYX_NODE_ID", "LAPTOP_RELAY")
    url = f"http://{HUB_IP}:{HUB_PORT}/api/mailroom/ack/{node_id}"
    try:
        resp = requests.post(url, timeout=2)
        if resp.status_code == 200:
            print(f"✅ Read Receipt sent for {node_id}.")
        else:
            print(f"❌ Failed to send receipt: {resp.status_code}")
    except Exception as e:
        print(f"⚠️ Error sending receipt: {e}")

def get_last_ack(target_node_id: str) -> float:
    """ Returns the timestamp of the last ACK from a specific node. """
    url = f"http://{HUB_IP}:{HUB_PORT}/api/mailroom/receipts"
    try:
        resp = requests.get(url, timeout=2)
        if resp.status_code == 200:
            receipts = resp.json()
            return receipts.get(target_node_id, 0.0)
    except: pass
    return 0.0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mailroom.py send <RECIPIENT> 'your message'")
        print("  python mailroom.py check")
        print("  python mailroom.py ack")
    elif sys.argv[1] == "send":
        if len(sys.argv) < 4:
            print("Usage: python mailroom.py send <RECIPIENT> 'your message'")
        else:
            node_id = os.getenv("CALYX_NODE_ID", "UNKNOWN_NODE")
            send_mail(node_id, sys.argv[2], sys.argv[3])
    elif sys.argv[1] == "check":
        check_mail()
    elif sys.argv[1] == "ack":
        acknowledge_mail()
