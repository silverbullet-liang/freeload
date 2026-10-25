#!/usr/bin/env bash
# ------------------------------------------------------------
# 多线程分块下载并安装 Chrome for Testing 内核
# 用法: bash install_chrome_kernel.sh [headless|chrome|both] [并发数]
# 环境变量: CHROME_VERSION 指定版本; CHS_DEST 指定安装目录
# 输出: 安装到 $CHS_DEST（默认 /opt/chs），成功打印 CHROME_READY
# ------------------------------------------------------------
set -uo pipefail

KIND="${1:-headless}"
JOBS="${2:-24}"
DEST="${CHS_DEST:-/opt/chs}"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

command -v curl    >/dev/null 2>&1 || die "缺少 curl"
command -v python3 >/dev/null 2>&1 || die "缺少 python3"

GOOD_URL="${CHS_GOOD_URL:-https://googlechromelabs.github.io/chrome-for-testing/last-known-good-versions.json}"
MIRROR_BASE="${CHS_MIRROR:-https://registry.npmmirror.com/-/binary/chrome-for-testing}"
FALLBACK_VERSION="${CHS_FALLBACK_VERSION:-153.0.8010.47}"

# 从 last-known-good-versions.json 取 Stable 版本
stable_from_json() {
  python3 -c "import sys,json;print(json.load(sys.stdin)['channels']['Stable']['version'])" 2>/dev/null
}

# 从镜像目录列表里取最新版本目录（最后一级兜底）
version_from_mirror_list() {
  curl -s --max-time 30 "$MIRROR_BASE/" | python3 -c "
import sys,json,re
try: d=json.load(sys.stdin)
except Exception: sys.exit(0)
vs=[x['name'].rstrip('/') for x in d if isinstance(x,dict) and x.get('type') in ('dir','directory')
    and re.fullmatch(r'\d+\.\d+\.\d+\.\d+', (x.get('name') or '').rstrip('/'))]
if vs: print(sorted(vs,key=lambda s:[int(i) for i in s.split('.')])[-1])
" 2>/dev/null
}

# 版本号多级回退：官方元数据 -> 镜像同名元数据 -> 镜像目录列表 -> 内置常量
resolve_version() {
  local v
  v="$(curl -s --max-time 25 "$GOOD_URL" | stable_from_json)"
  [ -n "$v" ] && { printf '%s' "$v"; return; }
  v="$(curl -sL --max-time 25 "$MIRROR_BASE/last-known-good-versions.json" | stable_from_json)"
  [ -n "$v" ] && { log "  版本号来源：镜像元数据（官方站点不可达）" >&2; printf '%s' "$v"; return; }
  v="$(version_from_mirror_list)"
  [ -n "$v" ] && { log "  版本号来源：镜像目录列表（取最新）" >&2; printf '%s' "$v"; return; }
  log "  版本号来源：内置兜底常量" >&2
  printf '%s' "$FALLBACK_VERSION"
}

# 只解析并打印版本号、不下载：bash install_chrome_kernel.sh --print-version
if [ "${1:-}" = "--print-version" ]; then resolve_version; printf '\n'; exit 0; fi

VERSION="${CHROME_VERSION:-}"
if [ -z "$VERSION" ]; then VERSION="$(resolve_version)"; fi
[ -n "$VERSION" ] || die "取版本号失败：可手工指定 CHROME_VERSION"
log "Chrome for Testing Stable = $VERSION"

# 分块可行性探测：直接按范围取 64KB，比对实际字节数。
# 被压缩的响应（Content-Encoding 常被中间层改写或缺失）会导致长度对不上，
# 强行分块会切错边界、且合并后大小校验照样通过，得到损坏文件。故以字节数为准。
# 分块可行性探测：直接按范围取 64KB，比对实际字节数。
# 被压缩的响应（Content-Encoding 常被中间层改写或缺失）会导致长度对不上，
# 强行分块会切错边界、且合并后大小校验照样通过，得到损坏文件。故以字节数为准。
range_ok() {
  local url="$1" want got
  want=65536
  got="$(curl -sL --max-time 25 -H 'Accept-Encoding: identity' -r 0-$((want-1)) "$url" 2>/dev/null | wc -c)"
  [ "$got" -eq "$want" ]
}

