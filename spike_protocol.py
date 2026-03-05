import json
import time
import hashlib
import msgpack
from typing import List, Optional

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False

if HAS_PYDANTIC:
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

        def to_bin(self) -> bytes:
            """Returns ultra-compact MessagePack binary."""
            return msgpack.packb(self.model_dump(), use_bin_type=True)

        @classmethod
        def from_bin(cls, data: bytes):
            unpacked = msgpack.unpackb(data, raw=False)
            return cls(**unpacked)
else:
    class NeuralSpike:
        """ Fallback for environments without Pydantic (e.g. some Termux builds). """
        def __init__(self, **kwargs):
            self.task_id = kwargs.get('task_id')
            self.synapse_id = kwargs.get('synapse_id')
            self.node_id = kwargs.get('node_id')
            self.timestamp = kwargs.get('timestamp', time.time())
            self.current_layer = kwargs.get('current_layer', 0)
            self.target_layer = kwargs.get('target_layer')
            self.model_name = kwargs.get('model_name', "Synapse-1.0")
            self.ttl = kwargs.get('ttl', 10)
            self.hop_count = kwargs.get('hop_count', 0)
            self.sparse_indices = kwargs.get('sparse_indices', [])
            self.vector_size = kwargs.get('vector_size', 0)
            self.input_hash = kwargs.get('input_hash')
            self.witness_hash = kwargs.get('witness_hash')
            self.signature = kwargs.get('signature')

        def set_spikes(self, dense_spikes: List[int]):
            self.vector_size = len(dense_spikes)
            self.sparse_indices = [i for i, val in enumerate(dense_spikes) if val > 0]

        def get_spikes(self) -> List[int]:
            dense = [0] * self.vector_size
            for idx in self.sparse_indices:
                if idx < self.vector_size:
                    dense[idx] = 1
            return dense

        def to_dict(self):
            return {
                "task_id": self.task_id,
                "synapse_id": self.synapse_id,
                "node_id": self.node_id,
                "timestamp": self.timestamp,
                "current_layer": self.current_layer,
                "target_layer": self.target_layer,
                "model_name": self.model_name,
                "ttl": self.ttl,
                "hop_count": self.hop_count,
                "sparse_indices": self.sparse_indices,
                "vector_size": self.vector_size,
                "input_hash": self.input_hash,
                "witness_hash": self.witness_hash,
                "signature": self.signature
            }

        def to_bin(self) -> bytes:
            return msgpack.packb(self.to_dict(), use_bin_type=True)

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