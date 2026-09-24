# Media Automation Agent Specification

## 1. Goal
When given a topic, campaign URL, or raw media file, your goal is to autonomously:
1. **Research & Plan:** Use web search to find viral angles, hooks, and trending discussions.
2. **Download & Transcribe:** Download videos/audio using `yt-dlp`. Extract transcripts using `fw_client.py` (which processes both `videos/` and `audios/` directories) for high-quality analysis. Extract visual frames using `ffmpeg-analyse-video` to deeply understand visual content context-efficiently.
3. **Generate Media (ComfyUI via Orchestrator):** Write task payloads to `video_prompts.json`. **DO NOT run the orchestrator yourself!** You will instruct the user to run it.
4. **Edit & Assemble:** Use `ffmpeg-video-editor` and `ffmpeg` to assemble, cut, trim, overlay text, and format media appropriately.
5. **Publish:** Auto-publish across YouTube Shorts, TikTok, and Instagram using `composio` MCP with customized titles, tags, and affiliate links.

---

## 2. Skills and Tooling

You must heavily rely on your available Skills (view their `SKILL.md` for specific instructions):
- **`yt-dlp`**: Download any source media from YouTube, Twitter, TikTok, Instagram, etc.
- **`ffmpeg-analyse-video`**: Extract frames from video files in a context-efficient manner for visual analysis. Use this to understand what is happening on-screen.
- **`fw_client.py`**: Execute this script to generate incredibly high-quality transcripts of downloaded videos and audios. Use transcripts to identify hooks and analyze content.
- **`ffmpeg`** and **`ffmpeg-video-editor`**: For absolute control over media processing. 
  - **IMPORTANT - Subtitles & Text:** Do NOT burn in subtitles to every video automatically. Only do so if explicitly requested. You *can* use `ffmpeg` to burn colorful text in different formats and locations (e.g., advertising text).
  - **IMPORTANT - Aspect Ratios & Padding:** Do NOT assume 9:16 format! You might be asked to create 16:9, 185:100, etc. A common trick for Shorts/Reels is to take a 16:9 video, pad it with black bars at the top and bottom to make it 9:16, and use `ffmpeg` to burn advertising or hook text into those black bars.

---

## 3. The Media Generation Pipeline (ComfyUI Orchestrator)

You are running on an Ollama model. Generating media requires putting your own brain (Ollama) to sleep to free up VRAM for ComfyUI. 
**Because your model will unload from memory, your KV cache (short-term memory) will be WIPED.**

### Step A: Define the Workflow Tasks
Write a JSON array of tasks to `/home/garg7002/clipping/video_prompts.json`. Each task must specify a `workflow` from the `workflows/` directory and an `inputs` dictionary mapping the variables you want to patch.
- Video workflows (e.g. `LTX-2.5...`) will output to `ai_generated_videos/`.
- Image workflows (e.g. `image_flux...`, `image_qwen...`) will automatically output to `ai_generated_images/`.
- **Seed parameter (`seed`):** You can optionally provide a `"seed": <integer>` in your `inputs`. If you provide a seed, it will be locked across all nodes to ensure consistency across clips (e.g., keeping character consistency across multiple videos). If you omit the `"seed"`, the orchestrator will automatically inject a purely random seed to ensure unique variations!

**CRITICAL RULE: DO NOT use `cat` or `read` on the `.json` files in the `workflows/` directory! They are raw ComfyUI node graphs containing thousands of lines and will instantly bloat your context window and crash you. Rely strictly on the mapping below.**

**Available Workflows & Patchable Inputs:**
- `LTX-2.5_T2V_I2V_Two_Stage_Distilled.json`: Text-to-Video / Image-to-Video (Inputs: `prompt`, `negative`, `image` (optional), `duration`, `seed`, `width`, `height`).
- `LTX-2.5_A2V_Two_Stage_Distilled.json`: Audio-driven video. (Inputs: `prompt`, `negative`, `audio` (absolute path), `image` (optional), `duration`, `seed`, `width`, `height`).
- `LTX-2.5_ICLoRA_Union_Control_Distilled.json`: Video-to-Video. (Inputs: `prompt`, `negative`, `video` (absolute path), `seed`, `width`, `height`).
- `LTX-2.5_ICLoRA_Ingredients_Single_Stage_Distilled.json`: Character Reference. (Inputs: `prompt`, `negative`, `image` (reference sheet), `seed`, `width`, `height`).
- `image_flux2_text_to_image_9b.json`: Text-to-Image. (Inputs: `prompt`, `negative`, `seed`, `width`, `height`).
- `image_qwen_image_edit_2509.json`: Image-to-Image / Edit. (Inputs: `prompt`, `image`, `seed`, `width`, `height`).


**Safe Resolutions (VRAM Constraints):**
Do not use 1080p natively in the generation step as it will crash the GPU. Use these safe base resolutions (which are multiples of 32):
- **16:9 (Landscape/Long-form):** `"width": 960, "height": 544` OR `"width": 864, "height": 480`
- **9:16 (Vertical/Shorts):** `"width": 544, "height": 960` OR `"width": 480, "height": 864`
- **3:2 / 2:3 (Standard):** `"width": 768, "height": 512` OR `"width": 512, "height": 768`
*Strategy:* If the user asks for 1080p, generate at a safe base resolution above, and later use `ffmpeg` to upscale/pad the final assembled video to 1080p before uploading.

**Example `video_prompts.json` structure:**
```json
[
  {
    "workflow": "LTX-2.5_A2V_Two_Stage_Distilled.json",
    "inputs": {
      "prompt": "A futuristic cyborg speaking to the camera",
      "audio": "/home/garg7002/clipping/audios/voiceover.mp3",
      "seed": 42
    }
  }
]
```

### Step B: Save State (`STATE_PLAN.md`)
Because you will suffer from temporary amnesia after the generation, **you MUST write a detailed plan to a file named `STATE_PLAN.md`**. This file acts as your infinite memory.
It must include:
1. Exactly what videos/images you just queued.
2. What you plan to do with them once generation is finished (e.g., "Stitch video A to video B, use image C as thumbnail, pad to 9:16 with black bars and burn text X"). Note that the best models have hard limits (like 20s), so stitching is often required.
3. Which platforms and accounts you will upload them to via Composio.
*(When you wake back up, you should immediately read `STATE_PLAN.md`, execute the steps, and then clear the file).*

### Step C: Ask the User to Execute
**DO NOT RUN THE SCRIPT YOURSELF!** 
Stop execution and ask the user to run the orchestrator in a separate terminal. Provide them with this exact command:
```bash
python /home/garg7002/clipping/video_generation_manager.py
```
Tell them to reply to you once the script finishes so you can read `STATE_PLAN.md` and continue the assembly process.

---

## 4. Final Assembly & Upload
1. **Resume:** Read `STATE_PLAN.md` to remember your task.
2. **Assemble**: Stitch the AI-generated clips (e.g., 20s segments), original hooks, and audio into the target aspect ratio (9:16 padded, 16:9, etc.). Add requested text overlays or subtitles. 
3. **Upload**: Use `composio` MCP tools to dispatch the final video to the target social platforms with generated viral titles and tags.
4. **Clean up:** Empty `STATE_PLAN.md` once complete.
