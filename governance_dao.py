import time
from typing import List, Dict, Any
from pydantic import BaseModel
from peer_database import PeerDatabase
from weighted_consensus import WeightedEnsemble
from rank_choice_voting import RankedChoiceConsensus

class Proposal(BaseModel):
    proposal_id: str
    description: str
    target_synapse: str
    new_weights_hash: str
    options: List[str] = ["ACCEPT", "REJECT"] # Default binary choice
    votes: Dict[str, Any] = {} # PeerID -> Vote (bool or List[str])
    status: str = "OPEN"
    voting_type: str = "WEIGHTED" # "WEIGHTED" or "RCV"

class SynapseDAO:
    """
    Implements the 'Parliament' logic.
    Nodes vote on network upgrades using stake-weighted or ranked-choice consensus.
    """
    def __init__(self, db: PeerDatabase):
        self.db = db
        self.ensemble = WeightedEnsemble(db)
        self.rcv = RankedChoiceConsensus()
        self.proposals: Dict[str, Proposal] = {}

    def create_proposal(self, proposer_id: str, description: str, synapse_id: str, weights_hash: str, options: List[str] = None):
        # Only high-reputation nodes can propose
        record = self.db.get_peer(proposer_id)
        if not record or record.reputation < 1.5:
            print(f"[DAO] REJECTED: Proposer {proposer_id[:8]} has insufficient reputation.")
            return None

        p_id = f"PROP_{int(time.time())}"
        v_type = "RCV" if options and len(options) > 2 else "WEIGHTED"
        
        self.proposals[p_id] = Proposal(
            proposal_id=p_id,
            description=description,
            target_synapse=synapse_id,
            new_weights_hash=weights_hash,
            options=options if options else ["ACCEPT", "REJECT"],
            voting_type=v_type
        )
        print(f"[DAO] NEW {v_type} PROPOSAL: {p_id} - {description}")
        return p_id

    def cast_vote(self, peer_id: str, proposal_id: str, vote: Any):
        if proposal_id in self.proposals:
            self.proposals[proposal_id].votes[peer_id] = vote
            print(f"[DAO] Vote recorded from {peer_id[:8]} for {proposal_id}")

    def tally_votes(self, proposal_id: str):
        if proposal_id not in self.proposals: return
        
        prop = self.proposals[proposal_id]
        
        if prop.voting_type == "RCV":
            winner, confidence = self.rcv.get_winner(prop.votes)
            if winner != "NO_WINNER":
                prop.status = f"PASSED ({winner})"
            else:
                prop.status = "FAILED"
        else:
            # Binary Weighted Vote
            mock_outputs = {}
            for pid, vote in prop.votes.items():
                mock_outputs[pid] = [1, 0] if vote == True or vote == "ACCEPT" else [0, 1]
                
            decision, confidence = self.ensemble.get_consensus(mock_outputs)
            
            if decision == [1, 0] and confidence > 66.0:
                prop.status = "PASSED"
            else:
                prop.status = "FAILED"
        
        print(f"[DAO] {proposal_id} Tally Result: {prop.status}")

# --- Verification Test ---
if __name__ == "__main__":
    db = PeerDatabase()
    dao = SynapseDAO(db)
    
    # 1. Setup Proposer
    proposer = "12D3KooW_VETERAN_ARCHITECT"
    db.update_peer(proposer, spikes=5000, reward=1000.0)
    db.peers[proposer].reputation = 1.9
    
    # 2. Create Proposal
    p_id = dao.create_proposal(
        proposer, 
        "Upgrade Sentiment Alpha to v1.1 (Optimized weights)", 
        "synapse_0", 
        "sha256-new-genome-hash"
    )
    
    # 3. Cast Votes
    dao.cast_vote(proposer, p_id, True)
    dao.cast_vote("12D3KooW_PIXEL_8", p_id, False) # New node vote
    
    # 4. Tally
    dao.tally_votes(p_id)
    
    if dao.proposals[p_id].status == "PASSED":
        print("\nSUCCESS: DAO Governance and stake-weighted voting functional.")
