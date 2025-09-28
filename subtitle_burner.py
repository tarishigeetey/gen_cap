#!/usr/bin/env python3
"""
subtitle_burner.py

Generates (or uses provided) subtitles for a video and burns them into a new video file.
Supports local OpenAI Whisper transcription (open-source repo), editable .srt output,
and styling via ASS (using pysubs2). Finally burns the ASS into the video via ffmpeg.

Example:
  python subtitle_burner.py --video input.mp4 --out out_subbed.mp4 \
       --model small --font "/path/to/NotoSans-Regular.ttf" --font_hindi "/path/to/NotoSansDevanagari-Regular.ttf" \
       --fontsize 36 --color "#FFFFFF" --position bottom

See --help.
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pysubs2

# whisper import (open-source repository)
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
    """
    Run whisper.transcribe on the given video file and return segments (list of dicts).
    Each segment: {start, end, text}
    """
    print(f"Loading Whisper model '{model_name}' (this may take a while)...")
    model = whisper.load_model(model_name)

    opts = {}
    if language:
        opts["language"] = language
        opts["task"] = "transcribe"

    print("Transcribing (this will read the audio from the video)...")
    result = model.transcribe(video_path, **opts)
    # result['segments'] contains timestamps and text
    segments = result.get("segments", [])
    print(f"Transcription finished: {len(segments)} segments.")
    return segments, result.get("text", "")

def segments_to_srt(segments, srt_path: str):
    """
    Write segments (from whisper) to an .srt file.
    segments: list of dicts with 'start', 'end', 'text'
    """
    def format_time(seconds: float):
        # srt time format: HH:MM:SS,mmm
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        msec = int((seconds - int(seconds)) * 1000)
        return f"{hrs:02d}:{mins:02d}:{secs:02d},{msec:03d}"

    with open(srt_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, start=1):
            start = format_time(seg["start"])
            end = format_time(seg["end"])
            text = seg["text"].strip()
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")
    print(f"Wrote SRT to {srt_path}")

def srt_to_ass_with_style(srt_path: str, ass_path: str, font: str, font_hindi: str = None,
                          fontsize: int = 36, color_hex: str = "#FFFFFF", position: str = "bottom", margin_v: int = 40):
    """
    Convert SRT -> ASS and set a single style that supports Unicode (Hindi).
    color_hex: like '#RRGGBB'
    position: 'bottom' or 'top' or 'center'
    margin_v: vertical margin in pixels
    """
    subs = pysubs2.load(srt_path, encoding="utf-8")
    # create style
    style = pysubs2.SSAStyle()
    style.fontname = font
    style.fontsize = fontsize

    # colors - pysubs2 expects bgr hex like &HBBGGRR
    if color_hex.startswith("#") and len(color_hex) == 7:
        r = color_hex[1:3]
        g = color_hex[3:5]
        b = color_hex[5:7]
        ass_color = f"&H{b}{g}{r}"  # &HBBGGRR
    else:
        ass_color = "&HFFFFFF"  # fallback white
    style.primarycolor = ass_color

    # Remove black border
    style.outline = 0   # no border
    style.shadow = 0    # no shadow
    style.borderstyle = 1

    # Alignment mapping: 2 bottom-center, 8 top-center, 5 middle-center
    align_map = {"bottom": 2, "top": 8, "center": 5}
    style.alignment = align_map.get(position, 2)
    style.marginv = margin_v

    subs.styles["Default"] = style

    # apply default style to all events
    subs.save(ass_path, encoding="utf-8")
    print(f"Wrote ASS to {ass_path} (font={font}, fontsize={fontsize}, color={color_hex}, position={position})")

def burn_ass_into_video(input_video: str, ass_file: str, output_video: str, crf: int = 18):
    """
    Use ffmpeg to burn ASS subtitles into video.
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-vf", f"ass={ass_file}",
        "-c:v", "libx264", "-crf", str(crf),
        "-preset", "medium",
        "-c:a", "copy",
        output_video
    ]
    run_cmd(cmd)
    print(f"Created video with burned subtitles: {output_video}")

def main():
    parser = argparse.ArgumentParser(description="Generate/burn subtitles using Whisper + ffmpeg + pysubs2")
    parser.add_argument("--video", required=True, help="Input video file")
    parser.add_argument("--transcript", help=".srt transcript file to use (if provided, Whisper transcription is skipped). If omitted, script runs Whisper locally.")
    parser.add_argument("--out", default="output_subbed.mp4", help="Output video file")
    parser.add_argument("--model", default="small", help="Whisper model to use (tiny, base, small, medium, large).")
    parser.add_argument("--language", default=None, help="Hint language for Whisper (e.g., 'hi' for Hindi)")
    parser.add_argument("--font", default=None, help="Path to TTF font to use for subtitles (required). For Hindi use a Devanagari-capable font.")
    parser.add_argument("--font_hindi", default=None, help="Optional separate font for Hindi fallbacks")
    parser.add_argument("--fontsize", type=int, default=36, help="Font size for subtitles")
    parser.add_argument("--color", default="#FFFFFF", help="Subtitle text color in hex, e.g. #FFFFFF")
    parser.add_argument("--position", default="bottom", choices=["bottom", "top", "center"], help="Subtitle vertical position")
    parser.add_argument("--margin_v", type=int, default=40, help="Vertical margin for subtitles (pixels)")
    parser.add_argument("--crf", type=int, default=18, help="ffmpeg CRF for output quality (lower => better)")
    args = parser.parse_args()

    if not os.path.isfile(args.video):
        print("Error: video file not found:", args.video)
        sys.exit(1)

    if not args.font:
        print("ERROR: --font is required. Provide the path to a TTF font that supports your language (e.g., Noto Sans / Noto Sans Devanagari).")
        sys.exit(1)

    # temp files
    tmpdir = tempfile.mkdtemp(prefix="subs_")
    srt_path = os.path.join(tmpdir, "generated.srt")
    ass_path = os.path.join(tmpdir, "styled.ass")

    if args.transcript and args.transcript.lower().endswith(".srt") and os.path.isfile(args.transcript):
        print("Using provided transcript:", args.transcript)
        # copy to working srt
        with open(args.transcript, "r", encoding="utf-8") as fr, open(srt_path, "w", encoding="utf-8") as fw:
            fw.write(fr.read())
    else:
        # transcribe with Whisper (video -> segments -> srt)
        segments, full_text = transcribe_with_whisper(args.video, args.model, args.language)
        segments_to_srt(segments, srt_path)

    # create ASS with styles
    srt_to_ass_with_style(srt_path, ass_path, font=args.font, font_hindi=args.font_hindi,
                          fontsize=args.fontsize, color_hex=args.color, position=args.position, margin_v=args.margin_v)

    # burn into video
    burn_ass_into_video(args.video, ass_path, args.out, crf=args.crf)

if __name__ == "__main__":
    main()
