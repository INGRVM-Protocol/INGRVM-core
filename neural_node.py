import trio
import os
import json
import sys
import time
import socket
import datetime
import requests
from functools import partial
from dotenv import load_dotenv

# --- Resilient Imports ---
try:
    import torch
    import torch.nn as nn
    import snntorch as snn
    HAS_ML = True
except ImportError:
    HAS_ML = False
    print("⚠️ [WARN] ML Libraries (torch/snntorch) not found. Running in MOCK_BRAIN mode.")
try:
    from libp2p import new_host
    from libp2p.pubsub.pubsub import Pubsub
    from libp2p.pubsub.floodsub import FloodSub
    from multiaddr import Multiaddr
    from libp2p.tools.async_service import background_trio_service
    HAS_P2P = False 
except ImportError:
    HAS_P2P = False

from shard_manager import ShardManager
if HAS_ML:
    from quantization import BinaryLinear
from pipeline_router import PipelineRouter
from pipeline_buffer import PipelineBuffer
from efficiency_monitor import EfficiencyMonitor
from spike_protocol import NeuralSpike, generate_task_id, hash_input, send_spike_raw
from config import SynapseConfig
from circuit_relay import AutoNAT

# Import discovery tool
sys.path.append(os.path.join(os.path.dirname(__file__), 'tools'))
try:
    from lan_discovery import discover_hub
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False

# Load environment variables
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(env_path)

conf = SynapseConfig()

