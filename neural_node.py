import trio
import os
import json
import sys
import torch
import torch.nn as nn
import snntorch as snn
import time

# --- Resilient Imports ---
try:
    from libp2p import new_host
    from libp2p.pubsub.pubsub import Pubsub
    from libp2p.pubsub.floodsub import FloodSub
    from multiaddr import Multiaddr
    from libp2p.tools.async_service import background_trio_service
    # Temporarily disabled for stability on Windows
    HAS_P2P = False 
except ImportError:
    HAS_P2P = False
    print("[WARN] libp2p not found. Running in Socket-Only mode.")

from shard_manager import ShardManager
from quantization import BinaryLinear
from pipeline_router import PipelineRouter
from pipeline_buffer import PipelineBuffer
from efficiency_monitor import EfficiencyMonitor
from spike_protocol import NeuralSpike, generate_task_id, hash_input

import datetime
from config import SynapseConfig
import requests
import datetime

conf = SynapseConfig()

# Sanitized Hub URL from environment or config
HUB_LOG_URL = os.getenv("CALYX_HUB_LOG_URL", f"{conf.get('node', 'hub_url')}/api/mesh/log")

def print_f(*args, **kwargs):
    text = " ".join(map(str, args))
    print(text, flush=True)
    
    # Task #27: Persistent Logging with PID
    try:
        # Resolve log path from environment or config
        log_path = os.getenv("CALYX_LOG_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "logs", "node_activity.jsonl"))
        log_entry = {
            "t": datetime.datetime.now().isoformat() + "Z",
            "pid": os.getpid(),
            "event": "NODE_LOG",
            "data": {"text": text}
        }
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")
            
        # Task #28: Real-time Mesh Stream (Broadcast to Hub)
        # Avoid infinite recursion if hub_server calls print_f (unlikely as it's separate)
        # Only nodes other than the Hub itself should stream here, but for now we filter by node_id in main
        if os.getenv("CALYX_NODE_ID", "NODE") != "PC_MASTER": 
            requests.post(HUB_LOG_URL, json={
                "node_id": os.environ.get("CALYX_NODE_ID", "NODE"),
                "event": "REMOTE_LOG",
                "data": {"text": text},
                "t": log_entry["t"]
            }, timeout=0.1)
    except Exception:
        pass

import socket
from functools import partial

# --- Configuration ---
TOPIC_ID = "synapse/synapse/0"
DISCOVERY_TOPIC = "synapse/mesh/discovery"
ADDR_FILE = "neuromorphic_env/current_node_addr.txt"
RAW_PORT = 60005 # Direct LAN fallback

# --- The "Mini-Brain" (Fully 1-bit BitNet) ---
num_inputs, num_hidden, num_outputs = 3, 8, 2
beta, vth = 0.99, 0.5
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

class MiniBrain(nn.Module):
    def __init__(self, layer_start=0, layer_end=5):
        super().__init__()
        self.layer_start = layer_start
        self.layer_end = layer_end
        self.fc1 = BinaryLinear(num_inputs, num_hidden)
        self.lif1 = snn.Leaky(beta=beta, threshold=vth)
        self.fc2 = BinaryLinear(num_hidden, num_outputs)
        self.lif2 = snn.Leaky(beta=beta, threshold=vth)
        self.mem1 = None
        self.mem2 = None

    def forward(self, x, layer_idx: int):
        """ Processes local layers starting from the current spike position. """
        current_x = x
        
        # Layer 0
        if layer_idx <= 0:
            if self.layer_start <= 0 <= self.layer_end:
                cur1 = self.fc1(current_x)
                spk1, self.mem1 = self.lif1(cur1, self.mem1)
                current_x = spk1
                layer_idx = 1 # Move to next local layer
            
        # Layer 1
        if layer_idx == 1:
            if self.layer_start <= 1 <= self.layer_end:
                cur2 = self.fc2(current_x)
                spk2, self.mem2 = self.lif2(cur2, self.mem2)
                current_x = spk2
                
        # Fast-forward through dummy layers to the end of our assigned shard
        return current_x, self.layer_end

# --- P2P Networking (Optional) ---
async def listen_loop(pubsub, node_id, spike_send_ch):
    if not HAS_P2P: return
    sub = await pubsub.subscribe(TOPIC_ID)
    while True:
        message = await sub.get()
        if message.from_id.to_string() == node_id: continue
        
        spike = NeuralSpike.from_bin(message.data)
        await spike_send_ch.send(spike)

# --- Direct Nerve (Sockets) ---
async def socket_server_loop(spike_send_ch):
    """ Secondary 'Direct Nerve' listener (Raw Sockets). """
    try:
        # Use Trio's high-level socket listener for better stability
        async def handler(stream):
            peer = stream.socket.getpeername()
            print_f(f"[DEBUG] Accepted connection from {peer}")
            try:
                data = await stream.receive_some(16384)
                if data:
                    print_f(f"[SOCKET] Raw data received: {len(data)} bytes")
                    spike = NeuralSpike.from_bin(data)
                    print_f(f"[SPIKE] Received! Task: {spike.task_id[:8]} | Layer: {spike.current_layer}")
                    await spike_send_ch.send(spike)
            except Exception as e:
                print_f(f"❌ Socket handler error: {e}")

        print_f(f"[SOCKET] Direct Nerve Listening on 0.0.0.0:{RAW_PORT}")
        await trio.serve_tcp(handler, RAW_PORT, host="0.0.0.0")
    except Exception as e:
        print_f(f"❌ Socket server crash: {e}")

async def discovery_listener(sub):
    if not HAS_P2P: return
    while True:
        message = await sub.get()
        await shard_mgr.handle_discovery_message(message)

async def thermal_monitor(eff_monitor, shard_mgr):
    """ Task #12: Background loop to protect the hardware. """
    while True:
        vitals = eff_monitor.check_thermal_health()
        is_healthy = vitals["is_safe"]
        for shard in shard_mgr.local_shards:
            if shard.is_ready != is_healthy:
                shard.is_ready = is_healthy
                status = "ONLINE" if is_healthy else "OFFLINE (OVERHEAT)"
                print_f(f"[THERMAL-GUARD] Shard {shard.model_name} is now {status}")
        await trio.sleep(10)

# --- Low Energy Probe (UDP Trigger) ---
async def probe_listener_loop(spike_send_ch):
    """ Task #27: Listens for low-energy UDP pings to trigger tests. """
    PROBE_PORT = 60006
    print_f(f"[PROBE] Listener active on UDP:{PROBE_PORT}")
    
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", PROBE_PORT))
        
        while True:
            try:
                data = await trio.to_thread.run_sync(s.recvfrom, 1024)
                msg_bin, sender_addr = data
                msg = json.loads(msg_bin.decode())
                
                if msg.get("type") == "PROBE_READY":
                    print_f(f"[PROBE] Received Mesh Probe from {msg['node_id']} ({sender_addr[0]})")
                    
                    # If we are the target or it's a 'FIRE' request, trigger a local spike
                    if msg.get("action") == "TRIGGER_SPIKE":
                        test_spike = NeuralSpike(
                            task_id=f"PROBE_{int(time.time())}",
                            synapse_id="Synapse-1.0",
                            node_id=NODE_ID_TEST,
                            input_hash="0xPROBE",
                            current_layer=0
                        )
                        test_spike.set_spikes([1, 1, 1])
                        await spike_send_ch.send(test_spike)
                        print_f("[PROBE] Triggered local spike injection!")
                        
            except Exception as e:
                # Log errors for Task #27 debugging
                if not isinstance(e, trio.WouldBlock):
                    print_f(f"❌ Probe Listener Error: {e}")
                await trio.sleep(0.1)

async def main():
    global NODE_ID_TEST, shard_mgr, router, brain, lan_ip
    print_f("!!! NEURAL NODE BOOTING !!!")

    # Task #01: Robust path resolution
    base_dir = os.path.dirname(os.path.abspath(__file__))
    discovery_path = os.path.join(base_dir, "mesh_discovery")
    config_path = os.path.join(base_dir, "shard_config.json")

    # 1. Identity & Config
    shard_mgr = ShardManager("TEMPORARY_ID", discovery_dir=discovery_path, config_path=config_path)
    NODE_ID_TEST = shard_mgr.node_id
    os.environ["CALYX_NODE_ID"] = NODE_ID_TEST # Set for log broadcasting
    lan_ip = shard_mgr.local_shards[0].node_ip if shard_mgr.local_shards else "127.0.0.1"
    
    print_f(f"--- Calyx Neural Node: {NODE_ID_TEST} ---")
    print_f(f"IP: {lan_ip}")

    eff_monitor = EfficiencyMonitor()

    # 2. Brain Initialization
    if shard_mgr.local_shards:
        s = shard_mgr.local_shards[0]
        brain = MiniBrain(s.layer_start, s.layer_end).to(device)
        print_f(f"[BRAIN] Shard Active: Layers {s.layer_start}-{s.layer_end}")
    else:
        brain = MiniBrain(0, 0).to(device)

    router = PipelineRouter(shard_mgr)
    
    # 3. Networking
    async with trio.open_nursery() as nursery:
        spike_send_ch, spike_recv_ch = trio.open_memory_channel(10)
        shard_mgr.file_spike_queue = spike_send_ch

        pubsub = None
        # Start P2P if available
        if HAS_P2P:
            listen_addr = Multiaddr(f"/ip4/{lan_ip}/tcp/60001")
            host = new_host()
            NODE_ID_TEST = host.get_id().to_string() # Update to actual Peer ID
            shard_mgr.node_id = NODE_ID_TEST # Sync with ShardManager
            
            pubsub = Pubsub(host, FloodSub())
            nursery.start_soon(listen_loop, pubsub, NODE_ID_TEST, spike_send_ch)
            # discovery
            sub = await pubsub.subscribe(DISCOVERY_TOPIC)
            nursery.start_soon(discovery_listener, sub)
            print_f(f"P2P ID: {host.get_id().to_string()}")

        # Start Fallbacks
        nursery.start_soon(socket_server_loop, spike_send_ch)
        nursery.start_soon(probe_listener_loop, spike_send_ch) # Task #27
        nursery.start_soon(thermal_monitor, eff_monitor, shard_mgr)
        nursery.start_soon(shard_mgr.broadcast_shards, pubsub) # Heartbeat
        nursery.start_soon(shard_mgr.poll_mesh_files)  # Incoming file spikes

        # 4. Processing Loop
        async for spike in spike_recv_ch:
            print_f(f"[SPIKE] Received! Task: {spike.task_id[:8]} | Layer: {spike.current_layer}")
            
            # TTL/Hop check (Task #15)
            if spike.hop_count >= spike.ttl:
                print_f(f"[WARN] Spike expired (TTL: {spike.ttl})")
                continue

            # Process locally
            input_tensor = torch.tensor(spike.get_spikes()).float().to(device)
            output_tensor, next_layer_idx = brain(input_tensor, spike.current_layer)
            
            # Route to next
            spike.hop_count += 1
            spike.current_layer = next_layer_idx
            spike.set_spikes(output_tensor.view(-1).tolist())
            
            dest, target_peer = router.route_spike(spike)
            if dest == "LOCAL":
                await spike_send_ch.send(spike)
            elif dest == "PEER":
                print_f(f"[ROUTING] to Peer: {target_peer}")
                await router.forward_spike(pubsub if HAS_P2P else None, TOPIC_ID, spike, target_peer)
            else:
                print_f(f"[FINISH] Task Complete: {spike.task_id[:8]}")
                # Response to Hub
                if NODE_ID_TEST != "PC_MASTER":
                    await router.forward_spike(pubsub if HAS_P2P else None, TOPIC_ID, spike, target_peer)

if __name__ == "__main__":
    try:
        trio.run(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print_f(f"Node Error: {e}")
        import traceback
        traceback.print_exc()
