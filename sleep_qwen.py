import requests
import sys

def main():
    # The Ollama server IP is 100.72.216.28 and port 11434
    url = "http://100.72.216.28:11434/api/generate"
    
    # Unload the model by sending keep_alive=0
    payload = {
        "model": "qwen3.8:27b",
        "keep_alive": 0
    }
    
    print(f"Sending sleep request to Ollama server at {url}...")
    try:
        response = requests.post(url, json=payload, timeout=15)
        response.raise_for_status()
        print("SUCCESS: Qwen server has been put to sleep (VRAM cleared).")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to put the server to sleep: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
