#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""浏览器控制器（基于 Chrome DevTools Protocol / CDP）

一个常驻的无头 Chrome + 每次调用一条短连接；页面、Cookie、控制台日志、油猴脚本
都留在浏览器侧，命令之间连续可用。

命令:
  start [url]                     启动/复用浏览器，可选打开网址
  open <url>                      打开网址（自动标注截图）
  shot [--full] [--out P] [--only 类型] [--no-region]
                                  标注全部组件（交互/标题/文字/媒体/结构容器）并截图，
                                  --only 只标某几类：interactive,head,text,media,region（逗号分隔）
  click  <n|CSS选择器>            按编号点击（默认自动重新截图）
  type   <n|CSS选择器> <文本>     聚焦并输入 / fill 清空后输入
  press  <键>                     按键，如 Enter / Control+a
  scroll <dy> [dx]                滚动（正数向下）
  move   <x> <y> [--steps N]      精密移动鼠标到视口坐标（CSS 像素，默认多步类人轨迹）
  click-at <x> <y> [--button B] [--count N]   按坐标点击（精密；B=left/right/middle）
  hover  <n|选择器> [--ms N]      悬停到元素中心并停留
  dblclick <n|选择器> | rclick <n|选择器>     双击 / 右键
  mdown  <n|选择器|x,y> | mup [x,y]           按下 / 抬起（手工拖拽）
  drag   <n|选择器|x,y> <dx> <dy> [--steps N] [--jitter PX]   平滑拖拽
  verify [--deep]                 识别人机验证（滑块/验证码）：位置、尺寸、是否前端含缺口位置
  solve  [--retry N] [--mode auto|dark|edge] [--duration MS] [--y-jitter PX]
                                  一键过滑块：定位缺口 → 类人滑动（随机速度/上下抖动/回冲）
  slide  <距离> [--duration MS] [--y-jitter PX]               仅执行类人滑动
  proxy  check|list|set           出口代理健康检查（真实出口 IP）/ 批量测活 / 设置
  wait   <毫秒> | load [秒] | stable [秒] | sel <选择器> [秒] | text <文本> [秒]
                                  等待：固定秒数 / 等加载 / 等画面稳定（截图识别）/ 等元素或文本出现
  console [--clear]               读取页面控制台日志
  eval   <js>                     执行 JS 并返回结果
  html   [选择器]                 输出 DOM
  net                             列出网络资源
  fetch  <url> [--method M] [--body B] [--header K:V ...]
                                  页面内同源请求：自动带 Cookie 与来源，返回状态与正文
  cookies                         列出浏览器 Cookie
  cookie set <name>=<value> [--domain D] [--path P] | cookie clear
  ua     [字符串]                 查看 / 设置 User-Agent
  cloak                           查看当前伪装身份；`cloak rotate` 换一套（随机 IP 头 / UA / 指纹）
  --proxy <url>                   start 时指定出口代理（真正改出口 IP）；或设 CLOAK_PROXIES=a,b 自动轮换
  --wait N / --stable [--stable-tol P]
                                  出图前等待：N 秒 / 直到画面稳定（--stable-tol 像素容差，默认 0=逐字节全等）
  userscript add <file.user.js> | list | clear
  inject <file.js>                一次性注入（仅当前页）
  url | title | status | close

