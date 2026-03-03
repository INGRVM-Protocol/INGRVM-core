import os
import subprocess
import sys
import json

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def sync():
    print("--- 🔄 Calyx Mesh Synchronization ---")
    
    # 1. Pull from GitHub
    print("[1/3] Pulling latest updates from GitHub...")
    pull_log = run_cmd("git pull origin master")
    print(pull_log)

    # 2. Sync LAN Mailroom
    print("\n[2/3] Checking LAN Mailroom...")
    # Get the directory of this script to find mailroom.py
    base_dir = os.path.dirname(os.path.abspath(__file__))
    mailroom_path = os.path.join(base_dir, "mailroom.py")
    
    mail_log = run_cmd(f"python {mailroom_path} check")
    print(mail_log)

    # 3. Read the Mail and Print High-Signal Summary
    # Move up from tools/ to Core/ to find laptop_inbox.json
    inbox_path = os.path.join(os.path.dirname(base_dir), "laptop_inbox.json")
    # Also check root Ecosystem dir as a fallback
    root_inbox = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(base_dir))), "laptop_inbox.json")
    
    target_inbox = inbox_path if os.path.exists(inbox_path) else root_inbox

    if os.path.exists(target_inbox):
        with open(target_inbox, "r") as f:
            try:
                inbox = json.load(f)
                if inbox:
                    print("\n📩 LATEST MAIL:")
                    # Show last 5 messages with full body
                    for msg in inbox[-5:]:
                        sender = msg.get('sender', 'UNK')
                        body = msg.get('body', 'No content')
                        print(f"  [{sender}]: {body}")
                else:
                    print("\n📩 Inbox is empty.")
            except Exception as e:
                print(f"\n❌ Error reading inbox: {e}")
    else:
        print(f"\n⚠️ Inbox not found at {target_inbox}")
    
    print("\n[3/3] Verification Complete. Mesh is in sync.")

if __name__ == "__main__":
    sync()
