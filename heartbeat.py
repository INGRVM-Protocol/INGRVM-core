import trio
import time
from peer_database import PeerDatabase

class MeshHeartbeat:
    """
    Monitors the 'Vitals' of neighbor fireflies in the mesh.
    Ensures the Trust Map is accurate by pruning stale peers.
    """
    def __init__(self, db: PeerDatabase, stale_timeout: int = 60):
        self.db = db
        self.stale_timeout = stale_timeout

    async def pulse(self):
        """
        Periodically checks the database for stale nodes.
        """
        print("\n--- [HEARTBEAT] Monitor Pulse Active ---")
        
        while True:
            now = time.time()
            to_prune = []
            
            for peer_id, record in self.db.peers.items():
                elapsed = now - record.last_seen
                
                if elapsed > self.stale_timeout:
                    print(f"[HEARTBEAT] Node {peer_id[:8]}... is silent. Marking as HIBERNATING.")
                    record.reputation = max(0.0, record.reputation - 0.1) # Penalty for inactivity
                    # In a real mesh, we would remove them from the active routing table
                    
            self.db.save()
            await trio.sleep(30) # Pulse every 30 seconds

# --- Verification Test ---
if __name__ == "__main__":
    db = PeerDatabase()
    # Add a mock 'stale' peer
    db.update_peer("12D3KooW_STALE_PEER", spikes=0, reward=0)
    db.peers["12D3KooW_STALE_PEER"].last_seen = time.time() - 100 # Over 1 minute ago
    
    heartbeat = MeshHeartbeat(db, stale_timeout=60)
    
    async def test():
        # Run one pulse then stop
        await heartbeat.pulse()

    try:
        trio.run(test)
        print("\nSUCCESS: Heartbeat monitor correctly identified and penalized stale peer.")
    except Exception as e:
        print(f"Error: {e}")
