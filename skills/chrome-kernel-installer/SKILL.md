---
name: chrome-kernel-installer
description: 浏览器内核下载与操作一体化工具包。下载：并发分块安装 Chrome for Testing 内核（chrome-headless-shell / chrome），用于沙箱重建无头浏览器，也适用于任何大文件高速分块下载。操作：基于 CDP 驱动无头浏览器——输入网址即可返回带编号标注的网页截图，按编号点击、输入、按键、滚动，读取控制台/网络/DOM，注入油猴脚本，并能用页面内请求穿过 JS 反爬挑战取数据。当用户需要下载浏览器内核、打开网址查看页面、点击页面元素、填写表单、滚动网页、截图、注入 userscript、调用站点接口，或需要页面日志与结构时触发。不适用于纯文本检索（用 search/fetch），也不适用于需要图形化 DevTools 面板的场景。
---

# 浏览器内核下载与操作

技能分两层，可独立使用：

- **底层 · 内核获取**：并发分块下载 Chrome for Testing 内核并做完整性校验（单线程只有 ~70 KB/s，且沙箱单条命令限 60 秒，所以必须并发 + 后台跑）。
- **上层 · 浏览器驱动**：基于 CDP（Chrome DevTools Protocol）的无头浏览器控制器。核心交互是**「截图 → 看编号 → 选编号操作」**：输入网址返回一张把页面上所有可点元素/卡片都框起来并编号的图片，之后用编号完成点击、输入、按键、滚动。
- **内建反爬适配**：默认抹除自动化特征（真实 UA、`navigator.webdriver=false` 等），导航时自动识别并等待 `slowAES` 一类 JS 挑战完成，并可用页面内同源 `fetch` 直取被挑战保护的接口。

两层解耦：控制器会自动定位已安装的内核；没有内核时才需要跑下载脚本，且由使用者按需触发，不自动下载。

## 何时使用

- 要下载 / 重建无头 Chrome 内核，或需要高速分块下载任意大文件
- 要打开某个网址、看页面长什么样（返回真实渲染截图）
- 要在页面上点按钮、填表单、翻页、搜索（可用编号，也可用 CSS 选择器）
- 要读页面控制台、网络请求、DOM 结构，或注入油猴脚本
- 目标站点有反爬（JS 挑战、无头检测）时也用它——技能已内建规避与挑战自愈
- **不适用**：纯文本检索（用 `search`/`fetch`）；需要拖拽图形化 DevTools 面板的场景（无头环境只提供等价的数据能力）

---

## 第 0 步 · 确认内核

先看状态；控制器会自己找内核，找不到才提示下载：

```bash
python3 scripts/browser.py status      # 已运行时打印 pid/端口/当前 URL
ls /opt/chs/chrome-headless-shell-linux64/chrome-headless-shell   # 内核是否已装
```

内核缺失时才下载（**必须后台跑 + 轮询**，否则被 60 秒上限掐断）：

```bash
nohup bash scripts/install_chrome_kernel.sh headless > /tmp/dl.log 2>&1 &
for i in $(seq 1 8); do
  [ -x /opt/chs/chrome-headless-shell-linux64/chrome-headless-shell ] && { echo READY; break; }
  sleep 8
done
tail -3 /tmp/dl.log
```

`browser.py` 按此顺序找内核：`$CHROME_BIN` → `/opt/chs/chrome-headless-shell-linux64/chrome-headless-shell` → `/opt/chs/chrome-linux64/chrome` → 系统 `google-chrome`/`chromium`。也可用 `CHROME_BIN` 指定。

版本号**自动解析，四级回退**：官方 `last-known-good-versions.json` → 镜像同名元数据 → 镜像目录列表（取最新）→ 内置常量。一般无需手工干预；想先看会装哪个版本：

```bash
bash scripts/install_chrome_kernel.sh --print-version
```

只有四级全不可达时才需要 `CHROME_VERSION=<版本>` 手工指定。

