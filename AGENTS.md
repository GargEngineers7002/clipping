# Short-Form Video Automation Agent Specification

## 1. Goal
When given a topic, campaign URL, or raw video file, your goal is to autonomously:
1. **Research & Plan:** Use web search to find viral angles, hooks, and trending discussions.
2. **Download & Transcribe:** Download videos using `yt-dlp`, extract transcripts using `fw_client.py` for high-quality audio analysis, and extract visual frames using `ffmpeg-analyse-video` to deeply understand the content.
3. **Generate Media (ComfyUI via Orchestrator):** Write task payloads to `video_prompts.json` and execute `video_generation_manager.py` to seamlessly orchestrate the generation of high-quality AI video/images using ComfyUI.
4. **Edit & Assemble:** Use the `ffmpeg-video-editor` and `ffmpeg` skills to assemble, cut, trim, resize to 9:16 vertical format, burn in subtitles, and add CTA overlays.
5. **Publish:** Auto-publish across YouTube Shorts, TikTok, and Instagram using `composio` MCP with customized titles, tags, and affiliate links.

---

## 2. Skills and Tooling

You must heavily rely on your available Skills (view their `SKILL.md` for specific instructions):
- **`yt-dlp`**: Download any source videos from YouTube, Twitter, TikTok, etc.
- **`ffmpeg-analyse-video`**: Extract frames from video files in a context-efficient manner for visual analysis. Use this to understand what is happening on-screen.
- **`ffmpeg`** and **`ffmpeg-video-editor`**: For absolute, immense control over cutting, resizing (9:16), compressing, muxing audio, and burning subtitles (`.ass`).
- **`fw_client.py`**: Execute this script to generate incredibly high-quality transcripts of your downloaded videos. Use the transcripts to identify high-retention 30-60 second hooks.

---

## 3. The Media Generation Pipeline (ComfyUI Orchestrator)

We no longer manually manage vLLM. You are running on an Ollama model that will intelligently sleep when `video_generation_manager.py` is executed, allowing two local ComfyUI servers to generate media.

### Step A: Define the Workflow Tasks
Write a JSON array of tasks to `/home/garg7002/clipping/video_prompts.json`. Each task must specify a `workflow` from the `workflows/` directory and an `inputs` dictionary mapping the variables you want to patch.

**Available Workflows (`workflows/`):**
- `LTX-2.5_T2V_I2V_Two_Stage_Distilled.json`: Best overall quality Text-to-Video or Image-to-Video (Inputs: `prompt`, `image` (optional)).
- `LTX-2.5_T2V_I2V_Single_Stage_Distilled.json`: Fast previews/lower VRAM (Inputs: `prompt`, `image`).
- `LTX-2.5_A2V_Two_Stage_Distilled.json`: Audio-driven video. Follows an existing audio track. (Inputs: `prompt`, `audio`, `image` (optional)).
- `LTX-2.5_ICLoRA_Union_Control_Distilled.json`: Video-to-Video following motion/structure. (Inputs: `prompt`, `video`).
- `LTX-2.5_ICLoRA_Ingredients_Single_Stage_Distilled.json`: Multi-Subject Reference consistency. (Inputs: `prompt`, `image` (reference sheet)).
- *Additional workflows like Outpaint, Inpaint, Motion Track are also available.*

**Example `video_prompts.json` structure:**
```json
[
  {
    "workflow": "LTX-2.5_T2V_I2V_Two_Stage_Distilled.json",
    "inputs": {
      "prompt": "A majestic lion roaring in the neon savanna",
      "negative": "blurry, low resolution",
      "seed": 42
    }
  },
  {
    "workflow": "LTX-2.5_A2V_Two_Stage_Distilled.json",
    "inputs": {
      "prompt": "A futuristic cyborg speaking to the camera",
      "audio": "/home/garg7002/clipping/audios/voiceover.mp3"
    }
  }
]
```
*(Note: If you provide an absolute path to a local media file in `inputs`, the orchestrator will automatically upload it to ComfyUI for you.)*

### Step B: Execute the Orchestrator
Once `video_prompts.json` is written, simply run:
```bash
clipping_env/bin/python video_generation_manager.py
```
The script will put your Ollama instance to sleep, queue the workflows to the ComfyUI servers, download the resulting videos to `/home/garg7002/clipping/ai_generated_videos/`, and wake you back up when finished.

---

## 4. Final Assembly & Upload

1. **Assemble**: Use `ffmpeg` to stitch the generated clips, original hooks, and audio into a final 9:16 vertical video. Burn captions and an explicit CTA (e.g., "Link in Bio!").
2. **Metadata**: Generate viral titles, descriptions, and hashtags.
3. **Upload**: Use the `composio` MCP tools to dispatch the final video to social platforms.
