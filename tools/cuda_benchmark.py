import torch
import torch.nn as nn
import time
from hardware_monitor import HardwareProtector
from quantization import BinaryLinear

def run_benchmark(dim=4096, batch_size=128):
    """
    Benchmarks the 1080 Ti performance on 1-bit vs 32-bit weights.
    We aim for 10x-30x theoretical throughput on neuromorphic hardware.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    monitor = HardwareProtector()
    
    print(f"--- 1080 Ti 'Crush' Mode Benchmark ---")
    print(f"Device: {device}")
    print(f"Dim:    {dim}x{dim}")
    print(f"Batch:  {batch_size}")
    
    # 1. Hardware Safeguard Check
    safe, msg = monitor.check_safeguards()
    if not safe:
        print(f"⚠️ {msg}")
        return

    # 2. Setup Layers
    dense_layer = nn.Linear(dim, dim).to(device)
    binary_layer = BinaryLinear(dim, dim).to(device)
    
    # 3. Benchmark Standard (32-bit)
    input_data = torch.randn((batch_size, dim)).to(device)
    
    # Warmup
    for _ in range(5):
        _ = dense_layer(input_data)
        _ = binary_layer(input_data)
    
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    
    start = time.time()
    for _ in range(100):
        _ = dense_layer(input_data)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    dense_time = (time.time() - start) / 100
    
    # 4. Benchmark Binary (1-bit Simulated)
    start = time.time()
    for _ in range(100):
        _ = binary_layer(input_data)
    torch.cuda.synchronize() if torch.cuda.is_available() else None
    binary_time = (time.time() - start) / 100
    
    # 5. Measure VRAM Savings (Theory vs Practice)
    param_count = dim * dim
    standard_vram_mb = (param_count * 4) / 1024**2 # 32-bit float = 4 bytes
    packed_vram_mb = (param_count / 8) / 1024**2    # 1-bit packed = 1/8 byte
    
    # 6. Report
    print(f"\n[RESULTS]:")
    print(f"Standard (32-bit): {dense_time*1000:.3f} ms / step")
    print(f"Binary (1-bit):   {binary_time*1000:.3f} ms / step")
    
    print(f"\n[VRAM PROJECTION (Dim {dim})]:")
    print(f"Standard Memory:  {standard_vram_mb:.2f} MB")
    print(f"Bit-Packed Memory: {packed_vram_mb:.2f} MB")
    print(f"VRAM Reduction:   {((standard_vram_mb - packed_vram_mb) / standard_vram_mb) * 100:.2f}%")
    
    if binary_time < dense_time:
        improvement = ((dense_time - binary_time) / dense_time) * 100
        print(f"✨ Speedup: {improvement:.2f}%")
    else:
        print("ℹ️ Note: Standard matmul is heavily optimized on CUDA. The true 1-bit advantage comes from 'Bit-Pack' kernels.")

    # 6. Final Safeguard
    safe, msg = monitor.check_safeguards()
    print(f"
[STATUS]: {msg}")

if __name__ == "__main__":
    run_benchmark()
