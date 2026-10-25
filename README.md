![白嫖清单](images/cover.png)

# 白嫖清单

**30 个能白嫖的服务，30 条天天在用的 AI 指令，2 个能直接装的技能。**
一个帮你省钱，一个帮你省事，一个帮你省时间。
服务是我亲手打的，指令是我亲手写的，技能是我自己在跑的——打不通、不好用的，直接删，不留墓碑。

> **Free tier, but actually verified.** 30 free services (AI / cloud storage / hosting / public APIs), 30 prompts and 2 skills. Every entry is tested by hand; dead links get deleted instead of kept as filler.

![services](https://img.shields.io/badge/services-30-3ddc97) ![prompts](https://img.shields.io/badge/prompts-30-3ddc97) ![skills](https://img.shields.io/badge/skills-2-3ddc97) ![license](https://img.shields.io/badge/license-MIT-111827) [![link-check](https://github.com/silverbullet-liang/freeload/actions/workflows/link-check.yml/badge.svg)](https://github.com/silverbullet-liang/freeload/actions/workflows/link-check.yml)

English overview: [README.en.md](README.en.md)

> 最后核对于 2026-10-25，每条都带自己的核对日期。

**三条路，看你现在要干嘛：**

| 你想 | 直接去 |
| :-- | :-- |
| 少花钱 | 下面四张表：AI · 网盘 · 服务器 · API，全是还在给的免费额度 |
| 少折腾 | [AI 指令](prompts/README.md)：30 条，复制粘贴就能用，不用改参数 |
| 少花时间 | [AI Skills](skills/)：2 个技能包，把「做视频」「操作网页」这类重活交给 AI 自己跑 |

---

## 这份清单凭什么能信

网上「免费资源合集」的通病有三样，这里一样都不做：

1. **转载不复测。** 某份流传很广的 B 站解析文档，第一条主推的接口实测 HTTP 000，域名早就没了。这类直接删，不留在表里充数。
2. **拿「免费」当噱头。** 注册送 10 次的、要买 token 的、绑卡才能试的、只在浏览器里能用的——都不算白嫖，不进表。
3. **只写额度不写坑。** 真正的成本全在「坑」那一列：限速怎么算、额度什么时候砍、什么时候开始收费、文档哪句已经过期。
4. **指令不是扒来的。** 这 30 条不是「1000 条提示词大全」那种凑数包，是自己写、自己在用的，一条一个文件，按用途分类。

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

- [AI](#ai) —— 5 条
- [网盘](#%E7%BD%91%E7%9B%98) —— 2 条
- [服务器](#%E6%9C%8D%E5%8A%A1%E5%99%A8) —— 10 条
- [API](#api) —— 13 条
- [AI 指令](#ai-%E6%8C%87%E4%BB%A4) —— 30 条
- [AI Skills](#ai-skills) —— 2 个

## AI

模型额度、免费 API Key、免费算力与推理额度。

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **夯** | [Agnes AI](https://apihub.agnes-ai.com/v1) | 文本 agnes-2.5-flash / agnes-2.0-flash，不设 token 总量（实际执行 20 RPM）；图片 agnes-image-2.0/2.1-flash，最高 4096×4096（1K 20 / 2K 10 / 3K 1 / 4K 1 RPM）；视频 agnes-video-v2.0，1 RPM，异步轮询、音画同步 | 邮箱 | RPM 有「允许发起 30 / 实际执行 20」两套数，按实际算；视频一次生成耗 3–5 次请求，高峰排队；高峰期 1M 上下文压到 512K；官方保留随时调整免费政策；超额只限速不封号；Key 仅创建时完整显示一次；国内另有 apihub.agnes-ai.cn/v1 | 2026-10-25 |
| **顶级** | [FreeTheAI](https://api.freetheai.org/v1) | 114+ 模型（GLM 5.3、Kimi K3、MiniMax M3、DeepSeek 等），文本 + 图片 + 视频，兼容 OpenAI / Anthropic / Responses 三种格式 | 邮箱 | 旧域名 api.freetheai.xyz 与 Discord 的 /signup、/checkin 已全部作废；现在每天必须在 freetheai.org 签到（UTC 零点清零），断签额度即停；日上限官方不公布（原文「limits remain server-owned」，第三方称约 50 次/天）；只收 Gmail / Outlook 这类主流邮箱，临时邮箱被拒；付费走加密货币钱包 | 2026-10-25 |
| **人上人** | [OpenRouter](https://openrouter.ai) | ID 带 :free 后缀的轮换模型集（2026 年中约 25–29 个），50 请求/天、20 请求/分钟；累计充值 $10 后升到 1000 次/天（每分钟仍 20） | 邮箱 | 免费模型每周轮换，今天能用的明天可能下架；失败请求也计次；余额为负时免费模型直接 402；无 prompt 缓存与预算控制；免费模型默认可能拿输入训练；另有 openrouter/free 自动路由可选 | 2026-10-25 |
| **人上人** | [Free.ai](https://api.free.ai) | 注册后 30000 token/天（约 300 条对话或 30 张图）；API 免费档 1000 请求/月、60 请求/分钟；模型覆盖 Qwen 3.6 35B、FLUX、CogVideoX、Kokoro、Whisper | 邮箱 | 匿名只能开网页（6000 token/天），调 API 必须 sk-free- 开头的 key；视频 1 条/2 天，且一条吃掉当天全部 30000 token；免费池只覆盖自托管开源模型，GPT-6 / Claude / Gemini / Veo 从付费余额扣；解除视频限制最低 $5/月；官方文档「先买 token 再生成 key」与免费档说明并存，以页面为准 | 2026-10-25 |
| **NPC** | [Pollinations](https://image.pollinations.ai/prompt/{prompt}) | 图片与文本都不限张数，全免注册免 key；OpenAI 兼容端点 text.pollinations.ai/openai；文本模型 GPT-OSS 20B | 免注册 | 按 IP 限速：图片 45 秒 1 张、文本 30 秒 1 条，超限直接 402；单图最大 768×768 且带 Pollinations logo；同 URL 命中缓存，seed 固定即同图；无 uptime 承诺 | 2026-10-25 |

## 网盘

免费空间、直链、离线下载与传输流量。

### 豆包生态

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **顶级** | [豆包 AI 云盘](https://www.doubao.com) | 免费 5TB（普通账号上限）、单文件 100MB、单次最多 200 个、只收文档与图片、上传下载不限速；入口在豆包 App / 网页左侧「云盘」 | 手机号 | 2026-06-22 起已经正式条款化，不是「规则没说明」：普通账号 5TB 封顶，此前的「无限容量」活动 6-30 已结束；只收文档和图片，视频、安装包传不上去；超 5TB 要买扩容（单价未公布）；底层存储由飞书科技提供，定位是「AI 功能配套」，别当主力备份盘 | 2026-10-25 |

### 偏门玩法

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **顶级** | [AI 对话当网盘（网页版）](https://chat.deepseek.com) | 网页版 AI 对话的附件上传，本来没有累积容量与文件总数上限：一个会话当一个文件夹，一条消息当一个子文件夹，往里堆就行。单文件有上限（DeepSeek 网页版单次最多 50 个、单个 ≤100MB），支持 PDF / Word / Excel / PPT / TXT / 图片；千问、豆包的网页对话同理 | 手机号 | 分享 != 整库外发：分享会话时勾选具体消息，生成公开链接，等于只把某个子文件夹发出去——Kimi 社区里大量作品就是这么传的；单文件有硬上限（DeepSeek 网页版 100MB），视频、安装包传不上去，改后缀加 .txt 能骗过前端校验，下载后记得改回来；能搜：对话名和消息内容都能搜，等于自带全文检索，但文件名不保证被索引，命名时把关键词写进消息正文；分享链接跟着会话走，会话删了链接就废，官方也没承诺长期保存；千问、豆包的附件上限与保留策略各不相同，换平台前先看输入框提示 | 2026-10-25 |

## 服务器

静态部署、动态主机、容器与边缘函数——能白嫖的运行环境。

服务器类多看一张「体感维度」表：速度、快捷、限制给 1–5 分（5 最好），注册方式与广告标识直接写文字。**分数低不等于评级低**——评级还看生态与账号体验，两张表回答的是不同问题。

### 静态部署

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **夯** | [Cloudflare Pages](https://pages.cloudflare.com) | 500 次构建/月、单站点 2 万文件、单文件 25MiB、100 个项目、静态请求不限带宽、预览部署无限、自定义域名 100 个 | 邮箱 | 单文件必须 ≤25MiB，更大要走 R2；新账号头两天限制新建项目；Functions 请求计入 Workers 配额；构建 20 分钟超时 | 2026-10-25 |
| **顶级** | [GitHub Pages](https://pages.github.com) | 站点 1GB、软带宽 100GB/月、软构建 10 次/小时（改用 Actions 部署不受此限）、自定义域名 + 自动 HTTPS | GitHub | 免费账号只能公开仓库；官方明令禁止当免费主机跑商业站/电商/SaaS；国内访问慢且丢包；超限返回 429；站点与源仓库各 1GB | 2026-10-25 |
| **顶级** | [Kimi CDN](https://kimi.moonshot.cn) | 在 Kimi 手机 App 里发布一个单文件 HTML，产物直接落在 Kimi 自用的 CDN 上（kimi-file.moonshot.cn），拿到一个公开可访问的地址：不买域名、不搭服务器、不备案，全屏渲染，可直接外发 | 手机号 | 它持久的原因不是承诺，是官方还没意识到有人在拿社区作品当 CDN 占存储、暂时没人治理——这是漏洞窗口，不是服务条款；哪天开始清理存量，老链接可能成批失效，重要内容自己留副本。取链接要靠页面自己打印：社区不给分享按钮、地址栏只显示网页标题，必须在页面里写 document.getElementById('pageUrl').textContent = window.location.href；只有手机 App 能发布，网页版和电脑端没有这个按钮；提示词必须写死「直接在 markdown 代码块输出、不要调 Python 工具、不要用 widget」，否则产出的不是能发布的全屏 HTML；链接 100 多字符且带 kimi-file.moonshot.cn，对外发建议过一道短链；发的是作品不是站点，改了要重新发布、换新链接 | 2026-10-25 |
| **人上人** | [上码 Upma](https://www.upma.cn) | 2 个项目、1GB 流量/月、单次上传 10MB、总存储 100MB、自定义域名 + 自动 SSL、香港 CN2 免备案 | 手机号 | 免费版页面底部挂「托管于上码」标识；超额 402 或暂停到下月；*.upma.site 子域归平台所有、闲置可收回；只托管静态文件；官网自标国内丢包 25% | 2026-10-25 |
| **人上人** | [ship.page](https://ship.page) | 匿名上传 HTML（10MB）/ ZIP（25MB、100 文件）/ 文件夹，秒出链接；纯 REST API 一次 POST 即部署；匿名 30 天、注册免费账号 90 天 | 免注册 | 单文件 10MB；不能绑自定义域名、不能原地更新（Pro 才有）；链接 47 位熵、无密码保护；10 次部署/分钟/IP；域名会变，实测 *.ship.place；过期后 30 天内可 restore；Pro $4/月（永久 + 密码保护 + 120 次/分） | 2026-10-25 |

### 动态部署

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **夯** | [InfinityFree](https://infinityfree.com) | 5GB 存储、不限带宽（公平使用）、400 个 MySQL 数据库、PHP 8.3/8.4、免费 SSL、免费子域或自定义域名、无强制广告，单账号可开 3 个 hosting account | 邮箱 | 每日 50,000 hits 硬限（按文件请求算，一页 11 次请求，约合 4,500 浏览量/天）；30,000 inode；单文件 10MB；超限自动暂停约 24 小时；PHP 执行约 10 秒；免费档无 SSH、无 cron；页面注入 /aes.js 反爬并触发一次二次导航；只支持 HTTP/1.1；长期无访问停用；实测有因「不允许的文件」整站被删的先例 | 2026-10-25 |
| **人上人** | [ByetHost](https://byet.host) | 5GB NVMe、不限带宽、PHP 8.3、MySQL 8、无限数据库、免费 SSL、cron jobs、400+ Softaculous 应用、无广告、无到期（byethost33 是其中一台节点） | 邮箱 | 一个账号只给一个 hosting account；账号名与密码创建时只显示一次，丢了只能重置；VistaPanel 难用；单文件 10MB；免费档切 PHP 版本要升级；同属 iFastNet，与 InfinityFree 共享底层资源限制；自定义域名要自己配 DNS | 2026-10-25 |

### AI 建站

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **顶级** | [豆包工作模式建站](https://www.doubao.com) | 用豆包「工作模式」配一个可被外部调用的接口，把 AI 输出当成站点内容与执行层；额度走豆包工作模式，目前没看到明示的调用上限 | 手机号 | 不校验 key 就等于把额度交给公网：任何人都能驱动你的接口烧额度，还能用提示词注入越过你设的指令。务必自己加一层校验（key 放请求头或路径，服务端先比对再转给模型），并给单次请求设长度与频率上限；同赛道对比：百度秒哒按「秒点」扣且 7 天过期，扣子官方写明 API 累计 500 次就封顶——豆包目前只按对话额度消耗，没看到调用次数上限，这是它唯一值得用的理由，也是最可能先被收紧的地方；上下文里别放账号密码与内部地址 | 2026-10-25 |
| **NPC** | [百度秒哒](https://miaoda.cn) | 一句话生成网站 / H5 / 小程序 / App。免费版按「秒点」计：注册送 200，每天登录送 100（免费版每月最多领 7 天，点数 7 天过期）；快速开发 10 点/次、深度开发 40 点/次、发布 20 点/次、开基础后端 15 点/天 | 手机号 | 规则写得极细且全在计费文档里，几乎没有空子：每月最多领 7 天点数、点数 7 天过期、发布与开后端都按次扣；免费版数据库 1GB、对象存储 200MB、并发 10，项目 5 天不活跃数据库就暂停；不能去水印、不能绑专属域名、不能下源码；付费标准版首月 14.9 元起 | 2026-10-25 |
| **NPC** | [Coze 扣子](https://www.coze.cn) | 字节的智能体 / 工作流平台，能把 Bot 发布成 HTTP API（/v3/chat）；国内个人免费版每天 500 资源点（零点重置、不累计） | 手机号 | 两套口径要分清：资源点每天 500、当天不用清零；API 侧官方文档写明「累计 500 次免费额度，超出后账号无法继续使用任何扣子 API」——这条是死线，不是每天重置；免费版 10 个 Bot、知识库 10GB；想长期当接口用必须付费（39.9 元/月起） | 2026-10-25 |

### 体感维度（1–5 分，5 最好）

| 平台 | 速度 | 快捷 | 注册 | 限制 | 广告 / 标识 | 主要缺点 |
| :-- | :--: | :--: | :-- | :--: | :-- | :-- |
| Cloudflare Pages | 5 | 4 | 邮箱 | 5 | 无 | 单文件 25MiB 上限；新账号 48 小时内限建项目 |
| InfinityFree | 2 | 2 | 邮箱 | 3 | 无 | 反爬二次导航拖首屏、PHP 10 秒、无 cron、每日 5 万 hits |
| GitHub Pages | 3 | 4 | GitHub | 4 | 无 | 必须公开仓库、不许商用、国内慢且丢包 |
| 豆包工作模式建站 | 3 | 4 | 手机号 | 4 | 无 | 接口默认裸奔、无鉴权、稳定性未知 |
| Kimi CDN | 4 | 5 | 手机号 | 3 | 无 | 真实链接要自己打印出来、超长、改了得重新发布 |
| 上码 Upma | 5 | 5 | 手机号 | 2 | 页脚「托管于上码」标识 + 右下角悬浮微件 | 额度只够小 Demo；子域归平台所有、闲置可收回 |
| ship.page | 3 | 5 | 免注册 | 3 | 有徽章（客户端注入，非必现） | 单文件 10MB；不能绑域名、不能原地更新；30 天到期 |
| ByetHost | 2 | 1 | 邮箱 | 3 | 无 | VistaPanel 繁琐、凭据只显示一次、一账号一站 |
| 百度秒哒 | 4 | 4 | 手机号 | 1 | 免费版可挂百度流量标识 | 秒点 7 天过期、不能绑域名、不能导出源码 |
| Coze 扣子 | 4 | 4 | 手机号 | 2 | 无 | 免费 API 累计 500 次封顶、资源点当天清零 |

### 去平台标识

免费平台靠品牌曝光活着，这段代码只是把注入的节点摘掉，页面本身不受影响。粘到 `</body>` 前，重新部署即可。

**上码 Upma** —— 页脚「托管于上码」标识 + 右下角悬浮微件

```html
<script>
(function(){
  function strip(){
    document.querySelectorAll('[data-shangma-branding],[data-shangma-report-modal],.upma-micro-widget')
      .forEach(function(el){el.remove()});
  }
  strip();
  if(document.body&&window.MutationObserver){
    new MutationObserver(strip).observe(document.body,{childList:true,subtree:true});
  }
})();
</script>
```

**ship.page** —— 有徽章（客户端注入，非必现）

```html
<script>
(function(){
  var sel="ship-page-badge,.ship-page-badge";
  function strip(){
    document.querySelectorAll(sel).forEach(function(el){el.remove()});
  }
  strip();
  if(document.body&&window.MutationObserver){
    new MutationObserver(strip).observe(document.body,{childList:true,subtree:true});
  }
})();
</script>
```

## API

通用第三方接口。条目按站长实测填，不收未经核对的转载。

### 语音

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **夯** | [edge.text-to-speech.cn](https://edge.text-to-speech.cn) | 免登录的 Edge TTS 代理：322 个音色（142 个 locale，含 8 个 zh-CN、3 个粤语），POST /generate.php 一次出 MP3（24kHz/48kbps/mono）+ 逐句 SRT 字幕 | 免注册 | 每次先 GET 首页取 csrf-token，请求必须带 Referer 或 Origin，否则报「不允许的请求来源」；假成功陷阱：非法 voice 或 volume=0 也返回 200 + URL，下载到的是 32315 字节 HTML（md5 048a2241792d9efbc94d44a256d40ca4），必须验 MP3 帧同步 0xFF Ex 或 ID3；产物公开可下载、无鉴权；字幕按句切不智能断句；第三方逆向封装，随时可能关 | 2026-10-25 |
| **人上人** | [浏览器 TTS 三件套](https://developer.mozilla.org/docs/Web/API/SpeechSynthesis) | Web Speech API（系统音色、完全免费离线）+ DECtalk WASM（1983 年老引擎，仅英文，11025Hz PCM）+ ResponsiveVoice CDN（51 语言 168 音色，旧版免 key） | 免注册 | Web Speech 各系统音色差异极大，Safari 长文本会截断；DECtalk 首次播放必须用户交互解锁 AudioContext；ResponsiveVoice 新版要 key 且仅限非商业；三者都不是「接口」，是前端方案，服务端批量合成用不上 | 2026-10-25 |

### 视频解析

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **顶级** | [米人 API](https://api.mir6.com/api/bzjiexi) | 免费 B 站解析，GET ?url=<BV 链接> 返回标题、封面、简介与 data 数组（含直链），开放 CORS | 免注册 | 仅普通 BV 视频，番剧/电影/电视剧不支持；返回的是 DASH 分离流，视频音频要自己 ffmpeg 合流；第三方站点随时限流，别当前端唯一依赖 | 2026-10-25 |

### 音乐

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **夯** | [zm.wwoyun.cn](https://zm.wwoyun.cn) | NeteaseCloudMusicApi 公共实例（宁波），搜索 / 直链 / 详情 / 歌词全套，接口与官方一致，实测搜索 200 | 免注册 | 直链数小时后失效，别写死；公共实例无 SLA，随时可能关；部分歌曲只给试听片段，别把 br 当音质承诺 | 2026-10-25 |
| **夯** | [Injahow Meting](https://api.injahow.cn/meting/) | Meting 轻接口：type=url 直接回 MP3 二进制流，type=song 出歌名/歌手/封面/歌词地址，type=lrc 回 LRC | 免注册 | 封面要传封面 ID（从 type=song 响应里取），不是歌曲 ID；直链有时效；单点第三方，挂了没有备用 | 2026-10-25 |
| **人上人** | [Paugram NetEase](https://api.paugram.com/netease/) | 歌曲详情 + 完整带时间轴歌词 + 250×250 封面，返回 JSON | 免注册 | 不返回音频直链，必须和别的接口搭配；封面只有 250px，做全屏背景会糊 | 2026-10-25 |
| **人上人** | [网易云官方外链](https://music.163.com/song/media/outer/url?id={id}.mp3) | 302 跳到 CDN 直链，CORS 为 *，一行 <audio src> 就能播 | 免注册 | 时效只有数十分钟；只给试听/标准音质；版权受限曲目直接 404 或跳到空；实测 302 可用 | 2026-10-25 |

### 天气

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **夯** | [Open-Meteo](https://api.open-meteo.com/v1/forecast) | 逐日 / 逐小时预报、地理编码（geocoding-api）、空气质量（air-quality-api）三套接口全免 key、开放 CORS，实测 200 | 免注册 | 免费档限非商业，商用要订阅；中国区降水与云量精度一般；geocoding 中文有时取到乡镇级，要自己按 population 排序；变量名拼错不会报错、只回空数组 | 2026-10-25 |
| **顶级** | [wttr.in](https://wttr.in/Beijing?format=j1) | 文本 / Markdown / JSON 三种输出，format=j1 给完整 JSON（当前天气 + 3 天逐时 + 天文），免 key | 免注册 | 无 SLA，高峰期明显变慢；中文城市名必须 URL 编码；j1 里数值全是字符串，运算前要转；返回体积大，前端别整包塞进状态 | 2026-10-25 |
| **人上人** | [MET Norway](https://api.met.no/weatherapi/locationforecast/2.0/compact) | 挪威气象局全球预报，compact 端点返回 GeoJSON 时序，免 key | 免注册 | 强制要求带可识别的 User-Agent（含联系方式），UGC 抓取会被封；挪威境外精度一般；有小时级限流 | 2026-10-25 |
| **人上人** | [7Timer](https://www.7timer.info/bin/astro.php) | 天文与常规两套产品，astro 给云量 / 视宁度 / 透明度，观星与摄影场景好用 | 免注册 | 6 小时一更新、网格分辨率粗；无中文；部分产品线已停更 | 2026-10-25 |
| **人上人** | [中央气象台 nmc.cn](http://www.nmc.cn/rest/province) | 非公开接口：/rest/province 省市列表、/f/rest/tempchart 温度曲线、/f/rest/aqi 空气质量、/f/rest/real 实况 | 免注册 | 非官方 API，随时改；实测 /rest/province 正常，/f/rest/real/54511 返回结构在但字段全空；只适合当兜底，别当主数据源 | 2026-10-25 |

### 人机验证

| 评级 | 名称 | 白嫖什么 | 门槛 | 坑 / 限制 | 最后确认 |
| :--: | :-- | :-- | :-- | :-- | :-- |
| **人上人** | [小象人机认证](https://xiaoxianghost.42web.io/renji/) | 一个共享的 Cloudflare Turnstile 实例：页面里嵌 data-sitekey="0x4AAAAAADfVUwxVYi1RFGI0"，验证 token 提交到它那儿校验，通过后按你的流程放行；不用注册 Cloudflare、不用自建 sitekey | 免注册 | sitekey 是共享的，别人拿它刷量会连累你一起被 CF 限流；校验只回 HTML，没有 JSON API，要自己用表单或 iframe 接；站点跑在 InfinityFree 上，本身带 /aes.js 反爬挑战，服务端直连拿不到真页面（要先用它给的 AES cookie 过挑战），所以只能浏览器端用；第三方随时关停；认真做站还是自己注册 Turnstile——免费额度 100 万次/月，注册成本只有几分钟 | 2026-10-25 |

## AI 指令

30 条，分 6 类。都是完整指令，复制即用，不用再改。

| 分类 | 条数 | 代表 |
| :-- | :--: | :-- |
| 编程开发 | 7 | Scratch3项目生成器、TurboWarp扩展规划助手、全栈工程师编程规范 等 |
| 翻译语言 | 1 | HTML多语言翻译器 |
| 工具实用 | 7 | B站评论七重编码器、Silverfile系统总纲、图片搜索入口配置 等 |
| 角色风格 | 5 | Prompt优化助手、冷面反讽角色、指数级字数挑战 等 |
| 生成创作 | 6 | MathJax像素画引擎、Pollinations AI绘图助手、万能标题生成器 等 |
| 游戏棋类 | 4 | 国际象棋对弈助手、国际象棋开局法则、国际象棋规则 等 |

完整索引见 [`prompts/`](prompts/README.md)，一条一个文件。

## AI Skills

2 个，共 17 个文件。每个都是完整目录：`SKILL.md` + 脚本 + 模板，放进支持 Skill 的客户端（Claude Code、Codex、Kimi 等）就能用，不需要改代码。

| 技能 | 能干什么 | 文件 | 入口 |
| :-- | :-- | :--: | :-- |
| chrome-kernel-installer | 装无头 Chrome 内核，再用「截图编号」操作网页：点击、填表、抓接口 | 8 | [SKILL.md](skills/chrome-kernel-installer/SKILL.md) |
| pocket-explainer | 给一个主题或文档，产出带配音、字幕、章节条的成品 mp4，6 套主题可选 | 9 | [SKILL.md](skills/pocket-explainer/SKILL.md) |

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
