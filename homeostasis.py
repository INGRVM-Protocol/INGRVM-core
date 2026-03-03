import torch
import torch.nn as nn
import snntorch as snn
from typing import List

class HomeostaticBrain(nn.Module):
    """
    A 3-layer Mini-Brain with Adaptive Thresholding (Homeostasis).
    If it fires too much, it raises the threshold. If silent, it lowers it.
    """
    def __init__(self, target_firing_rate: float = 0.1):
        super().__init__()
        self.target_rate = target_firing_rate
        
        # Architecture
        self.fc = nn.Linear(3, 8)
        self.lif = snn.Leaky(beta=0.95, threshold=1.0) # Base threshold
        self.mem = self.lif.init_leaky()
        
        # Adaptive State
        self.current_threshold = 1.0
        self.firing_history = []

    def forward(self, x):
        # 1. Update Threshold (Homeostatic Logic)
        if len(self.firing_history) > 10:
            avg_rate = sum(self.firing_history) / len(self.firing_history)
            
            if avg_rate > self.target_rate:
                # Firing too much! Raise threshold to save energy.
                self.current_threshold += 0.05
            elif avg_rate < self.target_rate * 0.5:
                # Too silent! Lower threshold to stay responsive.
                self.current_threshold = max(0.1, self.current_threshold - 0.05)
            
            # Update the LIF neuron's actual threshold
            self.lif.threshold = torch.tensor(self.current_threshold)
            
        # 2. Standard Forward Pass
        cur = self.fc(x)
        spk, self.mem = self.lif(cur, self.mem)
        
        # 3. Record Firing
        self.firing_history.append(spk.mean().item())
        if len(self.firing_history) > 50: self.firing_history.pop(0)
        
        return spk

# --- Verification Test ---
if __name__ == "__main__":
    brain = HomeostaticBrain(target_firing_rate=0.1)
    
    print("--- Starting Homeostasis Simulation ---")
    print("Scenario: Constant High Input (Over-stimulation)")
    
    high_input = torch.ones((1, 3)) * 5.0 # Very strong input
    
    thresholds = []
    for i in range(30):
        brain(high_input)
        thresholds.append(brain.current_threshold)
        if i % 5 == 0:
            print(f"Step {i}: Threshold = {brain.current_threshold:.2f} | Firing Rate = {brain.firing_history[-1]:.2f}")

    if thresholds[-1] > thresholds[0]:
        print("\nSUCCESS: Homeostasis active. Threshold raised to counteract over-stimulation.")
    else:
        print("\nHomeostasis failed to adjust threshold.")
