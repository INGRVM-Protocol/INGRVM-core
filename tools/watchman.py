import time
import requests
import json
import os

HUB_URL = "http://localhost:8000/api/mailroom/inbox/LAPTOP_RELAY"
LAST_CHECK_FILE = "watchman_state.json"

def get_last_timestamp():
    if os.path.exists(LAST_CHECK_FILE):
        with open(LAST_CHECK_FILE, "r") as f:
            return json.load(f).get("last_ts", 0)
    return 0

def save_last_timestamp(ts):
    with open(LAST_CHECK_FILE, "w") as f:
        json.dump({"last_ts": ts}, f)

def poll():
    print("🔭 Mailroom Watchman active. Monitoring for Laptop messages...")
    last_ts = get_last_timestamp()
    
    while True:
        try:
            resp = requests.get(HUB_URL, timeout=2)
            if resp.status_code == 200:
                letters = resp.json()
                for l in letters:
                    if l['timestamp'] > last_ts:
                        print("
" + "="*50)
                        print(f"🚨 ALERT: NEW MESSAGE FROM {l['sender']}")
                        print(f"BODY: {l['body']}")
                        print("="*50 + "
")
                        last_ts = l['timestamp']
                        save_last_timestamp(last_ts)
            
        except Exception as e:
            pass # Hub might be restarting
            
        time.sleep(2)

if __name__ == "__main__":
    poll()
