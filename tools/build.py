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
    ("server", "服务器", "静态部署、动态主机、容器与边缘函数——能白嫖的运行环境。"),
    ("api", "API", "通用第三方接口。条目按站长实测填，不收未经核对的转载。"),
]

GATES = ("免注册", "邮箱", "GitHub", "实名", "信用卡")
# 从夯到拉：越靠前越推荐，表格按此排序
RATINGS = ("夯", "顶级", "人上人", "NPC", "拉完了")
REQUIRED = ("name", "url", "what", "gate", "rating")


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
        if row.get("rating") and row["rating"] not in RATINGS:
            errors.append(f"{tag}: rating 只能是 {' / '.join(RATINGS)}，当前 {row['rating']!r}")
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


def _table(rows: list[dict], today: str) -> str:
    alive = [r for r in rows if r.get("status") != "dead"]
    dead = [r for r in rows if r.get("status") == "dead"]
    lines = [
        "| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |",
        "| :--: | :-- | :-- | :-- | :-- | :-- |",
    ]
    for row in alive + dead:
        name = str(row["name"]).strip()
        if row.get("status") == "dead":
            name = f"~~{name}~~"
        elif row.get("status") == "limited":
            name = f"{name}（缩水中）"
        lines.append(
            "| **{rating}** | [{name}]({url}) | {what} | {gate} | {gotcha} | {checked} |".format(
                rating=cell(row.get("rating")),
                name=cell(name),
                url=row["url"].strip(),
                what=cell(row.get("what")),
                gate=cell(row.get("gate")),
                gotcha=cell(row.get("gotcha")) or "—",
                checked=cell(row.get("checked")) or today,
            )
        )
    return "\n".join(lines)


def _server_table(rows: list[dict]) -> str:
    """服务器类体感维度表：速度/快捷/限制 1–5 分，注册与广告用文字。"""
    order = {name: i for i, name in enumerate(RATINGS)}
    rows = sorted(rows, key=lambda r: order.get(r.get("rating"), len(RATINGS)))
    lines = [
        "| 平台 | 速度 | 快捷 | 注册 | 限制 | 广告 / 标识 | 主要缺点 |",
        "| :-- | :--: | :--: | :-- | :--: | :-- | :-- |",
    ]
    for row in rows:
        s = row.get("score") or {}
        if not s:
            continue
        lines.append(
            "| {name} | {speed} | {quick} | {gate} | {limits} | {ads} | {flaws} |".format(
                name=cell(row["name"]),
                speed=cell(s.get("speed")) or "—",
                quick=cell(s.get("quick")) or "—",
                gate=cell(row.get("gate")),
                limits=cell(s.get("limits")) or "—",
                ads=cell(row.get("ads")) or "—",
                flaws=cell(row.get("flaws")) or "—",
            )
        )
    return "\n".join(lines) if len(lines) > 2 else ""


def _strip_block(rows: list[dict]) -> str:
    """凡带 strip_code 的条目，汇总成「去平台标识」小节。"""
    items = [r for r in rows if r.get("strip_code")]
    if not items:
        return ""
    parts = [
        "### 去平台标识\n\n免费平台靠品牌曝光活着，这段代码只是把注入的节点摘掉，页面本身不受影响。粘到 `</body>` 前，重新部署即可。"
    ]
    for row in items:
        parts.append(
            "**{name}**{ads}\n\n```html\n{code}\n```".format(
                name=cell(row["name"]),
                ads=f" —— {cell(row.get('ads'))}" if row.get("ads") else "",
                code=str(row["strip_code"]).strip(),
            )
        )
    return "\n\n".join(parts)


def build_top(rows_by_cat: dict[str, list[dict]]) -> str:
    """夯级速览：按分类列出 rating=夯 的条目。"""
    parts = []
    for key, name, _ in CATS:
        hits = [r for r in rows_by_cat.get(key, []) if r.get("rating") == "夯"]
        if hits:
            links = " · ".join(f"[{cell(r['name'])}]({r['url'].strip()})" for r in hits)
            parts.append(f"**{name}** {links}")
    return "\n\n".join(parts) if parts else "_还没有夯级条目。_"


def render(rows: list[dict], today: str, cat: str = "") -> str:
    """按 group 分节（组顺序取录入顺序），组内按评级从夯到拉排。"""
    if not rows:
        return "_待收录。_"
    order = {name: i for i, name in enumerate(RATINGS)}
    groups: list[str] = []
    for row in rows:
        g = str(row.get("group", "")).strip()
        if g not in groups:
            groups.append(g)
    rows = sorted(rows, key=lambda r: order.get(r.get("rating"), len(RATINGS)))
    parts = []
    for g in groups:
        items = [r for r in rows if str(r.get("group", "")).strip() == g]
        block = _table(items, today)
        parts.append(f"### {g}\n\n{block}" if g else block)
    if cat == "server":
        dim = _server_table(rows)
        if dim:
            parts.append("### 体感维度（1–5 分，5 最好）\n\n" + dim)
        strip = _strip_block(rows)
        if strip:
            parts.append(strip)
    return "\n\n".join(parts)


def main() -> int:
    argv = sys.argv[1:]
    today = datetime.date.today().isoformat()
    if "--today" in argv:
        idx = argv.index("--today")
        if idx + 1 >= len(argv):
            print("--today 需要一个 YYYY-MM-DD 参数", file=sys.stderr)
            return 2
        today = argv[idx + 1]
        try:
            datetime.date.fromisoformat(today)
        except ValueError:
            print(f"--today 格式不对：{today}", file=sys.stderr)
            return 2
    errors: list[str] = []
    warns: list[str] = []
    tables: dict[str, str] = {}
    counts: dict[str, int] = {}

    rows_by_cat: dict[str, list[dict]] = {}
    for key, _, _ in CATS:
        rows = load(key)
        rows_by_cat[key] = rows
        e, w = validate(key, rows, today)
        errors += e
        warns += w
        tables[key] = render(rows, today, key)
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
    text = text.replace("{{TOP}}", build_top(rows_by_cat))
    text = text.replace("{{TOTAL}}", str(sum(counts.values()))).replace("{{UPDATED}}", today)
    OUT.write_text(text, encoding="utf-8")

    summary = " · ".join(f"{name} {counts[key]}" for key, name, _ in CATS)
    print(f"README.md 已生成：{summary} · 共 {sum(counts.values())} 条")
    return 0


if __name__ == "__main__":
    sys.exit(main())
