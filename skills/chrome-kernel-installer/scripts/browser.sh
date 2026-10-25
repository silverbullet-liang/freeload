#!/usr/bin/env bash
# 浏览器控制器入口（对 browser.py 的薄封装，便于把 $0 目录解析为脚本目录）
exec python3 "$(cd "$(dirname "$0")" && pwd)/browser.py" "$@"
