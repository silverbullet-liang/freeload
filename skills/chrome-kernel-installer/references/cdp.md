# CDP 控制器参考

控制器 `scripts/browser.py` 只用 Python 标准库 + `websocket-client`，无其他依赖。本文说明其内部机制，便于排障与按需扩展。

## 架构：常驻进程 + 短连接

```
install_chrome_kernel.sh        并发分块下载内核 -> /opt/chs
        |
browser.py  launch()            以 --remote-debugging-port 启动内核，写 state.json
        |
browser.py  每次调用            读 state -> websocket 连页面目标 -> 发 CDP 命令 -> 断开
```

- 状态文件 `/tmp/chrome-browser/state.json`：`pid / port / chrome / page_ws / url / userscripts`
- 页面目标 ws 地址每次调用时从 `GET /json/list` 重新获取，避免目标变化后失效
- 浏览器进程用 `start_new_session=True` 独立于 CLI，因此 `close` 之前一直存活

## 预注入钩子（hook.js）

每次连接执行 `prepare()`，做三件事：

1. `Page.enable` / `Runtime.enable` / `Log.enable`
2. `Page.addScriptToEvaluateOnNewDocument(hook.js)` —— 捕获控制台与错误
3. 对每个已保存的油猴脚本再注册一次

`addScriptToEvaluateOnNewDocument` 绑定在目标上，**对之后每次导航都在页面脚本之前执行**，这正是能抓到页面首屏日志、以及让油猴脚本生效的原因。钩子用 `window.__kbx.hooked` 防重复。

> 注意：脚本注册是每次连接重新做的。若某命令连接后没有导航，重复注册不会重复执行（只在新文档生效），不会有副作用。

## 组件识别与标注（annotate.js）

`Runtime.evaluate(includeCommandLineAPI=true)` 执行，返回 JSON。流程：清理上次标注 → 收集候选 → 过滤可见性 → 按文档流排序 → 叠加边框/徽标 → 记录编号。

识别范围（**全部组件类型，含自定义**）：

- 标准交互标签：`a/area/button/input/select/textarea/summary/details/label/option/output/progress/meter`
- ARIA：任意 `[role]`、`[aria-haspopup]`、`[aria-expanded]`、`[aria-controls]`
- 属性式：`[onclick]`、`[onmousedown]`、`[onpointerdown]`、`[tabindex]`、`[contenteditable]`、`[draggable]`、`[data-action]`
- 自定义元素：标签含 `-`（Web Components）
- **JS 监听元素**：借命令行 API `getEventListeners(el)` 找 `click/mousedown/pointerdown/touchstart`（`includeCommandLineAPI` 就是为此）
- `cursor:pointer` 区域
- **递归穿透 Shadow DOM**：收集所有 shadowRoot 并在其中同样识别

去噪规则：同树内若已选中祖先则跳过；但 `html`/`body` 与面积 > 60% 视口的超大容器不参与去重（否则站点把事件委托挂在顶层时会误杀全部后代）。

编号与取用：按 `top,left` 排序编号；`el.setAttribute('data-kbx-n', n)` 并 `window.__kbxNodes[n]=el`。`click/type` 走 `window.__kbxNodes[n]`，因此**跨 Shadow DOM 也能取到元素**；`kind` 字段标明类型（`link/button/field/role:x/custom:x/clickable`），边框颜色按 kind 区分。

预算（防大页面卡死）：扫描元素 ≤6000、`getEventListeners` 调用 ≤800、标注 ≤300。

## 用到的 CDP 域

