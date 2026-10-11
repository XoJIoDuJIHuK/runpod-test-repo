FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /

# Install system utilities
RUN apt-get update && apt-get install -y git git-lfs wget && rm -rf /var/lib/apt/lists/*

# Clone the STABLE release of ComfyUI (prevents bleeding-edge breakages)
RUN git clone --depth 1 --branch v0.3.10 https://github.com/comfyanonymous/ComfyUI.git /ComfyUI

WORKDIR /ComfyUI
# Install stable dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod

WORKDIR /app
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY rp_handler.py /app/rp_handler.py

CMD ["python", "-u", "/app/rp_handler.py"]
