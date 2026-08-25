# Short-Form Video Automation Agent Specification

## 1. Goal

When given a topic or campaign URL (e.g., ContentRewards/Whop webinar), autonomously:

1. Research viral angles or find top-ranking video sources.
2. Clip high-retention segments (or generate AI video clips via ComfyUI).
3. Assemble 9:16 vertical videos with burned captions and explicit visual CTAs.
4. Auto-publish across YouTube Shorts, TikTok, and Instagram with customized titles, tags, and affiliate links in descriptions.

---

## 2. Execution Pipeline

### Step 1: Deep Research & Script Generation

- **LLM Endpoint:** Ollama (`http://127.0.0.1:11434/api/generate`) with model `qwen3-coder:30b`.
- **Payload Requirement:** Always include `"keep_alive": 0` in all Ollama API calls so VRAM is cleared immediately for video tasks.
- **Search Tool:** Exa Web Search to find:
  - Top trending hooks, discussions, and keywords around the query.
  - Relevant YouTube URLs if creating clipped content.

### Step 2: Content Sourcing & Clipping (If source videos exist)

- **Download:** Execute `yt-dlp -f "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]" -o "raw_input.mp4" "<URL>"`.
- **Transcribe:** Run `whisperx` or `faster-whisper` CLI to generate word-level timestamped `.json`.
- **Hook Extraction:** Pass transcripts to Qwen to locate optimal 30–60 second start and end timestamps.
- **Cut Clip:**
  ```bash
  ffmpeg -ss <START_TIME> -to <END_TIME> -i raw_input.mp4 -c:v libx264 -c:a aac clipped_raw.mp4
  ```

### Step 3: ComfyUI AI Generation (If generating pure AI clips)

- **Endpoint:** `http://127.0.0.1:8188/prompt`
- **Workflow:** Send JSON workflow payload utilizing the Wan 2.1 diffusion model.
- **Polling:** Poll `/history/<prompt_id>` until the generated `.mp4` is saved in `ComfyUI/output`.

### Step 4: Video Formatting & Call to Action (FFmpeg)

- **Format:** Vertical 1080x1920 (9:16 ratio).
- **CTA Overlay:** Overlay on-screen text banner (e.g., "Link in Description!") during the final 5–10 seconds.
- **Subtitles:** Generate `.ass` subtitles with highlighted text and burn them into the output:
  ```bash
  ffmpeg -y -i clipped_raw.mp4 -vf "crop=ih*(9/16):ih,ass=subtitles.ass,drawtext=text='Click Link in Description':fontcolor=yellow:fontsize=48:box=1:boxcolor=black@0.5:x=(w-text_w)/2:y=h-200:enable='gte(t,20)'" -c:a copy final_output_1.mp4
  ```

### Step 5: Metadata & Multi-Platform Upload

- **Metadata Generation:** Generate engaging short-form titles, relevant hashtags, and description text including the target referral/campaign link.
- **Upload:** Execute tool calls through MCP to upload:
  - YouTube Shorts: `upload_youtube_short(file="final_output_1.mp4", title=..., description=...)`
  - TikTok: `upload_tiktok_video(file="final_output_1.mp4", caption=...)`
  - Instagram Reels: `upload_instagram_reel(file="final_output_1.mp4", caption=...)`