| 能力 | CDP 方法 |
|---|---|
| 导航 | `Page.navigate` + 等 `Page.loadEventFired` |
| 截图 | `Page.captureScreenshot`（整页用 `Page.getLayoutMetrics` 取 `cssContentSize` 后 `captureBeyondViewport`） |
| 执行 JS | `Runtime.evaluate`（`returnByValue` + `awaitPromise`） |
| 控制台 | `Runtime.enable` + `hook.js` 缓冲，`Log.enable` 兜底 |
| 鼠标 | `Input.dispatchMouseEvent`（`mouseMoved`/`mousePressed`/`mouseReleased`/`mouseWheel`） |
| 键盘 | `Input.dispatchKeyEvent`（`keyDown`/`keyUp`，带 `windowsVirtualKeyCode` 与 `modifiers`） |
| 文本输入 | `Input.insertText`（支持中文，触发 `input` 事件） |
| 预注入 | `Page.addScriptToEvaluateOnNewDocument` |

## 键位映射

- 特殊键表：`Enter/Tab/Escape/Backspace/Delete/Arrow*/Home/End/PageUp/PageDown/Space`
- 单字符：字母 → `KeyX`，数字 → `DigitN`，其余按码位
- 组合键：`Alt=1, Ctrl=2, Meta=4, Shift=8`，如 `Control+Shift+k`

## 油猴脚本处理

`userscript add <file>` 会先剥离元数据块：

```
// ==UserScript==   ...   // ==/UserScript==
```

然后把正文包进 `try/catch` 并在 `userscript add` 时立即对当前页 `Runtime.evaluate` 一次，同时登记到 state，之后每次导航由 `prepare()` 自动重挂。

`@match` / `@grant` 等未做语义解析——脚本会对所有页面生效。需要限定站点时，在脚本正文里自行判断 `location.host`。

## 扩展新命令

1. 在 `main()` 的分派链加一个 `elif cmd == "...":` 分支
2. 需要新 CDP 方法时，直接在分支里 `page.call("Domain.method", {...})`
3. 需要新的页面侧逻辑时，写成 `scripts/*.js` 用 `evaluate(page, read_file(...))` 执行（避免在 Python 里堆转义）

## 反爬与 JS 挑战（实战要点）

1. **降低被挑战概率**：启动加 `--disable-blink-features=AutomationControlled`；UA 在 `prepare()` 里用 `Network.setUserAgentOverride` 覆写成与内核版本一致的真实 Chrome UA（版本号取自 `/json/version` 的 `Browser` 字段）；`hook.js` 在文档最前抹平 `navigator.webdriver/plugins/languages` 与 `window.chrome`。
2. **识别挑战页**：`CHALLENGE_RE` 匹配 `slowAES` / `aes.js` / `document.cookie="__test=…"` / `.decrypt(`，且页面极短（< 8KB）才判定，避免误伤正常页面。`navigate()` 命中后等一次 `Page.loadEventFired`（挑战脚本会 `location.href` 自跳），仍命中则 `Page.reload` 一次。
3. **挑战 Cookie 复用**：`__test` 落在持久 profile，每个命令连接同一浏览器，因此 solve 一次即可后续复用；`cookie clear` 可用于主动复现挑战。
4. **接口取数**：挑战保护的接口用页面内 `fetch`（`credentials:'include'`）才带得上 Cookie；若还返回 401，说明缺应用自身鉴权头（多为 `Authorization: Bearer <token>`，令牌取自 `localStorage`）。
5. **不要用 curl 硬扛**：这类主机会对脚本 UA/无 Cookie 请求持续返回挑战页甚至直接断 TLS（`unexpected eof`），直接交给浏览器即可。

## 等待：秒数 / 条件 / 视觉稳定

- `wait_stable(page, timeout, interval, need)`：连续 `Page.captureScreenshot(format=jpeg, quality=35)`，base64 **全等**则计入 hits，连中 `need`（默认 2）次即判定稳定。用「字节全等」而非像素阈值：渲染是确定性的，静态画面逐字节一致，零依赖、无阈值调参。
- `wait_until(page, expr, timeout)`：轮询 `Runtime.evaluate(expr)` 直到为真（`wait sel` / `wait text` 用它）。
- `settle(page, opts)`：出图前统一处理 `--stable` / `--wait N`；由 `take_shot()` 调用（选项经全局 `OPTS` 传入），因此**任意出图命令**都能附加这两个选项。

## 伪装身份与代理

