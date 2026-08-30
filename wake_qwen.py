import requests
import sys

def main():
    # The Qwen server IP is 100.72.216.28 and we set it to port 58328
    url = "http://100.72.216.28:58328/wake_up"
    
    print(f"Sending wake up request to Qwen server at {url}...")
    try:
        response = requests.post(url, timeout=15)
        response.raise_for_status()
        print("SUCCESS: Qwen server is waking up (or is already awake).")
        print(f"Response: {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Failed to wake up the server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
