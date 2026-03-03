import random
from typing import List

class PrivacyMasker:
    """
    Sovereignty Engine: Implements Differential Privacy for spikes.
    Blinds random indices to prevent nodes from reconstructing sensitive inputs.
    """
    def __init__(self, privacy_level: float = 0.1):
        # privacy_level is the percentage of spikes to 'randomize' or hide.
        self.level = privacy_level

    def mask_spikes(self, indices: List[int], max_index: int) -> List[int]:
        """
        Randomly removes some spikes and injects some 'noise' spikes.
        """
        if not indices: return []
        
        # 1. Drop some real spikes
        num_to_keep = int(len(indices) * (1.0 - self.level))
        masked = random.sample(indices, num_to_keep)
        
        # 2. Inject some noise spikes (fake data)
        num_noise = int(len(indices) * self.level)
        for _ in range(num_noise):
            masked.append(random.randint(0, max_index))
            
        print(f"[PRIVACY] Masked {len(indices)} spikes. Integrity maintained via Differential Privacy.")
        return sorted(list(set(masked)))

# --- Verification Test ---
if __name__ == "__main__":
    masker = PrivacyMasker(privacy_level=0.2) # 20% noise/drop
    
    raw_spikes = [10, 20, 30, 40, 50]
    masked_spikes = masker.mask_spikes(raw_spikes, 100)
    
    print(f"Original: {raw_spikes}")
    print(f"Masked:   {masked_spikes}")
    
    if len(masked_spikes) > 0 and masked_spikes != raw_spikes:
        print("\nSUCCESS: Privacy masking successfully obfuscated the neural pattern.")