- `random_identity()` 生成一套身份：真实版本号 UA、随机公网 IP 写入 `X-Forwarded-For`/`X-Real-IP`/`X-Client-IP`/`Client-IP`/`True-Client-IP`/`Forwarded`、随机时区、cores/memory、WebGL 厂商与渲染器。
- `prepare()` 每次连接下发：`Network.setExtraHTTPHeaders`、`Network.setUserAgentOverride`、`Emulation.setTimezoneOverride`、`Emulation.setLocaleOverride`；并注册 `identity_script()`（改 `navigator.platform/hardwareConcurrency/deviceMemory/languages` 与 WebGL `getParameter`）。
- 代理优先级：`--proxy` → `CHS_PROXY` → `CLOAK_PROXIES`（随机一个）；经启动参数 `--proxy-server=` 生效，`cloak rotate` 在配置了代理池时会重启以切换。
- **边界**：代理头不改变 TCP 源 IP；真实换 IP 必须走代理。

## 精密鼠标与坐标系

- 全部走 `Input.dispatchMouseEvent`：`mouseMoved` / `mousePressed` / `mouseReleased` / `mouseWheel`。
- **坐标是视口 CSS 像素**（`getBoundingClientRect` 口径），不是截图的设备像素；有 dpr 时必须换算。
- `mousePressed` 要带 `buttons` 位掩码（左 1 / 右 2 / 中 4），`mouseReleased` 的 `buttons` 必须为 0，否则部分组件不认。
- 双击 = 同点两次 press/release 且第二次 `clickCount:2`（`mouse_button(count=2)` 已处理）。
- 拖拽中每一步 `mouseMoved` 都要带 `button:"left"` + `buttons:1`，否则页面视为已松开。
- `glide()`：smoothstep 插值 + `jitter`（`sin(πt)` 包络 → 两端小、中间大）；默认步数 `min(28, dist/14+3)`。
- 鼠标位置存 state（`st["mouse"]`），跨命令保持；`mdown` → 多次 `move` → `mup` 可实现任意曲线拖拽。
- 悬停必须「先 `mouseMoved` 到目标再 sleep」；只 sleep 不会触发 `mouseenter`。

## 人机验证：识别、缺口定位、类人滑动

- **组件识别**（`CAPTCHA_SELS` + 结构启发式）：覆盖阿里 `nc_` / 极验 `geetest_` / 易盾 `yidun_` / 百度 `passMod_`，以及通用 `[class*=captcha|slider|vcode]`、`[id*=...]`、相关 iframe。
  「滑块把手」启发式只在**内容稀疏页面**（`innerText < 4000`）启用，且要求父容器 `overflow:hidden`、把手近正方、父宽 2.2~700px —— 否则大站点刷出大量假阳性（实测百度搜索页从 34 个降到 0）。
- **轨道定位**（`find_track`）不靠类名猜：从把手沿 DOM 向上找第一个「高 ≤70 且宽 ≥2.2×把手」的祖先。百度 `passMod_slide-control`(290×53)、自建 `.slider-track`(320×44) 均命中。
- **缺口定位三条路**：
  1. `layer_capture`：同一 rect 的多张图逐个 `visibility:hidden` 单独截图（`clip` 用 CSS 像素、`scale=1`），再 `matchTemplate(TM_CCOEFF_NORMED)`。**必须排除近纯色模板**（`std<5` 会让相关系数退化成 1.0 —— 实测百度另一层 `std=0` 全白）。
  2. `_blob_gap`：`cv2.connectedComponentsWithStats`，取面积最大且 `0.6 ≤ 宽高比 ≤ 1.7`、宽 ≤ 半幅的连通域（细长暗区、大面积背景都不算缺口）。
  3. `_col_gap`：列向暗像素数 / 竖直梯度；`score = 峰值/均值` 作分离度。
  置信度不足直接报错（`col` 需 `score ≥ 1.35`），**不盲拖**。