---

## 第 1 步 · 打开网址，返回标注截图

```bash
python3 scripts/browser.py open https://example.com
```

输出：一张 PNG 的路径 + **分层编号清单**：

```
SHOT: /sandbox/workspace/.browser/shots/shot_20260917_201500.png
ELEMENTS: 82  (交互29 标题10 文字22 媒体3 结构18)
[1]  interactive link          a "首页"
[15] interactive button        button "登录"
[31] head        heading       h1 "组件大全"
[41] text        text          p "这是一段普通正文，用于验证「文字」层能否被识别并编号。"
[74] region      region        form "验证码登录密码登录…"
```

**拿到路径后，用 `provide_file` 把图片发给用户**——用户看不到沙箱文件，必须发出来他才能看到页面。

**五层识别，覆盖全部组件**（不再只认「可点元素」）：

| 层 | 识别范围 | 颜色 |
|---|---|---|
| `interactive` 交互 | a/button/input/select/textarea/label/option、任意 `[role]`/ARIA、`[onclick]`/`[tabindex]`/`[contenteditable]`、`cursor:pointer`、**`addEventListener` 绑定区域**（CDP `getEventListeners`）、**Web Components** | 红/橙/蓝/绿/青 |
| `head` 标题 | h1~h6、`[role=heading]` | 近黑 |
| `text` 文字 | p/span/div/li/td/th/dt/dd/blockquote/figcaption/pre/code/… 中带实际文字的语义块 | 灰 |
| `media` 媒体 | img/svg/canvas/video/audio/iframe/picture | 青 |
| `region` 结构容器 | header/nav/main/section/article/aside/footer/form/table/ul/ol/dl/figure/fieldset/details/dialog | 浅灰虚线 |

编号规则：**按层分段**（交互 → 标题 → 文字 → 媒体 → 结构），段内按视觉位置（上→下、左→右）；每层有**配额**，避免「交互」把名额吃光导致文字/标题被整段截断（`news.qq.com` 修前 600 项全是交互、文字 0，修后 76 项五层均衡）。同文本链只留最外层，父组件已编号则不重复标子组件。

**每一层都能按编号操作**——`click 41` 就是点那段文字，`hover 31` 就是悬停标题，`drag 72 …` 就是拖那张图。编号写回 `data-kbx-n` 并缓存 `window.__kbxNodes[n]`，所以 **Shadow DOM 内部的组件同样可按编号操作**。

页面太密时裁剪范围（详见下方命令速查），或 `--no-region` 去掉结构容器大框、`--max 1200` 放宽上限。

刻意排除：`html`/`body`/`script`/`style` 与整页级超大容器（很多站点把事件委托挂在其上，一旦入选会吞掉所有后代）。

导航类命令（`open` / `start <url>`）与所有操作类命令默认都会自动出图，形成「看一批 → 点一个 → 再看一批」的闭环。要静默可加 `--no-shot`。

---

## 第 2 步 · 按编号操作

```bash
python3 scripts/browser.py click 2              # 点击编号 2（默认自动重新截图）
python3 scripts/browser.py click "#login"       # 也可用 CSS 选择器
python3 scripts/browser.py type  3 "你好"        # 聚焦编号 3 并输入
python3 scripts/browser.py fill  3 "keyword"    # 先清空再输入
python3 scripts/browser.py press Enter          # 按键
python3 scripts/browser.py press Control+a      # 组合键（Alt/Ctrl/Meta/Shift）
python3 scripts/browser.py scroll 800           # 向下滚 800px（正数向下）
python3 scripts/browser.py scroll 0 -1200       # 横向滚动
python3 scripts/browser.py wait 1500            # 等待 1.5 秒（等动画/请求）
```

要点：

