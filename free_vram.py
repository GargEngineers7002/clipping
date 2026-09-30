import requests

SERVERS = [
    "http://100.72.197.70:58328",  # TTS 2080 Ti
    "http://127.0.0.1:58328",      # Video Quadro 1
    "http://127.0.0.1:58329"       # Video Quadro 2
]

def free_comfyui_vram():
    print("Freeing VRAM across all ComfyUI servers...\n")
    payload = {"unload_models": True, "free_memory": True}
    
    for server in SERVERS:
        endpoint = f"{server}/free"
        try:
            response = requests.post(endpoint, json=payload, timeout=10)
            response.raise_for_status()
            print(f"[{server}] SUCCESS: VRAM freed and models unloaded.")
        except requests.exceptions.RequestException as e:
            print(f"[{server}] ERROR: Failed to free VRAM: {e}")

if __name__ == "__main__":
    free_comfyui_vram()
