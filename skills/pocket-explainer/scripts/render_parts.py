#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分片渲染：把单文件 HTML 切成 N 秒一段，逐片导出 WebM，并导出整片 WAV。

用法：
    python3 render_parts.py out.html -o parts/ --w 1920 --h 1080 --fps 30 --batch 30 --workers 2
    python3 render_parts.py out.html -o parts/ --wav-only        # 只导音轨

为什么分片：
  · 单片一镜到底时，Chrome 内存与编码队列会越积越高，中途 OOM 前功尽弃；
  · 分片后可断点续传（已存在的片自动跳过），也能多开 Chrome 并行。
速度：
  · 模板里做了「静态帧复用」——同镜头同字幕同动画进度桶的帧直接复用上一帧像素，
    讲解片里静态段落占多数，实测能省掉 60% 以上的快照调用。
"""
import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

try:
    import websocket
except ImportError:
    sys.exit("需要 websocket-client：pip install websocket-client")

CHROME_DEFAULT = os.environ.get(
    "CHROME_BIN",
    "/sandbox/workspace/chs/chrome-headless-shell-linux64/chrome-headless-shell")


class Tab:
    def __init__(self, html, download_dir, port):
        self.port = port
        self.proc = subprocess.Popen(
            [CHROME_DEFAULT, "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
             "--window-size=1280,720", "--remote-debugging-port=%d" % port,
             "--remote-allow-origins=*", "about:blank"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        ws_url = None
        for _ in range(80):
            try:
                with urllib.request.urlopen("http://127.0.0.1:%d/json/version" % port, timeout=1) as f:
                    ws_url = json.load(f)["webSocketDebuggerUrl"]
                    break
            except Exception:
                time.sleep(0.5)
        if not ws_url:
            raise RuntimeError("Chrome 调试端口未就绪（port %d）" % port)
        self.ws = websocket.create_connection(ws_url, timeout=3600)
        self.mid = 0
        tid = self._send("Target.createTarget", {"url": "file://" + os.path.abspath(html)})["result"]["targetId"]
        self.sid = self._send("Target.attachToTarget", {"targetId": tid, "flatten": True})["result"]["sessionId"]
        self._send("Page.enable", session=self.sid)
        self._send("Runtime.enable", session=self.sid)
        self._send("Page.setDownloadBehavior",
                   {"behavior": "allow", "downloadPath": os.path.abspath(download_dir)}, session=self.sid)

    def _send(self, method, params=None, session=None):
        self.mid += 1
        msg = {"id": self.mid, "method": method, "params": params or {}}
        if session:
            msg["sessionId"] = session
        self.ws.send(json.dumps(msg))
        while True:
            r = json.loads(self.ws.recv())
            if r.get("id") == self.mid:
                return r

    def ev(self, expr, await_promise=True):
        r = self._send("Runtime.evaluate",
                       {"expression": expr, "awaitPromise": await_promise, "returnByValue": True},
                       session=self.sid)
        res = r.get("result", {})
        if res.get("exceptionDetails"):
            raise RuntimeError(str(res["exceptionDetails"])[:300])
        return res.get("result", {}).get("value")

    def wait_ready(self, timeout=180):
        t0 = time.time()
        while time.time() - t0 < timeout:
            try:
                v = self.ev("(typeof window.__total==='function')?window.__total():0", await_promise=False)
                if v and float(v) > 0:
                    return float(v)
            except Exception:
                pass
            time.sleep(1)
        raise RuntimeError("页面未就绪（__total 一直为 0）")

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        self.proc.terminate()


def wait_file(path, timeout=1800):
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(path) and not os.path.exists(path + ".crdownload"):
            s1 = os.path.getsize(path)
            if s1 > 8192:
                time.sleep(0.4)
                if os.path.getsize(path) == s1:
                    return s1
        time.sleep(1)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("html")
    ap.add_argument("-o", "--out", default="parts")
    ap.add_argument("--w", type=int, default=1920)
    ap.add_argument("--h", type=int, default=1080)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--batch", type=float, default=30.0)
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--port", type=int, default=9400)
    ap.add_argument("--wav-only", action="store_true")
    ap.add_argument("--force", action="store_true", help="忽略已有分片")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    host = Tab(args.html, args.out, args.port)
    total = host.wait_ready()
    print("总时长 %.2fs（%d:%02d）" % (total, int(total // 60), int(total % 60)))

    wav = os.path.join(args.out, "master.wav")
    if args.wav_only or not os.path.exists(wav):
        print("导出音轨 ...")
        host.ev("window.__dumpWav()")
        sz = wait_file(wav, 900)
        print("  master.wav %.1f MB" % (sz / 1048576) if sz else "  音轨导出失败")
    if args.wav_only:
        host.close()
        return

    n = int((total + args.batch - 0.001) // args.batch) + 1
    jobs = [(i, i * args.batch, min(args.batch, total - i * args.batch)) for i in range(n)]
    jobs = [(i, t0, d) for i, t0, d in jobs if d > 0.01]

    done = set()
    for i, _t0, _d in jobs:
        p = os.path.join(args.out, "part_%03d.webm" % i)
        if not args.force and os.path.exists(p) and os.path.getsize(p) > 8192:
            done.add(i)
    print("分片 %d 个，已完成 %d，待渲染 %d，并行 %d"
          % (len(jobs), len(done), len(jobs) - len(done), args.workers))

    pending = [j for j in jobs if j[0] not in done]
    host.close()

    if pending:
        tabs = [Tab(args.html, args.out, args.port + 1 + k) for k in range(max(1, args.workers))]
        for tb in tabs:
            tb.wait_ready()
        try:
            while pending:
                batch = pending[:len(tabs)]
                pending = pending[len(tabs):]
                for k, (i, t0, d) in enumerate(batch):
                    tb = tabs[k]
                    st = time.time()
                    tb.ev("window.__renderPart(%f,%f,%d,%d,%d,%d)"
                          % (t0, d, args.w, args.h, args.fps, i))
                    p = os.path.join(args.out, "part_%03d.webm" % i)
                    sz = wait_file(p, 1800)
                    print("  [%02d] t=%6.1fs %.0fB %.1fs" % (i, t0, sz, time.time() - st), flush=True)
        finally:
            for tb in tabs:
                tb.close()

    print("分片完成：%s" % args.out)


if __name__ == "__main__":
    main()
