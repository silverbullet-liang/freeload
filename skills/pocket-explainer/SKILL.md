---
name: pocket-explainer
description: 把主题、文章或文档做成一条**成品 MP4** 讲解片——配音、字幕、章节进度条、6 套视觉主题，单文件 HTML 渲染，分片并行出片，一条命令产 mp4。含 EdgeTTS 逆向接口（322 音色、SRT 精确时间轴）、6 套主题变量、静态帧复用优化与踩坑清单。Use when the user says "做条视频/生成视频/出片/把这篇文档做成视频/讲解片" and expects a finished mp4 file (not a recording workflow). 不适用于复刻已有视频、真人口播、以实拍为主的片子。
---

# pocket-explainer

给一个主题或一篇文档，产出一条**可直接上传的 mp4**：配音、字幕、章节条、画面全部由代码生成。
不需要录屏，不需要 npm，不依赖 Remotion——一个 HTML 文件 + 一次分片渲染。

## 与 anything2explainer 的分工

| | pocket-explainer（本技能） | anything2explainer |
|---|---|---|
| 产物 | 成品 mp4，一条命令 | Remotion 工程 + 渲染 |
| 首次可用 | 5 分钟（写 deck.json 就能出） | 半小时（npm install + 建项目） |
| 8 分钟片子耗时 | 约 15 分钟 | 40 分钟起（多组并行） |
| 视觉 | 6 套主题，DOM/CSS 排版 | 单一暗场，Remotion 图元 |
| 复杂动效 | 弱（CSS 动画 + 快照） | 强（逐帧编程） |
| 手机端 | 能跑（浏览器打开即播） | 不能 |

**选哪个**：要快、要多风格、要在手机上看 → 本技能。要精细动效、要数据可视化编排 → anything2explainer。

## 流程

### 0 · 定四个参数（先问，一次问完）

1. **时长**：由句数决定，不是由字数。中文配音约 4.2 字/秒，8 分钟 ≈ 2000 字 ≈ 60–80 句。
2. **主题**：六选一，见 `reference/styles.md`。按题材选，不按喜好选。
3. **音色**：`reference/edge-tts.md` §7.3。中文默认 `zh-CN-XiaoxiaoNeural`（warm）；讲技术可换 `zh-CN-YunyangNeural`（professional）；要活泼用 `zh-CN-XiaoyiNeural`。
4. **语速**：`rate` 传 `0` 即原速。想让片子更紧凑，**不要**在合成时传 50（那是变速变调），而是写完后统一用 `assemble.py --tempo 1.18` 做保音高的时间压缩。

### 1 · 写 deck.json

```json
{
  "theme": "noir",
  "chapters": [{"name":"引子","at":0},{"name":"评分","at":96}],
  "shots": {
    "s1": "<h1>把社区作品<br>排成一张榜</h1><p>六维评分 · 名次评级</p>",
    "s2": "<div class=\"num\">6</div><p>个评分维度</p>"
  },
  "lines": [
    {"id":"s01","text":"社区里每天都有新作品，但没人告诉你哪个值得点开。","shot":"s1","hud":"01 / 引子"},
    {"id":"s02","text":"所以我做了个排行榜。","shot":"s2","hud":"01 / 引子"}
  ]
}
```

规则：

- **一句一镜**是默认。同一镜可挂多句（`shot` 重复），此时字幕换、画面不动——静态帧复用会直接跳过重绘，这是速度的关键。
- `dur` 不用写，`pack_audio.py` 会从 `audio/durations.json` 回填。
- `chapters[].at` 是秒，写不准就按 `lines` 累计时间粗估，后面用 `__seek` 校准。
- 镜头 HTML 只用模板已有的类：`h1 h2 p .num .mono .rule .card`。要新样式就加到模板里，不要在 deck 里写 `style=""`（渲染时会被快照成位图，改起来要重渲）。

### 2 · 配音

```bash
python3 scripts/tts_build.py lines.json -o audio/ --voice zh-CN-XiaoxiaoNeural --jobs 4
```

产出 `audio/<id>.mp3` + `<id>.srt` + `durations.json`。
**先跑 `--limit 3` 试三句**，确认音色和语速，再跑全量——全量重跑比试音贵得多。

### 3 · 组装单文件

```bash
python3 scripts/pack_audio.py deck.json -a audio/ -t template/player.html -o player.html
```

