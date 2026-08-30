import os
import time
import requests
import json
import uuid

# Configuration
# Assuming both servers are on the same machine but different ports
QWEN_SERVER_URL = "http://100.72.216.28:58328"
WAN_SERVER_URL = "http://100.72.216.28:58329"

OUTPUT_DIR = "/home/garg7002/clipping/ai_generated_videos"
PROMPTS_FILE = "/home/garg7002/clipping/video_prompts.json"

def set_sleep_state(server_url, sleep: bool):
    """
    Sends a request to the vLLM server to either wake it up or put it to sleep (Level 2).
    Level 2 sleep offloads both model weights and KV cache to free up VRAM.
    """
    if sleep:
        endpoint = f"{server_url}/sleep?level=2"
        action = "Sleep (Level 2)"
    else:
        endpoint = f"{server_url}/wake_up"
        action = "Wake up"
        
    print(f"[{server_url}] Sending {action} request...")
    try:
        response = requests.post(endpoint, timeout=30)
        response.raise_for_status()
        print(f"[{server_url}] SUCCESS: Processed {action} request.")
        # Give the GPU a moment to physically offload/load the weights
        time.sleep(3)
    except requests.exceptions.RequestException as e:
        print(f"[{server_url}] ERROR: Failed to {action.lower()} server: {e}")
        raise

def generate_video(prompt):
    """
    Sends the prompt to the Wan video model and saves the output.
    """
    print(f"\n>> Generating video for prompt: '{prompt}'")
    
    # Endpoint depends on how vLLM-omni exposes the video generation API.
    # Usually it's an OpenAI-compatible completions endpoint.
    endpoint = f"{WAN_SERVER_URL}/v1/completions" 
    
    payload = {
        "model": "Wan-AI/Wan2.2-T2V-A14B-FP8",
        "prompt": prompt,
        "max_tokens": 100, # Adjust parameters based on vllm-omni requirements
    }
    
    try:
        # Video generation takes significant time, so we set a high timeout (e.g., 10 mins)
        response = requests.post(endpoint, json=payload, timeout=600)
        response.raise_for_status()
        
        # Save output to ai_generated_videos/
        video_filename = f"video_{uuid.uuid4().hex[:8]}.mp4"
        video_path = os.path.join(OUTPUT_DIR, video_filename)
        
        # Depending on vllm-omni, it may return raw bytes or a JSON payload containing base64/url
        content_type = response.headers.get("content-type", "")
        
        if "application/json" in content_type:
            # If it's JSON, write the JSON directly (Opencode can parse it later to extract base64)
            data = response.json()
            json_path = video_path + ".json"
            with open(json_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f">> Saved JSON output to {json_path}")
        else:
            # If it returns raw video bytes
            with open(video_path, "wb") as f:
                f.write(response.content)
            print(f">> Saved raw video to {video_path}")
            
    except requests.exceptions.RequestException as e:
        print(f">> ERROR: Video generation failed for prompt '{prompt}': {e}")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 1. Read prompts stored by Opencode
    if not os.path.exists(PROMPTS_FILE):
        print(f"Waiting for prompts... {PROMPTS_FILE} does not exist.")
        # Create a dummy one for testing
        with open(PROMPTS_FILE, "w") as f:
            json.dump(["A majestic lion roaring in the savanna", "A futuristic car driving through neon city"], f)
            
    with open(PROMPTS_FILE, "r") as f:
        prompts = json.load(f)
        
    if not prompts:
        print("No prompts found in the file.")
        return
        
    print(f"Found {len(prompts)} prompts. Initiating pipeline...")
    
    # 2. Free up VRAM by putting Qwen to sleep
    print("\n--- Transitioning GPU for Video Generation ---")
    set_sleep_state(QWEN_SERVER_URL, sleep=True)
    
    # 3. Wake up Wan video model
    set_sleep_state(WAN_SERVER_URL, sleep=False)
    
    # 4. Process all prompts sequentially
    print("\n--- Starting Video Generation ---")
    for prompt in prompts:
        generate_video(prompt)
        
    # 5. Put Wan back to sleep
    print("\n--- Transitioning GPU back to LLM (Qwen) ---")
    set_sleep_state(WAN_SERVER_URL, sleep=True)
    
    # 6. Wake up Qwen so Opencode can continue thinking
    set_sleep_state(QWEN_SERVER_URL, sleep=False)
    
    print("\nPipeline completed successfully!")

if __name__ == "__main__":
    main()
