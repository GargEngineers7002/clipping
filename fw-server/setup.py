import os
import sys
import ctranslate2
from faster_whisper import WhisperModel

def main():
    print("=== faster-whisper setup ===")
    
    print("\n1. Checking for CUDA GPU accessibility...")
    try:
        cuda_devices = ctranslate2.get_cuda_device_count()
        if cuda_devices > 0:
            print(f"SUCCESS: Found {cuda_devices} CUDA device(s) available to ctranslate2.")
        else:
            print("WARNING: No CUDA devices found by ctranslate2! The server will fallback to CPU (which is very slow).")
    except Exception as e:
        print(f"Error checking CUDA: {e}")
        
    print("\n2. Downloading faster-whisper 'large-v3' model...")
    try:
        # Initializing the model downloads it and saves it in the cache (~/.cache/huggingface/hub/)
        # We specify device="cpu" just for the download step, so this script doesn't fail 
        # if run on a machine without a GPU (e.g. for pre-baking a docker image).
        # When main.py runs, it will load this cached model into the GPU.
        model = WhisperModel("large-v3", device="cpu", compute_type="float16")
        print("SUCCESS: Model 'large-v3' downloaded and cached successfully!")
    except Exception as e:
        print(f"Error downloading model: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