- **先 `shot` 再按编号操作**。页面变化后编号会重排，所以每次操作默认会自动补一张新图，照着最新图选号。
- **编号覆盖五层**：交互 / 标题 / 文字 / 媒体 / 结构容器都能用编号操作——想点某段文字、悬停某个标题、拖某张图，直接用它的编号即可；结构容器用虚线框标示，交互组件是实线框。
- `click` 用真实鼠标事件（mousePressed/mouseReleased），能触发前端框架的交互；坐标取自元素中心并自动 `scrollIntoView`，所以元素不在视口内也能点。
- `type` 用 `Input.insertText`，适合含中文的文本，会触发 `input` 事件；需要真实逐键行为时改 `press` 组合。
- 自定义控件（如自绘的协议勾选框）常常不在编号里，直接用 CSS 选择器点击更稳。

---

## 第 3 步 · 开发者工具能力

无头环境没有图形化 DevTools，但等价能力都在：

```bash
python3 scripts/browser.py console          # 控制台日志（含 warn/error 与未捕获异常）
python3 scripts/browser.py console --clear  # 读完后清空
python3 scripts/browser.py eval "document.querySelectorAll('.card').length"
python3 scripts/browser.py html "#main"     # 输出某元素 outerHTML（默认整页）
python3 scripts/browser.py net              # 已加载的网络资源及耗时/大小
python3 scripts/browser.py title            # 页面标题
python3 scripts/browser.py url              # 当前地址
```

控制台日志由预注入钩子在**页面自身脚本执行前**挂钩，所以导航后立刻打印的日志也能捕获（挂在 `window.__kbx.logs`，滚动保留最近 800 条）；且每次连接都会把钩子补注入当前文档，页面自行重载后仍可用。

---

## 第 4 步 · 注入油猴脚本

支持标准 userscript（`.user.js`）：自动剥离 `// ==UserScript== … // ==/UserScript==` 头，正文注入并**对后续每次导航持续生效**。

```bash
python3 scripts/browser.py userscript add my.user.js   # 注入并持久化（立即对当前页生效）
python3 scripts/browser.py userscript list             # 列出已注入
python3 scripts/browser.py userscript clear            # 清空
python3 scripts/browser.py inject once.js              # 只注入当前页，不持久化
```

- 持久化的脚本记录在浏览器状态里；浏览器重启后由 `prepare()` 自动重挂，且每次连接会补注入当前文档（带文件名去重守卫，不会重复执行）。
- `inject` 适合一次性调试片段；`userscript add` 适合需要每次刷新都运行的脚本。

---

## 第 5 步 · 直取接口与 Cookie（应对反爬）

被 JS 挑战保护的站点，只有页面自身的请求才带得上挑战 Cookie。用页面内同源请求取数据：

```bash
python3 scripts/browser.py fetch "/api/list"                          # 页面内 GET（自动带 Cookie）
python3 scripts/browser.py fetch "/api/x" --method POST --body '{}' --header "Content-Type: application/json"
python3 scripts/browser.py fetch "/api/me" --header "Authorization: Bearer <token>"
python3 scripts/browser.py cookies                                    # 列出 Cookie（含挑战 Cookie）
python3 scripts/browser.py cookie set __test=xxxx                     # 手工补写 Cookie
python3 scripts/browser.py cookie clear                               # 清空（可复现挑战）
python3 scripts/browser.py ua                                          # 查看当前 UA
```

要点：

- `fetch` 在**页面上下文**里发请求，天然带上该站 Cookie 与来源，能穿过大多数 JS 挑战；若响应正文命中挑战特征，会提示你改用 `open` 触发解题。
- 挑战 Cookie 存在持久 profile（`/tmp/chrome-browser/profile`）里，**solve 一次、后续命令复用**。
- 若接口返回 `401`，多半是缺少应用自身的鉴权头（如 `Authorization: Bearer <token>`）：令牌常在 `localStorage`，用 `eval "localStorage.getItem('<key>')"` 取出后经 `--header` 带上。
- UI 渲染为空但接口可用时，直接走接口拿数据，别死磕页面（实例：`site.php` 被主机拦截 → 应用初始化中断，但 `works.php` 正常）。

