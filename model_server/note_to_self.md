The ollama way:(DID USE)(maybe look at this Thread: <https://grok.com/share/c2hhcmQtMw_f9ab633f-28c0-47a4-bc70-598f7ab52724>)
Initializing the model:

DIDN'T USE:
ollama create qwen-max -f ./Modelfile
ollama run qwen-max --keepalive 0

DID USE:
ollama run qwen3.8:27b

with:

sudo -E systemctl edit ollama

[Service]
Environment="OLLAMA_KEEP_ALIVE=3h"
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_MODELS=/home/server/Desktop/ollama_models"

ollama run qwen3.8:27b

> > > /set parameter num_ctx 65536
> > > /save qwen3.8:27b-64k
> > > /bye

---

---

The ComfyUI setup:(DID USE) (maybe look at this Thread: <https://grok.com/share/c2hhcmQtMw_4156d910-d35c-4bb9-befb-75ec63058727>)

**Final clean recreation guide** for the exact dual-ComfyUI setup (GPU 0 + GPU 1) that is currently working.

Copy-paste everything below in order on a fresh machine that has the same hardware layout (2× GPUs with ~16 GB each or better, 32 GB+ system RAM recommended).

---

### 1. Base ComfyUI install (uv)

```bash
cd /home/server
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Create and activate venv with uv
uv venv .venv --python 3.12
source .venv/bin/activate

# Install ComfyUI + dependencies
uv pip install -r requirements.txt
uv pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124   # adjust CUDA version if needed
```

---

### 2. Custom nodes (final working set)

```bash
cd /home/server/ComfyUI/custom_nodes

git clone https://github.com/Lightricks/ComfyUI-LTXVideo.git
git clone https://github.com/Fannovel16/comfyui_controlnet_aux.git
git clone https://github.com/yuvraj108c/ComfyUI-Video-Depth-Anything.git

# Fix the known kornia pad breakage (required)
cd ComfyUI-LTXVideo
cp pyramid_blending.py pyramid_blending.py.bak
sed -i '/pad,/d' pyramid_blending.py
sed -i '/import torch.nn.functional as F/a pad = F.pad  # compatibility for kornia >= 0.8.3' pyramid_blending.py
cd ..

# Install node dependencies
cd /home/server/ComfyUI
source .venv/bin/activate
uv pip install opencv-python-headless matplotlib easydict einops imageio imageio-ffmpeg tqdm OpenEXR onnxruntime mediapipe
```

---

### 3. Model downloads (final working set)

```bash
cd /home/server/ComfyUI
mkdir -p models/{diffusion_models,text_encoders,vae,loras,checkpoints,videodepthanything}

# LTX-2.5 core (bf16 – the ones that actually run on the hardware)
hf download Lightricks/LTX-2.5 \
  ltx-2.5-22b-distilled-transformer-bf16.safetensors \
  --local-dir models/diffusion_models

hf download Lightricks/LTX-2.5 \
  ltx-2.5-audio-vae-bf16.safetensors \
  ltx-2.5-video-vae-bf16.safetensors \
  --local-dir models/vae

hf download Lightricks/LTX-2.5 \
  gemma4-12b-with-proj-ltx-2.5-bf16.safetensors \
  --local-dir models/text_encoders

# IC-LoRAs that are currently loaded in the working workflows
hf download Lightricks/LTX-2.5 \
  ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors \
  ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors \
  --local-dir models/loras

# -------------------------------------------------
# Extra LTX-2.5 components (highly recommended)
# -------------------------------------------------
hf download Lightricks/LTX-2.5 \
  latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors \
  --local-dir models/latent_upscale_models

hf download Lightricks/LTX-2.5 \
  model_patches/ltx-2.5-duration-head-bf16.safetensors \
  --local-dir models/model_patches

# Optional but useful Gemma E2B (prompt enhancer)
hf download Lightricks/LTX-2.5 \
  text_encoders/gemma4_e2b_it_bf16.safetensors \
  --local-dir models/text_encoders

# -------------------------------------------------
# Additional IC-LoRAs (for the other workflows)
# -------------------------------------------------
# Ingredients (already had one, but this is the official 2.5 name)
hf download Lightricks/LTX-2.5 \
  ltx-2.5-22b-ic-lora-ingredients-0.9.safetensors \
  --local-dir models/loras

# Union Control (the one currently used)
hf download Lightricks/LTX-2.3 \
  ltx-2.3-22b-ic-lora-union-control-ref0.5.safetensors \
  --local-dir models/loras

# In-Outpainting (covers both Inpaint + Outpaint workflows)
hf download Lightricks/LTX-2.3 \
  ltx-2.3-22b-ic-lora-in-outpainting-0.9.safetensors \
  --local-dir models/loras

# Motion Track
hf download Lightricks/LTX-2.3 \
  ltx-2.3-22b-ic-lora-motion-track.safetensors \
  --local-dir models/loras   # check exact filename on HF if needed

# -------------------------------------------------
# Video-Depth-Anything models (for the Union Control annotator)
# -------------------------------------------------
mkdir -p models/videodepthanything

hf download depth-anything/Video-Depth-Anything-Small \
  video_depth_anything_vits.pth \
  --local-dir models/videodepthanything

# Optional larger variants if you want better quality
# hf download depth-anything/Video-Depth-Anything-Base video_depth_anything_vitb.pth --local-dir models/videodepthanything
# hf download depth-anything/Video-Depth-Anything-Large video_depth_anything_vitl.pth --local-dir models/videodepthanything
```

(If you also want the Flux / Qwen models that were discussed earlier, add them the same way.)

---

### 4. Systemd services (exact working config)

**File 1:** `/etc/systemd/system/comfyui.service` (GPU 0 – port 58329)

```ini
[Unit]
Description=ComfyUI
After=network.target

[Service]
Type=simple
User=server
WorkingDirectory=/home/server/ComfyUI
Environment="CUDA_VISIBLE_DEVICES=0"
ExecStart=/home/server/ComfyUI/.venv/bin/python main.py --listen 0.0.0.0 --port 58329 --enable-manager
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**File 2:** `/etc/systemd/system/server_v.service` (GPU 1 – port 58328)

```ini
[Unit]
Description=ComfyUI
After=network.target

[Service]
Type=simple
User=server
WorkingDirectory=/home/server/ComfyUI
Environment="CUDA_VISIBLE_DEVICES=1"
ExecStart=/home/server/ComfyUI/.venv/bin/python main.py --listen 0.0.0.0 --port 58328 --enable-manager
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable & start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable comfyui.service server_v.service
sudo systemctl start comfyui.service server_v.service
```

---

### 5. Verification

```bash
# Check both services are running
systemctl status comfyui.service
systemctl status server_v.service

# Quick API check
curl http://127.0.0.1:58329/system_stats
curl http://127.0.0.1:58328/system_stats
```

After this the two servers will be listening on ports **58329** (GPU 0) and **58328** (GPU 1) exactly as they are now, with all the working LTX-2.5 + IC-LoRA models and the fixed custom nodes.

That’s the complete, known-good recreation list.

---

---

The vllm way:(DID NOT USE AT THE END A LOT OF HASSLE)

uv venv model_server_venv --python 3.12.12

source model_server_venv/bin/activate

uv pip install -r requirements.txt

hf download abihsoro/Qwen3.8-27B-AWQ-INT4
hf download unsloth/Wan2.2-T2V-A14B-FP8

sudo nvim /etc/systemd/system/server_q.service

[Unit]
Description=Server_q
After=network.target

[Service]
Type=simple
User=root
TimeoutStartSec=600
Environment="HF_HOME=/home/server/.cache/huggingface"
Environment="VLLM_SERVER_DEV_MODE=1"
ExecStart=/home/server/.keras/datasets/clipping/model_server/model_server_venv/bin/vllm serve RedHatAI/Qwen3.8-27B-INT4 \
 --trust-remote-code \
 --enable-auto-tool-choice \
 --tool-call-parser qwen3_coder \
 --reasoning-parser qwen3 \
 --gpu-memory-utilization 0.88 \
 --tensor-parallel-size 1 \
 --pipeline-parallel-size 2 \
 --max-model-len 16384 \
 --kv-cache-dtype auto \
 --enforce-eager \
 --enable-sleep-mode \
 --host 0.0.0.0 \
 --port 58328

# This line automatically pushes the server into Level 2 Sleep 5 seconds after boot

ExecStartPost=/bin/bash -c "until curl -s -f <http://0.0.0.0:58328/health> > /dev/null; do sleep 5; done; curl -s -X POST '<http://0.0.0.0:58328/sleep?level=2>'"

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable server_q.service
sudo systemctl start server_q.service

sudo nvim /etc/systemd/system/server_v.service

[Unit]
Description=Server_v
After=network.target

[Service]
Type=simple
User=root
Environment="HF_HOME=/home/server/.cache/huggingface"
Environment="VLLM_SERVER_DEV_MODE=1"

# We invoke vllm-omni to handle the native video diffusion transformer architecture

ExecStart=/home/server/.keras/datasets/clipping/model_server/model_server_venv/bin/vllm-omni serve unsloth/Wan2.2-T2V-A14B-FP8 \
 --gpu-memory-utilization 0.90 \
 --tensor-parallel-size 1 \
 --pipeline-parallel-size 2 \
 --enforce-eager \
 --enable-sleep-mode \
 --host 0.0.0.0 \
 --port 58329

# Pushes the video server cleanly into Level 2 Sleep 5 seconds after initialization

ExecStartPost=/bin/bash -c "until curl -s -f <http://0.0.0.0:58329/health> > /dev/null; do sleep 5; done; curl -s -X POST '<http://0.0.0.0:58329/sleep?level=2>'"

Restart=always
RestartSec=5

# Do NOT include WantedBy=multi-user.target here to prevent boot-time VRAM collisions with Qwen

# Stagger the boot using a master startup script

sudo systemctl daemon-reload

# sudo systemctl enable server_v.service <-- Do NOT enable

# Instead, start it manually or via a staggered boot script after Qwen sleeps

# sudo systemctl start server_v.service
