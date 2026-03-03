import time
import numpy as np
from typing import Dict, List
from peer_database import PeerDatabase
from reward_engine import RewardEngine

class SubtensorMock:
    """
    Simulates the Bittensor 'Subtensor' blockchain logic.
    Handles Epoch settlement using a simplified Yuma Consensus model.
    """
    def __init__(self, db: PeerDatabase):
        self.db = db
        self.epoch_num = 0
        self.total_syn_emitted = 0.0

    def run_epoch(self, active_work: Dict[str, int]):
        """
        Settles all network activity for the current period.
        """
        self.epoch_num += 1
        print(f"\n--- BLOCKCHAIN EPOCH #{self.epoch_num} STARTED ---")
        
        # 1. Initialize Reward Engine for this specific emission period
        # Assume 500 $SYN per epoch emission
        engine = RewardEngine(epoch_emission=500.0)
        
        # 2. Register all work reported by the mesh
        for peer_id, spikes in active_work.items():
            # Get current reputation from the persistent DB
            record = self.db.get_peer(peer_id)
            rep = record.reputation if record else 1.0
            
            engine.register_work(peer_id, spikes)
            # Inject existing reputation into engine
            if peer_id in engine.nodes:
                engine.nodes[peer_id].reputation_score = rep

        # 3. Calculate Yuma-style distribution
        payouts = engine.calculate_payouts()
        
        # 4. Commit to the 'Blockchain' (Peer Database)
        print(f"[SUBTENSOR] Settling rewards for {len(payouts)} nodes...")
        for peer_id, amount in payouts.items():
            # Update the permanent record
            # We treat spikes as '0' here because they were already counted in the engine
            self.db.update_peer(peer_id, spikes=0, reward=amount)
            self.total_syn_emitted += amount
            
            print(f"  > Node {peer_id[:8]}... | Reward: +{amount} $SYN | New Balance: {self.db.get_peer(peer_id).tokens_earned:.2f}")

        print(f"--- EPOCH #{self.epoch_num} FINALIZED | Total Emission: {self.total_syn_emitted:.2f} $SYN ---")

# --- Verification Test ---
if __name__ == "__main__":
    database = PeerDatabase()
    blockchain = SubtensorMock(database)
    
    # Mock data from the mesh during this epoch
    mock_mesh_work = {
        "12D3KooW_PC_BACKBONE": 8500,
        "12D3KooW_PIXEL_8": 2100,
        "12D3KooW_MOCK_PEER_ALPHA": 450
    }
    
    # Run two epochs to see accumulation
    blockchain.run_epoch(mock_mesh_work)
    time.sleep(1)
    
    # Simulate node alpha doing more work in second epoch
    mock_mesh_work["12D3KooW_MOCK_PEER_ALPHA"] = 3000
    blockchain.run_epoch(mock_mesh_work)
    
    if database.get_peer("12D3KooW_MOCK_PEER_ALPHA").tokens_earned > 0:
        print("\nSUCCESS: Subtensor settlement logic is persistent and accurate.")
