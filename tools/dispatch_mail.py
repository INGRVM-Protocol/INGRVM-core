import os
import sys
import time
from mailroom import get_last_ack

def dispatch(target_node, content):
    """
    Writes a markdown letter to the Mailroom directory. 
    If target has NOT sent an ACK since the file was last updated, APPEND.
    Otherwise, OVERWRITE.
    """
    # 1. Resolve Path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    mailroom_dir = os.path.join(base_dir, "Framework", "Mailroom")
    
    file_name = f"MAIL_TO_{target_node}.md"
    file_path = os.path.join(mailroom_dir, file_name)
    
    if not os.path.exists(mailroom_dir):
        os.makedirs(mailroom_dir, exist_ok=True)

    # 2. Check for ACK
    last_ack = get_last_ack(target_node)
    
    file_exists = os.path.exists(file_path)
    last_mod = os.path.getmtime(file_path) if file_exists else 0
    
    # If the file is newer than the last ACK, we append to avoid overwriting unread mail.
    mode = "a" if (file_exists and last_mod > last_ack) else "w"
    
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    header = f"\n\n--- 📥 New Update: {timestamp} ---\n" if mode == "a" else ""
    
    # 3. Add recipient-specific header for new files
    if mode == "w":
        content = f"# Mail to {target_node}\n\n" + content

    with open(file_path, mode, encoding="utf-8") as f:
        f.write(header + content)
    
    status = "APPENDED to unread mail" if mode == "a" else "OVERWROTE (previous mail was read)"
    print(f"✅ Mail {status} at {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python dispatch_mail.py <TARGET_NODE> <CONTENT_STRING>")
        print("Nodes: PC_MASTER, LAPTOP_RELAY, MOBILE_EDGE")
    else:
        dispatch(sys.argv[1], sys.argv[2])
