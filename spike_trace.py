import time
import json
import os
from typing import List, Dict

class SpikeTracer:
    """
    Developer Tool: Logs the exact timing of neural firing events.
    Used to debug asynchronous spike trains and identify dead neurons.
    """
    def __init__(self, log_path: str = "neuromorphic_env/spike_trace_log.json"):
        self.log_path = log_path
        self.trace = []

    def record_spike(self, layer: str, neuron_idx: int, magnitude: float = 1.0):
        timestamp = time.time()
        event = {
            "t": round(timestamp, 4),
            "layer": layer,
            "idx": neuron_idx,
            "mag": magnitude
        }
        self.trace.append(event)
        
        # In a real tool, we might use a circular buffer or stream to disk
        if len(self.trace) % 10 == 0:
            self.save_to_disk()

    def save_to_disk(self):
        with open(self.log_path, "w") as f:
            json.dump(self.trace, f, indent=4)

    def visualize_ascii(self):
        """Simple terminal-based timeline view."""
        if not self.trace: return
        
        print("\n--- [X-RAY] SPIKE TRAIN TIMELINE ---")
        start_t = self.trace[0]["t"]
        
        for event in self.trace:
            offset = int((event["t"] - start_t) * 100) # MS scale
            timeline = " " * offset + "⚡"
            print(f"[{event['layer']:10}] {timeline} (Idx: {event['idx']})")

# --- Verification Test ---
if __name__ == "__main__":
    tracer = SpikeTracer()
    
    print("--- Simulating Neural Activity Trace ---")
    
    # Simulate a wave of spikes through 3 layers
    tracer.record_spike("INPUT", 0)
    time.sleep(0.01)
    tracer.record_spike("HIDDEN", 4)
    time.sleep(0.01)
    tracer.record_spike("HIDDEN", 2)
    time.sleep(0.01)
    tracer.record_spike("OUTPUT", 1)
    
    tracer.visualize_ascii()
    
    if os.path.exists("neuromorphic_env/spike_trace_log.json"):
        print("\nSUCCESS: Spike Trace Debugger is logging and visualizing.")
