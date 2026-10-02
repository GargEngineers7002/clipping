import os
import requests
import glob
import time
from concurrent.futures import ThreadPoolExecutor

# List of AnimeGANv3 server endpoints
SERVERS = [
    "http://100.72.216.28:55328/process-video",
    "http://100.72.216.28:55329/process-video",
    "http://100.72.197.70:55329/process-video"
]

INPUT_DIR = "/home/garg7002/clipping/videos"

def stylize_video(file_path, server_url, model_type):
    filename = os.path.basename(file_path)
    print(f"[{filename} | {model_type}] Starting upload to {server_url}...")
    start_time = time.time()
    
    try:
        with open(file_path, "rb") as f:
            response = requests.post(server_url, files={"file": f}, data={"model_type": model_type}, timeout=600)
            
        if response.status_code == 200:
            # We trust the server to return the appropriately prefixed filename in content-disposition
            # But as a fallback we will name it explicitly
            out_name = os.path.join(INPUT_DIR, f"{model_type}_anonymized_{filename}")
            with open(out_name, "wb") as out_f:
                out_f.write(response.content)
            elapsed = time.time() - start_time
            print(f"[{filename} | {model_type}] Successfully anonymized and downloaded in {elapsed:.1f}s")
        else:
            print(f"[{filename} | {model_type}] Error: Server returned {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[{filename} | {model_type}] Failed to process: {e}")

def process_directory():
    print("Select AnimeGANv3 Model:")
    print("1. Shinkai (AnimeGANv3_Shinkai_37.onnx)")
    print("2. Hayao (AnimeGANv3_Hayao_36.onnx)")
    print("3. Both (Process with both models)")
    choice = input("Enter choice (1/2/3): ").strip()
    
    models_to_run = []
    if choice == "1":
        models_to_run = ["shinkai"]
    elif choice == "2":
        models_to_run = ["hayao"]
    elif choice == "3":
        models_to_run = ["shinkai", "hayao"]
    else:
        print("Invalid choice. Exiting.")
        return

    os.chdir(INPUT_DIR)
    files = glob.glob("*.mp4")
    
    # Filter out already processed files
    to_process = [f for f in files if not f.startswith("anonymized_") and not f.startswith("hayao_anonymized_") and not f.startswith("shinkai_anonymized_")]
        
    if not to_process:
        print("No new videos found to stylize.")
        return
        
    tasks = []
    for f in to_process:
        for m in models_to_run:
            tasks.append((f, m))
            
    print(f"Found {len(to_process)} files. Total tasks queued: {len(tasks)}. Starting multi-threaded processing...")
    
    # Use a ThreadPool to hit the servers concurrently
    with ThreadPoolExecutor(max_workers=len(SERVERS)) as executor:
        for idx, (file, model_type) in enumerate(tasks):
            file_path = os.path.join(INPUT_DIR, file)
            # Round-robin server assignment
            server_url = SERVERS[idx % len(SERVERS)]
            executor.submit(stylize_video, file_path, server_url, model_type)

if __name__ == "__main__":
    process_directory()
