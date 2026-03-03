# Calyx Node: Docker Environment
# Optimized for Neuromorphic Spiking Neural Networks (SNNs)

FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV CALYX_HOME /app

# Set working directory
WORKDIR $CALYX_HOME

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    libgmp-dev \
    cmake \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the Calyx source code
COPY . .

# Expose P2P and API ports
# Default P2P: 60001 | Discovery: 60002 | API: 8000
EXPOSE 60001 60002 8000

# Default command to run the master node
# In production, we'd use the phoenix_supervisor.py
CMD ["python", "master_node.py"]
