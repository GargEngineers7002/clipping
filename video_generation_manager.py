import os
import time
import requests
import json
import uuid
import sys

# Configuration
COMFYUI_SERVERS = ["http://100.72.216.28:58328", "http://100.72.216.28:58329"]

OUTPUT_DIR = "/home/garg7002/clipping/ai_generated_videos"
PROMPTS_FILE = "/home/garg7002/clipping/video_prompts.json"
WORKFLOWS_DIR = "/home/garg7002/clipping/workflows"


def free_comfyui_vram():
    print("\n[ComfyUI] Freeing VRAM on both ComfyUI servers...")
    payload = {"unload_models": True, "free_memory": True}
    for server in COMFYUI_SERVERS:
        endpoint = f"{server}/free"
        try:
            response = requests.post(endpoint, json=payload, timeout=15)
            response.raise_for_status()
            print(f"[{server}] SUCCESS: VRAM freed.")
        except requests.exceptions.RequestException as e:
            print(f"[{server}] ERROR: Failed to free VRAM: {e}")

def upload_to_comfyui(server_url, filepath):
    with open(filepath, 'rb') as f:
        files = {'image': f} # ComfyUI accepts all media under 'image'
        data = {'type': 'input', 'overwrite': 'true'}
        r = requests.post(f"{server_url}/upload/image", files=files, data=data)
        r.raise_for_status()
        return r.json()['name']

import random

def patch_workflow(wf, inputs):
    # If the agent didn't provide a seed, auto-generate a random one to ensure true randomness
    current_seed = inputs.get("seed", random.randint(1, 999999999999999))
    
    for node_id, node in wf.items():
        c_type = node.get("class_type", "")
        title = node.get("_meta", {}).get("title", "").lower()
        
        # Patch Prompts
        if "prompt" in title or "positive" in title:
            if "positive" in title or "prompt (positive)" in title:
                if "prompt" in inputs:
                    if "text" in node["inputs"]: node["inputs"]["text"] = inputs["prompt"]
                    if "value" in node["inputs"]: node["inputs"]["value"] = inputs["prompt"]
            elif "negative" in title or "prompt (negative)" in title:
                if "negative" in inputs:
                    if "text" in node["inputs"]: node["inputs"]["text"] = inputs["negative"]
                    if "value" in node["inputs"]: node["inputs"]["value"] = inputs["negative"]
                    
        # Patch Media Files
        if c_type == "LoadImage" and "image" in inputs:
            node["inputs"]["image"] = inputs["image"]
        if c_type == "LoadAudio" and "audio" in inputs:
            node["inputs"]["audio"] = inputs["audio"]
        if c_type == "VHS_LoadVideo" and "video" in inputs:
            node["inputs"]["video"] = inputs["video"]
            
        # Patch Seed (Always patched for randomness, locked if agent specified)
        if "noise_seed" in node["inputs"]: node["inputs"]["noise_seed"] = current_seed
        if "seed" in node["inputs"]: node["inputs"]["seed"] = current_seed
            
        # Patch Duration
        if "duration" in inputs and "duration" in title:
            if "value" in node["inputs"]: node["inputs"]["value"] = inputs["duration"]
            
        # Patch Resolution
        if "width" in inputs and "width" in node["inputs"]:
            node["inputs"]["width"] = inputs["width"]
        if "height" in inputs and "height" in node["inputs"]:
            node["inputs"]["height"] = inputs["height"]

def download_comfyui_outputs(server_url, history_result, task_id, workflow_name=""):
    saved_files = []
    # Output can be in multiple nodes, and ComfyUI categorizes them by 'images', 'gifs', or 'videos'
    for node_id, node_output in history_result.get("outputs", {}).items():
        for media_type in ["images", "gifs", "videos"]:
            if media_type in node_output:
                for item in node_output[media_type]:
                    fname = item["filename"]
                    url = f"{server_url}/view?filename={fname}&type=output"
                    r = requests.get(url)
                    if r.status_code == 200:
                        ext = os.path.splitext(fname)[1]
                        out_dir = OUTPUT_DIR
                        if workflow_name.startswith("image_") or ext.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                            out_dir = "/home/garg7002/clipping/ai_generated_images"
                            os.makedirs(out_dir, exist_ok=True)
                            
                        out_path = os.path.join(out_dir, f"{task_id}_{node_id}{ext}")
                        with open(out_path, "wb") as f:
                            f.write(r.content)
                        saved_files.append(out_path)
                        print(f"  -> Saved output to: {out_path}")
    return saved_files

