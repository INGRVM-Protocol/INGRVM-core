import sys
import os

# Add parent dir to path so we can import peer_database
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from peer_database import PeerDatabase

def purge():
    db_path = os.path.join(os.path.dirname(__file__), "..", "peer_db.json")
    if not os.path.exists(db_path):
        print(f"[PURGE] Database {db_path} not found.")
        return

    db = PeerDatabase(db_path=db_path)
    initial_count = len(db.peers)
    
    print(f"--- Purging Ghost Nodes from {db_path} ---")
    
    # Filter for nodes that are NOT our local known identities
    # Keep only nodes that have a valid reputation or specific PeerIDs we want
    # For this mock, we'll just purge nodes starting with 'ATX_'
    ghosts = [pid for pid in db.peers.keys() if pid.startswith("ATX_")]
    
    for ghost in ghosts:
        del db.peers[ghost]
        
    db.save()
    print(f"SUCCESS: Removed {len(ghosts)} ghost nodes. Database now has {len(db.peers)} records.")

if __name__ == "__main__":
    purge()
