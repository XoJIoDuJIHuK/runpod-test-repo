FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /

RUN apt-get update && apt-get install -y git git-lfs wget && rm -rf /var/lib/apt/lists/*

# Clone stable ComfyUI
RUN git clone --depth 1 --branch v0.3.10 https://github.com/comfyanonymous/ComfyUI.git /ComfyUI

WORKDIR /ComfyUI
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod

# Pin transformers to avoid the PyTorch >= 2.5 requirement warning
RUN pip install --no-cache-dir "transformers<4.48.0"

WORKDIR /app
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY rp_handler.py /app/rp_handler.py

CMD ["python", "-u", "/app/rp_handler.py"]
