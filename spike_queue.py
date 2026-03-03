import trio
import random
from typing import Dict, List, Tuple, Optional

class PrioritizedSpikeQueue:
    """
    Manages incoming neural traffic with reputation-based priority.
    Prevents 'Request Floods' from overwhelming the Mini-Brain.
    """
    def __init__(self, max_size: int = 100):
        self.queue = [] # List of (priority, task_data)
        self.max_size = max_size

    def push(self, peer_reputation: float, task_id: str, data: List[int]):
        """
        Higher reputation = Higher priority (Lower numerical value for sorting).
        """
        priority = 2.0 - peer_reputation # 0.0 is top priority, 2.0 is lowest
        
        if len(self.queue) < self.max_size:
            self.queue.append((priority, task_id, data))
            # Keep sorted by priority
            self.queue.sort(key=lambda x: x[0])
            print(f"[QUEUE] Task {task_id} added. Priority: {priority:.2f}")
        else:
            print("[QUEUE] WARNING: Buffer full. Dropping spike.")

    def pop(self) -> Optional[Tuple[float, str, List[int]]]:
        if self.queue:
            return self.queue.pop(0)
        return None

# --- Verification Test ---
if __name__ == "__main__":
    q = PrioritizedSpikeQueue(max_size=10)
    
    print("--- Starting Request Flood Simulation ---")
    
    # 1. Simulate a 'Whale' node (Reputation 2.0)
    q.push(peer_reputation=2.0, task_id="WHALE_TASK", data=[1, 1, 1])
    
    # 2. Simulate many 'New' nodes (Reputation 1.0)
    for i in range(3):
        q.push(peer_reputation=1.0, task_id=f"NEW_TASK_{i}", data=[0, 1, 0])
        
    # 3. Simulate an 'Untrusted' node (Reputation 0.1)
    q.push(peer_reputation=0.1, task_id="SUSPICIOUS_TASK", data=[0, 0, 0])
    
    print("\n[DRAIN] Processing Queue in Priority Order...")
    first_processed = q.pop()
    print(f"First out: {first_processed[1]}")
    
    if first_processed[1] == "WHALE_TASK":
        print("\nSUCCESS: Prioritization logic confirmed. Reputation-based QoS is active.")
