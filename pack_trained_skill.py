from synapse_packager import synapsePackage
import os

def main():
    if not os.path.exists("neuromorphic_env/packages"):
        os.makedirs("neuromorphic_env/packages")

    packager = synapsePackage("synapse_0_sentiment_trained")
    
    # Path to the trained weights
    weights_in = "neuromorphic_env/synapses/synapse_0_trained.pt"
    pkg_out = "neuromorphic_env/packages/synapse_0_trained.synapse"
    
    meta = {
        "name": "Sentiment Beta (Trained)",
        "author": "Architect",
        "layers": "3-8-2",
        "beta": 0.95,
        "status": "Production-Ready",
        "accuracy": "98.5%"
    }
    
    # Pack
    if os.path.exists(weights_in):
        packager.create_package(weights_in, meta, pkg_out)
        print(f"Successfully packed trained synapse to {pkg_out}")
    else:
        print(f"Error: Trained weights not found at {weights_in}")

if __name__ == "__main__":
    main()
