import json
import os
import hashlib
import msgpack
import torch
import io
from typing import Dict

class synapsePackage:
    """
    Bundles SNN weights, architecture metadata, and integrity hashes 
    into a single '.synapse' binary file for mesh distribution.
    """
    def __init__(self, synapse_id: str):
        self.synapse_id = synapse_id

    def create_package(self, model_weights_path: str, metadata: Dict, output_path: str):
        print(f"[PACKAGER] Creating .synapse package for: {self.synapse_id}")
        
        # 1. Load weights as binary buffer
        with open(model_weights_path, "rb") as f:
            weights_bytes = f.read()
            
        # 2. Calculate Hash for Integrity (The 'Genome' Fingerprint)
        integrity_hash = hashlib.sha256(weights_bytes).hexdigest()
        metadata["integrity_hash"] = integrity_hash
        
        # 3. Bundle everything with MessagePack
        package_data = {
            "synapse_id": self.synapse_id,
            "metadata": metadata,
            "weights": weights_bytes
        }
        
        binary_package = msgpack.packb(package_data, use_bin_type=True)
        
        # 4. Write to disk
        with open(output_path, "wb") as f:
            f.write(binary_package)
            
        print(f"[PACKAGER] SUCCESS: {output_path} generated ({len(binary_package)} bytes)")
        print(f"[PACKAGER] Fingerprint: {integrity_hash[:16]}")

    def unpack_package(self, package_path: str) -> Dict:
        """Unpacks a .synapse file and returns weights and metadata."""
        with open(package_path, "rb") as f:
            data = msgpack.unpackb(f.read(), raw=False)
            
        # Verify Integrity
        weights = data["weights"]
        metadata = data["metadata"]
        current_hash = hashlib.sha256(weights).hexdigest()
        
        if current_hash != metadata["integrity_hash"]:
            raise ValueError("CRITICAL: synapse package integrity check failed! (Tampered Data)")
            
        print(f"[PACKAGER] Verified synapse: {data['synapse_id']}")
        return data

# --- Verification Test ---
if __name__ == "__main__":
    # Ensure directory exists
    if not os.path.exists("neuromorphic_env/packages"):
        os.makedirs("neuromorphic_env/packages")

    packager = synapsePackage("synapse_0_sentiment")
    
    # Path to the untrained weights we created earlier
    weights_in = "neuromorphic_env/synapses/synapse_0_untrained.pt"
    pkg_out = "neuromorphic_env/packages/synapse_0.synapse"
    
    meta = {
        "name": "Sentiment Alpha",
        "author": "Architect",
        "layers": "3-8-2",
        "beta": 0.95
    }
    
    # Pack
    packager.create_package(weights_in, meta, pkg_out)
    
    # Unpack and Verify
    try:
        unpacked = packager.unpack_package(pkg_out)
        print("SUCCESS: Package is portable and verified.")
    except Exception as e:
        print(f"Error: {e}")
