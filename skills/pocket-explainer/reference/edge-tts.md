# edge.text-to-speech.cn 语音 API 接口文档

> 基于微软 Edge TTS 的 PHP 代理封装站，免费、无需登录。

---

## 1. 端点清单

| 方法 | 路径 | 作用 | 鉴权 |
|---|---|---|---|
| GET | `/` | 取 CSRF token | 无 |
| POST | `/generate.php` | 合成音频 + 字幕 | Referer/Origin + CSRF |
| GET | `/stats.php` | 今日用量统计 | 无 |
| GET | `/download/{id}.mp3` | 下载音频 | 无 |
| GET | `/download/{id}.srt` | 下载字幕 | 无 |

---

## 2. 鉴权

### 2.1 取 Token

```bash
TOKEN=$(curl -s https://edge.text-to-speech.cn/ \
        | grep -oP '<meta name="csrf-token" content="\K[^"]+')
```

- 每次调用前重新取，**不要硬编码**（token 随页面缓存周期轮换）
- 格式：`<时间戳>.<32位哈希>`，全站共享、可复用、不依赖 Cookie

### 2.2 请求头

| Header | 必需 | 说明 |
|---|---|---|
| `Content-Type: application/json` | 是 | |
| `X-CSRF-TOKEN: <token>` | 是 | |
| `Referer: https://edge.text-to-speech.cn/` | 二选一 | 来源白名单 |
| `Origin: https://edge.text-to-speech.cn` | 二选一 | 与 Referer 任一即可 |

伪造来源返回 `{"error":"不允许的请求来源: xxx"}`；缺 token 返回 `{"error":"缺少CSRF令牌，请刷新页面重试"}`。

---

## 3. POST /generate.php

### 3.1 请求体

```json
{
  "text":   "你好，世界。",
  "voice":  "zh-CN-XiaoxiaoNeural",
  "rate":   "0",
  "pitch":  "0",
  "volume": "100"
}
```

| 字段 | 类型 | 档位 | 说明 |
|---|---|---|---|
| `text` | string | 任意 | 待合成文本，建议 ≤5000 字 |
| `voice` | string | 322 个 ShortName 之一 | 见 §6 |
| `rate` | string | -50/-33/-20/0/20/33/50 | 百分比语义，-50=慢一倍，50=快 1.5 倍 |
| `pitch` | string | -50/-33/-20/0/20/33/50 | 同上 |
| `volume` | string | 33/66/100/133/166/200 | 100=正常；**不要传 0**（会失败） |

字段缺失容忍度高：仅传 `{"text":"x"}` 也返回 200（后端有默认值兜底）。

### 3.2 成功响应（HTTP 200）

```json
{
  "audio_url":    "/download/9029969901456447.mp3",
  "subtitle_url": "/download/9029969901456447.srt"
}
```

- 均为**相对路径**，拼域名即可
- 文件 ID 为 16 位数字，随时间单调递增，不可预测
- 产物公开可下载，无需凭证

### 3.3 错误响应

```json
{ "error": "请求来源验证失败" }
```

前端另处理配额类响应：`{code:402, msg:"..."}`（未实测触发）。

---

## 4. GET /stats.php

今日用量统计，无鉴权。

```bash
curl -s https://edge.text-to-speech.cn/stats.php
# {"users":27,"chars":58919,"date":"2026-09-25"}
```

---

## 5. GET /download/{id}.mp3

下载音频产物。

| 属性 | 值 |
|---|---|
| 编码 | MPEG Layer III |
| 采样率 | 24 kHz |
| 码率 | 48 kbps CBR |
| 声道 | Mono |
| MIME | `audio/mpeg` |
| Range 请求 | 支持 |

**假成功防御**：非法 voice / `volume="0"` / 空文本时，接口仍返回 200 + URL，但下载到的是 32315 字节 HTML 错误页（md5 `048a2241792d9efbc94d44a256d40ca4`，文件头 `<!DOCTYP`）。必须校验产物魔数（MP3 frame sync `0xFF 0xEX` 或 `ID3`）。

---

## 6. GET /download/{id}.srt

下载字幕产物，与音频同 ID。

```srt
1
00:00:00,100 --> 00:00:02,875
欢迎使用文字转语音服务。

2
00:00:02,825 --> 00:00:12,362
这是通过逆向分析得到的接口生成的一段测试音频。
```

- 起点非 0（实测 100 ms），系 Edge `WordBoundary` 元数据偏移
- **按句切分，不做智能断句**，长句会产生超长字幕条（如 51 字 / 9.5 秒），剪辑场景需二次切分

---

## 7. 音色表

### 7.1 获取方式

