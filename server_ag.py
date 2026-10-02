import os
import subprocess
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse

app = FastAPI()

MODELS = {
    "hayao": "deploy/AnimeGANv3_Hayao_36.onnx",
    "shinkai": "deploy/AnimeGANv3_Shinkai_37.onnx"
}

@app.post("/process-video")
async def process_video(file: UploadFile = File(...), model_type: str = Form("hayao")):
    input_path = f"inputs/vid/{file.filename}"
    
    # Prefix output filename with model name to avoid overwrites if both are requested
    out_filename = f"{model_type}_{file.filename}"
    output_path = f"output/results/{out_filename}"
    
    os.makedirs("inputs/vid", exist_ok=True)
    os.makedirs("output/results", exist_ok=True)
    
    with open(input_path, "wb") as buffer:
        while chunk := await file.read(8192 * 1024):
            buffer.write(chunk)
            
    selected_model = MODELS.get(model_type.lower(), MODELS["hayao"])
        
    # Trigger the repository's native script
    # This automatically loads and unloads the model from VRAM since it's a subprocess!
    subprocess.run([
        "python", "tools/video2anime.py",
        "-i", input_path,
        "-o", "output/results",
        "-m", selected_model
    ], check=True)
    
    # We return the processed file
    return FileResponse(output_path, media_type="video/mp4", filename=out_filename)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=55329)
