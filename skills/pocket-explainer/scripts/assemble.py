#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
拼片：分片 WebM + master.wav → 成品 MP4。

用法：
    python3 assemble.py parts/ -o out.mp4
    python3 assemble.py parts/ -o out.mp4 --tempo 1.18      # 整片提速 18%，音高不变
    python3 assemble.py parts/ -o out.mp4 --crf 20 --preset veryfast

说明：
  · --tempo 走 rubberband（保音高、质量优于 atempo）。不要用页面内的 playbackRate——
    那是直接变速，会把整片音高抬上去（本技能踩过：1.18× 使基频从 230Hz 变到 302Hz）。
  · 分片是 VP9，成品转 H.264 兼容性更好。
"""
import argparse
import glob
import os
import subprocess
import sys


def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write((p.stderr or "")[-1500:])
        raise SystemExit("命令失败：%s" % " ".join(cmd[:6]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("parts")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--tempo", type=float, default=1.0)
    ap.add_argument("--crf", default="20")
    ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--fps", default="")
    args = ap.parse_args()

    parts = sorted(glob.glob(os.path.join(args.parts, "part_*.webm")))
    if not parts:
        sys.exit("没有找到分片：%s/part_*.webm" % args.parts)
    wav = os.path.join(args.parts, "master.wav")
    if not os.path.exists(wav):
        sys.exit("缺少 master.wav（先用 render_parts.py --wav-only 导出）")

    lst = os.path.join(args.parts, "_concat.txt")
    with open(lst, "w", encoding="utf-8") as f:
        for p in parts:
            f.write("file '%s'\n" % os.path.abspath(p))

    audio_in = wav
    if abs(args.tempo - 1.0) > 1e-6:
        fast = os.path.join(args.parts, "master_tempo.wav")
        print("时间伸缩 x%.2f（rubberband，保音高）..." % args.tempo)
        run(["ffmpeg", "-v", "error", "-y", "-i", wav,
             "-filter:a", "rubberband=tempo=%.4f" % args.tempo, "-ar", "48000", "-ac", "1", fast])
        audio_in = fast

    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
           "-i", audio_in, "-map", "0:v:0", "-map", "1:a:0",
           "-c:v", "libx264", "-preset", args.preset, "-crf", args.crf,
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest"]
    if args.fps:
        cmd += ["-r", args.fps]
    cmd.append(args.out)
    print("编码 ...")
    run(cmd)

    print("成品：%s（%.1f MB）" % (args.out, os.path.getsize(args.out) / 1048576))
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_name,width,height,r_frame_rate",
         "-of", "default=nw=1", args.out], text=True)
    print(out.strip())
    if audio_in != wav:
        os.remove(audio_in)


if __name__ == "__main__":
    main()
