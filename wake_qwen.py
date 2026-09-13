import requests
import sys

def main():
    # The Ollama server IP is 100.72.216.28 and port 11434
    url = "http://100.72.216.28:11434/api/generate"
    
    # Preload the model by sending keep_alive=-1 and an empty prompt
    payload = {
        "model": "qwen3.8:27b",
        "keep_alive": -1
    }
    
    print(f"Sending wake up request to Ollama server at {url}...")
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print("SUCCESS: Qwen server is waking up (loading into VRAM).")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to wake up the server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
