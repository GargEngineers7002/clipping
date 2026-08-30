The ollama way:
Initializing the model:

ollama create qwen-max -f ./Modelfile
ollama run qwen-max --keepalive 0

---

The vllm way:

uv venv model_server_venv --python 3.12.12

source model_server_venv/bin/activate

uv pip install -r requirements.txt

---

sudo nvim /etc/systemd/system/server_q.service

[Unit]
Description=Server_q
After=network.target

[Service]
Type=simple
User=root
Environment="VLLM_SERVER_DEV_MODE=1"
ExecStart=/home/server/.keras/datasets/clipping/model_server/model_server_venv/bin/vllm serve Qwen/Qwen3.8-27B-AWQ \
 --quantization awq \
 --gpu-memory-utilization 0.90 \
 --max-model-len auto \
 --enable-sleep-mode \
 --host 0.0.0.0 \
 --port 58328

# This line automatically pushes the server into Level 2 Sleep 5 seconds after boot

ExecStartPost=/bin/bash -c "sleep 5 && curl -s -X POST '<http://localhost:8000/sleep?level=2>'"

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable server_q.service
sudo systemctl start server_q.service

---

sudo nvim /etc/systemd/system/server_v.service

[Unit]
Description=vLLM Video Generation Server (Wan 2.2)
After=network.target

[Service]
Type=simple
User=root
Environment="VLLM_SERVER_DEV_MODE=1"

# We invoke vllm-omni to handle the native video diffusion transformer architecture

ExecStart=/home/server/.keras/datasets/clipping/model_server/model_server_venv/bin/vllm-omni serve Wan-AI/Wan2.2-T2V-A14B \
 --gpu-memory-utilization 0.90 \
 --enable-sleep-mode \
 --host 0.0.0.0 \
 --port 58329

# Pushes the video server cleanly into Level 2 Sleep 5 seconds after initialization

ExecStartPost=/bin/bash -c "sleep 5 && curl -s -X POST '<http://localhost:8001/sleep?level=2>'"

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target

sudo systemctl daemon-reload
sudo systemctl enable server_v.service
sudo systemctl start server_v.service
