![白嫖清单](images/cover.png)

# 白嫖清单

**{{TOTAL}} 个能白嫖的服务，{{PROMPT_TOTAL}} 条天天在用的 AI 指令，{{SKILL_COUNT}} 个能直接装的技能。**
一个帮你省钱，一个帮你省事，一个帮你省时间。
服务是我亲手打的，指令是我亲手写的，技能是我自己在跑的——打不通、不好用的，直接删，不留墓碑。

> **Free tier, but actually verified.** {{TOTAL}} free services (AI / cloud storage / hosting / public APIs), {{PROMPT_TOTAL}} prompts and {{SKILL_COUNT}} skills. Every entry is tested by hand; dead links get deleted instead of kept as filler.

![services](https://img.shields.io/badge/services-{{TOTAL}}-3ddc97) ![prompts](https://img.shields.io/badge/prompts-{{PROMPT_TOTAL}}-3ddc97) ![skills](https://img.shields.io/badge/skills-{{SKILL_COUNT}}-3ddc97) ![license](https://img.shields.io/badge/license-MIT-111827) [![link-check](https://github.com/silverbullet-liang/freeload/actions/workflows/link-check.yml/badge.svg)](https://github.com/silverbullet-liang/freeload/actions/workflows/link-check.yml)

English overview: [README.en.md](README.en.md)

> 最后核对于 {{UPDATED}}，每条都带自己的核对日期。

**三条路，看你现在要干嘛：**

| 你想 | 直接去 |
| :-- | :-- |
| 少花钱 | 下面四张表：AI · 网盘 · 服务器 · API，全是还在给的免费额度 |
| 少折腾 | [AI 指令](prompts/README.md)：{{PROMPT_TOTAL}} 条，复制粘贴就能用，不用改参数 |
| 少花时间 | [AI Skills](skills/)：{{SKILL_COUNT}} 个技能包，把「做视频」「操作网页」这类重活交给 AI 自己跑 |

---

## 这份清单凭什么能信

网上「免费资源合集」的通病有三样，这里一样都不做：

1. **转载不复测。** 某份流传很广的 B 站解析文档，第一条主推的接口实测 HTTP 000，域名早就没了。这类直接删，不留在表里充数。
2. **拿「免费」当噱头。** 注册送 10 次的、要买 token 的、绑卡才能试的、只在浏览器里能用的——都不算白嫖，不进表。
3. **只写额度不写坑。** 真正的成本全在「坑」那一列：限速怎么算、额度什么时候砍、什么时候开始收费、文档哪句已经过期。
4. **指令不是扒来的。** 这 {{PROMPT_TOTAL}} 条不是「1000 条提示词大全」那种凑数包，是自己写、自己在用的，一条一个文件，按用途分类。

最近一轮实测了 12 个端点，删掉 6 个打不通或名不副实的。表里剩下的，都是当场验过的。

## 一页速查：直接抄答案

不想翻表，就按这张拿。这一版的最优解，下次实测变了会改。

| 你要什么 | 直接拿 | 为什么是它 |
| :-- | :-- | :-- |
| 三模态 AI 全白嫖（文本 + 图 + 视频） | Agnes AI | 三样全免、不卡 token 总量，只卡 RPM |
| 连注册都懒得 | Pollinations | 免 key 免注册，45 秒一张图、30 秒一段话 |
| 免费静态站，长期挂 | Cloudflare Pages | 500 次构建/月 + 不限带宽 + 2 万文件 |
| 手机上发一页 HTML | Kimi CDN | 手机 App 发一条，链接立刻可用 |
| 免注册临时发页 | ship.page | curl 一行，30 天 |
| 免费 PHP 主机 | InfinityFree | 5GB + 400 个库 + 单账号 3 个站点 |
| 大容量存文档 | 豆包 AI 云盘 | 免费 5TB，只收文档与图片 |
| 不封顶的文件池 | AI 对话当网盘 | 会话当文件夹，能搜、能分享 |
| 免费天气 / 音乐 API | Open-Meteo / Injahow | 都免 key，实测 200 |
| 让 AI 自己剪一条讲解片 | pocket-explainer | 一条命令出带配音字幕的 mp4 |
| 让 AI 操作网页 | chrome-kernel-installer | 截图带编号，按号点 |

## 评级

每张表按推荐度从高到低排：

| 评级 | 意思 |
| :--: | :-- |
| 夯 | 顶到天花板，优先用它 |
| 顶级 | 很好用，只有一点摩擦（比如每天要签到） |
| 人上人 | 有明显亮点，但额度或限速会咬人 |
| NPC | 中规中矩，能用但别指望 |
| 拉完了 | 名义免费，实际处处是墙 |

## 门槛

| 标记 | 含义 |
| :-- | :-- |
| 免注册 | 打开就能用，不留身份 |
| 邮箱 | 注册即可，不需要付款信息 |
| 手机号 | 收个验证码就能用，不做实名核验 |
| GitHub | 用 GitHub 账号授权 |
| 实名 | 要身份证 / 人脸这类真实身份核验，不只是手机号 |
| 信用卡 | 需要绑卡，注意自动续费与超额计费 |

## 目录

- [AI](#ai) —— {{AI_COUNT}} 条
- [网盘](#%E7%BD%91%E7%9B%98) —— {{PAN_COUNT}} 条
- [服务器](#%E6%9C%8D%E5%8A%A1%E5%99%A8) —— {{SERVER_COUNT}} 条
- [API](#api) —— {{API_COUNT}} 条
- [AI 指令](#ai-%E6%8C%87%E4%BB%A4) —— {{PROMPT_TOTAL}} 条
- [AI Skills](#ai-skills) —— {{SKILL_COUNT}} 个

## AI

{{AI_DESC}}

{{AI_TABLE}}

## 网盘

{{PAN_DESC}}

{{PAN_TABLE}}

## 服务器

{{SERVER_DESC}}

服务器类多看一张「体感维度」表：速度、快捷、限制给 1–5 分（5 最好），注册方式与广告标识直接写文字。**分数低不等于评级低**——评级还看生态与账号体验，两张表回答的是不同问题。

{{SERVER_TABLE}}

## API

{{API_DESC}}

{{API_TABLE}}

## AI 指令

{{PROMPT_SUMMARY}}

## AI Skills

{{SKILLS}}

## 怎么加一条

改 `data/` 下对应分类的 JSON，跑 `python3 tools/build.py`，README 自动重排。必填五项：`name` `url` `what` `gate` `rating`。

```json
{
  "name": "示例服务",
  "url": "https://example.com",
  "what": "每月 100 万 token、5 个并发",
  "gate": "邮箱",
  "rating": "人上人",
  "gotcha": "只算新用户；超量直接停服不扣费",
  "checked": "2026-10-25"
}
```

收录只有三条：**真的免费**（不用先付费再返现、不用邀人解锁）、**能长期用**（不是七天试用）、**现在还有效**（带核对日期，失效即删）。

## 免责

手工核对的事实汇编，不构成任何服务方背书。额度与条款随时会变，用之前自己看一眼官方页面。本清单不对第三方服务的可用性、数据安全与扣费负责。

## 最后

这份清单没有广告、没有返利链接、没有「点击领取」。如果它帮你省了钱或省了时间，点个 Star 让更多人看到——这是它唯一能传播的方式。

## License

MIT
