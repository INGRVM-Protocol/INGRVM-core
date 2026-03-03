import torch
import math
from typing import List

class SpikeSanitizer:
    """
    Security Middleware: Filters incoming 'Toxic Spikes' to prevent 
    model crashes, overflows, or adversarial data poisoning.
    """
    def sanitize(self, raw_spikes: List[float]) -> List[int]:
        """
        Clamps data to binary [0, 1] and removes non-finite values.
        """
        sanitized = []
        toxic_count = 0
        
        for val in raw_spikes:
            # 1. Check for 'Toxic' values (NaN or Infinity)
            if not math.isfinite(val):
                sanitized.append(0)
                toxic_count += 1
                continue
            
            # 2. Clamping: Standard SNNs only want pulses (0 or 1)
            # If a malicious node sends 999999.0, we clamp it to 1.
            if val >= 0.5:
                sanitized.append(1)
            else:
                sanitized.append(0)
                
        if toxic_count > 0:
            print(f"[SECURITY] Neutralized {toxic_count} toxic spike(s).")
            
        return sanitized

# --- Verification Test ---
if __name__ == "__main__":
    sanitizer = SpikeSanitizer()
    
    # Simulate a 'Toxic Spike' attack
    # [1.0, 0.0, NaN, 999999.0, -inf]
    toxic_input = [1.0, 0.0, float('nan'), 999999.0, float('-inf')]
    
    print("--- Starting Spike Sanitization Test ---")
    print(f"Raw Input: {toxic_input}")
    
    clean_output = sanitizer.sanitize(toxic_input)
    print(f"Clean Output: {clean_output}")
    
    # Verify: All values must be 0 or 1
    if all(v in [0, 1] for v in clean_output):
        print("\nSUCCESS: Toxic spikes neutralized. Model is safe.")
    else:
        print("\nFAILURE: Sanitization leaked invalid data.")
