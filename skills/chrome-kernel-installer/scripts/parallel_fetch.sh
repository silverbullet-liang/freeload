#!/usr/bin/env bash
# ------------------------------------------------------------
# 通用大文件并发分块下载器
# 用法: bash parallel_fetch.sh <URL> <输出文件> [并发数] [分块数]
# 要点: 必须 -L 跟随重定向; 合并按数字序; 完成后校验大小
# ------------------------------------------------------------
set -uo pipefail

URL="${1:-}"
OUT="${2:-}"
JOBS="${3:-24}"
CHUNKS="${4:-0}"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
[ -n "$URL" ] || die "用法: $0 <URL> <输出文件> [并发数]"
[ -n "$OUT" ] || die "用法: $0 <URL> <输出文件> [并发数]"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
PD="$WORK/parts"
mkdir -p "$PD"

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
  len="$(curl -sIL --max-time 30 "$url" | tr -d '\r' | awk 'tolower($1)=="content-length:"{v=$2} END{print v}')"
  if [ -z "${len:-}" ]; then
    len="$(curl -sL --max-time 30 -r 0-0 -D - -o /dev/null "$url" | tr -d '\r' \
           | awk 'tolower($1)=="content-range:"{print $3}' | cut -d/ -f2)"
  fi
  printf '%s' "$len"
}

LEN="$(fetch_len "$URL")"
if [ -z "${LEN:-}" ]; then
  printf '未知文件长度，退化为单线程下载\n'
  curl -L --retry 3 -o "$OUT" "$URL" || die "下载失败"
  printf '完成: %s (%s 字节)\n' "$OUT" "$(stat -c%s "$OUT")"
  exit 0
fi

if ! range_ok "$URL"; then
  printf '服务端不支持按字节范围取（响应被压缩），退化为单线程下载\n'
  curl -sL --retry 3 -o "$OUT" "$URL" || die "下载失败"
  printf '完成: %s (%s 字节)\n' "$OUT" "$(stat -c%s "$OUT")"
  exit 0
fi

MIN_CHUNK=65536
if [ "$CHUNKS" -gt 0 ]; then
  N="$CHUNKS"
else
  N=$(( (LEN + 1048575) / 1048576 ))
fi
MAXC=$(( LEN / MIN_CHUNK )); [ "$MAXC" -lt 1 ] && MAXC=1
[ "$N" -gt "$MAXC" ] && N="$MAXC"
[ "$N" -lt 1 ]  && N=1
STEP=$(( (LEN + N - 1) / N ))
printf '总长 %s 字节，分 %s 块，并发 %s\n' "$LEN" "$N" "$JOBS"

i=0
while [ "$i" -lt "$N" ]; do
  S=$(( i * STEP )); E=$(( S + STEP - 1 ))
  [ "$E" -ge "$LEN" ] && E=$(( LEN - 1 ))
  if [ "$S" -le "$E" ]; then
    curl -sL --retry 3 --retry-delay 1 -H 'Accept-Encoding: identity' -r "$S-$E" "$URL" -o "$PD/p$(printf '%05d' "$i")" &
    while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n 2>/dev/null || sleep 0.2; done
  fi
  i=$(( i + 1 ))
done
wait

# 逐块校验尺寸，补拉缺失/不完整的块（最多 3 轮）
for round in 1 2 3; do
  miss=0; i=0
  while [ "$i" -lt "$N" ]; do
    S=$(( i * STEP )); E=$(( S + STEP - 1 )); [ "$E" -ge "$LEN" ] && E=$(( LEN - 1 ))
    want=$(( E - S + 1 ))
    f="$PD/p$(printf '%05d' "$i")"
    got=0; [ -f "$f" ] && got="$(stat -c%s "$f" 2>/dev/null || echo 0)"
    if [ "$got" -ne "$want" ]; then
      miss=$(( miss + 1 ))
      curl -sL --retry 3 --retry-delay 1 -H 'Accept-Encoding: identity' -r "$S-$E" "$URL" -o "$f" &
      while [ "$(jobs -rp | wc -l)" -ge "$JOBS" ]; do wait -n 2>/dev/null || sleep 0.2; done
    fi
    i=$(( i + 1 ))
  done
  wait
  [ "$miss" -eq 0 ] && break
  printf '第 %s 轮补拉 %s 块\n' "$round" "$miss"
done

find "$PD" -type f -name 'p*' -print0 | sort -z -V | xargs -0 cat > "$OUT"
GOT="$(stat -c%s "$OUT" 2>/dev/null || echo 0)"
[ "$GOT" -eq "$LEN" ] || die "合并后大小不符: $GOT / $LEN"
printf '完成: %s (%s 字节)\n' "$OUT" "$GOT"
