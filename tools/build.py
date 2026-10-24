#!/usr/bin/env python3
"""data/*.json -> README.md。零依赖，改完跑一次即可。

用法:
    python3 tools/build.py            # 校验并写 README.md
    python3 tools/build.py --check    # 只校验，不写
"""
from __future__ import annotations

import datetime
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
TPL = ROOT / "template" / "README.tpl.md"
OUT = ROOT / "README.md"

STALE_DAYS = 180

# key, 锚点标题, 分类说明
CATS = [
    ("ai", "AI", "模型额度、免费 API Key、免费算力与推理额度。"),
    ("pan", "网盘", "免费空间、直链、离线下载与传输流量。"),
    ("server", "服务器", "免费 VPS、容器、边缘函数、数据库与对象存储。"),
]

GATES = ("免注册", "邮箱", "GitHub", "实名", "信用卡")
REQUIRED = ("name", "url", "what", "gate")


def cell(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\n", " ").strip()


def load(key: str) -> list[dict]:
    path = DATA / f"{key}.json"
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError(f"{path.name} 顶层必须是数组")
    return rows


def validate(key: str, rows: list[dict], today: str) -> tuple[list[str], list[str]]:
    errors, warns = [], []
    seen: set[str] = set()
    for i, row in enumerate(rows):
        tag = f"{key}.json[{i}]"
        if not isinstance(row, dict):
            errors.append(f"{tag}: 不是对象")
            continue
        for field in REQUIRED:
            if not str(row.get(field, "")).strip():
                errors.append(f"{tag}: 缺 {field}")
        if row.get("gate") and row["gate"] not in GATES:
            errors.append(f"{tag}: gate 只能是 {' / '.join(GATES)}，当前 {row['gate']!r}")
        url = str(row.get("url", ""))
        if url and not url.startswith(("http://", "https://")):
            errors.append(f"{tag}: url 必须以 http(s):// 开头")
        name = str(row.get("name", "")).strip()
        if name:
            if name in seen:
                errors.append(f"{tag}: 名称重复 {name!r}")
            seen.add(name)
        if row.get("status") and row["status"] not in ("alive", "limited", "dead"):
            errors.append(f"{tag}: status 只能是 alive / limited / dead")
        checked = str(row.get("checked", "")).strip()
        if not checked:
            warns.append(f"{tag}: 没填 checked，按今天 {today} 记")
        else:
            try:
                days = (datetime.date.fromisoformat(today) - datetime.date.fromisoformat(checked)).days
            except ValueError:
                errors.append(f"{tag}: checked 必须是 YYYY-MM-DD")
                continue
            if days > STALE_DAYS:
                warns.append(f"{tag}: {checked} 距今 {days} 天，该复核了")
            if days < 0:
                errors.append(f"{tag}: checked 在未来")
    return errors, warns


def render(rows: list[dict], today: str) -> str:
    if not rows:
        return "_待收录。_"
    alive = [r for r in rows if r.get("status") != "dead"]
    dead = [r for r in rows if r.get("status") == "dead"]
    lines = [
        "| 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |",
        "| :-- | :-- | :-- | :-- | :-- |",
    ]
    for row in alive + dead:
        name = str(row["name"]).strip()
        if row.get("status") == "dead":
            name = f"~~{name}~~"
        elif row.get("status") == "limited":
            name = f"{name}（缩水中）"
        lines.append(
            "| [{name}]({url}) | {what} | {gate} | {gotcha} | {checked} |".format(
                name=cell(name),
                url=row["url"].strip(),
                what=cell(row.get("what")),
                gate=cell(row.get("gate")),
                gotcha=cell(row.get("gotcha")) or "—",
                checked=cell(row.get("checked")) or today,
            )
        )
    return "\n".join(lines)


def main() -> int:
    today = datetime.date.today().isoformat()
    errors: list[str] = []
    warns: list[str] = []
    tables: dict[str, str] = {}
    counts: dict[str, int] = {}

    for key, _, _ in CATS:
        rows = load(key)
        e, w = validate(key, rows, today)
        errors += e
        warns += w
        tables[key] = render(rows, today)
        counts[key] = sum(1 for r in rows if r.get("status") != "dead")

    for w in warns:
        print(f"[warn] {w}")
    if errors:
        for e in errors:
            print(f"[error] {e}", file=sys.stderr)
        print(f"\n{len(errors)} 个错误，README 未生成。", file=sys.stderr)
        return 1

    if "--check" in sys.argv:
        print(f"\n校验通过：{sum(counts.values())} 条。")
        return 0

    text = TPL.read_text(encoding="utf-8")
    for key, _, desc in CATS:
        text = text.replace(f"{{{{{key.upper()}_TABLE}}}}", tables[key])
        text = text.replace(f"{{{{{key.upper()}_DESC}}}}", desc)
        text = text.replace(f"{{{{{key.upper()}_COUNT}}}}", str(counts[key]))
    text = text.replace("{{TOTAL}}", str(sum(counts.values()))).replace("{{UPDATED}}", today)
    OUT.write_text(text, encoding="utf-8")

    summary = " · ".join(f"{name} {counts[key]}" for key, name, _ in CATS)
    print(f"README.md 已生成：{summary} · 共 {sum(counts.values())} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
