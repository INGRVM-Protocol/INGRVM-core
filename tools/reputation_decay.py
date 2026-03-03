import sys
import os
import time

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from peer_database import PeerDatabase

def apply_decay(decay_rate: float = 0.01, inactivity_threshold_hrs: int = 24):
    """
    Simulates biological atrophy. Nodes that haven't been active 
    lose a small percentage of reputation.
    """
    db_path = os.path.join(os.path.dirname(__file__), "..", "peer_db.json")
    if not os.path.exists(db_path):
        print("[DECAY] Peer database not found.")
        return

    db = PeerDatabase(db_path=db_path)
    current_time = time.time()
    decay_count = 0
    
    print(f"--- 🕰️ COMMENCING REPUTATION DECAY ---")
    
    for peer_id, record in db.peers.items():
        # Calculate hours since last active
        idle_hrs = (current_time - record.last_seen) / 3600
        
        if idle_hrs > inactivity_threshold_hrs:
            old_rep = record.reputation
            # Decay reputation by a fixed percentage
            record.reputation = max(0.1, record.reputation * (1.0 - decay_rate))
            print(f"  [-] Node {peer_id[:8]} atrophied: {old_rep:.3f} -> {record.reputation:.3f}")
            decay_count += 1
            
    if decay_count > 0:
        db.save()
        print(f"\nSUCCESS: {decay_count} nodes impacted by biological decay.")
    else:
        print("\nSTATUS: All nodes are recently active. No decay applied.")

if __name__ == "__main__":
    # Test with a very aggressive threshold (1 second) to see it work
    apply_decay(decay_rate=0.05, inactivity_threshold_hrs=0)
