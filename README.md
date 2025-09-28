# GenCap 📸

A Python script to **generate and burn subtitles** into videos using **OpenAI Whisper**, **pysubs2**, and **FFmpeg**.  
It supports local transcription, `.srt` and `.ass` subtitle styling, Unicode languages (like Hindi), and fully customizable font, size, color, and position.  

---

## Features

- **Automatic Transcription**: Uses OpenAI Whisper to transcribe audio from any video.  
- **Subtitle Generation**: Converts Whisper output into `.srt` and `.ass` subtitle files.  
- **Custom Styling**: Adjust font, font size, color, position, and vertical margin.  
- **Unicode & Multilingual Support**: Supports non-Latin scripts (e.g., Hindi/Devanagari).  
- **Burn Subtitles into Video**: Uses FFmpeg to embed subtitles directly into the output video.  
- **Clean Visuals**: No black borders by default for sleek, modern subtitle appearance.  
- **Optional Pre-existing Transcript**: Can skip transcription if you already have a `.srt` file.  

---

## Solution Process (Step-by-Step)

The script works in **four main stages**:

### 1. Transcription
- If a transcript (`.srt`) is **not provided**, the script uses **Whisper** to transcribe the audio from the video.  
- Whisper returns **segments**, each containing:
  - `start` time
  - `end` time
  - `text` spoken in that interval  

### 2. SRT Generation
- Converts Whisper segments into an `.srt` file.  
- Each subtitle block in `.srt` format contains:
  1
  00:00:05,000 --> 00:00:10,000
  Hello, world!

### 3. ASS Styling
- Converts `.srt` → `.ass` using **pysubs2**.  
- Custom styling options include:
- `font` and `font_hindi` for multilingual support  
- `fontsize` for text size  
- `color` for subtitle text color  
- `position` (bottom, top, center) and `margin`  
- `outline` and `shadow` are removed for clean visuals (no black border)  

### 4. Burn Subtitles into Video
- Uses **FFmpeg** to embed `.ass` subtitles into the video:  

ffmpeg -i input.mp4 -vf "ass=styled.ass" -c:v libx264 -crf 18 -preset medium -c:a copy output.mp4

- The final video has the subtitles **permanently burned in**, compatible with any player.  

---

## Requirements

- Python 3.8+  
- [FFmpeg](https://ffmpeg.org/download.html)  
- Python packages:
```bash
pip install openai-whisper pysubs2 torch
```

## Usage Examples

### 1. Transcribe & Burn Subtitles
```bash
python subtitle_burner.py \
  --video input.mp4 \
  --out output_subbed.mp4 \
  --font "/path/to/NotoSans-Regular.ttf" \
  --fontsize 36 \
  --color "#FFFFFF" \
  --position bottom
  ```

  ### 2. With Language Hint (eg, Hindi)
  ```bash
  python subtitle_burner.py \
  --video input.mp4 \
  --out output_subbed.mp4 \
  --model small \
  --language hi \
  --font "/path/to/NotoSans-Regular.ttf" \
  --font_hindi "/path/to/NotoSansDevanagari-Regular.ttf" \
  --fontsize 36 \
  --color "#FFFFFF" \
  --position bottom
```
### 3. Use Existing .srt File
```bash
python subtitle_burner.py \
  --video input.mp4 \
  --transcript subtitles.srt \
  --out output_subbed.mp4 \
  --font "/path/to/NotoSans-Regular.ttf"
```
## Arguments/Options
| Argument       | Description                                                                  |
| -------------- | ---------------------------------------------------------------------------- |
| `--video`      | Input video file (required)                                                  |
| `--transcript` | Optional `.srt` transcript file (skips Whisper if provided)                  |
| `--out`        | Output video file (default: `output_subbed.mp4`)                             |
| `--model`      | Whisper model: `tiny`, `base`, `small`, `medium`, `large` (default: `small`) |
| `--language`   | Whisper transcription language hint (e.g., `hi` for Hindi)                   |
| `--font`       | Path to TTF font (required)                                                  |
| `--font_hindi` | Optional font for Hindi / Devanagari fallback                                |
| `--fontsize`   | Font size (default: 36)                                                      |
| `--color`      | Subtitle text color in hex, e.g., `#FFFFFF`                                  |
| `--position`   | Subtitle vertical position: `bottom`, `top`, `center` (default: `bottom`)    |
| `--margin_v`   | Vertical margin in pixels (default: 40)                                      |
| `--crf`        | FFmpeg CRF quality (default: 18)                                             |

---

## End Note

This project aims to simplify the process of generating high-quality, styled subtitles for videos.  
By combining **OpenAI Whisper** for transcription, **pysubs2** for styling, and **FFmpeg** for burning, you can create professional-looking subtitles in multiple languages with minimal effort.  

Whether you are creating content for YouTube, online courses, or personal projects, `subtitle_burner.py` allows you to automate the workflow while maintaining full control over font, color, size, and position.  

Contributions, suggestions, and improvements are welcome! Feel free to open an issue or submit a pull request.



