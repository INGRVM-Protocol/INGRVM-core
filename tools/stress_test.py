import torch
import time
import sys
import os

# Add parent dir to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from tools.hardware_monitor import HardwareProtector
from quantization import BinaryLinear

def run_stress_test(duration_secs=60):
    """
    Calyx Stress Test: Pushes the 1080 Ti to its thermal limit with 1-bit 'Crush' operations.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    monitor = HardwareProtector(temp_limit=85)
    
    print(f"🔥 --- Calyx Stress Test (1-bit / {duration_secs}s) ---")
    print(f"Targeting: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    
    # Setup large 1-bit layer
    dim = 8192
    binary_layer = BinaryLinear(dim, dim).to(device)
    input_data = torch.randn((256, dim)).to(device)
    
    start_time = time.time()
    iter_count = 0
    
    try:
        while time.time() - start_time < duration_secs:
            # 1. Check Hardware Safeguard
            safe, msg = monitor.check_safeguards()
            if not safe:
                print(f"
🛑 SHUTDOWN: {msg}")
                break
            
            # 2. Run Heavy 1-bit Matmul
            _ = binary_layer(input_data)
            
            # 3. Report every 50 iterations
            if iter_count % 50 == 0:
                vitals = monitor.get_gpu_vitals()
                if vitals:
                    print(f"⏳ {int(time.time() - start_time)}s | Temp: {vitals['temp']}°C | Load: {vitals['load']}% | VRAM: {vitals['vram_used']:.0f}MB", end='')
            
            iter_count += 1
            
        print("

✅ Stress test completed successfully.")
        print(f"Total Iterations: {iter_count}")
        
    except KeyboardInterrupt:
        print("
🛑 Stress test interrupted by user.")

if __name__ == "__main__":
    run_stress_test()
