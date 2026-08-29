faster-whisper-server Installation:

uv venv fw_server_venv --python 3.12.12

source fw_server_venv/bin/activate

uv pip install -r requirements.txt

python setup.py

---

Create a service file at /etc/systemd/system/fw-server.service with the following content, adjusting the paths to match your installation:

[Unit]
Description=fw-server
After=network.target

[Service]
Type=simple
User=server
WorkingDirectory=/home/server/.keras/datasets/clipping/fw-server
ExecStart=/home/server/.keras/datasets/clipping/fw-server/fw_server_venv/bin/python main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target

---

Enable and start the service with:

sudo systemctl daemon-reload
sudo systemctl enable fw-server
sudo systemctl start fw-server

---

Just make sure any firewall you might have running on the server (like ufw) is configured to allow traffic on port 58329.
