import os
import time
import requests
import json
import uuid

# Configuration
OLLAMA_SERVER_URL = "http://100.72.216.28:11434"
OLLAMA_MODEL_NAME = "qwen3.8:27b"
COMFYUI_PORTS = [58328, 58329]

OUTPUT_DIR = "/home/garg7002/clipping/ai_generated_videos"
PROMPTS_FILE = "/home/garg7002/clipping/video_prompts.json"

def set_ollama_sleep_state(sleep: bool):
    """
    Sends a request to the Ollama server to either wake it up or put it to sleep.
    sleep=True sets keep_alive to 0 to instantly unload from VRAM.
    sleep=False sets keep_alive to -1 to load it into VRAM.
    """
    endpoint = f"{OLLAMA_SERVER_URL}/api/generate"
    payload = {
        "model": OLLAMA_MODEL_NAME,
        "keep_alive": 0 if sleep else -1
    }
    action = "Sleep (Unload VRAM)" if sleep else "Wake up (Preload VRAM)"
        
    print(f"[Ollama] Sending {action} request...")
    try:
        response = requests.post(endpoint, json=payload, timeout=30)
        response.raise_for_status()
        print(f"[Ollama] SUCCESS: Processed {action}.")
        time.sleep(3)
    except requests.exceptions.RequestException as e:
        print(f"[Ollama] ERROR: Failed to {action.lower()} server: {e}")

def free_comfyui_vram():
    """
    Sends requests to both ComfyUI servers to unload models and free memory.
    """
    print("\n[ComfyUI] Freeing VRAM on both ComfyUI servers...")
    payload = {"unload_models": True, "free_memory": True}
    for port in COMFYUI_PORTS:
        endpoint = f"http://127.0.0.1:{port}/free"
        try:
            response = requests.post(endpoint, json=payload, timeout=15)
            response.raise_for_status()
            print(f"[ComfyUI Port {port}] SUCCESS: VRAM freed.")
        except requests.exceptions.RequestException as e:
            print(f"[ComfyUI Port {port}] ERROR: Failed to free VRAM: {e}")

def generate_video(prompt, port):
    """
    Sends the prompt to a ComfyUI server.
    NOTE: You must replace `workflow` with your actual exported ComfyUI Wan 2.1 API JSON!
    """
    print(f"\n>> Queuing video for prompt: '{prompt}' on ComfyUI port {port}")
    
    endpoint = f"http://127.0.0.1:{port}/prompt" 
    
    # This is a placeholder for your actual ComfyUI workflow API JSON.
    # You will need to parse your exported JSON and inject the `prompt` variable into the correct node.
    workflow = {
        "prompt": {} 
    }
    
    try:
        response = requests.post(endpoint, json=workflow, timeout=30)
        response.raise_for_status()
        data = response.json()
        print(f">> Successfully queued prompt! Prompt ID: {data.get('prompt_id')}")
        # Note: To actually wait for it to finish, you would need to poll http://127.0.0.1:{port}/history/{prompt_id}
            
    except requests.exceptions.RequestException as e:
        print(f">> ERROR: Video generation failed for prompt '{prompt}': {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Read prompts stored by Opencode
    if not os.path.exists(PROMPTS_FILE):
        print(f"Waiting for prompts... {PROMPTS_FILE} does not exist.")
        with open(PROMPTS_FILE, "w") as f:
            json.dump(["A majestic lion roaring in the savanna", "A futuristic car driving through neon city"], f)
            
    with open(PROMPTS_FILE, "r") as f:
        prompts = json.load(f)
        
    if not prompts:
        print("No prompts found in the file.")
        return
        
    print(f"Found {len(prompts)} prompts. Initiating pipeline...")
    
    # 2. Free up VRAM by putting Ollama (Qwen) to sleep
    print("\n--- Transitioning GPU for Video Generation ---")
    set_ollama_sleep_state(sleep=True)
    
    # 3. Process all prompts, alternating between ComfyUI servers for load balancing
    print("\n--- Queuing Video Generations to ComfyUI ---")
    for idx, prompt in enumerate(prompts):
        port = COMFYUI_PORTS[idx % len(COMFYUI_PORTS)]
        generate_video(prompt, port)
        
    # Note: In a production script, you should poll ComfyUI /history here to ensure 
    # all generation jobs are completely finished before moving to Step 4.
    print("\n[NOTE] Assuming jobs are finished (You should add polling logic here!)")
    time.sleep(5) 
        
    # 4. Unload ComfyUI models from VRAM
    print("\n--- Transitioning GPU back to LLM (Qwen) ---")
    free_comfyui_vram()
    
    # 5. Wake up Qwen (Ollama) so Opencode can continue thinking
    set_ollama_sleep_state(sleep=False)
    
    print("\nPipeline completed successfully!")

if __name__ == "__main__":
    main()
