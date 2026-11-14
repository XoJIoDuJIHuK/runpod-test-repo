FROM runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04

WORKDIR /

# Added common libs (ffmpeg, libgl1, build-essential) often needed by video/image custom nodes
RUN apt-get update && apt-get install -y \
    git git-lfs wget ffmpeg libgl1 libglib2.0-0 build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade PyTorch to 2.5.1+ to support Anima, Qwen encoders, and modern Comfy custom ops
RUN pip install --no-cache-dir --upgrade torch torchvision torchaudio

# Clone latest ComfyUI
RUN git clone https://github.com/comfyanonymous/ComfyUI.git /ComfyUI

WORKDIR /ComfyUI
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir runpod comfy-cli

# Disable comfy-cli telemetry prompt
RUN comfy --skip-prompt tracking disable

WORKDIR /ComfyUI/custom_nodes

RUN git clone --depth 1 https://github.com/rgthree/rgthree-comfy.git && \
    git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Pack.git && \
    git clone --depth 1 https://github.com/ltdrdata/ComfyUI-Impact-Subpack.git && \
    git clone --depth 1 https://github.com/dfl/comfyui-clip-with-break.git

# Install Python dependencies for cloned nodes
RUN for dir in /ComfyUI/custom_nodes/*; do \
        if [ -f "$dir/requirements.txt" ]; then \
            pip install --no-cache-dir -r "$dir/requirements.txt"; \
        fi; \
        if [ -f "$dir/install.py" ]; then \
            python "$dir/install.py"; \
        fi; \
    done

WORKDIR /app
COPY extra_model_paths.yaml /app/extra_model_paths.yaml
COPY rp_handler.py /app/rp_handler.py

CMD ["python", "-u", "/app/rp_handler.py"]