音色表内联在首页 HTML 的 `let voices = [...]` 中，**无独立接口**，须解析 HTML 提取。

### 7.2 字段结构

```json
{
  "FriendlyName": "Microsoft Xiaoxiao Online (Natural) - Chinese (Mainland)",
  "Gender": "Female",
  "Locale": "zh-CN",
  "Name": "Microsoft Server Speech Text to Speech Voice (zh-CN, XiaoxiaoNeural)",
  "ShortName": "zh-CN-XiaoxiaoNeural",
  "Status": "GA",
  "SuggestedCodec": "audio-24khz-48kbitrate-mono-mp3",
  "VoiceTag": { "ContentCategories": ["General"], "VoicePersonalities": ["Warm"] }
}
```

请求中用 **`ShortName`** 作为 `voice` 值。

### 7.3 中文音色（zh-CN 8 个）

| ShortName | 性别 | 特质 |
|---|---|---|
| `zh-CN-XiaoxiaoNeural` | Female | Warm（默认推荐） |
| `zh-CN-XiaoyiNeural` | Female | Lively |
| `zh-CN-YunjianNeural` | Male | Passion |
| `zh-CN-YunxiNeural` | Male | Lively, Sunshine |
| `zh-CN-YunxiaNeural` | Male | Cute |
| `zh-CN-YunyangNeural` | Male | Professional, Reliable |
| `zh-CN-liaoning-XiaobeiNeural` | Female | Humorous（东北口音） |
| `zh-CN-shaanxi-XiaoniNeural` | Female | Bright（陕西口音） |

另有 zh-HK 粤语 3 个：`zh-HK-HiuGaaiNeural`、`zh-HK-HiuMaanNeural`、`zh-HK-WanLungNeural`。

完整 322 条音色表（142 个 Locale，Female 163 / Male 159）可通过解析首页 HTML 提取。

---

## 8. 示例代码

### 8.1 cURL

```bash
UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36'
BASE='https://edge.text-to-speech.cn'
T=$(curl -s -A "$UA" "$BASE/" | grep -oP '<meta name="csrf-token" content="\K[^"]+')

curl -s -A "$UA" -X POST "$BASE/generate.php" \
  -H 'Content-Type: application/json' \
  -H "Referer: $BASE/" \
  -H "X-CSRF-TOKEN: $T" \
  -d '{"text":"你好，世界。","voice":"zh-CN-XiaoxiaoNeural","rate":"0","pitch":"0","volume":"100"}'
```

### 8.2 Python（含假成功防御）

```python
import hashlib, json, re, requests

BASE = "https://edge.text-to-speech.cn"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
BAD_MD5 = "048a2241792d9efbc94d44a256d40ca4"

class EdgeTTS:
    def __init__(self):
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA})
        self._token = None

    def _csrf(self):
        html = self.s.get(BASE + "/", timeout=30).text
        self._token = re.search(r'name="csrf-token" content="([^"]+)', html).group(1)
        return self._token

    def synthesize(self, text, voice="zh-CN-XiaoxiaoNeural",
                   rate="0", pitch="0", volume="100"):
        if not self._token:
            self._csrf()
        body = {"text": text, "voice": voice, "rate": str(rate),
                "pitch": str(pitch), "volume": str(volume)}
        r = self.s.post(BASE + "/generate.php", json=body, timeout=120,
                        headers={"Referer": BASE + "/",
                                 "X-CSRF-TOKEN": self._token})
        d = r.json()
        if "audio_url" not in d:
            raise RuntimeError(f"接口错误: {d}")
        audio = self.s.get(BASE + d["audio_url"], timeout=120).content
        # 假成功防御
        if (len(audio) < 1024
                or hashlib.md5(audio).hexdigest() == BAD_MD5
                or not (audio[:3] == b"ID3" or (audio[0] == 0xFF and audio[1] & 0xE0 == 0xE0))):
            raise RuntimeError(f"伪成功：voice={voice} volume={volume} 无效，产物非音频")
        return {"audio": audio,
                "srt": self.s.get(BASE + d["subtitle_url"], timeout=60).text}

    def refresh(self):
        self._csrf()

tts = EdgeTTS()
out = tts.synthesize("今天天气真不错。")
open("out.mp3", "wb").write(out["audio"])
print(out["srt"])
```

---

## 9. 注意事项

- **Token 会轮换**：与页面缓存周期绑定，长驻进程须定期重取，勿硬编码
- **Volume 不要传 0**：前端写着「0=静音」，实测导致合成失败，安全区间 33–200
- **产物 URL 无访问控制**：拿到链接即可下载，涉密文本的音频链接不要外发
- **自控频率**：站点无明确限流策略，生产集成请加并发上限与指数退避
