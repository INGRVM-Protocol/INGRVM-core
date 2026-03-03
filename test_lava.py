from lava.proc.lif.process import LIF
import lava
print(f"Lava version: {lava.__version__}")

# Simple test to create a LIF process
lif = LIF(shape=(1,), vth=10)
print("Successfully initialized a LIF neuron process!")
