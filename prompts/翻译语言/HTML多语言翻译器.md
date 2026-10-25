# 英文 HTML 页面中文本地化指令 v3.1

## 一、适用范围

本指令适用于任何国外英文 HTML 页面的中文翻译与本地化适配，包括但不限于：

- 单页应用（SPA）
- 静态信息页面
- 交互式工具 / 可视化页面
- 创意写作 / 艺术项目
- 个人博客 / 作品集
- 数据展示页面

---

## 二、核心原则（必须遵守）

1. **保留设计灵魂**：不改变布局、动画、交互节奏、视觉氛围
2. **完整覆盖可见文本**：HTML + CSS 伪元素 + JavaScript 动态文本
3. **本地化示例数据**：城市、人名、地点、日期格式全部替换
4. **保持功能等效**：分享、搜索、定位等核心功能必须正常工作
5. **交互行为不变**：用户操作流程、反馈逻辑、动画效果保持一致
6. **JS 按需调整**：若原逻辑依赖国外数据 / API / 平台，进行等价替换而非硬改
7. **代码中禁止出现引用标签**：如 `[reference:5]`、`[1]`、`[^note]` 等任何形式的引用标注，保持代码干净

---

## 三、JavaScript 调整情景与应对策略

### 情景 A：数据数组（直接替换）

**识别**：JavaScript 中有硬编码的城市列表、标签列表、分类列表等。

**应对**：替换为国内等价的、数量相当的数据。

```js
const CITIES = ['Mexico City', 'London', 'San Francisco', 'Delhi', 'Seattle', 'Oslo', 'Kyoto'];
// ↓
const CITIES = ['北京', '上海', '深圳', '成都', '杭州', '西安', '南京'];
```

**需注意**：

- 保持数组长度一致（若用于随机 / 循环，长度变化可能影响逻辑）
- 若页面存在真实的地理逻辑（如根据城市名查询经纬度、调用天气 API 等），替换城市名的同时必须同步更新对应的经纬度数据或 API 查询参数，确保 JS 逻辑可正常运行

---

### 情景 B：键值映射 / 字典（替换键值）

**识别**：对象 / Map 做名称映射，如颜色名、状态码、来源名等。

**应对**：替换所有值，保留键名（若键名用于内部逻辑）或同时替换键名（若键名用于显示）。

```js
const COLOR_NAMES = { pearl: 'Pearl', rose: 'Rose', amber: 'Amber' };
// ↓
const COLOR_NAMES = { pearl: '珍珠灰', rose: '玫瑰粉', amber: '琥珀色' };

const SOURCE_NAMES = { california: 'California', canada: 'Quebec', sonora: 'Sonora' };
// ↓
const SOURCE_NAMES = { yunnan: '云南', sichuan: '四川', inner_mongolia: '内蒙古' };
```

---

### 情景 C：地理 / 气候推断逻辑（调整范围）

**识别**：函数包含经纬度范围、季节判断，用于推断火灾、沙尘、气候类型等。

**应对**：将国外的经纬度 / 区域映射替换为国内等效区域。

```js
function inferFireSource(lat, lng, month) {
    // 原：推断北美火源
    if (lat > 32 && lat < 50 && lng > -125 && lng < -115 && month >= 5 && month <= 9) {
        return 'California';
    }
    if (lat > 35 && lat < 52 && lng > -90 && lng < -60 && month >= 4 && month <= 8) {
        return 'Quebec';
    }
    return 'distant';
}
// ↓
function inferFireSource(lat, lng, month) {
    // 改为：推断中国火源
    if (lat > 18 && lat < 54 && lng > 73 && lng < 135) {
        if (month >= 2 && month <= 5 && lat > 20 && lat < 30 && lng > 98 && lng < 108) {
            return '云南';
        }
        if (month >= 3 && month <= 6 && lat > 26 && lat < 32 && lng > 98 && lng < 108) {
            return '四川';
        }
        if (month >= 4 && month <= 7 && lat > 36 && lat < 42 && lng > 110 && lng < 120) {
            return '内蒙古';
        }
        if (month >= 10 && month <= 12 && lat > 20 && lat < 26 && lng > 108 && lng < 118) {
            return '广东';
        }
        return '中国境内';
    }
    return '远处';
}
```

---

### 情景 D：外部 API 调用（完全不动）

**识别**：`fetch()`、`XMLHttpRequest` 调用外部 API，返回数据用于展示。

**应对**：

- **API 返回的 JSON / 数据完全不动**，保持原值用于逻辑判断
- **不添加 `?lang=zh-CN` 等语言参数**，不修改 API 请求的任何参数
- API 仅支持国外地区：需寻找替代 API 或调整查询参数

**注意**：API 返回的是逻辑数据，不是用户可见文本，翻译会破坏后续条件判断。

```js
// 错误：直接翻译会破坏后续逻辑判断
if (data.weather === '晴朗') { ... } // 原 API 返回的是 'sunny'，这里永远进不去

// 正确：保持原值用于逻辑
if (data.weather === 'sunny') { ... }
```

---

### 情景 E：日期 / 时间 / 格式化（使用 locale）