## 反爬机制说明（为什么这样设计）

- **降低被挑战概率**：启动即关闭自动化特征——`--disable-blink-features=AutomationControlled`，UA 覆写为与内核版本一致的真实 Chrome UA，再由 `hook.js` 抹平 `navigator.webdriver` / `plugins` / `languages` / `window.chrome`。
- **挑战自愈**：`open` 导航后检测页面是否为挑战页（特征 `slowAES` / `aes.js` / `document.cookie="__test=…"` / `.decrypt(`，且页面极短），命中就等其自动 `location.href` 跳转，必要时 `reload` 一次。多数情况下 `aes.js` 在首帧内就完成自跳，表现为**透明通过**（Cookie 已写入、正文已是真实内容），无需人工干预。
- **钩子与脚本跨刷新存活**：CDP 的 `addScriptToEvaluateOnNewDocument` 随会话结束而失效，所以每次连接都会把 `hook.js` 与油猴脚本**补注入当前文档**（各自带幂等守卫），页面自行整页重载后依然有效。

---

## 第 6 步 · 等待加载：秒数 或 画面稳定

异步渲染（SPA / 懒加载 / 动画）常导致「截图太早、内容还没出来」。两种等待方式，可叠加：

```bash
python3 scripts/browser.py open https://spa.example/ --wait 2      # 固定等 2 秒再出图
python3 scripts/browser.py open https://spa.example/ --stable       # 截图识别：等画面不再变化
python3 scripts/browser.py click 5 --stable                         # 点击后等同法稳定再出图
```

独立等待命令（可单独调用，各带超时）：

```bash
python3 scripts/browser.py wait 1500                  # 等 1.5 秒
python3 scripts/browser.py wait load 10               # 等 load 完成，最多 10 秒
python3 scripts/browser.py wait stable 15             # 等画面稳定，最多 15 秒
python3 scripts/browser.py wait sel "#list .item" 10  # 等某元素出现
python3 scripts/browser.py wait text "加载完成" 10      # 等某文本出现
```

「画面稳定」的实现：连续截图（低质量 JPEG）比对，**连续两次完全一致**即判定稳定——天然覆盖懒加载、骨架屏消失、动画结束等场景；页面若一直变化（轮播/闪烁光标），会到超时才返回。

若页面只是**持续微动**（整屏轻微渐变、闪烁光标），逐字节永远不相等，此时用 `--stable-tol 8`（允许整幅最大灰度差 ≤8，降采样后比对）：

```bash
python3 scripts/browser.py shot --stable-tol 8     # 微动页也能判定稳定
```

## 第 7 步 · 伪装身份与出口代理

```bash
python3 scripts/browser.py cloak                                       # 查看当前伪装（IP 头 / UA / 时区 / 指纹 / 代理）
python3 scripts/browser.py cloak rotate                                # 换一套
python3 scripts/browser.py start --proxy http://host:port              # 指定出口代理
CLOAK_PROXIES="http://a:1,http://b:2" python3 scripts/browser.py start  # 代理池随机取，rotate 时切换
```

- 默认自动伪装：真实版本号 UA、`X-Forwarded-For`/`X-Real-IP` 等代理头、时区、语言、CPU 核数、内存、WebGL 厂商/渲染器。
- **重要边界**：代理头只影响「信任它」的站点的地域/限流判断，**并不改变 TCP 真实源 IP**；按真实 IP 判定的人机验证（如百度滑块）仍会触发。要真正更换出口 IP，必须提供**代理**。
- 真实出口可用 `proxy check` 核对（直连 vs 代理各测一次，返回真实出口 IP，不靠猜）：

```bash
python3 scripts/browser.py proxy check                 # 当前代理 + 直连，各报真实出口 IP
python3 scripts/browser.py proxy list                  # CLOAK_PROXIES 全量测活
CLOAK_CHECK=1 CLOAK_PROXIES="http://a:1,http://b:2" python3 scripts/browser.py start   # 自动跳过坏代理
```

