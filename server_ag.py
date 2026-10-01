import os
import subprocess
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse

app = FastAPI()
MODEL_PATH = "deploy/AnimeGANv3_Hayao_36.onnx" # Ensure you have downloaded a model here

@app.post("/process-video")
async def process_video(file: UploadFile = File(...)):
    input_path = f"inputs/vid/{file.filename}"
    output_path = f"output/results/{file.filename}"
    
    os.makedirs("inputs/vid", exist_ok=True)
    os.makedirs("output/results", exist_ok=True)
    
    with open(input_path, "wb") as buffer:
        while chunk := await file.read(8192 * 1024):
            buffer.write(chunk)
        
    # Trigger the repository's native script
    # This automatically loads and unloads the model from VRAM since it's a subprocess!
    subprocess.run([
        "python", "tools/video2anime.py",
        "-i", input_path,
        "-o", "output/results",
        "-m", MODEL_PATH
    ], check=True)
    
    # We return the processed file
    return FileResponse(output_path, media_type="video/mp4", filename=f"anonymized_{file.filename}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=55329)