**识别**：`toLocaleString()`、`toLocaleDateString()`、`Intl.DateTimeFormat()` 等。

**应对**：统一使用 `'zh-CN'` locale。

```js
date.toLocaleString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })
// ↓
date.toLocaleString('zh-CN', { month: 'long', day: 'numeric', year: 'numeric' })
```

---

### 情景 F：示例 / 演示数据（完全替换，但用户名保留）

**识别**：用于演示的静态数据（用户评论、文章列表、作品展示等）。

**应对**：替换为国内等价内容，保持数据结构和数量一致。**评论 / 文章中的用户名保持原文**，不翻译。

```js
const DEMO_ARTICLES = [
    { title: 'The Color of Sky', author: 'John Doe', date: '2025-03-15' },
    { title: 'What We Miss', author: 'Jane Smith', date: '2025-02-28' }
];
// ↓
const DEMO_ARTICLES = [
    { title: '天空的颜色', author: 'John Doe', date: '2025-03-15' },
    { title: '我们错过了什么', author: 'Jane Smith', date: '2025-02-28' }
];
```

---

### 情景 G：分享 / 社交平台 URL（双向切换）

**识别**：`window.open()`、`navigator.share()` 中包含国外平台 URL。

**应对**：**必须同时保留国内和国外两套平台**，支持双向切换，不能只替换为单一平台。

**深度适配时**：国内外两套 JS 逻辑都必须完整保留且可正常运行，用户可自由选择分享到国内或国外平台。

```js
// 原：仅国外平台
function share(platform) {
    const urls = {
        twitter: 'https://twitter.com/intent/tweet?text=...',
        facebook: 'https://www.facebook.com/sharer/...'
    };
    window.open(urls[platform]);
}
// ↓
// 改为：国内外平台并存，支持切换
function share(platform) {
    const urls = {
        // 国外平台
        twitter: 'https://twitter.com/intent/tweet?text=...',
        facebook: 'https://www.facebook.com/sharer/...',
        // 国内平台
        weibo: 'https://service.weibo.com/share/share.php?title=...',
        qq: 'https://connect.qq.com/widget/shareqq/index.html?title=...',
        copy: () => navigator.clipboard.writeText('...')
    };
    if (platform === 'copy') return urls.copy();
    window.open(urls[platform]);
}
```

---

### 情景 H：正则表达式 / 字符串匹配（区分用途）

**识别**：使用正则表达式匹配用户输入、解析 URL、提取文本等。

**应对**：先判断正则用途，再决定是否扩展：

- **用户输入验证**（如城市名、搜索关键词、表单字段）：在保留原有匹配逻辑的同时，扩展支持中文字符
- **数据结构提取**（如解析 API JSON、提取 URL 参数、匹配英文标识符）：**保持原样不动**，不扩展中文

```js
// 用户输入验证 → 扩展中文
const cityPattern = /^[a-zA-Z\s,]+$/;
// ↓
const cityPattern = /^[\u4e00-\u9fa5a-zA-Z\s,·\-]+$/;

// API 数据结构提取 → 保持原样
const keyPattern = /"title":\s*"([^"]+)"/;
// 不动
```

---

### 情景 I：随机文本 / 模板系统（完整翻译）

**识别**：`pick()`、`random()` 从数组中选取句子或词组。

**应对**：翻译整个数组，保留原模板变量（如 `{city}`、`{time}` 等）。

```js
const OPENINGS = [
    `Yesterday in {city}, the sun set at {time}.`,
    `In {city} yesterday, the day ended at {time}.`
];
// ↓
const OPENINGS = [
    `昨日在{city}，太阳在{time}落下。`,
    `{city}的昨日，白昼在{time}结束。`
];
```

**注意**：模板变量名（`{city}`）保持不变，仅翻译句子。

---

### 情景 J：计数 / 数字格式（使用 locale）

**识别**：`toLocaleString()` 用于数字千位分隔。

**应对**：使用 `'zh-CN'` locale。

```js
number.toLocaleString('en-US')
// ↓
number.toLocaleString('zh-CN')
```

---

## 四、JS 改动决策矩阵

| 改动类型 | 风险等级 | 是否需要测试 | 回退策略 |
|---------|---------|------------|---------|
| 硬编码数据替换（A / B / F） | 低 | 否 | 保留原数组注释 |
| 地理推断重写（C） | 高 | 必须 | 保留原函数备用 |
| API 调用（D） | 低 | 否 | 完全不动，无需回退 |
| 正则扩展（H） | 低 | 否 | 原正则保留为或分支 |
| 平台 URL 替换（G） | 中 | 是 | 保留国外平台入口 |
| Locale 切换（E / J） | 低 | 否 | 改回 `'en-US'` 即可 |

---

## 五、JS 改动安全原则

1. **不删除原有功能**：仅替换、扩展、适配，不削减
2. **保留变量名**：不改变外部引用的变量 / 函数名
3. **添加而非替换**：优先使用 `if` 判断添加分支，而非覆盖
4. **保留 fallback**：若新数据 / API 不可用，回退到原有逻辑
5. **不改变数据流**：数据获取 → 处理 → 渲染的流程保持不变