反爬：默认抹除自动化特征（UA 用真实版本号、navigator.webdriver=false 等），
并在导航时自动识别 JS 挑战（slowAES / aes.js 之类）并等待其跳转完成。
"""

import base64
import io
import json
import math
import os
import random
import re
import signal
import socket
import subprocess
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_DIR = "/tmp/chrome-browser"
STATE = os.path.join(STATE_DIR, "state.json")
PROFILE = os.path.join(STATE_DIR, "profile")
SHOT_DIR = "/sandbox/workspace/.browser/shots"

OPTS = {}  # main() 解析出的选项，供 take_shot 统一读取（--wait / --stable）

# JS 反爬挑战的典型特征：命中且页面很短，才判定为挑战页（避免误伤正常页面）
CHALLENGE_RE = re.compile(
    r"slowAES|document\.cookie\s*=\s*[\"']__test|aes\.js|\.decrypt\s*\(", re.I)

try:
    import websocket  # websocket-client
except ImportError:
    sys.exit("缺少依赖：pip install websocket-client")


def log(*a):
    print(*a, flush=True)


def read_file(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def read_state():
    try:
        with open(STATE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def write_state(st):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(st, f, ensure_ascii=False)


# ---------------------------------------------------------------- 内核定位 / 启动
def find_chrome():
    cands = []
    if os.environ.get("CHROME_BIN"):
        cands.append(os.environ["CHROME_BIN"])
    cands += [
        "/opt/chs/chrome-headless-shell-linux64/chrome-headless-shell",
        "/opt/chs/chrome-linux64/chrome",
    ]
    for name in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser", "chrome"):
        for d in os.environ.get("PATH", "").split(os.pathsep):
            q = os.path.join(d, name)
            if os.path.isfile(q) and os.access(q, os.X_OK):
                cands.append(q)
                break
    for c in cands:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def http_json(url, timeout=3.0):
    # 不要覆盖 Host 头：CDP 依据 Host 拼 webSocketDebuggerUrl，写成不带端口的
    # "127.0.0.1" 会让返回的 ws 地址丢失端口，随后连接被拒。用 urllib 默认的
    # Host: 127.0.0.1:port 即可（是 IP，满足 CDP 对 Host 的校验）。
    with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def is_alive(st):
    try:
        http_json(f"http://127.0.0.1:{st['port']}/json/version", timeout=1.5)
        return True
    except Exception:
        return False


def build_ua(version):
    return ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/%s Safari/537.36" % (version or "153.0.0.0"))


def version_from_browser(browser):
    m = re.search(r"Chrome/([\d.]+)", browser or "")
    return m.group(1) if m else "153.0.0.0"


# ---------------------------------------------------------------- 身份伪装（随机 IP 头 / UA / 指纹 / 代理）
# 说明：这里的「随机 IP」是把随机公网 IP 写进 X-Forwarded-For 等代理头，影响信任这些头的
# 站点的地域/限流判断；它**不改变 TCP 真实源 IP**，对按真实 IP 判定的人机验证无效。
# 要真正更换出口 IP，请用代理（--proxy / CHS_PROXY / CLOAK_PROXIES）。
UA_POOL = [
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
     "platform": "Win32", "languages": ["zh-CN", "zh", "en-US", "en"]},
    {"ua": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
     "platform": "MacIntel", "languages": ["zh-CN", "zh", "en-US", "en"]},
    {"ua": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari/537.36",
     "platform": "Linux x86_64", "languages": ["zh-CN", "zh", "en"]},
    {"ua": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.36",
     "platform": "Win32", "languages": ["zh-CN", "zh", "en-US", "en"]},
]
IP_POOL = ["61.%d.%d.%d", "113.%d.%d.%d", "183.%d.%d.%d", "223.%d.%d.%d",
           "112.%d.%d.%d", "218.%d.%d.%d", "117.%d.%d.%d", "120.%d.%d.%d"]
TZ_POOL = ["Asia/Shanghai", "Asia/Chongqing", "Asia/Harbin", "Asia/Urumqi"]
GL_POOL = [
    ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1650 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)"),
]


def random_ip():
    return random.choice(IP_POOL) % (random.randint(1, 254), random.randint(0, 255), random.randint(1, 254))


def random_identity():
    ua = random.choice(UA_POOL)
    gl = random.choice(GL_POOL)
    ip = random_ip()
    return {
        "ip": ip, "ua": ua["ua"], "platform": ua["platform"], "languages": ua["languages"],
        "cores": random.choice([4, 8, 12, 16]), "memory": random.choice([4, 8, 16]),
        "timezone": random.choice(TZ_POOL), "locale": "zh-CN",
        "glVendor": gl[0], "glRenderer": gl[1],
        "headers": {
            "X-Forwarded-For": ip, "X-Real-IP": ip, "X-Client-IP": ip,
            "Client-IP": ip, "True-Client-IP": ip, "Forwarded": "for=%s" % ip,
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        },
    }


def identity_script(ident):
    """把身份写进页面：navigator 的 platform/cores/memory/languages 与 WebGL 厂商/渲染器。"""
    cfg = json.dumps({k: ident[k] for k in
                      ("platform", "languages", "cores", "memory", "glVendor", "glRenderer")})
    return ("(function(){var id=%s;window.__kbx_ident=id;try{"
            "Object.defineProperty(navigator,'platform',{get:function(){return id.platform}});"
            "Object.defineProperty(navigator,'hardwareConcurrency',{get:function(){return id.cores}});"
            "Object.defineProperty(navigator,'deviceMemory',{get:function(){return id.memory}});"
            "Object.defineProperty(navigator,'languages',{get:function(){return id.languages}});"
            "Object.defineProperty(navigator,'language',{get:function(){return id.languages[0]}});"
            "var patch=function(P){if(!P)return;var g=P.getParameter;P.getParameter=function(p){"
            "if(p===37445)return id.glVendor;if(p===37446)return id.glRenderer;return g.call(this,p)}};"
            "patch(window.WebGLRenderingContext&&WebGLRenderingContext.prototype);"
            "patch(window.WebGL2RenderingContext&&WebGL2RenderingContext.prototype);"
            "}catch(e){}})();" % cfg)


def pick_proxy(explicit=None):
    """代理来源优先级：显式参数 > CHS_PROXY > CLOAK_PROXIES。
    CLOAK_PROXIES 默认随机取一个；设 CLOAK_CHECK=1 时逐个测活，自动跳过不可用的。"""
    if explicit:
        return explicit
    if os.environ.get("CHS_PROXY"):
        return os.environ["CHS_PROXY"]
    lst = [p.strip() for p in os.environ.get("CLOAK_PROXIES", "").split(",") if p.strip()]
    if not lst:
        return None
    if os.environ.get("CLOAK_CHECK"):
        alive = [p for p in lst if probe_proxy(p, timeout=6).get("ok")]
        if not alive:
            log("WARN: CLOAK_PROXIES 全部不可用，回退直连")
            return None
        log("代理池测活：%d/%d 可用" % (len(alive), len(lst)))
        return random.choice(alive)
    return random.choice(lst)


def launch(url=None, proxy=None):
    chrome = find_chrome()
    if not chrome:
        sys.exit("未找到 Chrome 内核。请先执行：bash scripts/install_chrome_kernel.sh headless")
    proxy = pick_proxy(proxy)
    port = free_port()
    os.makedirs(PROFILE, exist_ok=True)
    args = [
        chrome,
        "--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage",
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={port}",
        f"--user-data-dir={PROFILE}",
        "--window-size=1440,900", "--hide-scrollbars",
        "--no-first-run", "--no-default-browser-check",
        "--disable-extensions", "--disable-background-networking",
        "--allow-file-access-from-files",
        "--disable-blink-features=AutomationControlled",
        "about:blank",
    ]
    if "chrome-headless-shell" not in os.path.basename(chrome):
        args.insert(1, "--headless=new")
    if proxy:
        args.insert(1, "--proxy-server=%s" % proxy)
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)

    ver = None
    for _ in range(120):
        try:
            ver = http_json(f"http://127.0.0.1:{port}/json/version", timeout=1.0)
            break
        except Exception:
            if p.poll() is not None:
                sys.exit("Chrome 启动后立即退出，请检查内核是否完整")
            time.sleep(0.25)
    if not ver:
        p.kill()
        sys.exit("Chrome 未在超时内就绪")

    page_ws = None
    for _ in range(50):
        try:
            for t in http_json(f"http://127.0.0.1:{port}/json/list"):
                if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                    page_ws = t["webSocketDebuggerUrl"]
                    break
        except Exception:
            pass
        if page_ws:
            break
        time.sleep(0.2)
    if not page_ws:
        p.kill()
        sys.exit("未找到可用的页面目标")

    st = {"pid": p.pid, "port": port, "chrome": chrome, "page_ws": page_ws,
          "url": "about:blank", "userscripts": [],
          "identity": random_identity(), "proxy": proxy}
    write_state(st)
    return st


def ensure(url=None):
    st = read_state()
    if st and is_alive(st):
        return st
    # 复用上次记录的出口代理（`proxy set` 因此能在重启后生效）
    return launch(url, proxy=(st or {}).get("proxy"))


# ---------------------------------------------------------------- CDP 客户端
class Page:
    def __init__(self, ws_url):
        # CDP 返回的目标地址常是 localhost，可能解析到 ::1 导致连接被拒；统一成 127.0.0.1
        ws_url = re.sub(r"//localhost(?=[:/])", "//127.0.0.1", ws_url)
        self.ws = websocket.create_connection(ws_url, timeout=40, max_size=None,
                                              suppress_origin=True)
        self._id = 0
        self._events = []

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass

    def call(self, method, params=None, timeout=40):
        self._id += 1
        mid = self._id
        msg = {"id": mid, "method": method}
        if params:
            msg["params"] = params
        self.ws.send(json.dumps(msg))
        end = time.time() + timeout
        while True:
            self.ws.settimeout(max(0.3, end - time.time()))
            msg = json.loads(self.ws.recv())
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
            if msg.get("method"):
                self._events.append(msg)

    def wait_event(self, method, timeout=25):
        for i, e in enumerate(self._events):
            if e.get("method") == method:
                return self._events.pop(i)
        end = time.time() + timeout
        while time.time() < end:
            try:
                self.ws.settimeout(max(0.3, end - time.time()))
                msg = json.loads(self.ws.recv())
            except Exception:
                break
            if msg.get("method") == method:
                return msg
        return None


def connect(st):
    try:
        for t in http_json(f"http://127.0.0.1:{st['port']}/json/list"):
            if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                st["page_ws"] = t["webSocketDebuggerUrl"]
                break
    except Exception:
        pass
    return Page(st["page_ws"])


def evaluate(page, expr, by_value=True, cmd_api=False):
    res = page.call("Runtime.evaluate", {
        "expression": expr, "returnByValue": by_value,
        "awaitPromise": True, "userGesture": True,
        "includeCommandLineAPI": cmd_api,
    })
    if "exceptionDetails" in res:
        d = res["exceptionDetails"]
        raise RuntimeError("JS 异常: " + (d.get("exception", {}).get("description") or d.get("text", "")))
    return res.get("result", {}).get("value") if by_value else None


def prepare(page, st):
    """把钩子与油猴脚本登记给「后续导航」，并补注入「当前文档」。
    每次连接都做：CDP 的 addScriptToEvaluateOnNewDocument 随会话结束而失效，
    因此跨命令的页面自刷新会丢钩子——补注入当前文档即可恢复（钩子/脚本自带幂等守卫）。"""
    page.call("Page.enable", timeout=12)
    page.call("Runtime.enable", timeout=12)
    for dom in ("Log", "Network"):
        try:
            page.call(dom + ".enable", timeout=12)
        except Exception:
            pass

    ident = st.get("identity")
    if ident:
        try:
            page.call("Network.setExtraHTTPHeaders", {"headers": ident["headers"]})
            page.call("Network.setUserAgentOverride", {
                "userAgent": ident["ua"],
                "platform": ident["platform"],
            })
            page.call("Emulation.setTimezoneOverride", {"timezoneId": ident["timezone"]})
            page.call("Emulation.setLocaleOverride", {"locale": ident["locale"]})
        except Exception:
            pass

    hook = read_file(os.path.join(HERE, "hook.js"))
    if ident:
        page.call("Page.addScriptToEvaluateOnNewDocument", {"source": identity_script(ident)})
    page.call("Page.addScriptToEvaluateOnNewDocument", {"source": hook})
    for us in st.get("userscripts", []):
        if us.get("source"):
            page.call("Page.addScriptToEvaluateOnNewDocument", {"source": us["source"]})

    # 补注入当前文档（幂等：hook 用 __kbx.hooked、脚本用 __kbx_us 去重）
    try:
        if ident:
            evaluate(page, identity_script(ident), by_value=False)
        evaluate(page, hook, by_value=False)
        for us in st.get("userscripts", []):
            if us.get("source"):
                evaluate(page, us["source"], by_value=False)
    except Exception:
        pass


def normalize_url(u):
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", u) or u.startswith(("about:", "file:", "data:")):
        return u
    if u.startswith("/") or os.path.exists(u):
        return "file://" + os.path.abspath(u)
    return "https://" + u


def is_challenge(page):
    try:
        h = evaluate(page, "(document.documentElement?document.documentElement.outerHTML:'').slice(0,8000)")
        return bool(h) and len(h) < 8000 and bool(CHALLENGE_RE.search(h))
    except Exception:
        return False


def navigate(page, url, solve=True):
    """加载超时（站点不可达/极慢）时主动停止加载，避免页面目标被挂起的导航卡死。"""
    url = normalize_url(url)
    page.call("Page.navigate", {"url": url})
    if page.wait_event("Page.loadEventFired", timeout=20) is None:
        try:
            page.call("Page.stopLoading")
        except Exception:
            pass
        log("WARN: 20s 内未完成加载（站点可能不可达或极慢），已停止加载")
        return url
    time.sleep(0.4)
    if solve and is_challenge(page):
        log("检测到 JS 反爬挑战，等待自动跳转…")
        page.wait_event("Page.loadEventFired", timeout=12)
        time.sleep(0.6)
        if is_challenge(page):
            page.call("Page.reload", {})
            page.wait_event("Page.loadEventFired", timeout=15)
            time.sleep(0.5)
        log("挑战处理完成，Cookie 已写入" if not is_challenge(page) else "警告：仍疑似挑战页，可重试 open")
    return url


def resolve_selector(target):
    if str(target).isdigit():
        return json.dumps(f'[data-kbx-n="{target}"]')
    return json.dumps(target)


# ---------------------------------------------------------------- 截图 / 标注
def take_shot(page, st, out=None, full=False):
    settle(page, OPTS)
    aopts = {}
    if OPTS.get("only"):
        aopts["only"] = [s.strip() for s in str(OPTS["only"]).split(",") if s.strip()]
    if "no-region" in OPTS:
        aopts["noRegion"] = True
    if OPTS.get("max"):
        aopts["max"] = int(OPTS["max"])
    src = "window.__kbxOpts=%s;\n%s" % (json.dumps(aopts), read_file(os.path.join(HERE, "annotate.js")))
    info = json.loads(evaluate(page, src, cmd_api=True))
    if not info.get("ok"):
        raise RuntimeError("标注失败: " + str(info.get("error")))

    params = {"format": "png"}
    if full:
        m = page.call("Page.getLayoutMetrics")
        cs = m.get("cssContentSize") or m.get("contentSize") or {"width": 1440, "height": 900}
        params["captureBeyondViewport"] = True
        params["clip"] = {"x": 0, "y": 0, "width": int(cs["width"]),
                          "height": min(int(cs["height"]), 20000), "scale": 1}
    res = page.call("Page.captureScreenshot", params, timeout=60)
    png = base64.b64decode(res["data"])

    os.makedirs(SHOT_DIR, exist_ok=True)
    path = out or os.path.join(SHOT_DIR, "shot_%s.png" % time.strftime("%Y%m%d_%H%M%S"))
    with open(path, "wb") as f:
        f.write(png)
    with open(re.sub(r"\.png$", ".json", path), "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=1)

    log("SHOT: " + path)
    c = info.get("counts") or {}
    log("ELEMENTS: %d  (交互%d 标题%d 文字%d 媒体%d 结构%d)" % (
        info["count"], c.get("interactive", 0), c.get("head", 0), c.get("text", 0),
        c.get("media", 0), c.get("region", 0)))
    if info.get("truncated"):
        log("WARN: 页面元素过多已按上限截断，可用 --only 缩小范围")
    tshow = 0
    for it in info["items"]:
        if it.get("tier") == "text":
            tshow += 1
            if tshow > 60:
                continue
        log("[%d] %-11s %-13s %s %s" % (it["n"], it.get("tier", ""), it.get("kind", ""),
                                        it["tag"], ('"%s"' % it["text"]) if it["text"] else ""))
    if tshow > 60:
        log("…（文字项共 %d 个，此处仅列前 60；全部见同名 .json）" % tshow)
    return path, info


# ---------------------------------------------------------------- 等待：秒数 / 条件 / 视觉稳定
def shot_key(b64, tol=0.0):
    """tol<=0 时直接用原始字节（逐字节全等，零依赖）；tol>0 时降采样为灰度矩阵做容差比对。"""
    if tol <= 0:
        return b64
    try:
        import numpy as np
        from PIL import Image
        im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("L").resize((72, 72))
        return np.asarray(im, dtype="float32")
    except Exception:
        return b64


def shot_same(a, b, tol=0.0):
    if isinstance(a, str) or isinstance(b, str):
        return a == b
    return float(abs(a - b).max()) <= tol


def wait_stable(page, timeout=15.0, interval=0.6, need=2, tol=0.0):
    """截图识别：连续截图直到画面不再变化（连中 need 次即判定稳定）。
    tol>0 时允许像素级容差（抗轻微抖动/光标闪烁），tol=0 为逐字节全等。
    用于等 SPA 渲染、懒加载、动画结束。返回是否在超时内稳定。"""
    end = time.time() + timeout
    last, hits = None, 0
    while time.time() < end:
        try:
            cur = page.call("Page.captureScreenshot",
                            {"format": "jpeg", "quality": 35}, timeout=30).get("data", "")
        except Exception:
            return False
        k = shot_key(cur, tol)
        if last is not None and shot_same(k, last, tol):
            hits += 1
            if hits >= need:
                return True
        else:
            hits = 0
        last = k
        time.sleep(interval)
    return False


def wait_until(page, expr, timeout=15.0, interval=0.4):
    """轮询 JS 条件直到为真。"""
    end = time.time() + timeout
    while time.time() < end:
        try:
            if evaluate(page, expr):
                return True
        except Exception:
            pass
        time.sleep(interval)
    return False


def settle(page, opts):
    """出图前统一等待：--stable 等画面稳定（可带 --stable-tol 像素容差），--wait N 固定等 N 秒。"""
    tol = float(opts.get("stable-tol", 0) or 0)
    if "stable" in opts or "stable-tol" in opts:
        log("等待画面稳定（截图识别%s）…" % ("，容差≤%g" % tol if tol > 0 else ""))
        log("画面已稳定" if wait_stable(page, tol=tol) else "画面 15s 内未稳定，继续")
    if "wait" in opts:
        secs = float(opts["wait"])
        time.sleep(secs)
        log("已等待 %.2fs" % secs)


# ---------------------------------------------------------------- 键位
SPECIAL = {
    "enter": (13, "Enter", "Enter"), "return": (13, "Enter", "Enter"),
    "tab": (9, "Tab", "Tab"), "escape": (27, "Escape", "Escape"), "esc": (27, "Escape", "Escape"),
    "backspace": (8, "Backspace", "Backspace"), "delete": (46, "Delete", "Delete"),
    "arrowup": (38, "ArrowUp", "ArrowUp"), "arrowdown": (40, "ArrowDown", "ArrowDown"),
    "arrowleft": (37, "ArrowLeft", "ArrowLeft"), "arrowright": (39, "ArrowRight", "ArrowRight"),
    "home": (36, "Home", "Home"), "end": (35, "End", "End"),
    "pageup": (33, "PageUp", "PageUp"), "pagedown": (34, "PageDown", "PageDown"),
    "space": (32, " ", "Space"), " ": (32, " ", "Space"),
}
MODS = {"alt": 1, "ctrl": 2, "control": 2, "meta": 4, "cmd": 4, "command": 4,
        "super": 4, "win": 4, "shift": 8}


def resolve_key(key):
    low = key.lower()
    if low in SPECIAL:
        return SPECIAL[low]
    if len(key) == 1:
        if key.isalpha():
            up = key.upper()
            return (ord(up), key, "Key" + up)
        if key.isdigit():
            return (ord(key), key, "Digit" + key)
        return (ord(key), key, "")
    return (0, key, key)


def do_press(page, spec):
    parts = spec.split("+")
    mods = 0
    for p in parts[:-1]:
        if p.lower() not in MODS:
            raise RuntimeError("未知修饰键: " + p)
        mods |= MODS[p.lower()]
    key = parts[-1]
    vk, k, code = resolve_key(key)
    down = {"type": "keyDown", "modifiers": mods, "key": k, "code": code,
            "windowsVirtualKeyCode": vk, "nativeVirtualKeyCode": vk}
    if len(k) == 1 and k.isprintable():
        down["text"] = k
    page.call("Input.dispatchKeyEvent", down)
    page.call("Input.dispatchKeyEvent", {"type": "keyUp", "modifiers": mods, "key": k,
                                         "code": code, "windowsVirtualKeyCode": vk,
                                         "nativeVirtualKeyCode": vk})


# ---------------------------------------------------------------- 动作
def find_js(target):
    """按编号从 window.__kbxNodes 取元素（可跨 Shadow DOM）；否则按 CSS 选择器。"""
    if str(target).isdigit():
        return "var e=(window.__kbxNodes||{})[%d]||null;" % int(target)
    return "var e=document.querySelector(%s);" % json.dumps(target)


def action_click(page, target):
    info = evaluate(page, (
        "(function(){" + find_js(target) +
        "if(!e)return 'NULL';"
        "e.scrollIntoView({block:'center',inline:'center'});"
        "var r=e.getBoundingClientRect();"
        "return JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2),"
        "tag:e.tagName.toLowerCase(),text:(e.textContent||'').trim().slice(0,30)});})()"))
    if info == "NULL":
        raise RuntimeError(f"未找到元素：{target}（若用编号，请先 shot 重新编号）")
    d = json.loads(info)
    x, y = d["x"], d["y"]
    page.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": x, "y": y, "button": "none"})
    page.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": x, "y": y,
                                           "button": "left", "clickCount": 1, "buttons": 1})
    page.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": x, "y": y,
                                           "button": "left", "clickCount": 1, "buttons": 0})
    return d


def action_type(page, target, text, clear=False):
    ok = evaluate(page, (
        "(function(){" + find_js(target) +
        "if(!e)return false;"
        "e.scrollIntoView({block:'center'});if(e.focus)e.focus();return true;})()"))
    if not ok:
        raise RuntimeError(f"未找到元素：{target}")
    if clear:
        evaluate(page, (
            "(function(){" + find_js(target) +
            "if(!e)return 0;"
            "if('value' in e){e.value='';}else{e.textContent='';}"
            "e.dispatchEvent(new Event('input',{bubbles:true}));return 1;})()"))
    page.call("Input.insertText", {"text": text})


def action_scroll(page, dy, dx=0):
    pos = json.loads(evaluate(page, "JSON.stringify([Math.round(innerWidth/2),Math.round(innerHeight/2)])"))
    page.call("Input.dispatchMouseEvent", {"type": "mouseWheel", "x": pos[0], "y": pos[1],
                                           "deltaX": dx, "deltaY": dy, "button": "none"})


# ---------------------------------------------------------------- 精密鼠标操作
BTN_MASK = {"left": 1, "right": 2, "middle": 4}
POINT_RE = re.compile(r"^\s*-?\d+(?:\.\d+)?\s*[,\s]\s*-?\d+(?:\.\d+)?\s*$")


def _pt(v):
    """'x,y' / 'x y' / [x,y] → (x, y)。"""
    if isinstance(v, (list, tuple)):
        return float(v[0]), float(v[1])
    s = str(v).replace(",", " ").split()
    if len(s) != 2:
        raise ValueError("坐标格式应为 x,y 或 'x y'：%r" % v)
    return float(s[0]), float(s[1])


def is_point(target):
    return bool(POINT_RE.match(str(target)))


def elem_center(page, target):
    """编号 / CSS 选择器 → 元素中心（视口 CSS 像素）；'x,y' → 原样坐标。
    编号走 window.__kbxNodes，可命中 Shadow DOM 内部元素。"""
    if is_point(target) or isinstance(target, (list, tuple)):
        x, y = _pt(target)
        return {"x": x, "y": y, "w": 0, "h": 0, "tag": "point", "text": ""}
    info = evaluate(page, (
        "(function(){" + find_js(target) +
        "if(!e)return 'NULL';"
        "e.scrollIntoView({block:'center',inline:'center'});"
        "var r=e.getBoundingClientRect();"
        "return JSON.stringify({x:r.left+r.width/2,y:r.top+r.height/2,w:r.width,h:r.height,"
        "tag:e.tagName.toLowerCase(),text:(e.textContent||'').trim().slice(0,30)});})()"))
    if info == "NULL":
        raise RuntimeError(f"未找到元素：{target}（用编号请先 shot 重新编号）")
    return json.loads(info)


def get_mouse(page, st):
    """当前鼠标位置：优先状态里记录的，其次视口中心。"""
    m = st.get("mouse")
    if m:
        return float(m[0]), float(m[1])
    c = json.loads(evaluate(page, "JSON.stringify([Math.round(innerWidth/2),Math.round(innerHeight/2)])"))
    return float(c[0]), float(c[1])


def glide(page, x0, y0, x1, y1, steps=None, jitter=0.0, delay=(0.006, 0.02),
          ease=True, btn="none", mask=0):
    """两点间插值移动：smoothstep 缓入缓出；jitter 为垂直随机抖动（两端小、中间大）。
    btn/mask 用于拖拽过程中保持按键按下态。"""
    dist = math.hypot(x1 - x0, y1 - y0)
    if steps is None:
        steps = max(1, min(28, int(dist / 14) + 3))
    for i in range(1, steps + 1):
        t = i / steps
        e = t * t * (3 - 2 * t) if ease else t
        y = y0 + (y1 - y0) * e
        if jitter:
            y += random.uniform(-jitter, jitter) * math.sin(math.pi * t)
        page.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "button": btn, "buttons": mask,
                                               "x": round(x0 + (x1 - x0) * e, 1), "y": round(y, 1)})
        if steps > 1:
            time.sleep(random.uniform(*delay))
    page.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "button": btn, "buttons": mask,
                                           "x": round(x1, 1), "y": round(y1, 1)})
    return x1, y1


def mouse_button(page, x, y, button="left", count=1):
    mask = BTN_MASK.get(button)
    if not mask:
        raise ValueError("button 仅支持 left / right / middle")
    for c in range(1, count + 1):
        page.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": round(x, 1), "y": round(y, 1),
                                               "button": button, "clickCount": c, "buttons": mask})
        page.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": round(x, 1), "y": round(y, 1),
                                               "button": button, "clickCount": c, "buttons": 0})
        if c < count:
            time.sleep(random.uniform(0.03, 0.09))


def do_move(page, st, x, y, steps=None, jitter=0.0):
    x0, y0 = get_mouse(page, st)
    glide(page, x0, y0, x, y, steps=steps, jitter=jitter)
    st["mouse"] = [x, y]
    write_state(st)


def do_click_at(page, st, x, y, button="left", count=1, steps=None):
    x0, y0 = get_mouse(page, st)
    glide(page, x0, y0, x, y, steps=steps)
    mouse_button(page, x, y, button, count)
    st["mouse"] = [x, y]
    write_state(st)
    return {"x": x, "y": y}


# ---------------------------------------------------------------- 人机验证识别 / 缺口定位
CAPTCHA_SELS = [
    "#nc_1_n1z", ".nc-container", ".nc_wrapper", ".nc_scale",          # 阿里 / 通用
    ".geetest_slider_button", ".geetest_panel", ".geetest_holder", ".geetest_slider",  # 极验
    ".yidun_slider", ".yidun_panel", ".yidun_intelli",                 # 网易易盾
    ".sliderContainer", ".slider-btn", ".verify-bar", ".verify-box", ".verify-wrap",
    "[class*='captcha']", "[id*='captcha']", "[class*='vcode']", "[id*='vcode']",
    "[class*='slider'][class*='btn']", "[class*='slide'][class*='btn']",
    ".slider-track", "[class*='slider'][class*='track']", "[class*='slide'][class*='track']", ".drag-track",
    ".pass-captcha", "#passport-verify", ".tang-pass-verify", "#vcodeImg",  # 百度系
    "iframe[src*='captcha']", "iframe[src*='verify']", "iframe[src*='turing']",
]

CAPTCHA_JS = r"""
(function(){
 var sels=%s, out=[], seen=[];
 function rec(el,why){ try{
   if(seen.indexOf(el)>=0) return; seen.push(el);
   var r=el.getBoundingClientRect();
   if(r.width<4||r.height<4) return;
   var st=getComputedStyle(el);
   if(st.display==='none'||st.visibility==='hidden'||parseFloat(st.opacity||1)===0) return;
   out.push({sel:why,tag:el.tagName.toLowerCase(),id:el.id||'',
     cls:String(el.className||'').slice(0,90),
     x:Math.round(r.left),y:Math.round(r.top),w:Math.round(r.width),h:Math.round(r.height),
     ratio:+(r.height?(r.width/r.height).toFixed(2):0),
     iframe:el.tagName==='IFRAME',src:el.getAttribute?String(el.getAttribute('src')||'').slice(0,120):''});
 }catch(e){} }
 sels.forEach(function(s){ try{ document.querySelectorAll(s).forEach(function(e){rec(e,s);}); }catch(e){} });
 if((document.body.innerText||'').length<4000){   // 仅在内容稀疏的页面上启用启发式，避免大站点误报
   var c=document.querySelectorAll('div,span,button,i,img,a'), hh=0;
   for(var i=0;i<c.length&&hh<3;i++){ var e=c[i], r=e.getBoundingClientRect();
     if(r.width<24||r.width>64||r.height<24||r.height>64) continue;
     var ar=r.width/r.height; if(ar<0.7||ar>1.4) continue;
     var p=e.parentElement; if(!p) continue; var pr=p.getBoundingClientRect();
     if(pr.height>70||pr.width<r.width*2.2||pr.width>700) continue;
     if(getComputedStyle(p).overflow!=='hidden') continue;   // 滑块轨道必有 overflow:hidden
     rec(e,'slider-handle?'); hh++;
   }}
 return JSON.stringify(out.slice(0,80));
})()
"""

POS_JS = r"""
(function(){
 var pats=[/gap/i,/offsetX/i,/moveX/i,/sliderX/i,/targetX/i,/puzzleX/i,/\bdistance\b/i,
           /缺口/,/滑块/,/left\s*:\s*\d+/,/Math\.random\(\)\s*\*\s*\d+/];
 var scripts=[].slice.call(document.scripts), inlines='', ext=[];
 scripts.forEach(function(s){ if(s.src) ext.push(s.src); else inlines+=(s.textContent||'')+'\n'; });
 var hits=[];
 inlines.split('\n').forEach(function(l){ if(!l.trim())return;
   for(var i=0;i<pats.length;i++){ if(pats[i].test(l)){ hits.push(l.trim().slice(0,150)); break; } }});
 var bg=0, imgs=[], cv=document.querySelectorAll('canvas').length;
 [].slice.call(document.querySelectorAll('*')).forEach(function(e){
   var r=e.getBoundingClientRect();
   if(r.width>60&&r.height>30){ var st=getComputedStyle(e);
     if(st.backgroundImage&&st.backgroundImage!=='none') bg++; }});
 [].slice.call(document.images).forEach(function(i){
   if(i.getBoundingClientRect().width>40)
     imgs.push({src:String(i.currentSrc||i.src).slice(0,120),w:i.naturalWidth,h:i.naturalHeight});});
 return JSON.stringify({inline_len:inlines.length,inline_hits:hits.slice(0,12),
   ext_scripts:ext.slice(0,10),bg_layers:bg,imgs:imgs.slice(0,10),canvas:cv,
   dpr:window.devicePixelRatio||1,iw:innerWidth,ih:innerHeight});
})()
"""


def captcha_scan(page):
    return json.loads(evaluate(page, CAPTCHA_JS % json.dumps(CAPTCHA_SELS)))


def analyze_position(page):
    return json.loads(evaluate(page, POS_JS))


def _blob_gap(mask):
    """连通域法：缺口是规则实心的暗色块，取面积最大的近方形连通域（最稳）。"""
    try:
        import cv2
        n, _lab, stats, _c = cv2.connectedComponentsWithStats(mask, 8)
    except Exception:
        return None
    best = None
    for i in range(1, n):
        x, y, w, h, area = [int(v) for v in stats[i]]
        if area < 150 or area > 22000 or h < 12 or w < 8:
            continue
        ar = w / float(max(1, h))
        if ar < 0.6 or ar > 1.7:            # 缺口近似正方；细长暗区不是缺口
            continue
        if w > mask.shape[1] * 0.5:         # 超过半幅的暗块是背景内容，不是缺口
            continue
        if best is None or area > best["area"]:
            best = {"area": area, "cx": x + w / 2.0, "w": w, "h": h}
    if not best:
        return None
    return {"x": best["cx"], "width": best["w"], "score": float(best["area"]),
            "method": "blob", "note": "暗块 %dx%d" % (best["w"], best["h"])}


def _col_gap(a, mode, min_gap):
    """列统计回退：dark 找最暗列带（暗色凹槽），edge 找竖直边缘最强的列带。"""
    import numpy as np
    med = float(np.median(a))
    dark = (a < max(40.0, med - 38.0)).sum(axis=0).astype("float32")
    edge = np.abs(np.diff(a, axis=0)).sum(axis=0)
    k = max(3, min_gap // 3)
    nd = np.convolve(dark, np.ones(k) / k, mode="same")
    ne = np.convolve(edge + 1e-9, np.ones(k) / k, mode="same")
    nd = nd / (nd.max() or 1.0)
    ne = ne / (ne.max() or 1.0)
    score = nd if mode == "dark" else ne if mode == "edge" else (nd * 1.2 + ne * 0.8)
    i = int(np.argmax(score))
    thr, left, right = score[i] * 0.9, i, i
    while left > 0 and score[left - 1] >= thr:
        left -= 1
    while right < len(score) - 1 and score[right + 1] >= thr:
        right += 1
    return {"x": (left + right) / 2.0, "width": right - left + 1,
            "score": round(float(score[i] / max(1e-6, float(score.mean()))), 2),
            "method": "col-" + mode, "note": ""}


def detect_gap(img_bytes, box=None, mode="auto", min_x=0, min_gap=18):
    """定位「缺口」的水平位置，返回相对裁切区左缘的设备像素偏移。
    auto/dark 优先连通域法（缺口是实心暗块）；失败或 mode=edge 时退回列统计。
    min_x 用于排除左侧「拼图块/滑块」自身（否则会被当成缺口）。"""
    import numpy as np
    from PIL import Image
    im = Image.open(io.BytesIO(img_bytes)).convert("L")
    if box:
        im = im.crop((max(0, int(box[0])), max(0, int(box[1])),
                      min(im.width, int(box[2])), min(im.height, int(box[3]))))
    a = np.asarray(im, dtype="float32")
    if a.ndim != 2 or a.shape[1] < min_gap or a.shape[0] < 3:
        return None
    if min_x:
        a = a[:, int(min_x):]
    r = None
    if mode in ("auto", "dark"):
        thr = max(40.0, float(np.median(a)) - 38.0)
        r = _blob_gap((a < thr).astype("uint8"))
    if r is None:
        r = _col_gap(a, "edge" if mode == "edge" else "dark", min_gap)
    if r is None:
        return None
    r["x"] = r["x"] + (int(min_x) if min_x else 0)
    return r


def human_track(n, overshoot=0.0):
    """归一化位移序列：正弦速度剖面（两端慢、中间快）+ 可选末端过冲。"""
    n = max(1, n)
    v = [math.sin(math.pi * (i + 0.5) / n) ** 0.85 for i in range(n)]
    s = sum(v) or 1.0
    acc, out = 0.0, []
    for p in v:
        acc += p / s
        out.append(acc)
    out[-1] = 1.0 + overshoot
    return out


def human_slide(page, st, dist, handle=None, duration=None, y_jitter=None, overshoot=None):
    """类人拖动：随机时长、非匀速、上下随机抖动、1~2 次微停顿、末端过冲后回冲修正。"""
    x0, y0 = handle if handle else get_mouse(page, st)
    dist = float(dist)
    if abs(dist) < 4:
        raise RuntimeError("滑动距离过小：%.1fpx" % dist)
    if duration is None:
        duration = max(0.55, min(1.7, abs(dist) / 210.0 + random.uniform(0.18, 0.55)))
    if y_jitter is None:
        y_jitter = random.uniform(0.5, 2.6)
    if overshoot is None:
        overshoot = random.choice([0.0, 0.0, 0.004, 0.008, 0.012, 0.02])

    y_start = y0 + random.uniform(-y_jitter, y_jitter)
    page.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": round(x0, 1),
                                           "y": round(y_start, 1), "button": "none"})
    time.sleep(random.uniform(0.12, 0.34))                       # 按下前的犹豫
    page.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": round(x0, 1),
                                           "y": round(y_start, 1), "button": "left",
                                           "clickCount": 1, "buttons": 1})
    time.sleep(random.uniform(0.04, 0.13))

    total = dist * (1.0 + overshoot)
    n = max(18, int(abs(total) / random.uniform(3.2, 5.4)))
    pts = human_track(n, overshoot)
    pauses = sorted(random.sample(range(3, n - 3), k=random.choice([0, 1, 1, 2]))) if n > 10 else []
    step_sleep = duration / n
    for i, e in enumerate(pts, 1):
        x = x0 + total * e
        y = y_start + random.uniform(-y_jitter, y_jitter) * 0.6
        page.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": round(x, 1),
                                               "y": round(y, 1), "button": "left", "buttons": 1})
        time.sleep(max(0.004, step_sleep * random.uniform(0.6, 1.6)))
        if i in pauses:
            time.sleep(random.uniform(0.05, 0.16))               # 人类微停顿

    if overshoot:                                               # 过冲后回冲修正
        x_end, y_end = glide(page, x0 + total, y_start, x0 + dist, y0,
                             steps=random.randint(4, 8), delay=(0.008, 0.02),
                             btn="left", mask=1)
    else:
        x_end, y_end = x0 + dist, y0
        page.call("Input.dispatchMouseEvent", {"type": "mouseMoved", "x": round(x_end, 1),
                                               "y": round(y_end, 1), "button": "left", "buttons": 1})
    time.sleep(random.uniform(0.15, 0.5))                        # 松手前停顿
    page.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": round(x_end, 1),
                                           "y": round(y_end, 1), "button": "left",
                                           "clickCount": 1, "buttons": 0})
    st["mouse"] = [x_end, y_end]
    write_state(st)
    return {"dist": round(dist, 1), "duration": round(duration, 2),
            "y_jitter": round(y_jitter, 2), "overshoot_pct": round(overshoot * 100, 1), "steps": n}


# ---------------------------------------------------------------- 出口代理
PROBE_URLS = ["http://ip-api.com/json/?fields=query,country",
              "https://api.ipify.org", "http://ifconfig.me/ip"]


def probe_proxy(proxy=None, timeout=7):
    """经（或不经过）代理请求，返回真实出口 IP —— 用于验证代理是否真正改变了出口。"""
    op = urllib.request.build_opener(urllib.request.ProxyHandler(
        {"http": proxy, "https": proxy} if proxy else {}))
    last = ""
    for url in PROBE_URLS:
        try:
            t = time.time()
            req = urllib.request.Request(url, headers={"User-Agent": "curl/8.5.0"})
            body = op.open(req, timeout=timeout).read().decode("utf-8", "ignore")
            ms = int((time.time() - t) * 1000)
            m = re.search(r'"query"\s*:\s*"([^"]+)"', body) or re.search(r'"ip"\s*:\s*"([^"]+)"', body)
            ip = m.group(1) if m else re.sub(r"\s+", " ", body).strip()[:60]
            if ip:
                return {"ok": True, "ip": ip, "ms": ms, "via": url.split("/")[2]}
        except Exception as e:
            last = str(e)[:110]
    return {"ok": False, "err": last or "unreachable"}


def do_fetch(page, url, method="GET", body=None, headers=None):
    init = "method:%s,credentials:'include',headers:%s" % (json.dumps(method), json.dumps(headers or {}))
    if body is not None:
        init += ",body:" + json.dumps(body)
    expr = ("(async()=>{try{const r=await fetch(%s,{%s});const t=await r.text();"
            "return JSON.stringify({status:r.status,ct:r.headers.get('content-type')||'',"
            "len:t.length,body:t.slice(0,6000)});}"
            "catch(e){return JSON.stringify({error:String((e&&e.message)||e)})}})()"
            % (json.dumps(url), init))
    return json.loads(evaluate(page, expr))


def strip_userscript_meta(src):
    return re.sub(r"//\s*==UserScript==.*?//\s*==/UserScript==\s*", "", src, flags=re.S)


def build_userscript(path):
    src = strip_userscript_meta(read_file(path))
    key = os.path.basename(path)
    k = json.dumps(key)
    return ("/* userscript: %s */\n(function(){var ns=(window.__kbx_us=window.__kbx_us||{});"
            "if(ns[%s])return;ns[%s]=1;try{\n%s\n}catch(e){console.error('[userscript] '+e);}})();"
            % (key, k, k, src))


# ---------------------------------------------------------------- 参数解析
BOOL_FLAGS = {"full", "no-shot", "clear", "shot", "force", "stable", "no-region"}


def parse_args(argv):
    opts, pos = {}, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a.startswith("--"):
            k = a[2:]
            if k in BOOL_FLAGS:
                opts[k] = True
                i += 1
            elif i + 1 < len(argv) and not argv[i + 1].startswith("--"):
                v = argv[i + 1]
                if k in opts:
                    opts[k] = opts[k] + [v] if isinstance(opts[k], list) else [opts[k], v]
                else:
                    opts[k] = v
                i += 2
            else:
                opts[k] = True
                i += 1
        else:
            pos.append(a)
            i += 1
    return opts, pos


def as_list(v):
    if v is True or v is None:
        return []
    return v if isinstance(v, list) else [v]


# ---------------------------------------------------------------- 命令实现
def _mouse_cmd(page, st, cmd, args, opts):
    steps = int(opts["steps"]) if opts.get("steps") else None
    jitter = float(opts.get("jitter", 0) or 0)
    button = opts.get("button", "left")
    count = int(opts.get("count", 1) or 1)
    m0 = get_mouse(page, st)

    def near():
        if not args:
            return {"x": m0[0], "y": m0[1], "tag": "point", "text": ""}
        return elem_center(page, args[0])

    def settle_pt(c):
        st["mouse"] = [c["x"], c["y"]]
        write_state(st)

    if cmd == "move":
        if len(args) < 2:
            sys.exit("用法: move <x> <y> [--steps N] [--jitter PX]")
        do_move(page, st, float(args[0]), float(args[1]), steps, jitter)
        log("MOVE: (%s, %s) steps=%s jitter=%.1f" % (args[0], args[1], steps or "auto", jitter))
    elif cmd == "click-at":
        if len(args) < 2:
            sys.exit("用法: click-at <x> <y> [--button left|right|middle] [--count N]")
        d = do_click_at(page, st, float(args[0]), float(args[1]), button, count, steps)
        log("CLICK-AT: (%g, %g) button=%s count=%d" % (d["x"], d["y"], button, count))
    elif cmd == "hover":
        if not args:
            sys.exit("用法: hover <n|选择器> [--ms N]")
        c = near()
        glide(page, m0[0], m0[1], c["x"], c["y"], steps=steps, jitter=jitter)
        ms = int(opts.get("ms", 600) or 600)
        time.sleep(ms / 1000.0)
        settle_pt(c)
        log("HOVER: %s @(%d, %d) %dms" % (c.get("tag"), c["x"], c["y"], ms))
    elif cmd in ("dblclick", "rclick"):
        if not args:
            sys.exit("用法: %s <n|选择器>" % cmd)
        c = near()
        glide(page, m0[0], m0[1], c["x"], c["y"], steps=steps, jitter=jitter)
        mouse_button(page, c["x"], c["y"], "left" if cmd == "dblclick" else "right",
                     2 if cmd == "dblclick" else 1)
        settle_pt(c)
        log("%s: %s @(%d, %d)" % (cmd.upper(), c.get("tag"), c["x"], c["y"]))
    elif cmd in ("mdown", "mup"):
        c = near()
        press = cmd == "mdown"
        page.call("Input.dispatchMouseEvent", {
            "type": "mousePressed" if press else "mouseReleased",
            "x": round(c["x"], 1), "y": round(c["y"], 1), "button": button,
            "clickCount": 1, "buttons": BTN_MASK.get(button, 1) if press else 0})
        settle_pt(c)
        log("%s @(%d, %d) %s" % (cmd.upper(), c["x"], c["y"], button))
    elif cmd == "drag":
        if len(args) < 3:
            sys.exit("用法: drag <n|选择器|x,y> <dx> <dy> [--steps N] [--jitter PX]")
        c = near()
        tx, ty = c["x"] + float(args[1]), c["y"] + float(args[2])
        glide(page, m0[0], m0[1], c["x"], c["y"], steps=steps)
        page.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": round(c["x"], 1),
                                               "y": round(c["y"], 1), "button": "left",
                                               "clickCount": 1, "buttons": 1})
        time.sleep(random.uniform(0.05, 0.15))
        glide(page, c["x"], c["y"], tx, ty, steps=steps, jitter=jitter, btn="left", mask=1)
        time.sleep(random.uniform(0.08, 0.2))
        page.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": round(tx, 1),
                                               "y": round(ty, 1), "button": "left",
                                               "clickCount": 1, "buttons": 0})
        settle_pt({"x": tx, "y": ty})
        log("DRAG: (%d,%d) → (%g,%g)" % (c["x"], c["y"], tx, ty))
    else:
        sys.exit("未知鼠标命令: " + cmd)


def _pick_handle(items):
    """从候选里挑最像「滑块把手」的：小尺寸、类名含 slider/handle、非 iframe。"""

    def key(it):
        s = 0
        blob = (it["sel"] + " " + it["cls"] + " " + it["id"]).lower()
        if "handle" in blob:
            s += 4
        if "btn" in blob or "button" in blob:
            s += 2
        if "slider" in blob or "slider" in blob:
            s += 2
        if it["tag"] in ("div", "span", "button", "i"):
            s += 1
        if 26 <= it["w"] <= 70 and 26 <= it["h"] <= 70:
            s += 2
        if it["iframe"]:
            s -= 6
        return -s

    cands = [i for i in items if i["w"] <= 100 and i["h"] <= 100 and not i["iframe"]]
    return sorted(cands or items, key=key)[0]


TRACK_JS = r"""
(function(){
 var hs=document.querySelectorAll(%s);
 for(var i=0;i<hs.length;i++){
   var el=hs[i], r=el.getBoundingClientRect();
   if(r.width<20||r.height<20) continue;
   var p=el, d=0;
   while(p && d<6){ p=p.parentElement; d++; if(!p) break;
     var pr=p.getBoundingClientRect();
     if(pr.height<=70 && pr.width>=r.width*2.2 && pr.width<=800)
       return JSON.stringify({ok:true,x:Math.round(pr.left),y:Math.round(pr.top),
         w:Math.round(pr.width),h:Math.round(pr.height),cls:String(p.className||'').slice(0,50),
         hx:Math.round(r.left),hy:Math.round(r.top),hw:Math.round(r.width),hh:Math.round(r.height)});
   }
 }
 return JSON.stringify({ok:false});
})()
"""


def find_track(page, handle_sel):
    """沿 DOM 向上找「轨道」——不依赖类名，只要求：细高比合适的祖先容器。
    比按选择器猜更稳（很多站点轨道类名不含 slider/track）。"""
    try:
        return json.loads(evaluate(page, TRACK_JS % json.dumps(handle_sel)))
    except Exception:
        return {"ok": False}


def _pick_track(items, h, vw):
    """轨道：包含把手且明显更宽的元素；找不到就用整行。"""
    best = None
    for it in items:
        if it["w"] >= max(120, h["w"] * 2.5) and it["h"] <= 130 \
                and it["y"] <= h["y"] + h["h"] and it["y"] + it["h"] >= h["y"]:
            if best is None or it["w"] > best["w"]:
                best = it
    return best or {"x": 0, "y": max(0, h["y"] - 12), "w": vw, "h": h["h"] + 24}


def _pick_container(items, track):
    """包含轨道的最小候选元素，用于确定验证区域的上边界。"""
    best = None
    for it in items:
        if it is track or it["iframe"]:
            continue
        if it["x"] <= track["x"] + 4 and it["x"] + it["w"] >= track["x"] + track["w"] - 4 \
                and it["y"] <= track["y"] and it["y"] + it["h"] >= track["y"] + track["h"]:
            if best is None or it["w"] * it["h"] < best["w"] * best["h"]:
                best = it
    return best


def _captcha_cmd(page, st, cmd, args, opts):
    if cmd == "verify":
        items = captcha_scan(page)
        pos = analyze_position(page)
        log("人机验证候选：%d 个" % len(items))
        for it in items:
            name = "<%s%s%s>" % (it["tag"], ("#" + it["id"]) if it["id"] else "",
                                 ("." + it["cls"].split()[0]) if it["cls"] else "")
            log("  %-18s %-22s @%d,%d %dx%d 比例%s%s"
                % (it["sel"], name, it["x"], it["y"], it["w"], it["h"], it["ratio"],
                   ("  iframe:" + it["src"]) if it["iframe"] else ""))
        log("前端位置线索：内联脚本 %d 字符，命中 %d 行；外链脚本 %d 个；背景图层 %d；可见图片 %d；canvas %d"
            % (pos["inline_len"], len(pos["inline_hits"]), len(pos["ext_scripts"]),
               pos["bg_layers"], len(pos["imgs"]), pos["canvas"]))
        for hline in pos["inline_hits"][:6]:
            log("  | " + hline)
        for im in pos["imgs"][:4]:
            log("  img %dx%d  %s" % (im["w"], im["h"], im["src"]))
        verdict = None
        if len(pos["imgs"]) >= 2:                  # 多图层 → 实测各层是否真有内容
            shots, _li = layer_capture(page)
            if shots and len(shots) >= 2:
                import numpy as np
                stds = []
                for s in shots:
                    im = _dec(s)
                    stds.append(round(float(np.std(im)), 1) if im is not None else -1.0)
                log("图层活跃度 std：%s" % stds)
                live = [v for v in stds if v >= 5]
                if len(live) >= 2:
                    verdict = "多图层且各层均有内容 → 位置可由本地模板匹配求出（不依赖服务端）"
                elif live:
                    verdict = "多图层但仅一层有内容 → 位置由服务端渲染进图片，前端不含坐标，须图像识别"
                else:
                    verdict = "多图层但均近似空白 → 无有效图源，无法本地求解"
        if verdict is None:
            if pos["inline_hits"]:
                verdict = "前端存在位置相关脚本线索 → 缺口坐标或计算逻辑可能就在前端"
            else:
                verdict = "前端未见显式缺口位置信息 → 多由服务端下发或强混淆，只能靠图像识别"
        log("判定：" + verdict)
        if not items:
            log("提示：未匹配到已知验证组件（可能为 canvas / 封闭 iframe / 自定义组件），可用 shot 看编号。")
        return

    if cmd == "slide":
        if not args:
            sys.exit("用法: slide <距离px> [--duration MS] [--y-jitter PX] [--overshoot 比例]")
        r = human_slide(page, st, float(args[0]),
                        duration=(float(opts["duration"]) / 1000.0 if opts.get("duration") else None),
                        y_jitter=float(opts["y-jitter"]) if opts.get("y-jitter") else None,
                        overshoot=float(opts["overshoot"]) if opts.get("overshoot") else None)
        log("SLIDE: 距离%.1fpx 用时%.2fs 抖动±%.2fpx 过冲%.1f%% 步数%d"
            % (r["dist"], r["duration"], r["y_jitter"], r["overshoot_pct"], r["steps"]))
        return

    if cmd == "solve":
        retry = int(opts.get("retry", 1) or 1)
        mode = opts.get("mode", "auto")
        for attempt in range(1, retry + 1):
            items = captcha_scan(page)
            if not items:
                sys.exit("未识别到验证组件；先跑 `verify` 查看（也可用 shot 看编号后手工 drag）")
            pos = analyze_position(page)
            h = _pick_handle(items)
            track = _pick_track(items, h, pos["iw"] or 1440)
            tw = find_track(page, h["sel"])            # 沿 DOM 向上找轨道，更可靠
            if tw.get("ok"):
                h = {"sel": h["sel"], "tag": h["tag"], "id": h["id"], "cls": h["cls"],
                     "x": tw["hx"], "y": tw["hy"], "w": tw["hw"], "h": tw["hh"]}
                track = {"x": tw["x"], "y": tw["y"], "w": tw["w"], "h": tw["h"],
                         "sel": tw.get("cls", "")}
            log("把手 %s <%s%s> @%d,%d %dx%d   轨道 @%d,%d %dx%d"
                % (h["sel"], h["tag"], ("#" + h["id"]) if h["id"] else "",
                   h["x"], h["y"], h["w"], h["h"], track["x"], track["y"], track["w"], track["h"]))
            dist = None
            lg = layer_gap(page)                      # 策略 1：双图层 → 模板匹配
            if lg and lg["corr"] >= 0.5 and abs(lg["dist"]) >= 4:
                dist = lg["dist"]
                log("定位：双图层模板匹配 corr=%.3f → 需滑 %.1fpx" % (lg["corr"], dist))
            if dist is None:                          # 策略 2：单图暗色缺口 → 连通域
                dpr = float(pos["dpr"]) or 1.0
                png = base64.b64decode(page.call("Page.captureScreenshot", {"format": "png"}, timeout=60)["data"])
                cont = _pick_container(items, track)
                top = cont["y"] if cont else max(0, track["y"] - 180)
                if track["y"] - top < 40:               # 容器判定失败 → 取轨道上方 180px
                    top = max(0, track["y"] - 180)
                pad = 6
                crop_x0 = max(0, track["x"] - pad)
                crop_y0 = max(0, top)
                bottom = max(crop_y0 + 30, track["y"] - 2)   # 只扫轨道上方：缺口在图片里
                box = [crop_x0 * dpr, crop_y0 * dpr,
                       (track["x"] + track["w"] + pad) * dpr, bottom * dpr]
                min_x = max(0, int((h["x"] + h["w"] - crop_x0 + 4) * dpr))
                g = detect_gap(png, box=box, mode=mode, min_x=min_x)
                if not g:
                    sys.exit("缺口定位失败（可试 --mode edge，或用 shot 看编号后手工 drag）")
                crop_w = (box[2] - box[0]) / dpr
                reliable = (g["method"] == "blob" and g["width"] <= max(24.0, crop_w * 0.5)) \
                    or (g["method"].startswith("col") and g["score"] >= 1.35)
                if not reliable:
                    sys.exit("缺口定位置信度不足（%s 宽%.0fpx 指标%s）→ 建议：shot 看编号后用 drag 手工拖，或换 --mode"
                             % (g["method"], g["width"], g["score"]))
                gap_left = crop_x0 + (g["x"] - g["width"] / 2.0) / dpr
                dist = gap_left - h["x"]
                log("定位：%s %s 偏移%.1f 宽%dpx → 需滑 %.1fpx"
                    % (g["method"], g["note"], g["x"], g["width"], dist))
            if abs(dist) < 4:
                log("滑动距离过小，跳过")
                return
            r = human_slide(page, st, dist, handle=(h["x"] + h["w"] / 2.0, h["y"] + h["h"] / 2.0),
                            duration=(float(opts["duration"]) / 1000.0 if opts.get("duration") else None),
                            y_jitter=float(opts["y-jitter"]) if opts.get("y-jitter") else None)
            log("SLIDE#%d: 距离%.1fpx 用时%.2fs 抖动±%.2fpx 过冲%.1f%% 步数%d"
                % (attempt, r["dist"], r["duration"], r["y_jitter"], r["overshoot_pct"], r["steps"]))
            time.sleep(random.uniform(0.7, 1.3))
            left = captcha_scan(page)
            still = any("slide" in (i["sel"] + i["cls"] + i["id"]).lower() for i in left)
            gone = not still
            log("复检：验证组件 %d → %d，%s" % (len(items), len(left), "疑似通过" if gone else "仍在（可能未通过）"))
            if gone:
                return
            if attempt < retry:
                log("重试第 %d 次…" % (attempt + 1))
                time.sleep(random.uniform(0.8, 1.6))
        log("提示：若该验证码不是「缺口滑块」（如整图几何/圆形验证），或答案完全由服务端渲染，"
            "本地定位无法可靠完成 → 可用 shot 看编号后 drag 手工拖，或跳过。")
        return

    sys.exit("未知验证命令: " + cmd)


def _proxy_cmd(st, opts, args):
    sub = args[0] if args else "check"
    cur = opts.get("proxy") or os.environ.get("CHS_PROXY") or st.get("proxy")
    if sub == "check":
        for label, p in (("当前代理", cur), ("直连", None)):
            r = probe_proxy(p)
            log("%s：%s" % (label, ("出口 IP %s（%dms via %s）" % (r["ip"], r["ms"], r["via"]))
                          if r.get("ok") else "不可用（%s）" % r.get("err")))
    elif sub == "list":
        lst = [p.strip() for p in os.environ.get("CLOAK_PROXIES", "").split(",") if p.strip()]
        if not lst:
            sys.exit("未设置 CLOAK_PROXIES（形如 http://host:port,http://user:pass@host:port）")
        ok = 0
        for p in lst:
            r = probe_proxy(p, timeout=6)
            if r.get("ok"):
                ok += 1
                log("OK   %-42s → %s（%dms）" % (p, r["ip"], r["ms"]))
            else:
                log("FAIL %-42s → %s" % (p, r.get("err")))
        log("代理池：%d/%d 可用" % (ok, len(lst)))
    elif sub == "set":
        if len(args) < 2:
            sys.exit("用法: proxy set <url> | proxy set none")
        st["proxy"] = None if args[1].lower() in ("none", "-", "") else args[1]
        write_state(st)
        log("已记录代理：%s（下次启动生效：先 close，再执行任意命令会自动重启）"
            % (st["proxy"] or "直连"))
    else:
        sys.exit("用法: proxy check [url] | proxy list | proxy set <url|none>")


# ---------------------------------------------------------------- 双图层验证码（模板匹配）
LAYER_JS = r"""
(function(){
 var cands=[].slice.call(document.images).filter(function(i){
   var r=i.getBoundingClientRect();
   return r.width>50&&r.height>50&&i.complete&&i.naturalWidth>0;});
 var groups=[];
 cands.forEach(function(i){
   var r=i.getBoundingClientRect(), k=Math.round(r.left)+','+Math.round(r.top)+','+Math.round(r.width);
   var g=null;
   for(var j=0;j<groups.length;j++){ if(groups[j].k===k){g=groups[j];break;} }
   if(!g){ g={k:k,items:[]}; groups.push(g); }
   g.items.push({el:i,rect:[r.left,r.top,r.width,r.height],src:String(i.currentSrc||i.src).slice(0,80)});
 });
 var best=null;
 groups.forEach(function(g){ if(g.items.length>=2 && (!best||g.items.length>best.items.length)) best=g; });
 if(!best) return JSON.stringify({ok:false});
 window.__kbx_layers=best.items.map(function(it){ return it.el; });
 return JSON.stringify({ok:true,count:best.items.length,
   items:best.items.map(function(it){ return {rect:it.rect.map(function(v){return Math.round(v);}),src:it.src}; })});
})()
"""


def _dec(b):
    import numpy as np
    import cv2
    return cv2.imdecode(np.frombuffer(b, np.uint8), cv2.IMREAD_UNCHANGED)


def _ch3(x):
    import cv2
    if x.ndim == 2:
        return cv2.cvtColor(x, cv2.COLOR_GRAY2BGR)
    if x.shape[2] == 4:                     # 透明底合成到白底，避免模板带 alpha 干扰
        a = x[:, :, 3:4].astype("float32") / 255.0
        return (x[:, :, :3].astype("float32") * a + 255.0 * (1 - a)).astype("uint8")
    return x


def match_layers(bg_png, piece_png):
    """在「含缺口的底图」里模板匹配「拼图块」，返回横向位移与置信度。"""
    import numpy as np
    import cv2
    A, B = _dec(bg_png), _dec(piece_png)
    if A is None or B is None:
        return None
    A, B = _ch3(A), _ch3(B)
    if float(np.std(B)) < 5.0:              # 空白/纯色图层不能作模板（相关系数会退化成 1.0）
        return None
    if B.shape[0] >= A.shape[0] or B.shape[1] >= A.shape[1]:
        h, w = B.shape[:2]
        B = cv2.resize(B, (max(8, w // 3), max(8, h // 3)), interpolation=cv2.INTER_AREA)
    if B.shape[0] >= A.shape[0] or B.shape[1] >= A.shape[1]:
        return None
    res = cv2.matchTemplate(np.ascontiguousarray(A), np.ascontiguousarray(B), cv2.TM_CCOEFF_NORMED)
    _mn, mx, _ml, ml = cv2.minMaxLoc(res)
    return {"dx": float(ml[0]), "dy": float(ml[1]), "corr": round(float(mx), 3)}


def layer_capture(page):
    """逐个隐藏其它层，把同一区域每层单独截一张图（clip 以 CSS 像素为单位，scale=1）。
    用于「底图 + 拼图块」双图结构：坐标不在 DOM 里，但两层都在前端，可本地匹配求出。"""
    info = json.loads(evaluate(page, LAYER_JS))
    if not info.get("ok"):
        return None, info
    rect = info["items"][0]["rect"]
    shots = []
    try:
        for i in range(info["count"]):
            evaluate(page, "(function(){var L=window.__kbx_layers||[];"
                           "L.forEach(function(e,k){e.style.visibility=(k===%d)?'visible':'hidden';});return 1;})()" % i)
            res = page.call("Page.captureScreenshot", {"format": "png",
                "clip": {"x": rect[0], "y": rect[1], "width": rect[2], "height": rect[3], "scale": 1}}, timeout=30)
            shots.append(base64.b64decode(res["data"]))
    finally:
        try:
            evaluate(page, "(function(){var L=window.__kbx_layers||[];"
                           "L.forEach(function(e){e.style.visibility='';});return 1;})()")
        except Exception:
            pass
    return shots, info


def layer_gap(page):
    """双图层验证码求缺口位移：返回 {dist, corr, layer} 或 None。"""
    shots, info = layer_capture(page)
    if not shots or len(shots) < 2:
        return None
    best = None
    for a in range(len(shots)):
        for b in range(len(shots)):
            if a == b:
                continue
            m = match_layers(shots[a], shots[b])          # a=底图, b=块
            if m and (best is None or m["corr"] > best[3]["corr"]):
                best = (a, b, shots, m)
    if not best:
        return None
    a, b, _s, m = best
    log("图层匹配：层%d(底) × 层%d(块) → dx=%.1f dy=%.1f corr=%.3f" % (a, b, m["dx"], m["dy"], m["corr"]))
    return {"dist": m["dx"], "corr": m["corr"], "layer": a}


def restart(st):
    """强制重启浏览器（页面目标卡死后的恢复手段）。"""
    if st and st.get("pid"):
        try:
            os.kill(st["pid"], signal.SIGTERM)
        except Exception:
            pass
    time.sleep(0.8)
    try:
        os.remove(STATE)
    except Exception:
        pass
    return launch()


def open_session():
    """返回 (state, page)。若页面目标无响应（例如挂了未完成的导航），
    自动重启浏览器重试一次，避免一条命令因一次卡死而整体失败。"""
    page = None
    for attempt in (1, 2):
        st = ensure()
        try:
            page = connect(st)
            prepare(page, st)
            return st, page
        except Exception as e:
            try:
                if page:
                    page.close()
            except Exception:
                pass
            if attempt == 1:
                log("页面目标无响应（%s），自动重启浏览器重试…" % type(e).__name__)
                restart(st)
            else:
                raise


def main():
    argv = sys.argv[1:]
    if not argv:
        log(__doc__)
        return
    opts, pos = parse_args(argv)
    cmd = pos[0]
    args = pos[1:]
    global OPTS
    OPTS = opts
    if opts.get("proxy"):
        os.environ["CHS_PROXY"] = opts["proxy"]

    if cmd == "close":
        st = read_state()
        if st and st.get("pid"):
            try:
                os.kill(st["pid"], signal.SIGTERM)
            except Exception:
                pass
        try:
            os.remove(STATE)
        except Exception:
            pass
        log("CLOSED")
        return

    st, page = open_session()
    try:

        if cmd == "start":
            if args:
                st["url"] = navigate(page, args[0])
                write_state(st)
            log("STARTED pid=%s port=%s cloak_ip=%s proxy=%s"
                % (st["pid"], st["port"], (st.get("identity") or {}).get("ip"), st.get("proxy") or "(直连)"))
            if "shot" in opts or args:
                take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd in ("open", "goto"):
            if not args:
                sys.exit("用法: open <url>")
            st["url"] = navigate(page, args[0])
            write_state(st)
            log("URL: " + st["url"])
            log("UA: " + evaluate(page, "navigator.userAgent"))
            take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd == "shot":
            take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd == "click":
            if not args:
                sys.exit("用法: click <n|选择器>")
            d = action_click(page, args[0])
            log("CLICK: %s" % d.get("tag"))
            time.sleep(0.6)
            page.wait_event("Page.loadEventFired", timeout=1)
            if "no-shot" not in opts:
                take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd in ("type", "fill"):
            if len(args) < 2:
                sys.exit("用法: %s <n|选择器> <文本>" % cmd)
            action_type(page, args[0], args[1], clear=(cmd == "fill"))
            log("TYPED: %s" % args[1])
            if "no-shot" not in opts:
                time.sleep(0.3)
                take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd == "press":
            if not args:
                sys.exit("用法: press <键>")
            do_press(page, args[0])
            log("PRESS: %s" % args[0])
            time.sleep(0.4)
            page.wait_event("Page.loadEventFired", timeout=1)
            if "no-shot" not in opts:
                take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd == "scroll":
            if not args:
                sys.exit("用法: scroll <dy> [dx]")
            dy = int(args[0])
            dx = int(args[1]) if len(args) > 1 else 0
            action_scroll(page, dy, dx)
            log("SCROLL: dy=%d dx=%d" % (dy, dx))
            if "no-shot" not in opts:
                time.sleep(0.4)
                take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd in ("move", "click-at", "hover", "dblclick", "rclick", "mdown", "mup", "drag"):
            _mouse_cmd(page, st, cmd, args, opts)
            if "no-shot" not in opts:
                time.sleep(0.35)
                page.wait_event("Page.loadEventFired", timeout=1)
                take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd in ("verify", "solve", "slide"):
            _captcha_cmd(page, st, cmd, args, opts)
            if "no-shot" not in opts and cmd != "verify":
                take_shot(page, st, opts.get("out"), "full" in opts)

        elif cmd == "proxy":
            _proxy_cmd(st, opts, args)

        elif cmd == "wait":
            if not args:
                sys.exit("用法: wait <毫秒> | wait load [秒] | wait stable [秒] | wait sel <选择器> [秒] | wait text <文本> [秒]")
            mode = args[0]
            if mode.isdigit():
                time.sleep(int(mode) / 1000.0)
                log("WAITED: %sms" % mode)
            elif mode == "load":
                t = float(args[1]) if len(args) > 1 else 20.0
                ev = page.wait_event("Page.loadEventFired", timeout=t)
                log("LOADED" if ev else "加载未在 %.0fs 内完成" % t)
            elif mode in ("stable", "stab"):
                t = float(args[1]) if len(args) > 1 else 15.0
                log("STABLE 画面已稳定" if wait_stable(page, timeout=t) else "未在 %.0fs 内稳定" % t)
            elif mode == "sel":
                if len(args) < 2:
                    sys.exit("用法: wait sel <选择器> [秒]")
                t = float(args[2]) if len(args) > 2 else 15.0
                ok = wait_until(page, "!!document.querySelector(%s)" % json.dumps(args[1]), timeout=t)
                log("FOUND" if ok else "未在 %.0fs 内出现" % t)
            elif mode == "text":
                if len(args) < 2:
                    sys.exit("用法: wait text <文本> [秒]")
                t = float(args[2]) if len(args) > 2 else 15.0
                ok = wait_until(page, "document.body.innerText.indexOf(%s)>-1" % json.dumps(args[1]), timeout=t)
                log("FOUND" if ok else "未在 %.0fs 内出现" % t)
            else:
                sys.exit("未知等待模式: %s" % mode)

        elif cmd == "console":
            logs = json.loads(evaluate(
                page, "JSON.stringify((window.__kbx&&window.__kbx.logs)||[])"))
            if "clear" in opts:
                evaluate(page, "(window.__kbx&&(window.__kbx.logs=[]),1)")
            if not logs:
                log("(无控制台输出)")
            for e in logs:
                log("[%s] %s" % (e.get("level", "log"), e.get("text", "")))

        elif cmd == "eval":
            if not args:
                sys.exit("用法: eval <js>")
            v = evaluate(page, args[0])
            log(json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))

        elif cmd == "html":
            sel = args[0] if args else None
            if sel:
                expr = ("(()=>{const e=document.querySelector(%s);return e?e.outerHTML:'(未匹配)';})()"
                        % json.dumps(sel))
            else:
                expr = "document.documentElement?document.documentElement.outerHTML:''"
            h = evaluate(page, expr) or ""
            log(h[:20000] + ("\n...(已截断，共 %d 字符)" % len(h) if len(h) > 20000 else ""))

        elif cmd == "net":
            rows = json.loads(evaluate(page, (
                "JSON.stringify(performance.getEntriesByType('resource')"
                ".map(e=>({name:e.name,type:e.initiatorType,ms:Math.round(e.duration),"
                "kb:Math.round((e.transferSize||0)/1024)})))")))
            log("RESOURCES: %d" % len(rows))
            for r in rows:
                log("%5sms %6skb %-10s %s" % (r["ms"], r["kb"], r["type"], r["name"][:120]))

        elif cmd == "fetch":
            if not args:
                sys.exit("用法: fetch <url> [--method M] [--body B] [--header K:V ...]")
            headers = {}
            for h in as_list(opts.get("header")):
                if ":" in h:
                    k, v = h.split(":", 1)
                    headers[k.strip()] = v.strip()
            r = do_fetch(page, args[0], opts.get("method", "GET"), opts.get("body"), headers)
            if "error" in r:
                log("FETCH ERROR: " + r["error"])
            else:
                log("HTTP %s  %s  %dB" % (r["status"], r.get("ct", ""), r["len"]))
                body = r.get("body", "")
                log(body)
                if CHALLENGE_RE.search(body):
                    log("提示：响应疑似 JS 反爬挑战。对该 URL 执行 open 可完成挑战并写入 Cookie。")

        elif cmd == "cookies":
            page.call("Network.enable")
            cks = page.call("Network.getCookies", {}).get("cookies", [])
            log("COOKIES: %d" % len(cks))
            for c in cks:
                log("%s=%s  domain=%s path=%s%s" % (
                    c.get("name"), c.get("value"), c.get("domain"), c.get("path"),
                    " httpOnly" if c.get("httpOnly") else ""))

        elif cmd == "cookie":
            sub = args[0] if args else ""
            page.call("Network.enable")
            if sub == "set":
                if len(args) < 2 or "=" not in args[1]:
                    sys.exit("用法: cookie set name=value [--domain D] [--path P]")
                n, v = args[1].split("=", 1)
                dom = opts.get("domain") or evaluate(page, "location.hostname")
                ok = page.call("Network.setCookie", {
                    "name": n, "value": v, "domain": dom, "path": opts.get("path", "/")})
                log("COOKIE SET: %s=%s @%s -> %s" % (n, v, dom, ok.get("success", True)))
            elif sub == "clear":
                page.call("Network.clearBrowserCookies")
                log("COOKIES CLEARED")
            else:
                sys.exit("用法: cookie set name=value | cookie clear")

        elif cmd == "ua":
            page.call("Network.enable")
            if args:
                st["ua"] = args[0]
                write_state(st)
                page.call("Network.setUserAgentOverride", {"userAgent": args[0]})
                log("UA SET: " + args[0])
            else:
                log(evaluate(page, "navigator.userAgent"))

        elif cmd == "userscript":
            sub = args[0] if args else "list"
            if sub == "add":
                if len(args) < 2:
                    sys.exit("用法: userscript add <file.user.js>")
                name = os.path.basename(args[1])
                src = build_userscript(args[1])
                st.setdefault("userscripts", []).append({"name": name, "source": src})
                write_state(st)
                page.call("Page.addScriptToEvaluateOnNewDocument", {"source": src})
                evaluate(page, src, by_value=False)
                log("USERSCRIPT ADDED: %s（已注入当前页，并对后续导航生效）" % name)
            elif sub == "list":
                us = st.get("userscripts", [])
                log("USERSCRIPTS: %d" % len(us))
                for u in us:
                    log("- " + u["name"])
            elif sub == "clear":
                st["userscripts"] = []
                write_state(st)
                log("USERSCRIPTS CLEARED（重启浏览器后彻底生效）")
            else:
                sys.exit("用法: userscript add <file> | list | clear")

        elif cmd == "inject":
            if not args:
                sys.exit("用法: inject <file.js>")
            evaluate(page, read_file(args[0]), by_value=False)
            log("INJECTED: " + args[0])

        elif cmd == "cloak":
            sub = args[0] if args else ""
            if sub == "rotate":
                st["identity"] = random_identity()
                write_state(st)
                if [p for p in os.environ.get("CLOAK_PROXIES", "").split(",") if p.strip()]:
                    log("CLOAK_PROXIES 已配置，重启浏览器切换出口代理…")
                    try:
                        page.close()
                    except Exception:
                        pass
                    st = restart(st)
                    page = connect(st)
                    prepare(page, st)
                else:
                    prepare(page, st)
                i = st["identity"]
                log("CLOAK ROTATED: XFF=%s  tz=%s  platform=%s  proxy=%s"
                    % (i["ip"], i["timezone"], i["platform"], st.get("proxy") or "(直连)"))
            else:
                i = st.get("identity") or {}
                log("IP(伪装头) %s" % i.get("ip"))
                log("出口代理   %s" % (st.get("proxy") or "(直连，真实 IP 未改变)"))
                log("UA        %s" % i.get("ua"))
                log("TZ/LOCALE %s / %s" % (i.get("timezone"), i.get("locale")))
                log("CORES/MEM %s / %s" % (i.get("cores"), i.get("memory")))
                log("HEADERS   %s" % ", ".join((i.get("headers") or {}).keys()))

        elif cmd == "url":
            log(evaluate(page, "location.href"))

        elif cmd == "title":
            log(evaluate(page, "document.title"))

        elif cmd == "status":
            log("RUNNING pid=%s port=%s" % (st["pid"], st["port"]))
            log("CHROME %s" % st["chrome"])
            ident = st.get("identity") or {}
            log("CLOAK-IP %s   TZ %s   PROXY %s" % (ident.get("ip"), ident.get("timezone"), st.get("proxy") or "(直连)"))
            log("UA     %s" % ident.get("ua"))
            log("URL    %s" % evaluate(page, "location.href"))
            log("WEBDRIVER %s" % evaluate(page, "String(navigator.webdriver)"))
            log("USERSCRIPTS %d" % len(st.get("userscripts", [])))

        else:
            sys.exit("未知命令: " + cmd)
    finally:
        page.close()


if __name__ == "__main__":
    main()