- **类人滑动**（`human_track` + `human_slide`）：`sin(πt)^0.85` 速度剖面累积成位移（两端慢中间快）；随机时长（`dist/210 + 0.18~0.55`，夹 0.55~1.7s）、每步 sleep ×0.6~1.6、随机 0~2 次 50~160ms 微停顿、按概率末端过冲 0.4%~2% 再回冲、按下前犹豫 0.12~0.34s、松手前停顿 0.15~0.5s、上下抖动默认 0.5~2.6px。
- **成功判定**：`captcha_scan` 复检，只要还剩 `sel/cls/id` 含 `slide` 的候选就算未通过。注意服务端类名是 `passMod_slide-btn`——写成 `slider` 会漏判出**假通过**（已踩）。
- **服务端渲染的答案**：百度安全验证把缺口画进服务端生成的 `cap/img`，DOM 无坐标、另一层是空图 → 本地无解。`verify` 用「各图层 std」给出实测判定，不靠结构猜。

## 代理测活

- `probe_proxy(proxy)`：`build_opener(ProxyHandler({...}))` 依次请求 `ip-api.com/json` → `api.ipify.org` → `ifconfig.me/ip`，正则取 `query`/`ip`，返回真实出口 IP、耗时、来源域名。
- `proxy=None` 时用空 `ProxyHandler({})` **显式直连**，避免环境变量干扰对照 —— 这是「证明真换 IP 没有」的关键。
- `CLOAK_CHECK=1` 时 `pick_proxy` 逐个测活再随机取；全挂则回退直连并告警。
- `ensure()` 重启用 `st["proxy"]`，所以 `proxy set` 在 `close` 后生效。

## 组件识别分层（annotate.js）

- 五层：`interactive` / `head` / `text` / `media` / `region`；分层采集、**按层分段编号**，段内按 `getBoundingClientRect` 视觉位置排序。
- **分层配额**（`CAP = {interactive:360, head:80, text:240, media:90, region:70}`）：不设配额时某一层会吃光总名额 —— 实测 `news.qq.com` 修前 600 项全是交互、文字/标题 0；修后 76 项五层均衡。`--max` 会按比例缩放配额。
- **祖先去重必须对交互层也生效**：`hasPickedAncestor()` 跳过「祖先已入选且祖先不是整页级超大容器」的后代，否则嵌套的 `cursor:pointer` / 监听元素会成百上千地涌入。
- **文字层的两条关键规则**：
  1. 父级也是文字候选（`TEXT_TAGS`）且文本相同 → 只留最外层（`h1 > span` 留 h1、`td > b` 留 td）。**父级不在 `TEXT_TAGS` 时不能合并**，否则 `footer > p` 这类会被双双漏掉（已踩）。
  2. 内部已有编号组件时，只有「自身直接文字 `directText` 长度 < 2」才跳过（纯按钮外壳）；**段落里含行内链接仍要编号**，否则整段文字被吞（已踩）。
- `region` 只标「内部含已编号内容」的容器，避免整页大框刷屏；`--no-region` 可整体关闭。
- `data-kbx-m` 是采集期的临时标记（用于同一次运行内判断「内部已有编号」），收尾时统一清除。
- 覆盖验收：`demo/all_types.html` 含 60 个样本（含 Shadow DOM 内的 h4/p/button），`covered 60/60`。

## 沙箱注意

- 无头内核启动参数已带 `--no-sandbox --disable-gpu --disable-dev-shm-usage`（root + 小 `/dev/shm` 必需）
- `/tmp/chrome-browser` 可能被回收；截图默认落 `/sandbox/workspace/.browser/shots/` 以持久化
- 单条命令限 60 秒：导航类命令已把等待上限设到 20 秒，超时即 `Page.stopLoading` 中止（站点不可达时不会卡住页面目标）；超长页面用视口截图而非整页
- **会话自愈**：`open_session()` 在 `connect/prepare` 抛错时（常见于挂了未完成导航导致的 `Page.enable` 超时），会自动重启浏览器并重试一次，单条命令不会因一次卡死而失败