---

## 六、完整适配流程

### 第一步：全面扫描

- 搜索 `.js` 代码中所有 `'en-US'`、`'en'` → 替换为 `'zh-CN'`
- 搜索所有硬编码的城市 / 地名 / 人名 → 按对照表替换
- 搜索所有国外平台 URL → 按对照表替换
- 搜索所有 `console.log`（可选替换为中文注释或删除）
- **代码注释也要翻译**（包括单行 `//` 和多行 `/* */` 注释，保留原注释位置，仅将英文内容译为中文）

### 第二步：逻辑适配

- 识别所有地理推断函数 → 重写为国内范围
- 识别所有 API 调用 → 检查返回数据结构，**完全不动**
- 识别所有正则表达式 → 区分用途后决定是否扩展中文字符

### 第三步：平台适配

- 分享功能 → 添加国内平台 + 国内外切换（深度适配时两套逻辑都要保留）
- 社交链接 / 作者账号 → 访问 HTML 中提供的作者链接，若链接可正常访问则保留；若无法访问，则在网络中搜索该作者的其他账户链接（微博、B站、小红书等），找到可访问的链接后替换
- 代码平台链接 → GitHub 国内可用，不替换；其他平台（CodePen、JSFiddle、StackBlitz 等）若国内无法访问且找不到类似替代品，首选 GitHub 或 CSDN 替代（但不限于这两个）
- 地图 / 位置服务 → 若使用 Google Maps，需替换为高德 / 百度（需额外处理）

### 第四步：测试验证

- 所有按钮 / 输入框正常工作
- 所有动态文本正确显示
- 所有链接跳转正确
- 所有分享功能可正常打开
- 页面在不同屏幕尺寸下表现一致

---

## 七、平台与地名完整对照表（通用版）

### 社交媒体 / 内容平台

| 国外平台 | 国内替代 / 对应 | 国内俗称 |
|---------|---------------|---------|
| Twitter / X | 微博 | 推特 |
| Facebook | 无直接对应（保留或移除） | 脸书 |
| Instagram | 小红书 / 微博 | — |
| YouTube | Bilibili（B站） | 油管 |
| Reddit | 知乎 / 贴吧 | — |
| WhatsApp | 微信 | — |

### 代码 / 开发平台

| 国外平台 | 处理方式 |
|---------|---------|
| GitHub | 国内可用，**不替换** |
| CodePen | 国内可能无法访问，首选 GitHub 或 CSDN 替代（但不限于这两个） |
| JSFiddle | 同上 |
| StackBlitz | 同上 |
| Glitch | 同上 |

### 城市

| 国外城市 | 国内对应 |
|---------|---------|
| Mexico City | 北京 |
| London | 上海 |
| San Francisco | 深圳 |
| Delhi | 成都 |
| Seattle | 杭州 |
| Oslo | 西安 |
| Kyoto | 南京 |

### 自然地理

| 国外区域 | 国内对应 |
|---------|---------|
| California | 云南 / 四川 / 内蒙古（按纬度对应） |
| Quebec | 东北三省 |
| Sonora | 新疆 / 甘肃 |
| Sahara | 塔克拉玛干沙漠 |
| Amazon | 西双版纳 / 海南热带雨林 |

---

## 八、快速检查清单（适配完成后）

- [ ] `<html lang="zh-CN">`
- [ ] 所有 `<meta>` 标签（title、description、keywords）已翻译
- [ ] 所有可见静态文本已翻译（按钮、标签、标题、段落、提示）
- [ ] CSS 伪元素（`::before`、`::after` 的 `content`）已翻译
- [ ] JavaScript 中所有硬编码字符串（数组、对象值、模板字符串）已翻译
- [ ] JavaScript 中所有代码注释已翻译
- [ ] JavaScript 中所有 `toLocaleString` 使用 `'zh-CN'`
- [ ] 所有示例数据（城市、人名、标签）已替换为国内内容，**且同步更新了相关经纬度 / 地理逻辑**
- [ ] 地理 / 气候推断逻辑已调整为国内范围
- [ ] 分享平台已同时保留国内 + 国外平台，支持双向切换
- [ ] 作者账号 / 社交链接已处理：原链接可访问则保留，无法访问则搜索作者其他账户链接替换
- [ ] 代码平台链接已处理（GitHub 保留，其他无法访问的已替换）
- [ ] 翻译脚注已添加（译者占位符 `{{TRANSLATOR_NAME}}`）
- [ ] 所有外部链接正常跳转
- [ ] 交互功能完整可用（输入、按钮、动画、分享）
- [ ] 页面在不同屏幕尺寸下表现正常

---

**指令版本：3.1（优化版）**

**适用范围：所有国外 HTML 页面**

**核心更新**：
- 增加代码注释翻译要求
- API 返回数据完全不动，不添加语言参数
- 评论用户名保持原文
- 正则表达式区分用途处理
- 代码平台链接单独处理（GitHub 保留）
- 深度适配时两套 JS 逻辑都保留
- 城市数据替换需同步更新地理逻辑
- 平台名称标注国内俗称
- 禁止代码中出现引用标签

**最后更新：2026年7月**
