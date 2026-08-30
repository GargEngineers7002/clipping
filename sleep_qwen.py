import requests
import sys

def main():
    # The Qwen server IP is 100.72.216.28 and we set it to port 58328
    # Using level=2 to fully offload weights and KV cache to maximize free VRAM
    url = "http://100.72.216.28:58328/sleep?level=2"
    
    print(f"Sending sleep request to Qwen server at {url}...")
    try:
        response = requests.post(url, timeout=15)
        response.raise_for_status()
        print("SUCCESS: Qwen server has been put to sleep (Level 2).")
        print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to put the server to sleep: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
