import torch
import psutil
try:
    import GPUtil
except ImportError:
    GPUtil = None

from typing import Dict

class EfficiencyMonitor:
    """
    Quantifies the 'Solarpunk Advantage' of Neuromorphic SNNs.
    Converts Joules into tangible human metrics.
    Also handles Thermal Guarding (Task #12) for the Laptop.
    """
    def __init__(self, cpu_threshold=85.0, gpu_threshold=80.0):
        self.cpu_threshold = cpu_threshold
        self.gpu_threshold = gpu_threshold
        self.ENERGY_MAC_DENSE = 3.1  # Picojoules (pJ)
        self.ENERGY_SPIKE_ADD = 0.1  # pJ

    def check_thermal_health(self) -> Dict:
        """
        Returns True if the node is within safe thermal and memory limits.
        Task #22: Added VRAM Pressure Sensor.
        """
        vitals = {
            "cpu_temp": 0.0, 
            "gpu_temp": 0.0, 
            "vram_used_pct": 0.0,
            "is_safe": True, 
            "reason": "OK"
        }
        
        # 1. CPU Temperature (Laptop-critical)
        try:
            temps = psutil.sensors_temperatures()
            if 'coretemp' in temps:
                vitals["cpu_temp"] = max([t.current for t in temps['coretemp']])
            elif 'cpu_thermal' in temps:
                vitals["cpu_temp"] = temps['cpu_thermal'][0].current
        except Exception: pass
        
        if vitals["cpu_temp"] > self.cpu_threshold:
            vitals["is_safe"] = False
            vitals["reason"] = f"CPU_OVERHEAT ({vitals['cpu_temp']}C)"

        # 2. GPU Temperature & VRAM Pressure
        if GPUtil:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0] # Assuming primary GPU
                    vitals["gpu_temp"] = gpu.temperature
                    vitals["vram_used_pct"] = gpu.memoryUtil * 100
                    
                    if vitals["gpu_temp"] > self.gpu_threshold:
                        vitals["is_safe"] = False
                        vitals["reason"] = f"GPU_OVERHEAT ({vitals['gpu_temp']}C)"
                    
                    if vitals["vram_used_pct"] > 90.0: # VRAM Pressure threshold
                        vitals["is_safe"] = False
                        vitals["reason"] = f"VRAM_PRESSURE ({vitals['vram_used_pct']:.1f}%)"
            except Exception: pass
            
        return vitals

    def calculate_savings(self, 
                          num_inputs: int, 
                          num_hidden: int, 
                          num_outputs: int, 
                          actual_spikes: int) -> Dict:
        
        total_synapses = (num_inputs * num_hidden) + (num_hidden * num_outputs)
        energy_dense_pj = total_synapses * self.ENERGY_MAC_DENSE
        energy_snn_pj = actual_spikes * self.ENERGY_SPIKE_ADD
        
        energy_saved_pj = energy_dense_pj - energy_snn_pj
        joules_saved = energy_saved_pj / 1e12
        
        # Human Tangibles
        phone_mins = joules_saved / self.J_PER_PHONE_CHARGE_MIN
        led_secs = joules_saved / self.J_PER_LED_SEC
        
        return {
            "joules_saved": joules_saved,
            "reduction_pct": round((energy_saved_pj / energy_dense_pj) * 100, 2),
            "phone_charge_mins": round(phone_mins, 4),
            "led_bulb_secs": round(led_secs, 2)
        }

if __name__ == "__main__":
    monitor = EfficiencyMonitor()
    # Mock a large 80B shard inference (massive synapse count)
    # 80B total params, let's say 1M params per shard
    stats = monitor.calculate_savings(1000, 1000, 1000, actual_spikes=5000)
    print(f"Efficiency: {stats['reduction_pct']}%")
    print(f"Tangible: Saved {stats['led_bulb_secs']} seconds of LED light per inference.")
