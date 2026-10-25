#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 audio/<id>.mp3 以 base64 内嵌进 deck JSON，产出可直接双击播放的单文件 HTML。

用法：
    python3 pack_audio.py deck.json -a audio/ -t ../template/player.html -o out.html

deck.json 结构：
{
  "theme": "noir",
  "rate": 1.0,
  "shots": { "1": "<h1>标题</h1>", "2": "..." },
  "chapters": [ {"name":"引子","at":0}, ... ],
  "lines": [ {"id":"s01","text":"第一句","dur":3.2,"shot":"1","hud":"01 / 引子"}, ... ]
}

产出：out.html（媒体完全内联，离线可用；音频体积约为 mp3 的 1.37 倍）
"""
import argparse
import base64
import json
import os
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("deck")
    ap.add_argument("-a", "--audio", default="audio")
    ap.add_argument("-t", "--template", required=True)
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--no-audio", action="store_true", help="只打结构，不带音轨（先看画面）")
    args = ap.parse_args()

    deck = json.load(open(args.deck, encoding="utf-8"))
    lines = deck.get("lines") or []
    if not lines:
        sys.exit("deck.json 里没有 lines")

    durations = {}
    dpath = os.path.join(args.audio, "durations.json")
    if os.path.exists(dpath):
        for i, d in json.load(open(dpath, encoding="utf-8")):
            durations[str(i)] = float(d)

    missing, total_b64 = [], 0
    for i, l in enumerate(lines):
        lid = str(l.get("id") or "s%02d" % (i + 1))
        l["id"] = lid
        if l.get("dur") is None:
            l["dur"] = durations.get(lid, 0.0)
        if args.no_audio:
            continue
        p = os.path.join(args.audio, lid + ".mp3")
        if not os.path.exists(p):
            missing.append(lid)
            continue
        b = base64.b64encode(open(p, "rb").read()).decode("ascii")
        l["audio"] = b
        total_b64 += len(b)

    if missing:
        print("缺音频 %d 句：%s%s" % (len(missing), ", ".join(missing[:8]),
                                     " ..." if len(missing) > 8 else ""))
        sys.exit(1)

    total = sum(float(l.get("dur") or 0) for l in lines)
    deck["total"] = round(total, 3)
    payload = json.dumps(deck, ensure_ascii=False, separators=(",", ":"))

    tpl = open(args.template, encoding="utf-8").read()
    if "/*__DECK__*/" not in tpl:
        sys.exit("模板里找不到 /*__DECK__*/ 注入点")
    html = tpl.replace("/*__DECK__*/", payload, 1)
    open(args.out, "w", encoding="utf-8").write(html)

    print("出片 HTML：%s" % args.out)
    print("  镜头 %d · 句子 %d · 总时长 %.1fs（%d:%02d）"
          % (len(deck.get("shots") or {}), len(lines), total, int(total // 60), int(total % 60)))
    print("  内嵌音频 %.2f MB · 文件 %.2f MB"
          % (total_b64 / 1048576, os.path.getsize(args.out) / 1048576))


if __name__ == "__main__":
    main()