def generate_video(task, server_url):
    print(f"\n>> Processing task using workflow: {task.get('workflow')} on {server_url}")
    wf_path = os.path.join(WORKFLOWS_DIR, task['workflow'])
    if not os.path.exists(wf_path):
        print(f"ERROR: Workflow {wf_path} not found!")
        return False
        
    with open(wf_path) as f:
        wf = json.load(f)
        
    inputs = dict(task.get("inputs", {}))
    
    # Pre-upload any local files to ComfyUI
    for key, value in inputs.items():
        if isinstance(value, str) and os.path.isabs(value) and os.path.isfile(value):
            print(f"   -> Uploading {value} to ComfyUI...")
            inputs[key] = upload_to_comfyui(server_url, value)
            
    patch_workflow(wf, inputs)
    
    # Queue workflow
    client_id = str(uuid.uuid4())
    payload = {"prompt": wf, "client_id": client_id}
    r = requests.post(f"{server_url}/prompt", json=payload, timeout=30)
    r.raise_for_status()
    prompt_id = r.json()["prompt_id"]
    print(f"   -> Queued workflow! Prompt ID: {prompt_id} on {server_url}")
    
    # Wait for result
    start = time.time()
    timeout = 1800 # 30 minutes max
    while time.time() - start < timeout:
        r = requests.get(f"{server_url}/history/{prompt_id}")
        if r.status_code == 200:
            hist = r.json()
            if prompt_id in hist:
                print(f"   -> Generation complete on {server_url}!")
                download_comfyui_outputs(server_url, hist[prompt_id], client_id[:8], task.get('workflow', ''))
                return True
        time.sleep(5)
    print(f"   -> ERROR: Generation timed out on {server_url}!")
    return False

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    if not os.path.exists(PROMPTS_FILE):
        print(f"No prompts file found at {PROMPTS_FILE}")
        sys.exit(0)
            
    with open(PROMPTS_FILE, "r") as f:
        tasks = json.load(f)
        
    if not tasks:
        print("No tasks found in the file.")
        sys.exit(0)
        
    print(f"Found {len(tasks)} tasks. Initiating pipeline...")
    
    print("\n--- Generating Media via ComfyUI ---")
    
    failed_tasks = []
    
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    with ThreadPoolExecutor(max_workers=len(COMFYUI_SERVERS)) as executor:
        future_to_task = {}
        for idx, task in enumerate(tasks):
            server = COMFYUI_SERVERS[idx % len(COMFYUI_SERVERS)]
            future = executor.submit(generate_video, task, server)
            future_to_task[future] = task
            
        for future in as_completed(future_to_task):
            task = future_to_task[future]
            try:
                success = future.result()
                if not success:
                    failed_tasks.append(task)
            except Exception as e:
                print(f"ERROR executing task: {e}")
                failed_tasks.append(task)
            
    free_comfyui_vram()
    
    # Trigger cleanup on the server
    for server in COMFYUI_SERVERS:
        cleanup_url = server.replace(":58328", ":8189").replace(":8189", ":8189") + "/cleanup"
        if "58329" in server:
             cleanup_url = server.replace(":58329", ":8189") + "/cleanup"
        try:
            r = requests.post(cleanup_url, timeout=5)
            if r.status_code == 200:
                print(f"Cleanup triggered on {server}")
        except Exception as e:
            pass # ignore if cleanup server not running there

    # Rewrite the prompts file retaining only the failed tasks (recovery mechanism)
    with open(PROMPTS_FILE, "w") as f:
        json.dump(failed_tasks, f, indent=2)
        
    if failed_tasks:
        print(f"\nPipeline completed, but {len(failed_tasks)} tasks failed. They have been left in {PROMPTS_FILE} so you can fix and rerun.")
    else:
        print("\nPipeline completed successfully!")

if __name__ == "__main__":
    main()
