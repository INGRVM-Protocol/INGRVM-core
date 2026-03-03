import time
from typing import List, Dict
from pydantic import BaseModel, Field

class NodeStats(BaseModel):
    peer_id: str
    useful_work_spikes: int = 0
    reputation_score: float = 1.0 # q_i in whitepaper
    last_active: float = Field(default_factory=time.time)

class RewardEngine:
    """
    Implements the Calyx Tokenomics.
    Formula: R_i = E * (w_i * q_i) / Sum(w_j * q_j)
    Includes dynamic inflation to scale with network size.
    """
    def __init__(self, epoch_emission: float = 100.0, inflation_rate: float = 0.05):
        self.epoch_emission = epoch_emission
        self.inflation_rate = inflation_rate
        self.nodes: Dict[str, NodeStats] = {}

    def adjust_inflation(self, active_node_count: int):
        """
        Adjusts emissions based on network density.
        """
        if active_node_count > 50: # Threshold for 'Growth' phase
            self.epoch_emission *= (1.0 - self.inflation_rate)
            print(f"[ECONOMY] Inflation Brake: Emission set to {self.epoch_emission:.2f}")
        else:
            self.epoch_emission *= (1.0 + (self.inflation_rate / 2))
            print(f"[ECONOMY] Growth Stimulus: Emission set to {self.epoch_emission:.2f}")

    def register_work(self, peer_id: str, spikes: int):
        if peer_id not in self.nodes:
            self.nodes[peer_id] = NodeStats(peer_id=peer_id)
        
        self.nodes[peer_id].useful_work_spikes += spikes
        self.nodes[peer_id].last_active = time.time()
        
        # Reputation boost for active work
        self.nodes[peer_id].reputation_score = min(2.0, self.nodes[peer_id].reputation_score + 0.01)

    def distribute_mesh_rewards(self, shard_contributions: Dict[str, int], total_task_spikes: int):
        """
        Task #14: Multi-node Reward Splitting.
        Distributes spikes for a single inference task across all participating nodes.
        :param shard_contributions: { 'node_id': layers_processed }
        :param total_task_spikes: The output spike count of the final layer.
        """
        total_layers = sum(shard_contributions.values())
        if total_layers == 0: return

        for node_id, layers in shard_contributions.items():
            # Calculate proportion of work based on layers processed
            work_proportion = layers / total_layers
            node_share = int(total_task_spikes * work_proportion)
            
            self.register_work(node_id, spikes=max(1, node_share))
            print(f"[REWARDS] Distributed {node_share} spikes to {node_id} for mesh contribution.")

    def calculate_payouts(self) -> Dict[str, float]:
        """Calculates the $SYN distribution for the current epoch."""
        payouts = {}
        
        # Calculate denominator: Sum of (work * quality) for all nodes
        total_utility_weighted_work = sum(
            node.useful_work_spikes * node.reputation_score 
            for node in self.nodes.values()
        )
        
        if total_utility_weighted_work == 0:
            return {peer_id: 0.0 for peer_id in self.nodes}

        for peer_id, node in self.nodes.items():
            # R_i formula
            node_utility = node.useful_work_spikes * node.reputation_score
            reward = self.epoch_emission * (node_utility / total_utility_weighted_work)
            payouts[peer_id] = round(reward, 4)
            
        return payouts

# --- Verification Test ---
if __name__ == "__main__":
    engine = RewardEngine(epoch_emission=1000.0) # 1000 $SYN per epoch
    
    # Simulate 3 nodes with different hardware/reputation
    # 1. PC Backbone (High work, high reputation)
    engine.register_work("12D3KooW_PC_BACKBONE", spikes=5000)
    engine.nodes["12D3KooW_PC_BACKBONE"].reputation_score = 1.8 
    
    # 2. Pixel 8 (Medium work, standard reputation)
    engine.register_work("12D3KooW_PIXEL_8", spikes=1200)
    
    # 3. New Laptop (Low work, starting reputation)
    engine.register_work("12D3KooW_LAPTOP", spikes=300)
    
    payouts = engine.calculate_payouts()
    
    print("--- Epoch Reward Distribution ---")
    for peer_id, amount in payouts.items():
        stats = engine.nodes[peer_id]
        print(f"[{peer_id[:12]}] Work: {stats.useful_work_spikes}, Rep: {stats.reputation_score:.2f} -> Reward: {amount} $SYN")
    
    total_distributed = sum(payouts.values())
    print(f"\nTotal Distributed: {total_distributed} $SYN")
