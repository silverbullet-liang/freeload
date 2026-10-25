#!/usr/bin/env python3
"""每周体检：把 data/*.json 里的 url 全部打一遍。

退出码 1 = 有入口确认不通（404/410/5xx/连不上），由 workflow 拿去开 issue。
403 / 405 / 429 记为 warn，不算死——多数是 Cloudflare 挑战或限流，真人打开是好的。
401 记为通：端点存在，只是要 key。
带 "probe" 的条目用 probe 探（基址本身可能就该 404），带 "skip_check" 的跳过（纯前端方案，没有端点）。
"""
from __future__ import annotations

import concurrent.futures
import json
import pathlib
import sys
import urllib.error
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPORT = ROOT / "reports"
UA = "Mozilla/5.0 (compatible; freeload-link-check/1.0; +https://github.com/silverbullet-liang/freeload)"
TIMEOUT = 15
SAMPLE = {"{prompt}": "a%20cat", "{id}": "2671812705", "{keyword}": "test"}
WARN_CODES = {403, 405, 429}


def probe(url: str) -> tuple[int, str]:
    """HEAD 不可靠——不少 API 只实现 GET，HEAD 会假报 404，所以 HEAD 失败一律换 GET 复核。"""
    last = (0, "no attempt")
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.status, ""
        except urllib.error.HTTPError as exc:
            last = (exc.code, "HTTP %d" % exc.code)
        except Exception as exc:  # noqa: BLE001 - 网络层什么都可能抛
            last = (0, type(exc).__name__)
    return last


def collect() -> tuple[list[dict], list[dict]]:
    rows, skipped = [], []
    for path in sorted(DATA.glob("*.json")):
        for item in json.loads(path.read_text(encoding="utf-8")):
            base = {"cat": path.stem, "name": item["name"], "url": item.get("url", ""),
                    "gate": item.get("gate", ""), "rating": item.get("rating", "")}
            if item.get("skip_check"):
                skipped.append(base)
                continue
            target = item.get("probe") or item.get("url", "")
            for token, value in SAMPLE.items():
                target = target.replace(token, value)
            rows.append({**base, "probe": target})
    return rows, skipped


def main() -> int:
    rows, skipped = collect()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda r: probe(r["probe"]), rows))

    ok, warn, fail = [], [], []
    for row, (code, note) in zip(rows, results):
        row["status"], row["note"] = code, note
        if 200 <= code < 400 or code == 401:
            ok.append(row)
        elif code in WARN_CODES:
            warn.append(row)
        else:
            fail.append(row)

    today = date.today().isoformat()
    REPORT.mkdir(exist_ok=True)
    (REPORT / "link-check.json").write_text(
        json.dumps({"date": today, "ok": len(ok), "warn": len(warn), "fail": len(fail),
                    "skipped": len(skipped), "items": rows, "skip": skipped},
                   ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = ["# 链接体检 · %s" % today, "",
             "通 %d · 可疑 %d · 不通 %d（共 %d，另跳过 %d）"
             % (len(ok), len(warn), len(fail), len(rows) + len(skipped), len(skipped)), ""]
    if fail:
        lines += ["## 不通（需要处理）", "", "| 分类 | 条目 | 状态 | 链接 |", "| :-- | :-- | :-- | :-- |"]
        lines += ["| %s | %s | %s %s | %s |" % (r["cat"], r["name"], r["status"], r["note"], r["url"]) for r in fail]
        lines.append("")
    if warn:
        lines += ["## 可疑（403/405/429，多半是反爬挑战）", "", "| 分类 | 条目 | 状态 |", "| :-- | :-- | :-- |"]
        lines += ["| %s | %s | %s |" % (r["cat"], r["name"], r["status"]) for r in warn]
        lines.append("")
    if skipped:
        lines += ["## 跳过（纯前端方案，没有可探端点）", ""]
        lines += ["- %s（%s）" % (r["name"], r["cat"]) for r in skipped]
        lines.append("")
    (REPORT / "link-check.md").write_text("\n".join(lines), encoding="utf-8")

    print("通 %d / 可疑 %d / 不通 %d / 跳过 %d" % (len(ok), len(warn), len(fail), len(skipped)))
    for r in fail:
        print("  DEAD", r["status"], r["name"], r["url"])
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
