import os
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from faster_whisper import WhisperModel

app = FastAPI(title="Faster-Whisper Server")

# Initialize the model at startup
print("Loading Whisper 'large-v3' model to GPU...")
# Using device="cuda", float16 as requested
model = WhisperModel("large-v3", device="cuda", compute_type="float16")
print("Model loaded successfully!")

@app.post("/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")
    
    # Save the uploaded file to a temporary file on disk
    try:
        fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
        with os.fdopen(fd, "wb") as f:
            # Read in chunks to avoid high RAM usage for large video files
            while chunk := await file.read(8192 * 1024):  # 8MB chunks
                f.write(chunk)
                
        # Transcribe the temp file
        # 'av' is installed, so faster-whisper will automatically extract audio
        print(f"Transcribing {file.filename}...")
        segments, info = model.transcribe(temp_path, beam_size=5)
        
        # We must iterate over the generator to actually perform the transcription
        transcript_text = []
        for segment in segments:
            transcript_text.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text
            })
            
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
        # Clean up the temporary file
        if 'temp_path' in locals() and os.path.exists(temp_path):
            os.remove(temp_path)

if __name__ == "__main__":
    import uvicorn
    # Listens on all interfaces at port 58329
    uvicorn.run(app, host="0.0.0.0", port=58329)