---

## 第 8 步 · 精密鼠标操作

所有鼠标事件走 `Input.dispatchMouseEvent`，坐标是**视口 CSS 像素**（与 `getBoundingClientRect` 一致，不是设备像素）。默认多步插值成类人轨迹，不做瞬移。

| 命令 | 说明 |
|---|---|
| `move <x> <y> [--steps N] [--jitter PX]` | 精密移动；`--steps` 越大越细腻，`--jitter` 加垂直抖动 |
| `click-at <x> <y> [--button left\|right\|middle] [--count N]` | 按坐标点击（精密定位，绕开选择器） |
| `hover <n\|选择器> [--ms N]` | 悬停到元素中心并停留 N 毫秒（触发 mouseenter / 悬浮菜单） |
| `dblclick` / `rclick <n\|选择器>` | 双击 / 右键 |
| `mdown <目标>` / `mup [目标]` | 按下 / 抬起——手工分步拖拽（跨命令保持按下态） |
| `drag <目标> <dx> <dy> [--steps N] [--jitter PX]` | 移到目标 → 按下 → 插值到 (dx,dy) → 松开 |

鼠标位置记在 state 里，`mdown` 后可接任意多次 `move` 再 `mup`，实现任意曲线拖拽。

```bash
python3 scripts/browser.py move 640 360 --steps 40
python3 scripts/browser.py hover 12 --ms 800
python3 scripts/browser.py drag 7 240 30 --jitter 2
python3 scripts/browser.py mdown 7 && python3 scripts/browser.py move 900 400 && python3 scripts/browser.py mup
```

## 第 9 步 · 人机验证识别与一键过滑块

```bash
python3 scripts/browser.py verify        # 识别验证组件 + 判定位置信息是否在前端
python3 scripts/browser.py solve  [--retry N] [--mode auto|dark|edge] [--duration MS] [--y-jitter PX]
python3 scripts/browser.py slide  <距离px> [--duration MS] [--y-jitter PX] [--overshoot 比例]
```

`verify` 不靠猜：列出验证组件（位置/尺寸/是否 iframe）+ 前端脚本线索，并**实测各图层活跃度**后给判定。实测百度安全验证：

```
  img 350x350  https://passport.baidu.com/cap/img?ak=...&id=...
  img 458x459  data:image/png;base64,iVBOR...
图层活跃度 std：[75.7, 0.0]
判定：多图层但仅一层有内容 → 位置由服务端渲染进图片，前端不含坐标，须图像识别
```

`solve` 的定位策略**逐级降级，不硬猜**：

1. **双图层模板匹配**：多层重叠图片 → 逐个隐藏其它层分别截图，`cv2.matchTemplate` 求位移（适用于「底图 + 拼图块」结构；坐标不在 DOM，但两层都在前端）。纯色/空白层会被判为无效模板而跳过。
2. **连通域找缺口**：单图 + 暗色凹槽 → 取面积最大的近方形暗块（形状 + 尺寸双约束，细长暗区/超过半幅的暗块都排除）。
3. **列统计回退**：暗带（`--mode dark`）/ 竖直边缘（`--mode edge`）。

置信度不足时**直接报错并给出手工方案**，绝不盲拖。滑动本身是类人的：随机时长、正弦速度剖面、上下随机抖动、1~2 次微停顿、末端过冲后回冲修正。

```bash
python3 scripts/browser.py solve --retry 2                        # 失败自动重新定位重试
python3 scripts/browser.py solve --mode edge                      # 缺口偏亮时改边缘法
python3 scripts/browser.py drag ".slider-btn" 160 0 --jitter 2    # 定位失败时手工拖
```

**如实说明**：`solve` 只解决「客户端可判定」的滑块。若答案被服务端渲染进图片（百度安全验证即如此：另一层 base64 图 std=0，是空白的），或站点对轨迹做服务端风控，本地无法保证通过——此时 `verify` 会明确写「前端不含坐标」，请改用 `shot` 看编号后 `drag` 人工介入。

