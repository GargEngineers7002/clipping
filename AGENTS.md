# Media Automation Agent Specification

## 1. Goal
When given a topic, campaign URL, or raw media file, your goal is to autonomously:
1. **Research & Plan:** Use web search to find viral angles, hooks, and trending discussions.
2. **Download & Transcribe:** Download videos/audio using `yt-dlp`. Extract transcripts using `fw_client.py` for high-quality analysis.
3. **Generate Audio (TTS):** Use `tts_generation_manager.py` with Breeze TTS 2 workflows to synthesize high-quality voiceovers.
4. **Generate Media (Video/Image):** Use `video_generation_manager.py` to create AI video and images based on transcripts or TTS audio.
5. **Edit & Assemble:** Use `ffmpeg-video-editor` and `ffmpeg` to assemble, cut, trim, overlay text, and format media appropriately.
6. **Publish:** Auto-publish across platforms using `composio` MCP.

---

## 2. Shared GPU Concurrency Warning
**CRITICAL RULE:** `fw_client.py` (Faster-Whisper) and `tts_generation_manager.py` (Breeze TTS) both share the exact same RTX 2080 Ti GPU on the remote server (`100.72.197.70`). 
You **MUST NEVER** run them in parallel. Always wait for transcriptions (`fw_client.py`) to fully finish before running TTS (`tts_generation_manager.py`), or vice versa.

---

## 3. The Audio Generation Pipeline (TTS)
You can synthesize speech by writing a JSON array to `/home/garg7002/clipping/tts_prompts.json` and then running `python tts_generation_manager.py`. The script will automatically chunk long text, run it through ComfyUI, stitch the audio chunks with `ffmpeg`, and save it to `ai_generated_audios/tts/`.

**Available TTS Workflows (`tts_workflows/`):**
- `breeze_voice_design_api.json`: (Single Speaker) Inputs: `text`, `instruction`.
- `breeze_voice_direction_api.json`: (Single Speaker with Ref) Inputs: `text`, `instruction`, `audio` (absolute path to ref).
- `breeze_multi_speaker_api.json`: (Multi-Speaker Dialogue) Inputs: `speakers` (array).

**Example `tts_prompts.json` Single Speaker:**
```json
[
  {
    "workflow": "breeze_voice_direction_api.json",
    "inputs": {
      "text": "Hello world! This is a long script.",
      "instruction": "Speak happily",
      "audio": "/home/garg7002/clipping/audios/ref.mp3"
    }
  }
]
```

**Example `tts_prompts.json` Multi-Speaker:**
```json
[
  {
    "workflow": "breeze_multi_speaker_api.json",
    "inputs": {
      "speakers": [
        {"name": "Alice", "audio": "/home/garg7002/clipping/audios/alice_ref.mp3"},
        {"name": "Bob", "audio": "/home/garg7002/clipping/audios/bob_ref.mp3"}
      ]
    }
  }
]
```

---

## 4. The Media Generation Pipeline (Video)
You can generate video/images by writing a JSON array of tasks to `/home/garg7002/clipping/video_prompts.json` and then running `python video_generation_manager.py`. 

**CRITICAL RULE: DO NOT use `cat` or `read` on the `.json` files in the `workflows/` directory! They are massive and will instantly crash your context window. Rely strictly on the mapping below.**

**Available Workflows & Patchable Inputs:**
- `LTX-2.5_T2V_I2V_Two_Stage_Distilled.json`: Text-to-Video / Image-to-Video (Inputs: `prompt`, `negative`, `image` (optional), `duration`, `seed`, `width`, `height`).
- `LTX-2.5_A2V_Two_Stage_Distilled.json`: Audio-driven video. (Inputs: `prompt`, `negative`, `audio` (absolute path), `image` (optional), `duration`, `seed`, `width`, `height`).
- `LTX-2.5_ICLoRA_Union_Control_Distilled.json`: Video-to-Video. (Inputs: `prompt`, `negative`, `video` (absolute path), `seed`, `width`, `height`).
- `LTX-2.5_ICLoRA_Ingredients_Single_Stage_Distilled.json`: Character Reference. (Inputs: `prompt`, `negative`, `image` (reference sheet), `seed`, `width`, `height`).
- `image_flux2_text_to_image_9b.json`: Text-to-Image. (Inputs: `prompt`, `negative`, `seed`, `width`, `height`).
- `image_qwen_image_edit_2509.json`: Image-to-Image / Edit. (Inputs: `prompt`, `image`, `seed`, `width`, `height`).

**Safe Resolutions (VRAM Constraints):**
Do not use 1080p natively. Use these safe base resolutions (which are multiples of 32):
- **16:9 (Landscape/Long-form):** `"width": 960, "height": 544` OR `"width": 864, "height": 480`
- **9:16 (Vertical/Shorts):** `"width": 544, "height": 960` OR `"width": 480, "height": 864`
- **3:2 / 2:3 (Standard):** `"width": 768, "height": 512` OR `"width": 512, "height": 768`
*Strategy:* If the user asks for 1080p, generate at a safe base resolution above, and later use `ffmpeg` to upscale/pad the final assembled video to 1080p.

**Example `video_prompts.json` structure:**
```json
[
  {
    "workflow": "LTX-2.5_A2V_Two_Stage_Distilled.json",
    "inputs": {
      "prompt": "A futuristic cyborg speaking to the camera",
      "audio": "/home/garg7002/clipping/ai_generated_audios/tts/voiceover.wav",
      "seed": 42
    }
  }
]
```

---

## 5. Execution
Because you are using an independent CLI orchestration agent, **you CAN and SHOULD run all python scripts yourself using your tools.** 
You do not need to ask the user to run `video_generation_manager.py` or `tts_generation_manager.py`. Execute them directly and read their output.
