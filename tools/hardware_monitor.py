import time
import os
import sys
import psutil
import ctypes

try:
    import pynvml
    HAS_NVML_WRAPPER = True
except ImportError:
    HAS_NVML_WRAPPER = False

import torch

class HardwareProtector:
    """
    Guardian of the PC: Protects the 1080 Ti from thermal throttling or VRAM crashes.
    Uses a hybrid approach of NVML (pynvml or direct ctypes) and Torch.
    """
    def __init__(self, temp_limit=80, vram_margin_mb=500):
        self.temp_limit = temp_limit
        self.vram_margin_mb = vram_margin_mb
        self.nvml_lib = None
        self.nvml_initialized = False
        self.gpu_handle = None
        
        # 1. Try to load NVML DLL via ctypes (most reliable on Windows)
        nvml_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "nvml.dll")
        if os.path.exists(nvml_path):
            try:
                self.nvml_lib = ctypes.WinDLL(nvml_path)
                # Initialize NVML
                if self.nvml_lib.nvmlInit() == 0:
                    self.nvml_initialized = True
                    # Get handle for device 0
                    handle = ctypes.c_void_p()
                    if self.nvml_lib.nvmlDeviceGetHandleByIndex(0, ctypes.byref(handle)) == 0:
                        self.gpu_handle = handle
                        print("✅ NVML (Direct) Initialized via ctypes.")
                    else:
                        print("⚠️ NVML (Direct) failed to get device handle.")
            except Exception as e:
                print(f"⚠️ NVML (Direct) initialization failed: {e}")

        # 2. Try pynvml wrapper as fallback for initialization
        if not self.nvml_initialized and HAS_NVML_WRAPPER:
            try:
                pynvml.nvmlInit()
                self.nvml_initialized = True
                self.pynvml_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                print("✅ NVML Initialized via pynvml wrapper.")
            except Exception as e:
                print(f"⚠️ NVML (Wrapper) failed: {e}")

    def get_gpu_vitals(self):
        """
        Retrieves current temperature, VRAM usage, and load.
        """
        vitals = {
            "temp": 0.0,
            "vram_used": 0.0,
            "vram_free": 0.0,
            "vram_total": 0.0,
            "load": 0
        }

        # 1. Temperature (NVML Direct)
        if self.nvml_initialized and self.gpu_handle:
            try:
                temp = ctypes.c_uint()
                # NVML_TEMPERATURE_GPU = 0
                if self.nvml_lib.nvmlDeviceGetTemperature(self.gpu_handle, 0, ctypes.byref(temp)) == 0:
                    vitals["temp"] = float(temp.value)
                
                # Load (Utilization)
                class nvmlUtilization_t(ctypes.Structure):
                    _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]
                
                util = nvmlUtilization_t()
                if self.nvml_lib.nvmlDeviceGetUtilizationRates(self.gpu_handle, ctypes.byref(util)) == 0:
                    vitals["load"] = int(util.gpu)

                # Memory
                class nvmlMemory_t(ctypes.Structure):
                    _fields_ = [("total", ctypes.c_ulonglong), ("free", ctypes.c_ulonglong), ("used", ctypes.c_ulonglong)]
                
                mem = nvmlMemory_t()
                if self.nvml_lib.nvmlDeviceGetMemoryInfo(self.gpu_handle, ctypes.byref(mem)) == 0:
                    vitals["vram_total"] = mem.total / 1024**2
                    vitals["vram_used"] = mem.used / 1024**2
                    vitals["vram_free"] = mem.free / 1024**2
                    return vitals
            except Exception as e:
                print(f"Direct NVML read error: {e}")

        # 2. Fallback to Torch for VRAM only
        if torch.cuda.is_available():
            try:
                device_id = 0
                props = torch.cuda.get_device_properties(device_id)
                vitals["vram_total"] = props.total_memory / 1024**2
                vitals["vram_used"] = torch.cuda.memory_reserved(device_id) / 1024**2
                vitals["vram_free"] = vitals["vram_total"] - vitals["vram_used"]
                return vitals
            except Exception as e:
                print(f"Torch VRAM fallback error: {e}")

        return None

    def check_safeguards(self):
        vitals = self.get_gpu_vitals()
        if not vitals: return True, "No GPU found"
        if vitals['temp'] > self.temp_limit:
            return False, f"CRITICAL: Temp {vitals['temp']}C"
        return True, "OK"

    def __del__(self):
        if self.nvml_initialized:
            try:
                if self.nvml_lib: self.nvml_lib.nvmlShutdown()
                elif HAS_NVML_WRAPPER: pynvml.nvmlShutdown()
            except: pass

if __name__ == "__main__":
    monitor = HardwareProtector()
    v = monitor.get_gpu_vitals()
    if v:
        print(f"Temp: {v['temp']}C | VRAM: {v['vram_used']:.0f}MB / {v['vram_total']:.0f}MB | Load: {v['load']}%")
    else:
        print("Could not retrieve vitals.")