---

## 典型工作流

**场景 A · 搜索并读取结果**（截图 → 点编号 → 输入 → 回车 → 再截图）

```bash
python3 scripts/browser.py open https://example.com       # 出图，找到搜索框编号（假设是 3）
python3 scripts/browser.py type 3 "关键词"                 # 出图，确认输入框已填
python3 scripts/browser.py press Enter                    # 出图，显示搜索结果
python3 scripts/browser.py html ".results"                # 需要结构化数据时直接取 DOM
```

**场景 B · 注入脚本后验证**

```bash
python3 scripts/browser.py open https://example.com
python3 scripts/browser.py userscript add clean.user.js   # 例如去掉遮挡广告
python3 scripts/browser.py shot                           # 对比注入前后截图
python3 scripts/browser.py console                        # 看脚本有没有报错
python3 scripts/browser.py close                          # 用完关闭，释放进程
```

**场景 C · 登录后用接口取数据（站点有反爬）**

```bash
python3 scripts/browser.py open https://site.example/            # 让浏览器完成 JS 挑战、写入 Cookie
python3 scripts/browser.py click ".tab[data-tab=mine]"           # 进账号页
python3 scripts/browser.py click "#submitBtn"                    # 提交登录（编号或选择器均可）
TOKEN=$(python3 scripts/browser.py eval "localStorage.getItem('token')||''")
python3 scripts/browser.py fetch "/api/list" --header "Authorization: Bearer $TOKEN" | head -c 400
```

---

## 命令速查

| 命令 | 作用 |
|---|---|
| `start [url]` | 启动/复用浏览器，可选打开网址并出图 |
| `open <url>` / `goto` | 打开网址（自动标注截图） |
| `shot [--full] [--out P] [--only 类型] [--no-region]` | 分层标注截图；`--full` 整页，`--only` 只要某几层 |
| `click <n\|选择器> [--no-shot]` | 点击 |
| `type <n\|选择器> <文本>` / `fill` | 输入 / 清空后输入 |
| `press <键>` | 按键，如 `Enter`、`Control+a`、`ArrowDown` |
| `scroll <dy> [dx]` | 滚动 |
| `wait <ms>` | 固定等待毫秒 |
| `wait load [秒]` / `wait stable [秒]` | 等页面加载完成 / **截图识别**等画面稳定 |
| `wait sel <选择器> [秒]` / `wait text <文本> [秒]` | 等元素出现 / 等文本出现 |
| `--wait N` / `--stable [--stable-tol P]` | 出图前统一等待：固定 N 秒 / 直到画面稳定（P 为像素容差） |
| `move` / `click-at` / `hover` / `dblclick` / `rclick` / `mdown` / `mup` / `drag` | 精密鼠标操作集（视口 CSS 像素，多步类人轨迹） |
| `verify` / `solve` / `slide` | 识别验证组件并判定位置来源 / 一键过滑块 / 单独执行类人滑动 |
| `proxy check\|list\|set` | 出口代理健康检查（真实出口 IP）/ 批量测活 / 记录代理 |
| `console [--clear]` | 控制台日志 |
| `eval <js>` / `html [选择器]` / `net` | 执行 JS / 取 DOM / 网络资源 |
| `fetch <url> [--method M] [--body B] [--header K:V]` | 页面内同源请求（自动带 Cookie） |
| `cookies` / `cookie set\|clear` / `ua [串]` | Cookie 与 UA 查看 / 设置 |
| `cloak` / `--proxy <url>` | 伪装身份查看/轮换；出口代理（或 `CLOAK_PROXIES=a,b`） |
| `userscript add\|list\|clear` / `inject <file>` | 油猴脚本 / 一次性注入 |
| `url` / `title` / `status` / `close` | 地址 / 标题 / 状态 / 关闭 |

