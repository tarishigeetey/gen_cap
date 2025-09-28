#!/usr/bin/env python3
"""
subtitle_burner.py

Generates (or uses provided) subtitles for a video and burns them into a new video file.
Supports local OpenAI Whisper transcription, editable .srt output,
and styling via ASS (using pysubs2). Finally burns the ASS into the video via ffmpeg.

Features:
- Bold subtitles by default.
- Preserves your existing SRT file safely.
- Validates SRT content before converting to ASS.
- Correct handling of hex colors for ASS (yellow appears yellow).
- No border/outline or shadow for clean visuals.
"""

import argparse
import os
import subprocess
import sys
import pysubs2

# whisper import
try:
    import whisper
except Exception as e:
    print("ERROR: failed to import whisper. Make sure you installed `openai-whisper` and torch.")
    raise

def run_cmd(cmd):
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        print("ffmpeg error:", proc.stderr[:1000])
        raise RuntimeError("Command failed: " + " ".join(cmd))
    return proc

def transcribe_with_whisper(video_path: str, model_name: str = "small", language: str = None):
    print(f"Loading Whisper model '{model_name}' (this may take a while)...")
    model = whisper.load_model(model_name)

    opts = {}
    if language:
        opts["language"] = language
        opts["task"] = "transcribe"

    print("Transcribing (this will read the audio from the video)...")
    result = model.transcribe(video_path, **opts)
    segments = result.get("segments", [])
    print(f"Transcription finished: {len(segments)} segments.")
    return segments, result.get("text", "")

def segments_to_srt(segments, srt_path: str):
    def format_time(seconds: float):
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        msec = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{msec:03d}"

    with open(srt_path, "w", encoding="utf-8", newline="\n") as f:
        for i, seg in enumerate(segments, start=1):
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
    print(f"Wrote SRT to {srt_path}")

def validate_srt(srt_path):
    """Ensure SRT file is non-empty and valid."""
    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if not content:
        raise RuntimeError(f"SRT file is empty: {srt_path}")
    if "-->" not in content:
        raise RuntimeError(f"SRT file format invalid (no timing lines found): {srt_path}")
    return True

def hex_to_ass_color(color_hex: str):
    """Convert #RRGGBB -> ASS integer &HAABBGGRR"""
    if not color_hex.startswith("#") or len(color_hex) != 7:
        return 0x00FFFFFF  # default white
    r = int(color_hex[1:3], 16)
    g = int(color_hex[3:5], 16)
    b = int(color_hex[5:7], 16)
    return 0x00000000 | (b << 16) | (g << 8) | r  # &H00BBGGRR

def srt_to_ass_with_style(srt_path: str, ass_path: str, font: str, font_hindi: str = None,
                          fontsize: int = 36, color_hex: str = "#FFFFFF", position: str = "bottom", margin_v: int = 40):
    subs = pysubs2.load(srt_path, format_="srt", encoding="utf-8")
    style = pysubs2.SSAStyle()
    style.fontname = font
    style.fontsize = fontsize
    style.bold = True

    # Correct color handling
    style.primarycolor = hex_to_ass_color(color_hex)

    # Remove borders and shadows
    style.outline = 0
    style.shadow = 0
    style.outlinecolor = 0x00000000
    style.shadowcolor = 0x00000000

    # Position mapping
    align_map = {"bottom": 2, "top": 8, "center": 5}
    style.alignment = align_map.get(position, 2)
    style.marginv = margin_v

    subs.styles["Default"] = style
    subs.save(ass_path, encoding="utf-8")
    print(f"Wrote ASS to {ass_path} (bold, font={font}, size={fontsize}, color={color_hex}, no border)")

def burn_ass_into_video(input_video: str, ass_file: str, output_video: str, crf: int = 18):
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", f"ass={ass_file}",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "192k",
        "-map", "0:v:0",
        "-map", "0:a:0?",
        output_video
    ]
    run_cmd(cmd)
    print(f"Created video with burned subtitles: {output_video}")

def main():
    parser = argparse.ArgumentParser(description="Generate/burn subtitles using Whisper + ffmpeg + pysubs2")
    parser.add_argument("--video", required=True, help="Input video file")
    parser.add_argument("--transcript", help=".srt transcript file to use (skip Whisper)")
    parser.add_argument("--out", default="output_subbed.mp4", help="Output video file")
    parser.add_argument("--model", default="small", help="Whisper model (tiny, base, small, medium, large)")
    parser.add_argument("--language", default=None, help="Hint language for Whisper (e.g., 'hi')")
    parser.add_argument("--font", required=True, help="TTF font path for subtitles")
    parser.add_argument("--font_hindi", default=None, help="Optional font for Hindi")
    parser.add_argument("--fontsize", type=int, default=36, help="Font size")
    parser.add_argument("--color", default="#FFFFFF", help="Subtitle text color")
    parser.add_argument("--position", default="bottom", choices=["bottom", "top", "center"], help="Vertical position")
    parser.add_argument("--margin_v", type=int, default=40, help="Vertical margin")
    parser.add_argument("--crf", type=int, default=18, help="FFmpeg CRF")
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print("Error: video file not found:", args.video)
        sys.exit(1)

    video_dir = os.path.dirname(os.path.abspath(args.video))
    srt_path = os.path.join(video_dir, "generated.srt")
    ass_path = os.path.join(video_dir, "styled.ass")

    if args.transcript and os.path.isfile(args.transcript):
        print("Using provided SRT:", args.transcript)
        with open(args.transcript, "r", encoding="utf-8") as fr:
            content = fr.read()
        if not content.strip():
            raise RuntimeError("Provided SRT is empty!")
        with open(srt_path, "w", encoding="utf-8", newline="\n") as fw:
            fw.write(content)
        print(f"SRT copied to {srt_path}")
    else:
        segments, _ = transcribe_with_whisper(args.video, args.model, args.language)
        segments_to_srt(segments, srt_path)

    validate_srt(srt_path)

    srt_to_ass_with_style(
        srt_path, ass_path,
        font=args.font, font_hindi=args.font_hindi,
        fontsize=args.fontsize, color_hex=args.color,
        position=args.position, margin_v=args.margin_v
    )

    burn_ass_into_video(args.video, ass_path, args.out, crf=args.crf)

if __name__ == "__main__":
    main()
