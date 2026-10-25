#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键出片：deck.json → 成品 mp4。

    python3 make_video.py deck.json -o out.mp4 --voice zh-CN-XiaoxiaoNeural \
        --w 1920 --h 1080 --fps 30 --batch 30 --workers 2

它会依次做四件事（每一步都可单独重跑，已完成的会跳过）：
  1. tts_build.py   逐句合成（缺哪句补哪句）
  2. pack_audio.py  音频 base64 内嵌，产出单文件 HTML
  3. render_parts.py 分片渲染 + 导出整片音轨
  4. assemble.py    拼接、可选时间伸缩、编码 mp4

只想改画面：加 --skip-tts。
只想重录一版：加 --skip-tts --force-render。
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def sh(cmd):
    print("\n$ " + " ".join(cmd), flush=True)
    p = subprocess.run(cmd)
    if p.returncode != 0:
        sys.exit("步骤失败（退出码 %d），修好后重跑本命令即可续传" % p.returncode)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--work", default="_build")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    ap.add_argument("--rate", default="0")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--batch", type=float, default=30.0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--tempo", type=float, default=1.0)
    ap.add_argument("--crf", default="20")
    ap.add_argument("--skip-tts", action="store_true")
    ap.add_argument("--force-render", action="store_true")
    ap.add_argument("--template", default=os.path.join(HERE, "..", "template", "player.html"))
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    audio_dir = os.path.join(args.work, "audio")
    parts_dir = os.path.join(args.work, "parts")
    deck = json.load(open(args.deck, encoding="utf-8"))

    if not args.skip_tts:
        lines_path = os.path.join(args.work, "lines.json")
        with open(lines_path, "w", encoding="utf-8") as f:
            json.dump([{"id": l.get("id") or "s%02d" % (i + 1), "text": l["text"]}
                       for i, l in enumerate(deck["lines"])], f, ensure_ascii=False, indent=1)
        sh([sys.executable, os.path.join(HERE, "tts_build.py"), lines_path,
            "-o", audio_dir, "--voice", args.voice, "--rate", args.rate,
            "--jobs", str(args.jobs)])

    html = os.path.join(args.work, "player.html")
    sh([sys.executable, os.path.join(HERE, "pack_audio.py"), args.deck,
        "-a", audio_dir, "-t", os.path.abspath(args.template), "-o", html])

    cmd = [sys.executable, os.path.join(HERE, "render_parts.py"), html, "-o", parts_dir,
           "--w", str(args.w), "--h", str(args.h), "--fps", str(args.fps),
           "--batch", str(args.batch), "--workers", str(args.workers)]
    if args.force_render:
        cmd.append("--force")
    sh(cmd)

    sh([sys.executable, os.path.join(HERE, "assemble.py"), parts_dir, "-o", args.out,
        "--tempo", str(args.tempo), "--crf", args.crf, "--fps", str(args.fps)])

    print("\n完成：%s（%.1f MB）" % (args.out, os.path.getsize(args.out) / 1048576))


if __name__ == "__main__":
    main()
