import ctypes
import os
import pynvml

def test_nvml():
    print("--- 🛡️ NVML Diagnostics ---")
    nvml_path = os.path.join(os.environ.get("SystemRoot", "C:\Windows"), "System32", "nvml.dll")
    print(f"Checking path: {nvml_path}")
    print(f"Path exists: {os.path.exists(nvml_path)}")
    
    if os.path.exists(nvml_path):
        try:
            # Manually load it before pynvml tries
            lib = ctypes.WinDLL(nvml_path)
            print("✅ Manually loaded nvml.dll with ctypes.WinDLL")
            
            # Now try pynvml
            pynvml.nvmlInit()
            print("✅ pynvml.nvmlInit() Succeeded!")
            
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            name = pynvml.nvmlDeviceGetName(handle)
            if isinstance(name, bytes): name = name.decode()
            print(f"✅ Device 0: {name}")
            
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            print(f"✅ Temperature: {temp}°C")
            
            pynvml.nvmlShutdown()
        except Exception as e:
            print(f"❌ Failed: {e}")
    else:
        print("❌ nvml.dll not found in System32.")

if __name__ == "__main__":
    test_nvml()
