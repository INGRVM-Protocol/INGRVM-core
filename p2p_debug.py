import trio
import torch
import torch.nn as nn
from collections import OrderedDict
from libp2p import new_host
from libp2p.pubsub.pubsub import Pubsub
from libp2p.pubsub.floodsub import FloodSub
from libp2p.security.insecure.transport import InsecureTransport
from multiaddr import Multiaddr
from libp2p.peer.id import ID as PeerID
from libp2p.peer.peerinfo import PeerInfo
from libp2p.tools.async_service import background_trio_service
from spike_protocol import NeuralSpike, generate_task_id, hash_input
from libp2p.crypto.ed25519 import create_new_key_pair
import os
import logging
import sys

# Protocol for Insecure Transport
# Important: Use the protocol ID defined in the libp2p library
PLAINTEXT_PROTOCOL_ID = "/plaintext/2.0.0"

def print_f(*args, **kwargs):
    print(*args, **kwargs, flush=True)

TOPIC_ID = "synapse/synapse/0"
ADDR_FILE = "neuromorphic_env/p2p_test_addr.txt"
LAN_IP = "192.168.68.52" # The PC's LAN IP

def make_insecure_host(listen_addrs):
    """
    Creates a libp2p host that ONLY uses insecure (plaintext) transport.
    Uses 'sec_opt' as identified via function inspection.
    """
    key_pair = create_new_key_pair()
    
    # Force the security transport to be insecure
    # Map protocol ID to the transport instance
    insecure_opt = {PLAINTEXT_PROTOCOL_ID: InsecureTransport(key_pair)}
    
    return new_host(
        key_pair=key_pair,
        listen_addrs=listen_addrs,
        sec_opt=insecure_opt
    )

async def run_node_a():
    """ The Receiver (Server) - Runs on PC """
    print_f("[NODE A] Initializing INSECURE node on LAN IP: " + LAN_IP)
    
    listen_addr = Multiaddr(f"/ip4/{LAN_IP}/tcp/60001")
    host = make_insecure_host([listen_addr])
    
    router = FloodSub(protocols=['/floodsub/1.0.0'])
    pubsub = Pubsub(host, router)
    
    async with host.run(listen_addrs=[listen_addr]), background_trio_service(pubsub), trio.open_nursery() as nursery:
        full_addr = f"/ip4/{LAN_IP}/tcp/60001/p2p/{host.get_id().to_string()}"
        with open(ADDR_FILE, "w") as f: f.write(full_addr)
        
        print_f(f"\n--- [NODE A ONLINE - PLAINTEXT MODE] ---")
        print_f(f"Address: {full_addr}")
        print_f("READY. Awaiting spikes...")
        
        sub = await pubsub.subscribe(TOPIC_ID)
        
        while True:
            message = await sub.get()
            try:
                spike = NeuralSpike.from_bin(message.data)
                if spike.node_id == "NODE_A": continue 
                
                print_f(f"\n[RECEIVE] Spike from {spike.node_id} (Task: {spike.task_id})")
                
                ack = NeuralSpike(
                    task_id=spike.task_id,
                    synapse_id=spike.synapse_id,
                    node_id="NODE_A",
                    input_hash=spike.input_hash
                )
                ack.set_spikes([1])
                await pubsub.publish(TOPIC_ID, ack.to_bin())
                print_f(f"[SEND] ACK sent for Task {spike.task_id}")
            except Exception as e:
                print_f(f"[ERROR] {e}")

async def run_node_b():
    """ The Initiator (Client) - Runs on Laptop """
    print_f("[NODE B] Searching for Node A at " + ADDR_FILE)
    
    while not os.path.exists(ADDR_FILE):
        await trio.sleep(1.0)
    
    with open(ADDR_FILE, "r") as f:
        addr_str = f.read().strip()
    
    maddr = Multiaddr(addr_str)
    peer_id_str = maddr.value_for_protocol(0x1a5)
    peer_id = PeerID.from_string(peer_id_str)
    
    target_multiaddr = Multiaddr(f"/ip4/{LAN_IP}/tcp/60001")
    peer_info = PeerInfo(peer_id, [target_multiaddr])
    
    # Client MUST also use insecure transport
    # Provide a random local port to satisfy new_host requirements
    client_listen = Multiaddr("/ip4/127.0.0.1/tcp/0")
    host = make_insecure_host([client_listen])
    router = FloodSub(protocols=['/floodsub/1.0.0'])
    pubsub = Pubsub(host, router)
    
    async with host.run(listen_addrs=[]), background_trio_service(pubsub), trio.open_nursery() as nursery:
        print_f("[NODE B] Handshaking (PLAINTEXT)...")
        await host.connect(peer_info)
        print_f("[NODE B] SUCCESS: Connected to PC!")
        
        sub = await pubsub.subscribe(TOPIC_ID)
        await trio.sleep(2)
        
        spike = NeuralSpike(
            task_id=generate_task_id("NODE_B", "synapse_0"),
            synapse_id="synapse_0",
            node_id="NODE_B",
            input_hash=hash_input("Plaintext Test")
        )
        spike.set_spikes([1, 1, 1])
        
        print_f(f"\n[SEND] Publishing Spike (Task: {spike.task_id})")
        await pubsub.publish(TOPIC_ID, spike.to_bin())
        
        print_f("[WAIT] Awaiting ACK from PC...")
        with trio.fail_after(10):
            while True:
                message = await sub.get()
                resp = NeuralSpike.from_bin(message.data)
                if resp.node_id == "NODE_A":
                    print_f(f"\n[SUCCESS] ACK Received from PC!")
                    return

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python p2p_debug.py <a|b>")
    elif sys.argv[1].lower() == 'a':
        trio.run(run_node_a)
    elif sys.argv[1].lower() == 'b':
        trio.run(run_node_b)