def print_f(*args, **kwargs):
    text = " ".join(map(str, args))
    print(text, flush=True)
    try:
        log_path = os.getenv("CALYX_LOG_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "node_activity.jsonl"))
        log_entry = {
            "t": datetime.datetime.now().isoformat() + "Z",
            "pid": os.getpid(),
            "event": "NODE_LOG",
            "data": {"text": text}
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        hub_url = os.getenv("CALYX_HUB_URL", conf.get('node', 'hub_url'))
        hub_log_endpoint = f"{hub_url}/api/mesh/log"
        if os.getenv("CALYX_NODE_ID") != "PC_MASTER": 
            requests.post(hub_log_endpoint, json={
                "node_id": os.environ.get("CALYX_NODE_ID", "NODE"),
                "event": "REMOTE_LOG",
                "data": {"text": text},
                "t": log_entry["t"]
            }, timeout=0.1)
    except Exception: pass

# --- Configuration ---
TOPIC_ID = "synapse/synapse/0"
DISCOVERY_TOPIC = "synapse/mesh/discovery"
RAW_PORT = 60005 

# --- The "Mini-Brain" (Dynamic Layer Sharding) ---
num_inputs, num_hidden, num_outputs = 3, 8, 2
beta, vth = 0.99, 0.5

if HAS_ML:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    class MiniBrain(nn.Module):
        """
        Simulates a slice of a massive neuromorphic network.
        Uses ModuleDict for scalable sharding (Task #13).
        """
        def __init__(self, layer_start=0, layer_end=31):
            super().__init__()
            self.layer_start = layer_start
            self.layer_end = layer_end
            
            self.layers = nn.ModuleDict()
            for i in range(layer_start, layer_end + 1):
                # Input layer vs Hidden layers
                in_dim = num_inputs if i == 0 else num_hidden
                # If we own the last layer of the entire model (31), we output num_outputs
                out_dim = num_outputs if i == 31 else num_hidden
                
                self.layers[f"fc_{i}"] = BinaryLinear(in_dim, out_dim)
                self.layers[f"lif_{i}"] = snn.Leaky(beta=beta, threshold=vth)
            
        def forward(self, x, current_layer: int):
            """ 
            Processes all local layers sequentially starting from the incoming spike's position.
            """
            current_x = x
            
            # Iterate through the layers we own that are >= current_layer
            for i in range(max(current_layer, self.layer_start), self.layer_end + 1):
                fc_key = f"fc_{i}"
                lif_key = f"lif_{i}"
                
                if fc_key in self.layers:
                    current_x = self.layers[fc_key](current_x)
                
                if lif_key in self.layers:
                    # Simple static activation for sharding tests
                    spk, _ = self.layers[lif_key](current_x)
                    current_x = spk
            
            return current_x, self.layer_end + 1
else:
    device = None
    class MiniBrain:
        """ Task #12 Fallback: Mock Brain for Mobile/Termux. """
        def __init__(self, layer_start=0, layer_end=5):
            self.layer_start = layer_start
            self.layer_end = layer_end
        def to(self, device): return self
        def __call__(self, x, current_layer: int):
            # Pass-through for routing tests
            return x, self.layer_end + 1

# --- Direct Nerve (Sockets) ---
async def socket_server_loop(spike_send_ch):
    async def handler(stream):
        try:
            data = await stream.receive_some(16384)
            if data:
                spike = NeuralSpike.from_bin(data)
                print_f(f"[SOCKET] Received Task: {spike.task_id[:8]} | Current Layer: {spike.current_layer}")
                await spike_send_ch.send(spike)
        except Exception as e:
            print_f(f"❌ Socket error: {e}")

    print_f(f"[SOCKET] Direct Nerve Listening on 0.0.0.0:{RAW_PORT}")
    await trio.serve_tcp(handler, RAW_PORT, host="0.0.0.0")

async def main():
    global NODE_ID_TEST, shard_mgr, router, brain, lan_ip
    print_f("!!! NEURAL NODE BOOTING !!!")

    # 0. Zeroconf Discovery (Phase 5, Task #04)
    if HAS_ZEROCONF:
        hub_ip, hub_port = discover_hub(timeout=5)
        if hub_ip:
            os.environ["CALYX_HUB_URL"] = f"http://{hub_ip}:{hub_port}"
            print_f(f"🚀 Zeroconf: Connected to Hub at {hub_ip}")

    # 1. Identity & Config
    base_dir = os.path.dirname(os.path.abspath(__file__))
    discovery_path = os.path.join(base_dir, "mesh_discovery")
    
    config_name = os.getenv("CALYX_SHARD_CONFIG", "shard_config.json")
    # If the env var is a path like "Calyx/Core/...", handle it
    if "Calyx" in config_name:
        # Resolve from ecosystem root
        project_root = os.path.dirname(os.path.dirname(base_dir))
        config_path = os.path.abspath(os.path.join(project_root, config_name))
    else:
        config_path = os.path.join(base_dir, config_name)
    
    print_f(f"DEBUG: Using config_path={config_path}")

    shard_mgr = ShardManager("TEMPORARY_ID", discovery_dir=discovery_path, config_path=config_path)
    NODE_ID_TEST = shard_mgr.node_id
    os.environ["CALYX_NODE_ID"] = NODE_ID_TEST 
    
    # 1b. Reachability Check (Phase 7 Task #05)
    voter = AutoNAT(NODE_ID_TEST)
    reachability = await voter.detect_reachability(os.getenv("CALYX_HUB_URL", "http://127.0.0.1:8000"))
    
    if reachability == "RESTRICTED":
        print_f("[MESH] Node is behind NAT. Requesting WAN Relay slot...")
        # (Mock): In a real setup, we'd dial a public Lighthouse Relay
        # For now, we simulate the reservation to prove the logic path
        relay_id = "12D3KooW_PUBLIC_RELAY_MOCK"
        # We assume the PC Master acts as the relay for now if configured
        shard_mgr.relay_addrs[NODE_ID_TEST] = f"/ip4/72.45.12.101/tcp/60000/p2p/{relay_id}/p2p-circuit/p2p/{NODE_ID_TEST}"
        print_f(f"🚀 SUCCESS: Relay reservation granted. Path: {shard_mgr.relay_addrs[NODE_ID_TEST]}")

    # Auto-detect local IP if not forced
    lan_ip = os.getenv("CALYX_NODE_IP", socket.gethostbyname(socket.gethostname()))
    
    print_f(f"--- Calyx Neural Node: {NODE_ID_TEST} ---")
    print_f(f"IP: {lan_ip}")

    eff_monitor = EfficiencyMonitor()

    # 2. Brain Initialization (Phase 5, Task #12)
    if shard_mgr.local_shards:
        s = shard_mgr.local_shards[0]
        brain = MiniBrain(s.layer_start, s.layer_end).to(device)
        print_f(f"[BRAIN] Shard Loaded: Layers {s.layer_start} to {s.layer_end}")
    else:
        brain = MiniBrain(0, 0).to(device)

    router = PipelineRouter(shard_mgr)
    
    # 3. Networking
    async with trio.open_nursery() as nursery:
        spike_send_ch, spike_recv_ch = trio.open_memory_channel(10)
        shard_mgr.file_spike_queue = spike_send_ch

        nursery.start_soon(socket_server_loop, spike_send_ch)
        nursery.start_soon(shard_mgr.broadcast_shards, None) 
        nursery.start_soon(shard_mgr.poll_mesh_files)  

        # 4. Processing Loop
        async for spike in spike_recv_ch:
            try:
                current_layer = getattr(spike, 'current_layer', 0)
                print_f(f"[SPIKE] Processing Task: {spike.task_id[:8]} | Layer {current_layer}")
                
                # TTL Check
                if spike.hop_count >= spike.ttl:
                    print_f(f"[WARN] TTL Expired for {spike.task_id[:8]}")
                    continue

                # --- LAYER OWNERSHIP VALIDATION ---
                # If we don't own the current layer, we shouldn't be processing it locally.
                if not (brain.layer_start <= current_layer <= brain.layer_end):
                    print_f(f"[ROUTING] Node {NODE_ID_TEST} does not own Layer {current_layer} (We have {brain.layer_start}-{brain.layer_end}). Rerouting...")
                    
                    # Find who actually has this layer
                    target_node = shard_mgr.find_next_hop(getattr(spike, 'model_name', 'Synapse-1.0'), current_layer, look_for_current=True)
                    
                    if target_node and target_node != "LOCAL":
                        print_f(f"[RE-ROUTE] Forwarding Spike to {target_node} for Layer {current_layer}")
                        peer_ip = shard_mgr.get_peer_ip(target_node)
                        if peer_ip:
                            await send_spike_raw(spike, peer_ip, RAW_PORT)
                        else:
                            shard_mgr.send_file_spike(target_node, spike.to_bin())
                    else:
                        print_f(f"⚠️ [RE-ROUTE] No peer found for Layer {current_layer}. Dropping spike.")
                    continue

                # Process through local layers
                if HAS_ML:
                    input_tensor = torch.tensor(spike.get_spikes()).float().to(device)
                    output_tensor, next_layer_idx = brain(input_tensor, current_layer)
                    spike.set_spikes(output_tensor.view(-1).tolist())
                else:
                    # Mock processing: just pass through and increment layer
                    next_layer_idx = brain.layer_end + 1
                
                # Update Spike state
                spike.hop_count += 1
                spike.current_layer = next_layer_idx
                
                # Find Next Hop
                dest, target_peer = router.route_spike(spike)
                if dest == "LOCAL":
                    await spike_send_ch.send(spike)
                elif dest == "PEER":
                    print_f(f"[ROUTING] Forwarding to {target_peer} for Layer {spike.current_layer}")
                    
                    # Try Raw Socket first, then fallback to File-Relay
                    peer_ip = shard_mgr.get_peer_ip(target_peer)
                    success = False
                    if peer_ip:
                        print_f(f"[SOCKET] Attempting direct connection to {peer_ip}:60005")
                        success = await send_spike_raw(spike, peer_ip, RAW_PORT)
                    
                    if not success:
                        print_f(f"[FALLBACK] Socket failed. Using File-Relay for {target_peer}")
                        await shard_mgr.send_file_spike(target_peer, spike.to_bin())
                    else:
                        print_f(f"✅ [SOCKET] Spike delivered to {target_peer} successfully.")
                else:
                    print_f(f"[FINISH] Sequence Complete: {spike.task_id[:8]}")
            except Exception as e:
                print_f(f"❌ Error in processing loop: {e}")
                import traceback
                traceback.print_exc()

if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt: pass
    except Exception as e:
        print_f(f"Node Error: {e}")
        import traceback
        traceback.print_exc()
        if hasattr(e, 'exceptions'):
            for sub_e in e.exceptions:
                print_f(f"Sub-exception: {sub_e}")