状态存在 `/tmp/chrome-browser/state.json`；截图在 `/sandbox/workspace/.browser/shots/`。命令之间状态不丢，因此可以像人一样连续操作。

---

## 内核下载铁律（用到底层时）

1. 版本号从 `last-known-good-versions.json` 取 Stable，不要写死
2. 必须 `curl -sL`（镜像会 302，漏 `-L` 只拿到 125 字节错误页）
3. 合并必须数字序：`sort -z -V`，`cat part_*` 是字母序会拼坏 zip
4. 分块前必须按范围探测 64KB 实际字节数（响应被压缩会导致校验通过但文件损坏）
5. 合并后必须 `zipfile.testzip()` 且大小等于探测长度
6. 并发压到 8–12；命令必须 `nohup ... &` 后台跑再轮询

---

## 故障速查

| 现象 | 原因 | 处理 |
|---|---|---|
| `未找到 Chrome 内核` | 未安装 | 跑 `install_chrome_kernel.sh`（后台） |
| 启动后立即退出 | 内核不完整 | 重下并校验 zip |
| 版本号取不到 | 元数据站点不可达 | 已自动四级回退；全挂时才 `CHROME_VERSION=<版本>` |
| `未找到元素：N` | 编号过期 | 重新 `shot` 再选号 |
| 点击无效 | 元素被覆盖 / 需先滚动 | 先 `scroll` 或改用 CSS 选择器 |
| 自定义组件/Shadow DOM 点不动 | 已支持（含 Shadow 内部）；仍无效 | 用 `eval` 直接派发：`window.__kbxNodes[n].click()` |
| 提交报「请先勾选同意」 | 自定义协议控件非标准 checkbox | 用选择器点它（如 `click "#agreeBox"`） |
| 控制台为空 | 页面在命令之外自刷新 | 钩子会补注入当前文档，重读即可；更早日志无法追回 |
| 截图整页超长 | 页面很长 | 已上限 20000px，必要时用视口截图 |
| 下载卡住 | 并发过高被限流 | 降到 8–12 |
| 大小校验通过但 zip 损坏 | 响应被压缩、分块切错 | 保留 64KB 探测步骤 |
| 接口返回挑战 HTML | 站点 JS 反爬 | 用 `fetch`（页面内）或先 `open` 该地址拿 Cookie |
| 接口 401 | 缺应用鉴权头 | `--header "Authorization: Bearer <token>"` |
| 无头被识别为机器人 | 自动化特征 | 已默认规避；必要时 `userscript` 注入自定义伪装 |
| 页面目标卡死（`Page.enable` 超时） | 多为挂了未完成的导航 | 控制器已**自动重启并重试一次**；仍失败再手动 `close` |
| 站点不可达 / 极慢 | 网络不通（如境外站点） | 20s 后**自动停止加载并告警**，不会卡死；换站点或重试 |
| 搜索被弹「安全验证」 | 站点对机房 IP 出验证码 | 交互本身没问题（已提交），换站点或人工过验证 |
| 微动页面 `--stable` 永不稳定 | 逐字节比对被微小差异破坏 | 改用 `--stable-tol 8` |
| `solve` 报「定位置信度不足」 | 缺口非暗块 / 图源不可判别 | 换 `--mode edge`；或用 `shot` 看编号后 `drag` 手工拖 |
| `verify` 说「前端不含坐标」 | 答案由服务端渲染进图片 | 本地无法求位置，属站点设计；只能人工或图像识别 |
| `drag` 拖了但元素没动 | 目标未按下 / 落在覆盖层上 | 用 `mdown`→`move`→`mup` 分步；或先 `hover` 确认命中 |
| `proxy check` 显示出口 IP 没变 | 只加了伪装头，没走代理 | 必须 `--proxy` / `CHS_PROXY` / `CLOAK_PROXIES` 才是真换 IP |

> 深入协议细节、按 CDP 域扩展命令、反爬处理见 `references/cdp.md`。
