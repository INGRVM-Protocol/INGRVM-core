import trio
import os
import json
import sys
from libp2p import new_host
from multiaddr import Multiaddr
from libp2p.tools.async_service import background_trio_service

from config import SynapseConfig

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

BEACON_ADDR_FILE = "neuromorphic_env/bootstrap_beacon_addr.txt"

async def main():
    """
    The Lighthouse: A stable libp2p node that facilitates mesh discovery.
    Running this on the PC provides a static target for the Laptop/Mobile nodes.
    """
    conf = SynapseConfig()
    print_f("--- Starting Synapse Lighthouse (Bootstrap Relay) ---")
    
    # 1. Identity & Network
    # Use config for IP and Port, default to a lighthouse-specific port if needed
    # but for now we follow the mesh p2p_port.
    lan_ip = conf.get("node", "lan_ip") or "0.0.0.0" 
    p2p_port = 60000 # Keep 60000 for lighthouse specifically? 
    # Actually, let's use a dedicated config key for lighthouse port if we want it fixed.
    
    listen_addr = Multiaddr(f"/ip4/{lan_ip}/tcp/{p2p_port}")
    
    host = new_host()
    node_id = host.get_id().to_string()
    
    async with host.run(listen_addrs=[listen_addr]):
        full_addr = f"/ip4/{lan_ip}/tcp/60000/p2p/{node_id}"
        
        # Save address so other nodes can find it
        with open(BEACON_ADDR_FILE, "w") as f:
            f.write(full_addr)
            
        print_f(f"[LIGHTHOUSE] ID: {node_id}")
        print_f(f"[LIGHTHOUSE] Listening on: {full_addr}")
        print_f("[LIGHTHOUSE] Status: ONLINE. Awaiting mesh connections...")
        
        # The lighthouse just stays alive to provide a stable peer for others to dial.
        # libp2p handles the 'Relay' and 'Identify' logic internally once connected.
        await trio.sleep_forever()

if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt:
        if os.path.exists(BEACON_ADDR_FILE): os.remove(BEACON_ADDR_FILE)
    except Exception as e:
        print_f(f"[ERROR] Lighthouse: {e}")
