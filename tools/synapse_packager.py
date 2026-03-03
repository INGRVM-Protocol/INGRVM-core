import os
import sys
import json
import zipfile
import hashlib

def package_synapse(synapse_id):
    """
    Bundles a synapse (manifest, weights, and logic) into a .calyx file.
    Includes a SHA-256 fingerprint for integrity verification.
    """
    syn_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "synapses")
    pkg_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "packages")
    
    if not os.path.exists(pkg_dir):
        os.makedirs(pkg_dir)

    print(f"--- 📦 PACKAGING SYNAPSE: {synapse_id} ---")

    # Files to include (Phase 4: Added Sharding Info)
    files_to_pack = {
        "manifest": f"{synapse_id}.json",
        "weights": f"{synapse_id}.pt",
        "logic": f"train_{synapse_id}.py",
        "shards": "shard_config.json"
    }

    output_path = os.path.join(pkg_dir, f"{synapse_id}.synapse")
    
    try:
        with zipfile.ZipFile(output_path, 'w') as zipf:
            # Add core files
            for key, filename in files_to_pack.items():
                if key == "shards":
                    # Look for shard_config in the Core dir
                    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filename)
                else:
                    file_path = os.path.join(syn_dir, filename)
                
                if os.path.exists(file_path):
                    zipf.write(file_path, arcname=filename)
                    print(f"  [+] Added {key}: {filename}")
                else:
                    if key != "shards": # Shards are optional but recommended
                        print(f"  [-] WARNING: {key} ({filename}) missing. Skipping.")

        # Generate Integrity Hash
        with open(output_path, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
        
        print(f"\nSUCCESS: Synapse packaged at {output_path}")
        print(f"FINGERPRINT: {file_hash[:16]}...")
        
    except Exception as e:
        print(f"ERROR: Packaging failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python synapse_packager.py <synapse_id>")
    else:
        package_synapse(sys.argv[1])
