import os
import subprocess
import sys
import json
import socket
import datetime
import requests

def run_cmd(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def update_local_ip():
    """ Detects local IP and updates shard_config_laptop.json """
    try:
        local_ip = socket.gethostbyname(socket.gethostname())
        # Base dir is Calyx/Core/tools/
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(os.path.dirname(base_dir), "shard_config_laptop.json")
        
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                config = json.load(f)
            
            if config.get("lan_ip") != local_ip:
                config["lan_ip"] = local_ip
                with open(config_path, "w") as f:
                    json.dump(config, f, indent=4)
                print(f"📡 Local IP detected and updated: {local_ip}")
            else:
                print(f"📡 Local IP is stable: {local_ip}")
        return local_ip
    except Exception as e:
        print(f"⚠️ Could not update local IP: {e}")
        return None

def sync():
    print("--- 🔄 Calyx Mesh Synchronization (Mission Control) ---")
    
    # 0. Update Local IP
    update_local_ip()

    # 1. Pull from GitHub
    print("\n[1/5] Pulling latest updates from GitHub...")
    pull_log = run_cmd("git pull origin master")
    print(pull_log)

    # 2. Discover Hub via Zeroconf
    print("\n[2/5] Discovering PC Master Hub...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    discovery_path = os.path.join(base_dir, "lan_discovery.py")
    discovery_log = run_cmd(f"python {discovery_path}")
    print(discovery_log)

    # 3. Sync LAN Mailroom
    print("\n[3/5] Checking LAN Mailroom...")
    mailroom_path = os.path.join(base_dir, "mailroom.py")
    mail_log = run_cmd(f"python {mailroom_path} check")
    print(mail_log)

    # 4. Fetch Read Receipts (Task #22)
    print("\n[4/5] Syncing Read Receipts...")
    try:
        hub_ip = os.getenv("CALYX_HUB_IP", "192.168.68.51")
        resp = requests.get(f"http://{hub_ip}:8000/api/mailroom/receipts", timeout=2)
        if resp.status_code == 200:
            receipts = resp.json()
            if receipts:
                print("🧾 READ RECEIPTS:")
                for node, ts in receipts.items():
                    readable_ts = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    print(f"  ✅ {node} read their mail at {readable_ts}")
            else:
                print("  (No receipts found)")
    except Exception:
        print("  ⚠️ Could not sync receipts (Hub offline?)")

    # 5. Read the Mail and Print High-Signal Summary
    print("\n[5/5] Checking Inbox...")
    inbox_path = os.path.join(os.path.dirname(base_dir), "laptop_inbox.json")
    # Fallback to root for older versions
    root_inbox = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(base_dir))), "laptop_inbox.json")
    target_inbox = inbox_path if os.path.exists(inbox_path) else root_inbox

    if os.path.exists(target_inbox):
        with open(target_inbox, "r") as f:
            try:
                inbox = json.load(f)
                if inbox:
                    print("\n📩 LATEST MAIL:")
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
    
    print("\nVerification Complete. Mesh is in sync.")

if __name__ == "__main__":
    sync()
