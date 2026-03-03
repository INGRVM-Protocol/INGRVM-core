import json
import os

class NodeNamer:
    """
    UX Engine: Maps cryptographic PeerIDs to human-readable names.
    Example: 12D3... -> "The_Architect_PC"
    """
    def __init__(self, mapping_path: str = "node_names.json"):
        self.mapping_path = mapping_path
        self.names = self.load_names()

    def load_names(self):
        if os.path.exists(self.mapping_path):
            with open(self.mapping_path, "r") as f:
                return json.load(f)
        return {}

    def set_name(self, peer_id: str, name: str):
        self.names[peer_id] = name
        with open(self.mapping_path, "w") as f:
            json.dump(self.names, f, indent=4)
        print(f"[NAMER] Peer {peer_id[:8]}... is now known as '{name}'")

    def get_name(self, peer_id: str) -> str:
        return self.names.get(peer_id, peer_id[:12] + "...")

# --- Verification Test ---
if __name__ == "__main__":
    test_path = os.path.join(os.path.dirname(__file__), "..", "tests", "test_names.json")
    namer = NodeNamer(test_path)
    
    mock_id = "12D3KooWGvGysq8okeVg5U5rbAsfpt8HXG1DRvLx7t1hvT2egeJS"
    namer.set_name(mock_id, "Austin_Backbone_PC")
    
    friendly = namer.get_name(mock_id)
    print(f"ID: {mock_id[:12]}...")
    print(f"Human Name: {friendly}")
    
    if friendly == "Austin_Backbone_PC":
        print("\nSUCCESS: Node naming system is functional.")
        
    if os.path.exists(test_path):
        os.remove(test_path)
