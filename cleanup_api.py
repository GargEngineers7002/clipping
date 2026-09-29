from fastapi import FastAPI
import os
import glob

app = FastAPI()

# Adjust this path based on where ComfyUI is installed on the target server
COMFY_INPUT_DIR = os.path.expanduser("~/ComfyUI/input")

@app.post("/cleanup")
def cleanup_inputs():
    try:
        files = glob.glob(os.path.join(COMFY_INPUT_DIR, "*"))
        count = 0
        for f in files:
            if os.path.isfile(f):
                os.remove(f)
                count += 1
        return {"status": "success", "deleted_files": count}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8189)  # Running on 8189 to avoid conflicts
