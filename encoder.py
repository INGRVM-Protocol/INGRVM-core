import torch
import snntorch.spikegen as spikegen
from typing import List

class TextSpikeEncoder:
    """
    Converts raw text into neuromorphic spike trains using ASCII normalization 
    and Rate Coding.
    """
    def __init__(self, num_steps: int = 10):
        self.num_steps = num_steps

    def encode(self, text: str) -> torch.Tensor:
        """
        1. Tokenizes text into character-level ASCII.
        2. Normalizes to [0, 1] range.
        3. Generates a rate-coded spike train.
        """
        # Convert to ASCII integers
        ascii_values = [ord(char) for char in text]
        
        # Simple Normalization: ASCII max is ~127, but let's use 255 for standard padding
        data_tensor = torch.tensor(ascii_values).float() / 255.0
        
        # Rate Coding: higher value = higher frequency of spikes over time
        # Returns shape: (num_steps, len(text))
        spike_train = spikegen.rate(data_tensor, num_steps=self.num_steps)
        
        return spike_train

# --- Verification Test ---
if __name__ == "__main__":
    encoder = TextSpikeEncoder(num_steps=5)
    sample_text = "Bio" # B=66, i=105, o=111
    
    spikes = encoder.encode(sample_text)
    
    print(f"--- Text-to-Spike Encoding: '{sample_text}' ---")
    print(f"Input Length: {len(sample_text)} characters")
    print(f"Temporal Steps: {spikes.shape[0]}")
    print(f"Output Shape (Steps, Characters): {spikes.shape}")
    
    print("\nSpike Pattern (1 = Fire, 0 = Idle):")
    # Transpose to show characters as rows, time as columns
    for i, char in enumerate(sample_text):
        char_spikes = spikes[:, i].tolist()
        print(f"'{char}': {char_spikes}")

    if spikes.sum() > 0:
        print("\nSUCCESS: Text has been successfully translated into temporal spikes.")