音频以 base64 内嵌，体积约为 mp3 的 1.37 倍（8 分钟片子约 4–5 MB），换来「双击即播、离线可用、发微信不丢音」。

### 4 · 试看

浏览器打开 `player.html`：点一下开始，看前 30 秒。

必查三项：字幕有没有被图形压住、章节条进度是否跟得上、主题的文字对比度在手机屏上够不够。

### 5 · 渲染

```bash
python3 scripts/render_parts.py player.html -o parts/ --w 1920 --h 1080 --fps 30 --batch 30 --workers 2
```

- 会先导 `parts/master.wav`（整片音轨），再逐片渲染 `part_000.webm`…
- 中断了直接重跑，已存在的分片自动跳过。
- `--workers` 不要超过 `nproc - 1`；每多开一个 Chrome 约多吃 400MB 内存。

### 6 · 出片

```bash
python3 scripts/assemble.py parts/ -o out.mp4 --tempo 1.0 --crf 20
```

### 7 · 质检（必做，两分钟）

```bash
ffprobe -v error -show_entries format=duration:stream=codec_name,width,height,r_frame_rate -of default=nw=1 out.mp4
ffmpeg -ss 60 -i out.mp4 -frames:v 1 -y /tmp/chk.png     # 抽 3 帧看画面不是黑的
ffmpeg -i out.mp4 -map 0:a:0 -af volumedetect -f null - 2>&1 | grep volume
```

判据：`mean_volume` 落在 −25 ~ −16 dB、`max_volume` < 0；抽帧各不相同；时长与音轨差 < 1 秒。

## 速度：实测基准（1080p，8 分钟片子，3 核）

| 环节 | 耗时 |
|---|---|
| 配音 162 句（4 并发） | 3–4 分钟 |
| 打包 HTML | 10 秒 |
| 分片渲染（静态帧复用） | 12–14 分钟 |
| 拼接编码 | 1 分钟 |
| **合计** | **约 17 分钟** |

优化手段按收益排序：

1. **静态帧复用**（模板已内置）：同镜头 + 同字幕 + 同动画进度桶的帧不重新快照。讲解片 60% 以上是静态帧，这一条省掉的就是大头。
2. **分片**：每片 30 秒。片太大编码队列积压，片太小拼接开销上升。
3. **并行**：`--workers 2` 在 3 核上约节省 35%，再多会因内存与 GPU 争抢而变慢。
4. **降帧率**：24fps 比 30fps 省 20% 渲染时间，幻灯片式画面看不出差别。
5. 不要指望 4K60——同一台机器上帧数 ×4、像素 ×4，会从 15 分钟变成 2 小时以上。

## 踩坑清单（都是实际踩过的）

1. **黑帧**：渲染前必须隐藏覆盖在舞台上的遮罩/控制条（模板里叫 `#gate` `#ctrl`），否则快照抓到的是遮罩层，整片全黑且看不出报错。
2. **变调**：不要用 `AudioBufferSourceNode.playbackRate` 加速。它没有 `preservesPitch`，1.18× 会把基频从 230Hz 抬到 302Hz。要快就用 `assemble.py --tempo`（rubberband）。
3. **SRT 起点不是 0**：EdgeTTS 返回的字幕第一句从约 100ms 开始，直接当时间轴会让每句累积偏移。`tts_build.py` 已做对齐。
4. **假成功**：EdgeTTS 对非法音色/空文本也返回 200 + URL，下载到的是 HTML 错误页（32315 字节）。必须校验 MP3 魔数，脚本已内置。
5. **JSON 注入**：deck 数据放进 `<script type="application/json">`，不要拼成 JS 字面量——几 MB 的 base64 拼进 JS 会让解析卡住十几秒。
6. **模板变量重名**：渲染循环里的临时变量别叫 `local`（与浏览器全局冲突），会让整段脚本编译失败，表现为「点了没反应」。
7. **章节条不同步**：进度条按章节真实区间填，不要按章节数均分——章节长短不一时会明显错位。
8. **重跑前清残留**：`parts/` 里的分片若来自上一次不同 fps 的渲染，会把时长拼歪。改参数后加 `--force`。

## 参考

- `reference/edge-tts.md` — 配音接口全文（端点、鉴权、322 音色、错误处理）
- `reference/styles.md` — 6 套主题的变量契约与排版规则
- `template/player.html` — 播放器与渲染器模板（主题、字幕、章节、`__renderPart`、`__dumpWav`）
