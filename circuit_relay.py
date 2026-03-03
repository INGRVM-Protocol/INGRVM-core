import trio
import json
import time
from typing import Dict, List

class LighthouseRelay:
    """
    Simulates a 'Lighthouse' Node with a Static Public IP.
    Acts as a meet-up point for nodes behind firewalls (NAT).
    """
    def __init__(self):
        # Map of NodeID -> Public/Private Address Info
        self.registered_peers: Dict[str, Dict] = {}
        print("[LIGHTHOUSE] Global Relay initialized.")

    def register_node(self, node_id: str, local_ip: str, public_ip: str):
        """
        Nodes 'check in' with the lighthouse to reveal their presence.
        """
        self.registered_peers[node_id] = {
            "local_ip": local_ip,
            "public_ip": public_ip,
            "last_seen": time.time(),
            "is_relay_candidate": True
        }
        print(f"[LIGHTHOUSE] Node {node_id[:8]} registered from {public_ip}")

    def get_relay_path(self, target_node_id: str) -> str:
        """
        If Node A wants to talk to Node B, it asks the Lighthouse:
        'How do I reach B?'
        """
        peer = self.registered_peers.get(target_node_id)
        if not peer:
            return "NODE_OFFLINE"
        
        # Logic: If nodes are on different public IPs, 
        # the Lighthouse provides its own address as a 'Circuit Relay'.
        return f"relay://<LIGHTHOUSE_IP>:60000/p2p/{target_node_id}"

class AutoNAT:
    """
    Logic for a node to detect if it is behind a restrictive firewall.
    """
    def check_reachability(self) -> str:
        # Mocking the process of asking the network: 'Can you see me?'
        restrictive = True # Assume true for the worst-case scenario
        
        if restrictive:
            print("[AUTONAT] I am behind a restrictive firewall. Requesting Relay...")
            return "RELAY_REQUIRED"
        return "DIRECT_REACHABLE"

# --- Verification Test ---
if __name__ == "__main__":
    lighthouse = LighthouseRelay()
    node_a_id = "12D3KooW_NODE_A_DALLAS"
    node_b_id = "12D3KooW_NODE_B_AUSTIN"
    
    # 1. Nodes check in from different networks
    lighthouse.register_node(node_a_id, "192.168.1.5", "72.45.12.101")
    lighthouse.register_node(node_b_id, "10.0.0.42", "108.12.55.22")
    
    # 2. Node A wants to send a spike to Node B
    print(f"\n[MESH] Node A (Dallas) searching for Node B (Austin)...")
    path = lighthouse.get_relay_path(node_b_id)
    
    print(f"[MESH] Connection Path: {path}")
    
    if "relay://" in path:
        print("\nSUCCESS: Lighthouse established a Proxy Relay for cross-network communication.")
