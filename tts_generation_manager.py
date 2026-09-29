import os
import sys
import time
import json
import uuid
import re
import requests
import subprocess

TTS_SERVERS = ["http://100.72.197.70:58328"]
OUTPUT_DIR = "/home/garg7002/clipping/ai_generated_audios/tts"
PROMPTS_FILE = "/home/garg7002/clipping/tts_prompts.json"
WORKFLOWS_DIR = "/home/garg7002/clipping/tts_workflows"

def get_alive_server():
    for server in TTS_SERVERS:
        try:
            r = requests.get(f"{server}/system_stats", timeout=5)
            if r.status_code == 200:
                return server
        except requests.exceptions.RequestException:
            continue
    return None

def upload_to_comfyui(server_url, filepath):
    with open(filepath, 'rb') as f:
        files = {'image': f}
        data = {'type': 'input', 'overwrite': 'true'}
        r = requests.post(f"{server_url}/upload/image", files=files, data=data)
        r.raise_for_status()
        return r.json()['name']

def chunk_text(text):
    # Split text into chunks by sentences to avoid token limits
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks = []
    current_chunk = ""
    for s in sentences:
        if len(current_chunk) + len(s) > 1000:
            if current_chunk: chunks.append(current_chunk.strip())
            current_chunk = s
        else:
            current_chunk += " " + s
    if current_chunk: chunks.append(current_chunk.strip())
    return chunks

def patch_and_queue_tts(wf, inputs, server_url, chunk_text_val=None):
    # Deep copy to avoid mutating original
    wf_patched = json.loads(json.dumps(wf))
    
    multi_speaker_node = None
    speaker_nodes = {}

    for node_id, node in wf_patched.items():
        c_type = node.get("class_type", "")
        title = node.get("_meta", {}).get("title", "").lower()

        # Handle text injection
        if "text" in node["inputs"] and isinstance(node["inputs"]["text"], str):
            if chunk_text_val:
                node["inputs"]["text"] = chunk_text_val
            elif "text" in inputs:
                node["inputs"]["text"] = inputs["text"]

        if "instruction" in node["inputs"] and "instruction" in inputs:
            node["inputs"]["instruction"] = inputs["instruction"]

        # Handle audio references
        if c_type == "LoadAudio" and "audio" in inputs:
            node["inputs"]["audio"] = upload_to_comfyui(server_url, inputs["audio"])

        # Track Multi-Speaker Nodes
        if c_type == "Breeze TTS 2 Multi-Speaker":
            multi_speaker_node = node
        if c_type == "Breeze TTS 2 Speaker":
            speaker_nodes[node_id] = node
            
    # Dynamic Multi-Speaker logic
    if multi_speaker_node and "speakers" in inputs:
        used_slots = []
        for i, speaker_data in enumerate(inputs["speakers"]):
            slot = i + 1
            slot_key = f"speaker_{slot}"
            used_slots.append(slot_key)
            
            # Find the speaker node connected to this slot
            connected_node_id = None
            if slot_key in multi_speaker_node["inputs"]:
                connected_node_id = multi_speaker_node["inputs"][slot_key][0]
                
            if connected_node_id and connected_node_id in speaker_nodes:
                speaker_nodes[connected_node_id]["inputs"]["name"] = speaker_data.get("name", f"Speaker{slot}")
                if "audio" in speaker_data:
                    # Find LoadAudio node connected to this speaker
                    audio_node_id = speaker_nodes[connected_node_id]["inputs"]["reference_audio"][0]
                    wf_patched[audio_node_id]["inputs"]["audio"] = upload_to_comfyui(server_url, speaker_data["audio"])

        # Disconnect unused speakers
        for slot in range(1, 9):
            slot_key = f"speaker_{slot}"
            if slot_key not in used_slots and slot_key in multi_speaker_node["inputs"]:
                del multi_speaker_node["inputs"][slot_key]

    client_id = str(uuid.uuid4())
    r = requests.post(f"{server_url}/prompt", json={"prompt": wf_patched, "client_id": client_id})
    r.raise_for_status()
    return r.json()["prompt_id"], client_id

def download_output(server_url, prompt_id, task_id, idx):
    start = time.time()
    while time.time() - start < 600:
        r = requests.get(f"{server_url}/history/{prompt_id}")
        if r.status_code == 200:
            hist = r.json()
            if prompt_id in hist:
                for node_id, node_output in hist[prompt_id].get("outputs", {}).items():
                    if "audio" in node_output:
                        # Depends on ComfyUI Audio Save format, adjust if needed
                        fname = node_output["audio"][0]["filename"]
                        url = f"{server_url}/view?filename={fname}&type=output"
                        ar = requests.get(url)
                        if ar.status_code == 200:
                            out_path = os.path.join(OUTPUT_DIR, f"{task_id}_{idx}.mp3")
                            with open(out_path, "wb") as f:
                                f.write(ar.content)
                            print(f"  -> Saved output to: {out_path}")
                            return out_path
                return None
        time.sleep(3)
    print("Generation timed out.")
    return None

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    server = get_alive_server()
    if not server:
        print("ERROR: No TTS ComfyUI servers are alive.")
        sys.exit(1)
        
    if not os.path.exists(PROMPTS_FILE):
        print(f"No prompts file found at {PROMPTS_FILE}")
        sys.exit(0)
            
    with open(PROMPTS_FILE, "r") as f:
        tasks = json.load(f)
        
    if not tasks:
        sys.exit(0)
        
    for task in tasks:
        print(f"\n>> Processing TTS task with workflow: {task.get('workflow')}")
        wf_path = os.path.join(WORKFLOWS_DIR, task['workflow'])
        with open(wf_path) as f:
            wf = json.load(f)
            
        inputs = task.get("inputs", {})
        task_id = str(uuid.uuid4())[:8]
        
        # Check if we need to chunk (only for single speaker long texts)
        if "text" in inputs and "speakers" not in inputs and len(inputs["text"]) > 1000:
            chunks = chunk_text(inputs["text"])
            print(f"Text is long, chunking into {len(chunks)} parts...")
            files = []
            for idx, chunk in enumerate(chunks):
                prompt_id, client_id = patch_and_queue_tts(wf, inputs, server, chunk_text_val=chunk)
                out_file = download_output(server, prompt_id, task_id, idx)
                if out_file: files.append(out_file)
            
            if len(files) > 1:
                concat_list = os.path.join(OUTPUT_DIR, f"{task_id}_list.txt")
                with open(concat_list, "w") as f:
                    for file in files:
                        f.write(f"file '{os.path.basename(file)}'\n")
                
                final_out = os.path.join(OUTPUT_DIR, f"{task_id}_final.mp3")
                subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list, "-c", "copy", final_out], check=True)
                print(f"Stitched chunks into {final_out}")
                for file in files: os.remove(file)
                os.remove(concat_list)
        else:
            prompt_id, client_id = patch_and_queue_tts(wf, inputs, server)
            download_output(server, prompt_id, task_id, 0)
            

    # Trigger cleanup on the server
    cleanup_url = server.replace(":58328", ":8189").replace(":8188", ":8189") + "/cleanup"
    try:
        r = requests.post(cleanup_url, timeout=5)
        print(f"Cleanup triggered: {r.json()}")
    except Exception as e:
        print(f"Warning: Failed to trigger cleanup API: {e}")

    with open(PROMPTS_FILE, "w") as f:
        json.dump([], f)

if __name__ == "__main__":
    main()
