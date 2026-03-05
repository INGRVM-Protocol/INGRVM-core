import socket
import time
from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
import os

class CalyxHubListener(ServiceListener):
    def __init__(self):
        self.found_hub_ip = None
        self.found_hub_port = None

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        pass

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        info = zc.get_service_info(type_, name)
        if info:
            # Convert addresses from bytes to readable strings
            addresses = [socket.inet_ntoa(addr) for addr in info.addresses]
            if addresses:
                self.found_hub_ip = addresses[0]
                self.found_hub_port = info.port
                print(f"🚀 Found Calyx Hub: {name} at {self.found_hub_ip}:{self.found_hub_port}")

def discover_hub(timeout=5):
    """
    Browses for the Calyx Hub on the local network.
    Returns (ip, port) if found, else (None, None).
    """
    print(f"🔍 Searching for Calyx Hub (_calyx-hub._tcp.local.)... (timeout {timeout}s)")
    zeroconf = Zeroconf()
    listener = CalyxHubListener()
    browser = ServiceBrowser(zeroconf, "_calyx-hub._tcp.local.", listener)

    start_time = time.time()
    while time.time() - start_time < timeout:
        if listener.found_hub_ip:
            break
        time.sleep(0.5)

    zeroconf.close()
    return listener.found_hub_ip, listener.found_hub_port

def update_env_with_hub(ip, port):
    """ Updates the .env file with the discovered Hub details. """
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Calyx", ".env")
    if not os.path.exists(env_path):
        print("⚠️ .env not found. Skipping auto-update.")
        return

    hub_url = f"http://{ip}:{port}"
    
    with open(env_path, "r") as f:
        lines = f.readlines()

    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("CALYX_HUB_URL="):
            new_lines.append(f"CALYX_HUB_URL={hub_url}\n")
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.append(f"CALYX_HUB_URL={hub_url}\n")

    with open(env_path, "w") as f:
        f.writelines(new_lines)
    
    print(f"📝 Updated .env with CALYX_HUB_URL={hub_url}")

if __name__ == "__main__":
    ip, port = discover_hub()
    if ip:
        update_env_with_hub(ip, port)
    else:
        print("❌ Could not find Calyx Hub on the local network.")
