import json
import os
import torch
import torch.nn as nn

class synapseRegistry:
    """
    Manages the persistence of SNN 'synapses' (weights and metadata) on the local node.
    """
    def __init__(self, storage_dir="synapses"):
        self.storage_dir = storage_dir
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)

    def save_synapse(self, synapse_id: str, model: nn.Module, metadata: dict):
        """Saves the model weights and metadata to disk."""
        synapse_path = os.path.join(self.storage_dir, f"{synapse_id}.pt")
        meta_path = os.path.join(self.storage_dir, f"{synapse_id}.json")
        
        # Save weights
        torch.save(model.state_dict(), synapse_path)
        
        # Save metadata (Architecture, beta, etc.)
        with open(meta_path, "w") as f:
            json.dump(metadata, f, indent=4)
            
        print(f"[REGISTRY] Saved synapse: {synapse_id}")

    def load_synapse(self, synapse_id: str, model: nn.Module):
        """Loads weights into the provided model skeleton."""
        synapse_path = os.path.join(self.storage_dir, f"{synapse_id}.pt")
        meta_path = os.path.join(self.storage_dir, f"{synapse_id}.json")
        
        if not os.path.exists(synapse_path):
            print(f"[REGISTRY] synapse {synapse_id} not found.")
            return None
            
        model.load_state_dict(torch.load(synapse_path))
        
        with open(meta_path, "r") as f:
            metadata = json.load(f)
            
        print(f"[REGISTRY] Loaded synapse: {synapse_id}")
        return metadata

# --- Test the Registry ---
if __name__ == "__main__":
    # Create a dummy model
    class DummySNN(nn.Module):
        def __init__(self):
            super().__init__()
            self.fc = nn.Linear(3, 2)
    
    test_model = DummySNN()
    registry = synapseRegistry()
    
    test_meta = {
        "synapse_id": "synapse_0",
        "name": "Sentiment Alpha",
        "version": "1.0.0",
        "num_inputs": 3,
        "num_outputs": 2,
        "beta": 0.99
    }
    
    # Save
    registry.save_synapse("synapse_0", test_model, test_meta)
    
    # Load into a new instance
    new_model = DummySNN()
    loaded_meta = registry.load_synapse("synapse_0", new_model)
    
    if loaded_meta:
        print("SUCCESS: synapse Persistence functional.")
        print(f"Loaded Name: {loaded_meta['name']}")
