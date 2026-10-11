FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /

# Install system dependencies
RUN apt-get update && apt-get install -y git git-lfs wget && rm -rf /var/lib/apt/lists/*

# Clone ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI
WORKDIR /ComfyUI
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod
RUN pip uninstall -y comfy-kitchen # workaround for error with type hints

# Optional: Add any custom ComfyUI node extensions here
# RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git /ComfyUI/custom_nodes/ComfyUI-Manager

WORKDIR /app
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY rp_handler.py /app/rp_handler.py

CMD ["python", "-u", "/app/rp_handler.py"]
