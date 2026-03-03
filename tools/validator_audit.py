import random
from typing import List, Dict

class ValidatorAuditor:
    """
    Quality Control: Periodically audits peer work.
    If a node reports a result that deviates from the ensemble, 
    they risk being slashed.
    """
    def audit_task(self, worker_id: str, reported_indices: List[int], ground_truth: List[int]) -> bool:
        """
        Compares reported spikes vs. actual expected spikes.
        """
        # Calculate overlap (IoU)
        set_reported = set(reported_indices)
        set_truth = set(ground_truth)
        
        intersection = len(set_reported.intersection(set_truth))
        union = len(set_reported.union(set_truth))
        
        accuracy = intersection / union if union > 0 else 1.0
        
        print(f"[AUDIT] Worker {worker_id[:8]} accuracy: {accuracy:.2%}")
        
        if accuracy < 0.50:
            print(f"[CRITICAL] Low accuracy detected! Flagging {worker_id[:8]} for slashing.")
            return False
        
        print(f"[AUDIT] Work verified. Node {worker_id[:8]} reputation increased.")
        return True

# --- Verification Test ---
if __name__ == "__main__":
    auditor = ValidatorAuditor()
    
    # 1. Honest Worker (3 out of 4 match = 75% accuracy)
    honest_indices = [1, 5, 12, 18]
    truth = [1, 5, 12, 19] 
    
    print("--- Testing Honest Audit ---")
    auditor.audit_task("WORKER_HONEST", honest_indices, truth)
    
    # 2. Lazy Worker (Faking it)
    lazy_indices = [99, 99, 99]
    
    print("\n--- Testing Lazy Audit ---")
    success = auditor.audit_task("WORKER_LAZY", lazy_indices, truth)
    
    if not success:
        print("\nSUCCESS: Audit loop correctly caught the malicious worker.")