fetch_len() {
  local url="$1" len
  len="$(curl -sIL --max-time 30 -H 'Accept-Encoding: identity' "$url" | tr -d '\r' | awk 'tolower($1)=="content-length:"{v=$2} END{print v}')"
  if [ -z "${len:-}" ]; then
    len="$(curl -sL --max-time 30 -H 'Accept-Encoding: identity' -r 0-0 -D - -o /dev/null "$url" | tr -d '\r' \
           | awk 'tolower($1)=="content-range:"{print $3}' | cut -d/ -f2)"
  fi
  printf '%s' "$len"
}

verify_zip() {
  python3 - "$1" <<'PY'
import sys, zipfile
try:
    z = zipfile.ZipFile(sys.argv[1])
    bad = z.testzip()
except Exception as e:
    print("ZIP_ERR: %s" % e)
    sys.exit(1)
print("ZIP_OK" if bad is None else "ZIP_BAD: %s" % bad)
sys.exit(0 if bad is None else 1)
PY
}

fetch_parallel() {
  local url="$1" out="$2" jobs="${3:-12}"
  local len
  len="$(fetch_len "$url")"
  [ -n "${len:-}" ] || die "取文件长度失败: $url"

  local n=$(( (len + 1048575) / 1048576 ))
  [ "$n" -gt 96 ] && n=96
  [ "$n" -lt 1 ]  && n=1
  local step=$(( (len + n - 1) / n ))
  if ! range_ok "$url"; then
    log "  该镜像不支持分块取（响应被压缩），退化为单线程"
    curl -sL --retry 3 -H 'Accept-Encoding: identity' -o "$out" "$url" || die "单线程下载失败"
    local g; g="$(stat -c%s "$out" 2>/dev/null || echo 0)"
    [ "$g" -gt 1000000 ] || die "下载内容过小，疑似错误页: $g"
    return 0
  fi

  local pd="$WORK/parts"
  mkdir -p "$pd"
  log "  分块 $n 块 / 并发 $jobs / 总长 $len 字节"

  local i s e
  for i in $(seq 0 $((n-1))); do
    s=$(( i * step )); e=$(( s + step - 1 ))
    [ "$e" -ge "$len" ] && e=$(( len - 1 ))
    [ "$s" -gt "$e" ] && continue
    curl -sL --retry 3 --retry-delay 1 -H 'Accept-Encoding: identity' -r "$s-$e" "$url" -o "$pd/p$(printf '%05d' "$i")" &
    while [ "$(jobs -rp | wc -l)" -ge "$jobs" ]; do wait -n 2>/dev/null || sleep 0.2; done
  done
  wait

  find "$pd" -type f -name 'p*' -print0 | sort -z -V | xargs -0 cat > "$out"

  local got
  got="$(stat -c%s "$out" 2>/dev/null || echo 0)"
  [ "$got" -eq "$len" ] || die "合并后大小不符: $got / $len"
}

install_one() {
  local kind="$1" pkg url zf bin
  if [ "$kind" = "chrome" ]; then pkg="chrome-linux64"; else pkg="chrome-headless-shell-linux64"; fi
  url="https://registry.npmmirror.com/-/binary/chrome-for-testing/${VERSION}/linux64/${pkg}.zip"
  zf="$WORK/${pkg}.zip"

  log "→ 下载 $pkg"
  fetch_parallel "$url" "$zf" "$JOBS" || die "下载失败: $pkg"
  verify_zip "$zf" || die "zip 校验失败（分块错序或下载不完整）: $pkg"

  mkdir -p "$DEST"
  python3 -c "import zipfile,sys;zipfile.ZipFile(sys.argv[1]).extractall(sys.argv[2])" "$zf" "$DEST" || die "解压失败"

  if [ "$kind" = "chrome" ]; then bin="$DEST/$pkg/chrome"; else bin="$DEST/$pkg/chrome-headless-shell"; fi
  chmod +x "$bin" 2>/dev/null
  [ -x "$bin" ] || die "未找到可执行文件: $bin"
  log "  已安装: $bin"
}

case "$KIND" in
  headless) install_one headless ;;
  chrome)   install_one chrome ;;
  both)     install_one headless; install_one chrome ;;
  *) die "用法: $0 [headless|chrome|both] [并发数]" ;;
esac

BIN="$DEST/chrome-headless-shell-linux64/chrome-headless-shell"
if [ -x "$BIN" ]; then log "版本: $("$BIN" --version 2>/dev/null)"; fi
log "CHROME_READY"
