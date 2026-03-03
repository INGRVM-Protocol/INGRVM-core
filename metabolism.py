import time
import math

class NodeMetabolism:
    """
    Solarpunk Concept: Nodes have a 'Virtual Energy Pool' (Joules).
    Every spike consumed energy. Energy regenerates via 'Solar Harvest'.
    Prevents mesh spamming and rewards efficiency.
    """
    def __init__(self, max_energy: float = 100.0, recovery_rate: float = 2.0):
        self.max_energy = max_energy
        self.recovery_rate = recovery_rate # Joules per second
        self.current_energy = max_energy
        self.last_update = time.time()
        
        # Energy Cost per Spike (Joules)
        self.SPIKE_COST = 0.05 

    def _regenerate(self):
        """Calculates solar harvest since last check."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Recover energy up to max
        recovery = elapsed * self.recovery_rate
        self.current_energy = min(self.max_energy, self.current_energy + recovery)
        self.last_update = now

    def consume_spikes(self, count: int) -> bool:
        """
        Attempts to fire a batch of spikes. 
        Returns True if node has enough energy.
        """
        self._regenerate()
        
        total_cost = count * self.SPIKE_COST
        
        if self.current_energy >= total_cost:
            self.current_energy -= total_cost
            print(f"[METABOLISM] Fired {count} spikes. Energy remaining: {self.current_energy:.2f} J")
            return True
        else:
            print(f"[METABOLISM] CRITICAL: Energy Low ({self.current_energy:.2f} J). Node is resting...")
            return False

    def get_status(self):
        self._regenerate()
        return {
            "energy_level": f"{(self.current_energy / self.max_energy) * 100:.1f}%",
            "joules": round(self.current_energy, 2)
        }

# --- Verification Test ---
if __name__ == "__main__":
    meta = NodeMetabolism(max_energy=10.0, recovery_rate=1.0)
    
    print("--- Starting Metabolic Pulse Test ---")
    
    # 1. Simulate heavy burst
    print("Scenario: Heavy Neural Burst...")
    for _ in range(5):
        meta.consume_spikes(50) # 50 spikes per step
        
    # 2. Check status
    print(f"Status after burst: {meta.get_status()}")
    
    # 3. Simulate exhaustion
    print("\nScenario: Pushing to the limit...")
    meta.consume_spikes(200)
    
    # 4. Wait for 'Solar Harvest'
    print("\n[WAIT] Resting for 2 seconds to harvest solar energy...")
    time.sleep(2)
    
    if meta.current_energy > 1.0:
        print(f"Status after rest: {meta.get_status()}")
        print("\nSUCCESS: Metabolic scaling and Solar Recovery functional.")
