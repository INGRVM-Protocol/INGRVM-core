import json
import time
import hashlib
import msgpack
from pydantic import BaseModel, Field
from typing import List, Optional

class NeuralSpike(BaseModel):
    """
    The 'Blockchain-Ready' protocol for neuromorphic data transmission.
    Optimized with Sparse-Vector Encoding for massive bandwidth reduction.
    """
    task_id: str
    synapse_id: str
    node_id: str
    timestamp: float = Field(default_factory=time.time)
    
    # PIPELINE ROUTING
    current_layer: int = 0
    target_layer: Optional[int] = None
    model_name: str = "Synapse-1.0"
    
    # MESH SAFETY (Task #04)
    ttl: int = 10 # Max hops before the spike is dropped
    hop_count: int = 0
    
    # OPTIMIZATION: Sparse Encoding
    # Instead of [0,0,1,0,1], we send indices [2, 4] and the total size.
    sparse_indices: List[int] = []
    vector_size: int = 0
    
    input_hash: str
    witness_hash: Optional[str] = None
    signature: Optional[str] = None

    def set_spikes(self, dense_spikes: List[int]):
        """Converts a dense list to sparse indices."""
        self.vector_size = len(dense_spikes)
        self.sparse_indices = [i for i, val in enumerate(dense_spikes) if val > 0]

    def get_spikes(self) -> List[int]:
        """Reconstructs the dense list from sparse indices."""
        dense = [0] * self.vector_size
        for idx in self.sparse_indices:
            if idx < self.vector_size:
                dense[idx] = 1
        return dense

    # --- Serialization ---

    def to_bin(self) -> bytes:
        """Returns ultra-compact MessagePack binary."""
        return msgpack.packb(self.model_dump(), use_bin_type=True)

    @classmethod
    def from_bin(cls, data: bytes):
        unpacked = msgpack.unpackb(data, raw=False)
        return cls(**unpacked)

# --- LAN Socket Helper ---
import socket
import trio

async def send_spike_raw(spike: 'NeuralSpike', ip: str, port: int = 60005) -> bool:
    """Sends a spike via raw TCP socket (Trio-friendly)."""
    try:
        # Use Trio high-level API for non-blocking connect
        async with await trio.open_tcp_stream(ip, port) as stream:
            await stream.send_all(spike.to_bin())
            return True
    except Exception:
        return False

def generate_task_id(node_id: str, synapse_id: str) -> str:
    raw_id = f"{node_id}-{synapse_id}-{time.time()}"
    return hashlib.sha256(raw_id.encode()).hexdigest()[:16]

def hash_input(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

# --- Optimization Test ---
if __name__ == "__main__":
    # Simulate a layer of 1000 neurons where only 5 fire (Typical SNN sparsity)
    dense_data = [0] * 1000
    dense_data[42] = 1
    dense_data[123] = 1
    dense_data[500] = 1
    
    spike = NeuralSpike(
        task_id=generate_task_id("TEST_NODE", "synapse_0"),
        synapse_id="synapse_0",
        node_id="TEST_NODE",
        input_hash=hash_input("Sparse Test")
    )
    spike.set_spikes(dense_data)
    
    # Compare size with old dense method (mocked)
    dense_json_size = len(json.dumps(dense_data)) + 200 # Approx metadata
    sparse_bin_size = len(spike.to_bin())
    
    print("--- Sparse-Vector Optimization Results ---")
    print(f"Original (Dense) Size: ~{dense_json_size} bytes")
    print(f"Sparse Binary Size:     {sparse_bin_size} bytes")
    print(f"Bandwidth Reduction:    {((dense_json_size - sparse_bin_size) / dense_json_size) * 100:.1f}%")
    
    # Verify reconstruction
    reconstructed = spike.get_spikes()
    if reconstructed[123] == 1 and sum(reconstructed) == 3:
        print("\nSUCCESS: Sparse reconstruction is perfect and highly efficient.")
