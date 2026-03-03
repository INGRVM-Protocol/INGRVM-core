import os
import sys
import json
import torch

def scaffold_synapse(name):
    """
    Scaffolds a new Calyx AI synapse.
    Generates the manifest, placeholder model, and training template.
    """
    safe_name = name.lower().replace(" ", "_")
    synapses_dir = "synapses"
    if not os.path.exists(synapses_dir):
        os.makedirs(synapses_dir)

    print(f"--- 🧬 SCAFFOLDING NEW synapse: {name} ---")

    # 1. Generate Manifest (.json)
    manifest = {
        "id": safe_name,
        "name": name,
        "version": "0.1.0",
        "category": "General",
        "description": f"Initial scaffold for {name}",
        "architecture": {
            "num_inputs": 100,
            "num_hidden": 64,
            "num_outputs": 10
        }
    }
    
    manifest_path = os.path.join(synapses_dir, f"{safe_name}.json")
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=4)
    print(f"  [+] Created Manifest: {manifest_path}")

    # 2. Create Training Template (.py)
    template = f'''import torch
import snntorch as snn
from snntorch import surrogate

def train_{safe_name}():
    print("Initializing {name} Training Loop...")
    # Define your SNN architecture here
    # Use surrogate gradients for backpropagation
    pass

if __name__ == "__main__":
    train_{safe_name}()
'''
    template_path = os.path.join(synapses_dir, f"train_{safe_name}.py")
    with open(template_path, "w") as f:
        f.write(template)
    print(f"  [+] Created Training Template: {template_path}")

    # 3. Placeholder Model (.pt)
    dummy_weights = torch.randn((100, 100))
    model_path = os.path.join(synapses_dir, f"{safe_name}.pt")
    torch.save(dummy_weights, model_path)
    print(f"  [+] Created Placeholder Model: {model_path}")

    print(f"\nSUCCESS: synapse '{name}' is ready for development.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python new_synapse.py 'Your synapse Name'")
    else:
        scaffold_synapse(sys.argv[1])
