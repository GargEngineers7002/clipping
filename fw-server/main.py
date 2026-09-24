import os
import tempfile
import asyncio
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import traceback

# Restrict to a maximum of 2 concurrent GPU transcriptions (4.3 GB * 2 = 8.6 GB VRAM)
gpu_semaphore = asyncio.Semaphore(2)

def transcribe_worker(temp_path):
    # Load NVIDIA libraries in the worker process
    import ctypes
    import glob
    try:
        import nvidia.cublas.lib
        import nvidia.cudnn.lib
        cublas_dir = os.path.dirname(nvidia.cublas.lib.__file__)
        cudnn_dir = os.path.dirname(nvidia.cudnn.lib.__file__)
        for lib in glob.glob(os.path.join(cublas_dir, "libcublas.so.*")):
            ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
        for lib in glob.glob(os.path.join(cudnn_dir, "libcudnn.so.*")):
            ctypes.CDLL(lib, mode=ctypes.RTLD_GLOBAL)
    except Exception:
        pass

    from faster_whisper import WhisperModel
    print("Loading Whisper 'large-v3' model into VRAM...")
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")
    
    segments, info = model.transcribe(temp_path, beam_size=5)
    transcript_text = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
    
    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "duration": info.duration,
        "segments": transcript_text
    }

app = FastAPI(title="Faster-Whisper Server")

@app.post("/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Save the uploaded file to a temporary file on disk
    try:
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
        with os.fdopen(fd, "wb") as f:
            while chunk := await file.read(8192 * 1024):  # 8MB chunks
                f.write(chunk)
                
        print(f"Queueing {file.filename} (Waiting for available GPU slot...)")
        
        # Enforce max 2 concurrent GPU jobs
        async with gpu_semaphore:
            print(f"Starting GPU transcription for {file.filename}")
            loop = asyncio.get_running_loop()
            
            # Spawn a fresh process for transcription. When it finishes, the process dies and VRAM drops to 0!
            with ProcessPoolExecutor(max_workers=1, mp_context=mp.get_context("spawn")) as pool:
                result = await loop.run_in_executor(pool, transcribe_worker, temp_path)
            
            print(f"Finished transcribing {file.filename}. Subprocess destroyed, VRAM cleared.")
            return JSONResponse(content=result)
            
    except Exception as e:
        print(f"Error during transcription: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    # Listens on all interfaces at port 58329
    uvicorn.run(app, host="0.0.0.0", port=58329)
