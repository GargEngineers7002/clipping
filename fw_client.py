import os
import time
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
SERVER_URL = "http://100.72.197.70:58329/transcribe"
VIDEOS_DIR = "/home/garg7002/clipping/videos"
TRANSCRIPTS_DIR = "/home/garg7002/clipping/transcripts"
# Max concurrent uploads. Since you have a 12 MB/s link, 2-4 concurrent 
# uploads should easily saturate it and ensure you don't fall back to DERP.
MAX_CONCURRENT_UPLOADS = 3  

def process_video(video_path):
    filename = os.path.basename(video_path)
    base_name, _ = os.path.splitext(filename)
    transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{base_name}.json")
    
    # Skip if we already have the transcript
    if os.path.exists(transcript_path):
        print(f"[{filename}] Skipping, transcript already exists.")
        return True
        
    print(f"[{filename}] Starting upload...")
    start_time = time.time()
    
    try:
        # We use a context manager for the file so it closes properly
        with open(video_path, "rb") as f:
            # Send file as multipart/form-data
            files = {"file": (filename, f)}
            response = requests.post(SERVER_URL, files=files)
            
        # Raise an exception if the server returns an HTTP error code (like 500)
        response.raise_for_status()
        
        # Save the returned JSON transcript
        with open(transcript_path, "w", encoding="utf-8") as out_f:
            json.dump(response.json(), out_f, indent=2)
            
        elapsed = time.time() - start_time
        print(f"[{filename}] Successfully transcribed in {elapsed:.1f}s")
        return True
        
    except Exception as e:
        print(f"[{filename}] Failed: {e}")
        return False

def main():
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
    
    valid_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.mp3', '.wav', '.m4a', '.flac')
    
    media_files = []
    
    for directory in [VIDEOS_DIR, "/home/garg7002/clipping/audios"]:
        if os.path.exists(directory):
            media_files.extend([
                os.path.join(directory, f) 
                for f in os.listdir(directory) 
                if f.lower().endswith(valid_extensions)
            ])
    
    if not media_files:
        print(f"No valid media files found in {VIDEOS_DIR} or audios dir.")
        return
        
    print(f"Found {len(media_files)} files. Starting multi-threaded processing...")
    
    # ThreadPoolExecutor is perfect for network-bound tasks like this in Python
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT_UPLOADS) as executor:
        # Submit all tasks to the executor
        futures = {executor.submit(process_video, vf): vf for vf in media_files}
        
        # Process results as they complete
        for future in as_completed(futures):
            vf = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"Unhandled exception for {os.path.basename(vf)}: {e}")
                
    print("All tasks completed.")

if __name__ == "__main__":
    main()
