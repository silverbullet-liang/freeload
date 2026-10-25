#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EdgeTTS 批量合成（edge.text-to-speech.cn 逆向接口）

用法：
    python3 tts_build.py lines.json -o audio/ --voice zh-CN-XiaoxiaoNeural --rate 0 --jobs 4

输入 lines.json：["第一句", "第二句", ...] 或 [{"id":"s01","text":"第一句"}, ...]
输出：
    audio/<id>.mp3      24kHz/48kbps/mono
    audio/<id>.srt      该句逐词时间戳（起点非 0，需减偏移）
    durations.json      [[id, 秒], ...]，供分镜时间轴直接使用

设计要点（踩过的坑都在这里）：
  1. CSRF token 每次运行重取，不缓存——它会轮换。
  2. 接口「假成功」：非法音色/空文本也返回 200 + URL，下载到的是 HTML 错误页。
     必须校验 MP3 魔数（ID3 或 0xFF 0xEx），否则会得到一堆坏文件还不知道。
  3. srt 起点不是 0（实测 100ms 左右），要对齐到 0，否则句子之间会累积错位。
  4. srt 按句切分、不做智能断句，长句字幕条会很长——字幕建议按字数二次切分（见 --split）。
  5. 并发别超过 6，共用站点有全站配额（/stats.php 可查）。
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys
import time

import requests

BASE = "https://edge.text-to-speech.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BAD_MD5 = "048a2241792d9efbc94d44a256d40ca4"


def get_token(session):
    r = session.get(BASE + "/", timeout=20)
    r.raise_for_status()
    m = re.search(r'<meta name="csrf-token" content="([^"]+)"', r.text)
    if not m:
        raise RuntimeError("取不到 CSRF token（页面结构可能变了）")
    return m.group(1)


def is_mp3(blob):
    if len(blob) < 3:
        return False
    if blob[:3] == b"ID3":
        return True
    return blob[0] == 0xFF and (blob[1] & 0xE0) == 0xE0


def probe_duration(path):
    """用 ffprobe 拿真实时长；失败返回 0"""
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path], stderr=subprocess.DEVNULL, timeout=20)
        return round(float(out.strip()), 3)
    except Exception:
        return 0.0


def srt_shift(blob, shift):
    """把 srt 的所有时间戳减去 shift 秒，使其从 0 开始"""
    def fix(m):
        h, mi, s, ms = m.group(1), m.group(2), m.group(3), m.group(4)
        t = int(h) * 3600 + int(mi) * 60 + int(s) + int(ms) / 1000.0 - shift
        t = max(0.0, t)
        return "%02d:%02d:%02d,%03d" % (
            int(t // 3600), int(t % 3600 // 60), int(t % 60), int(round(t % 1 * 1000)))
    text = blob.decode("utf-8", "ignore") if isinstance(blob, (bytes, bytearray)) else blob
    return re.sub(r"(\d{2}):(\d{2}):(\d{2}),(\d{3})", fix, text).encode("utf-8")


def srt_text(blob):
    return "".join(l for l in blob.decode("utf-8", "ignore").splitlines()
                   if l.strip() and "-->" not in l and not l.strip().isdigit())


def synth(session, token, text, voice, rate, pitch, volume, out, idx, retries=3):
    payload = {"text": text, "voice": voice, "rate": str(rate),
               "pitch": str(pitch), "volume": str(volume)}
    last = ""
    for attempt in range(retries):
        try:
            r = session.post(BASE + "/generate.php", json=payload, timeout=90,
                             headers={"Content-Type": "application/json",
                                      "X-CSRF-TOKEN": token,
                                      "Referer": BASE + "/",
                                      "Origin": BASE})
            j = r.json()
            if "audio_url" not in j:
                last = str(j.get("error") or j)
                if "CSRF" in last:
                    token = get_token(session)
                time.sleep(1.5 * (attempt + 1))
                continue
            ab = session.get(BASE + j["audio_url"], timeout=90).content
            if not is_mp3(ab) or len(ab) < 1024:
                last = "产物不是 MP3（假成功），%d 字节" % len(ab)
                time.sleep(2 * (attempt + 1))
                continue
            mp3 = os.path.join(out, "%s.mp3" % idx)
            with open(mp3, "wb") as f:
                f.write(ab)
            sb = b""
            if j.get("subtitle_url"):
                sb = session.get(BASE + j["subtitle_url"], timeout=60).content
            dur = probe_duration(mp3)
            if sb:
                first = re.search(rb"(\d{2}):(\d{2}):(\d{2}),(\d{3})", sb)
                off = 0.0
                if first:
                    off = (int(first.group(1)) * 3600 + int(first.group(2)) * 60
                           + int(first.group(3)) + int(first.group(4)) / 1000.0)
                with open(os.path.join(out, "%s.srt" % idx), "wb") as f:
                    f.write(srt_shift(sb, off))
            return idx, dur, srt_text(sb), ""
        except Exception as e:
            last = "%s: %s" % (type(e).__name__, e)
            time.sleep(1.5 * (attempt + 1))
    return idx, 0.0, "", last


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", help="lines.json")
    ap.add_argument("-o", "--out", default="audio")
    ap.add_argument("--voice", default="zh-CN-XiaoxiaoNeural")
    ap.add_argument("--rate", default="0", help="-50..50，百分比语义")
    ap.add_argument("--pitch", default="0")
    ap.add_argument("--volume", default="100")
    ap.add_argument("--jobs", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0, help="只跑前 N 句（试音用）")
    args = ap.parse_args()

    raw = json.load(open(args.src, encoding="utf-8"))
    items = []
    for i, it in enumerate(raw):
        if isinstance(it, str):
            items.append(("s%02d" % (i + 1), it))
        else:
            items.append((str(it.get("id") or "s%02d" % (i + 1)), str(it["text"])))
    if args.limit:
        items = items[:args.limit]

    os.makedirs(args.out, exist_ok=True)
    session = requests.Session()
    session.headers.update({"User-Agent": UA})
    token = get_token(session)

    todo = [it for it in items
            if not (os.path.exists(os.path.join(args.out, it[0] + ".mp3"))
                    and os.path.getsize(os.path.join(args.out, it[0] + ".mp3")) > 1024)]
    print("共 %d 句，已完成 %d，待合成 %d" % (len(items), len(items) - len(todo), len(todo)))

    durs, fails = {}, []
    done = 0
    with cf.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as ex:
        futs = {ex.submit(synth, session, token, t, args.voice, args.rate,
                          args.pitch, args.volume, args.out, i): i for i, t in todo}
        for fu in cf.as_completed(futs):
            idx, dur, _txt, err = fu.result()
            done += 1
            if err:
                fails.append((idx, err))
                print("  ✗ %s  %s" % (idx, err))
            else:
                durs[idx] = dur
                print("  ✓ %s  %.2fs  [%d/%d]" % (idx, dur, done, len(todo)))

    # 已完成但本次没重跑：补时长
    for idx, _t in items:
        if idx not in durs:
            p = os.path.join(args.out, idx + ".mp3")
            if os.path.exists(p):
                durs[idx] = probe_duration(p)

    table = [[idx, durs.get(idx, 0.0)] for idx, _t in items]
    json.dump(table, open(os.path.join(args.out, "durations.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    total = sum(d for _i, d in table)
    print("总时长 %.2fs（%d:%02d）" % (total, int(total // 60), int(total % 60)))
    if fails:
        print("失败 %d 句，重跑本命令会自动续传" % len(fails))
        sys.exit(1)


if __name__ == "__main__":
    main()
