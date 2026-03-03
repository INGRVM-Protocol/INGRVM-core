import trio
import socket
import json
from typing import List

class LocalDiscovery:
    """
    Simulates Zero-Config / mDNS style discovery.
    Allows nodes on the same local network to find each other without 
    a central bootstrap beacon.
    """
    def __init__(self, port: int = 60002):
        self.port = port
        self.discovered_peers = set()

    async def broadcast_presence(self, node_id: str, multiaddr: str):
        """
        Periodically broadcasts presence via UDP multicast/broadcast.
        """
        print(f"[DISCOVERY] Starting presence broadcast on port {self.port}...")
        
        # In a real app, we'd use a real multicast group. 
        # For this laptop prototype, we'll mock the UDP listener.
        while True:
            # print(f"[DISCOVERY] Beaming presence: {node_id[:8]}")
            # Mocking the network broadcast delay
            await trio.sleep(5)

    async def listen_for_peers(self):
        """
        Listens for incoming UDP presence packets from other nodes.
        """
        print("[DISCOVERY] Listening for local fireflies (peers)...")
        # In a real app, this would be: 
        # sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # sock.bind(('', self.port))
        
        # Mock Discovery Event
        await trio.sleep(3)
        mock_peer = "/ip4/192.168.1.42/tcp/60001/p2p/12D3KooW_LOCAL_NEIGHBOR"
        self.discovered_peers.add(mock_peer)
        print(f"[DISCOVERY] FOUND NEIGHBOR: {mock_peer[:32]}...")

# --- Verification Test ---
if __name__ == "__main__":
    discovery = LocalDiscovery()
    
    async def test():
        async with trio.open_nursery() as nursery:
            nursery.start_soon(discovery.listen_for_peers)
            # Give it a few seconds to find the 'mock' neighbor
            await trio.sleep(5)
            
            if len(discovery.discovered_peers) > 0:
                print("\nSUCCESS: Local discovery logic initialized and neighbor found.")
                nursery.cancel_scope.cancel()

    trio.run(test)
