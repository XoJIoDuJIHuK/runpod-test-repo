FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /

RUN apt-get update && apt-get install -y git git-lfs wget && rm -rf /var/lib/apt/lists/*

# Upgrade PyTorch to 2.5.1+ to support Anima, Qwen encoders, and modern Comfy custom ops
RUN pip install --no-cache-dir --upgrade torch torchvision torchaudio

# Clone latest ComfyUI with native Anima support
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI

WORKDIR /ComfyUI
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod

WORKDIR /app
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY rp_handler.py /app/rp_handler.py

CMD ["python", "-u", "/app/rp_handler.py"]
