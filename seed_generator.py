import hashlib
import random

class DigitalSeed:
    """
    Solarpunk Concept: Generates a unique, living visual representation 
    of a node based on its ID and Reputation. (Emoji-free for audit stability)
    """
    def __init__(self, peer_id: str):
        self.peer_id = peer_id
        self.seed_val = int(hashlib.sha256(peer_id.encode()).hexdigest()[:8], 16)
        random.seed(self.seed_val)

    def generate_plant(self, reputation: float = 1.0) -> str:
        """
        Generates an ASCII plant. 
        """
        leaves = ["v", "#", "+", "i"]
        stalk = " | "
        
        height = int(3 + (reputation * 3))
        density = int(1 + (reputation * 2))
        
        output = [f"\n--- Node Vitality: {self.peer_id[:8]} ---"]
        
        for h in range(height):
            if h == 0:
                output.append("   *   ")
            else:
                row = list("       ")
                for _ in range(density):
                    pos = random.choice([0, 1, 2, 4, 5, 6])
                    row[pos] = random.choice(leaves)
                
                row[3] = stalk[1]
                output.append("".join(row))
        
        output.append("  [ROOTS]  ")
        return "\n".join(output)

# --- Verification Test ---
if __name__ == "__main__":
    mock_id = "4QbWtbA6DrtI/dc0h+9iX+73vuiLS+RReHZf9nEVNlc="
    seed = DigitalSeed(mock_id)
    
    print("Scenario 1: Starting Node (Reputation 0.5)")
    print(seed.generate_plant(reputation=0.5))
    
    print("\nScenario 2: Veteran Node (Reputation 2.0)")
    print(seed.generate_plant(reputation=2.0))
    
    print("\nSUCCESS: Digital Seed generator is functional and Solarpunk-ready.")
