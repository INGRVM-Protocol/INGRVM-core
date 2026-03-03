from typing import List, Dict, Tuple
from collections import Counter

class RankedChoiceConsensus:
    """
    Implements Instant-Runoff Voting (Ranked Choice).
    Nodes submit a list of preferences. Logic eliminates bottom choices 
    and redistributes until a winner emerges.
    """
    def get_winner(self, ballots: Dict[str, List[str]]) -> Tuple[str, float]:
        """
        ballots: Map of PeerID -> Ordered List of Proposal IDs
        Example: {"peer_1": ["prop_A", "prop_B"], "peer_2": ["prop_B", "prop_A"]}
        """
        active_ballots = list(ballots.values())
        all_candidates = set()
        for b in active_ballots:
            all_candidates.update(b)
            
        print(f"\n--- [DAO] Commencing Ranked Choice Voting (Voters: {len(ballots)}) ---")
        
        iteration = 1
        while True:
            # 1. Count first choices
            first_choices = [b[0] for b in active_ballots if b]
            counts = Counter(first_choices)
            
            if not counts:
                return "NO_WINNER", 0.0
                
            total_votes = len(first_choices)
            winner, top_votes = counts.most_common(1)[0]
            
            # 2. Check for majority
            confidence = (top_votes / total_votes) * 100
            print(f"[ROUND {iteration}] Top: {winner} ({confidence:.1f}%)")
            
            if confidence > 50.0:
                print(f"[DAO] WINNER FOUND: {winner}")
                return winner, confidence
            
            # 3. Eliminate lowest and redistribute
            if len(counts) <= 1:
                # No majority possible
                return winner, confidence
                
            least_popular, _ = counts.most_common()[-1]
            print(f"[DAO] Eliminating lowest: {least_popular}")
            
            # Update ballots: remove the eliminated candidate from everywhere
            new_ballots = []
            for b in active_ballots:
                new_b = [c for i, c in enumerate(b) if c != least_popular]
                if new_b:
                    new_ballots.append(new_b)
            
            active_ballots = new_ballots
            iteration += 1
            if iteration > 10: break # Safety break

# --- Verification Test ---
if __name__ == "__main__":
    rcv = RankedChoiceConsensus()
    
    # 5 nodes voting on 3 different network upgrades
    mock_ballots = {
        "node_1": ["v1.1_performance", "v1.2_security", "v1.0_legacy"],
        "node_2": ["v1.2_security", "v1.1_performance", "v1.0_legacy"],
        "node_3": ["v1.0_legacy", "v1.2_security", "v1.1_performance"],
        "node_4": ["v1.1_performance", "v1.2_security", "v1.0_legacy"],
        "node_5": ["v1.2_security", "v1.1_performance", "v1.0_legacy"]
    }
    
    winner, confidence = rcv.get_winner(mock_ballots)
    
    if winner != "NO_WINNER":
        print(f"\nSUCCESS: Ranked choice consensus reached winner: {winner}")
