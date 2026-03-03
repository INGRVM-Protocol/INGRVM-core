import trio
import os
import sys
import subprocess

# This version runs the logic in parallel but via a single Trio nursery 
# to mirror the successful debug test.

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

NODE_SCRIPT = "neuromorphic_env/neural_node.py"
SENDER_SCRIPT = "neuromorphic_env/spike_sender.py"
ADDR_FILE = "neuromorphic_env/current_node_addr.txt"

async def run_node(nursery):
    print_f("[MASTER] Launching Neural Node...")
    # We use Popen but manage it via Trio if possible, or just standard Popen
    proc = subprocess.Popen([sys.executable, NODE_SCRIPT])
    return proc

async def run_sender():
    print_f("[MASTER] Waiting for node to publish address...")
    while not os.path.exists(ADDR_FILE):
        await trio.sleep(0.5)
    
    print_f("[MASTER] Node is ready. Launching Spike Sender...")
    # Run sender and wait for it
    sender_proc = subprocess.run([sys.executable, SENDER_SCRIPT])
    return sender_proc

async def main():
    print_f("--- Starting Virtual Mesh Orchestrator (Unified) ---")
    if os.path.exists(ADDR_FILE): os.remove(ADDR_FILE)

    node_proc = None
    try:
        node_proc = subprocess.Popen([sys.executable, NODE_SCRIPT])
        await run_sender()
    finally:
        if node_proc:
            print_f("[MASTER] Cleaning up...")
            node_proc.terminate()
            node_proc.wait()

if __name__ == "__main__":
    trio.run(main)
