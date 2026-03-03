import time
import random
from collections import deque
from typing import List, Optional

class SpikeSpeculator:
    """
    Implements 'Speculative Spiking' to hide network latency.
    The node predicts the next spike based on the recent firing pattern.
    """
    def __init__(self, history_size: int = 5):
        self.history = deque(maxlen=history_size)
        self.predictions_made = 0
        self.correct_predictions = 0

    def record_actual_spike(self, spike_data: List[int]):
        """Records ground truth when it finally arrives from the mesh."""
        self.history.append(tuple(spike_data))

    def predict_next_spike(self) -> List[int]:
        """
        Uses a simple Markov-style pattern match to guess the next spike.
        """
        self.predictions_made += 1
        
        if len(self.history) < 2:
            return [0, 0]
            
        if self.history[-1] == self.history[-2]:
            return list(self.history[-1])
            
        from collections import Counter
        most_common = Counter(self.history).most_common(1)[0][0]
        return list(most_common)

    def verify_prediction(self, actual_spike: List[int], predicted_spike: List[int]):
        """Compares the 'guess' with the 'truth'."""
        if actual_spike == predicted_spike:
            self.correct_predictions += 1
            return True
        return False

    def get_stats(self):
        accuracy = (self.correct_predictions / self.predictions_made) * 100 if self.predictions_made > 0 else 0
        return {
            "total_predictions": self.predictions_made,
            "accuracy": f"{accuracy:.1f}%",
            "latency_savings_ms": self.correct_predictions * 50 
        }

# --- Verification Test ---
if __name__ == "__main__":
    speculator = SpikeSpeculator()
    pattern = [[1, 0], [0, 1], [1, 0], [1, 0], [1, 0]]
    
    print("--- Starting Speculative Spiking Test ---")
    
    for i in range(10):
        prediction = speculator.predict_next_spike()
        actual = random.choice(pattern)
        is_correct = speculator.verify_prediction(actual, prediction)
        speculator.record_actual_spike(actual)
        
        status = "[HIT]" if is_correct else "[MISS]"
        print(f"Step {i+1}: Guess {prediction} | Actual {actual} | {status}")

    stats = speculator.get_stats()
    print(f"\n--- Performance Results ---")
    print(f"Prediction Accuracy: {stats['accuracy']}")
    print(f"Estimated Network Lag Hidden: {stats['latency_savings_ms']}ms")
