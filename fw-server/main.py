import os
import tempfile
import time
import asyncio
import gc
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

# Global state for VRAM management
model_instance = None
model_lock = asyncio.Lock()
last_active_time = time.time()
active_requests = 0

async def unload_model_if_idle():
    """Background task that checks every 5 seconds if the model has been idle for >30s."""
    global model_instance
    while True:
        await asyncio.sleep(5)
        async with model_lock:
            # Only unload if the model exists, there are NO active requests, and 30s have passed
            if model_instance is not None and active_requests == 0:
                if (time.time() - last_active_time) > 30:
                    print("Idle timeout (30s) reached. Unloading model to free VRAM...")
                    del model_instance
                    model_instance = None
                    # Force garbage collection to ensure CTranslate2 releases the VRAM immediately
                    gc.collect()
                    print("VRAM successfully freed.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the idle checker loop in the background when the server starts
    checker_task = asyncio.create_task(unload_model_if_idle())
    yield
    # Cancel the loop when the server shuts down
    checker_task.cancel()

app = FastAPI(title="Faster-Whisper Server", lifespan=lifespan)

@app.post("/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    global model_instance, last_active_time, active_requests
    
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Save the uploaded file to a temporary file on disk
    try:
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
        with os.fdopen(fd, "wb") as f:
            while chunk := await file.read(8192 * 1024):  # 8MB chunks
                f.write(chunk)
                
        # Safely acquire the lock to check/load the model
        async with model_lock:
            if model_instance is None:
                print("Loading Whisper 'large-v3' model into VRAM...")
                # We load it in a thread so it doesn't block FastAPI's event loop
                loop = asyncio.get_running_loop()
                model_instance = await loop.run_in_executor(
                    None, 
                    lambda: WhisperModel("large-v3", device="cuda", compute_type="float16")
                )
                print("Model loaded successfully!")
            
            # Increment active requests so the idle checker knows we're busy
            active_requests += 1

        print(f"Transcribing {file.filename}...")
        
        # Define the synchronous transcription function
        def run_transcription():
            segments, info = model_instance.transcribe(temp_path, beam_size=5)
            transcript_text = []
            for segment in segments:
                transcript_text.append({
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text
                })
            return info, transcript_text

        # Run transcription in a background thread to prevent blocking the async event loop
        loop = asyncio.get_running_loop()
        info, transcript_text = await loop.run_in_executor(None, run_transcription)
            
        print(f"Finished transcribing {file.filename}")
        return JSONResponse(content={
            "language": info.language,
            "language_probability": info.language_probability,
            "duration": info.duration,
            "segments": transcript_text
        })
        
    except Exception as e:
        print(f"Error during transcription: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Crucial cleanup: Decrement active requests and start the 30s timer
        async with model_lock:
            if active_requests > 0:
                active_requests -= 1
            last_active_time = time.time()
            
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    # Listens on all interfaces at port 58329
    uvicorn.run(app, host="0.0.0.0", port=58329)
