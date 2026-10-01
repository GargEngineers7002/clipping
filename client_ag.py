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

def stylize_video(file_path, server_url):
    filename = os.path.basename(file_path)
    print(f"[{filename}] Starting upload to {server_url}...")
    start_time = time.time()
    
    try:
        with open(file_path, "rb") as f:
            response = requests.post(server_url, files={"file": f}, timeout=600)
            
        if response.status_code == 200:
            out_name = os.path.join(INPUT_DIR, f"anonymized_{filename}")
            with open(out_name, "wb") as out_f:
                out_f.write(response.content)
            elapsed = time.time() - start_time
            print(f"[{filename}] Successfully anonymized and downloaded in {elapsed:.1f}s")
        else:
            print(f"[{filename}] Error: Server returned {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[{filename}] Failed to process: {e}")

def process_directory():
    os.chdir(INPUT_DIR)
    files = glob.glob("*.mp4")
    
    # Filter out already processed files
    to_process = [f for f in files if not f.startswith("anonymized_")]
        
    if not to_process:
        print("No new videos found to stylize.")
        return
        
    print(f"Found {len(to_process)} files to stylize. Starting multi-threaded processing...")
    
    # Use a ThreadPool to hit the servers concurrently
    with ThreadPoolExecutor(max_workers=len(SERVERS)) as executor:
        for idx, file in enumerate(to_process):
            file_path = os.path.join(INPUT_DIR, file)
            # Round-robin server assignment
            server_url = SERVERS[idx % len(SERVERS)]
            executor.submit(stylize_video, file_path, server_url)

if __name__ == "__main__":
    process_directory()
