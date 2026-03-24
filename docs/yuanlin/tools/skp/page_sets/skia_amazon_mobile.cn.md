# skia_amazon_mobile.py - Amazon 移动端页面集定义

> 源文件: [tools/skp/page_sets/skia_amazon_mobile.py](../../../tools/skp/page_sets/skia_amazon_mobile.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于以移动端用户代理从 Amazon 搜索结果页面录制 Skia Picture（SKP）文件。页面 URL 包含搜索查询 "nicolas+cage"，其搜索结果页面展示了产品缩略图网格、价格标签、评分星标和赞助商标识等丰富的电商 UI 元素。Amazon 作为全球最大的电商平台，其移动端渲染是测试 Skia 在高密度内容页面表现的理想目标。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是移动端电商类网站的代表性测试用例。在 Skia 移动端页面集的电商覆盖中：
- **Amazon**（本文件）：零售产品搜索结果
- **Booking.com**：旅行酒店搜索结果

两者共同覆盖了电商搜索列表页的不同布局风格（Amazon 偏向紧凑列表，Booking 偏向大卡片）。

## 主要类与结构体

### `SkiaBuildbotMobilePage(page_module.Page)`
移动端页面定义类。

**注意**：此类命名为 `SkiaBuildbotMobilePage`，与其他移动端页面集使用的 `SkiaMobilePage` 略有不同，但功能完全等价。

**属性**：
- `shared_page_state_class`：`SharedMobilePageState`
- `archive_data_file`：`'data/skia_amazon_mobile.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 Amazon 搜索结果并等待 15 秒

### `SkiaAmazonMobilePageSet(story.StorySet)`
页面集合定义。

**URL**：`https://www.amazon.com/s?k=nicolas+cage&ref=is_box_`
**来源**：`go/skia-skps-3-2019`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaBuildbotMobilePage | URL 和父页面集 | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | SkiaBuildbotMobilePage | Telemetry action_runner | 导航并等待 15 秒 |
| `__init__()` | SkiaAmazonMobilePageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **HTTPS 协议**：使用安全的 HTTPS 连接。
2. **搜索参数**：URL 包含 `k=nicolas+cage`（搜索词）和 `ref=is_box_`（来源标识）参数。
3. **15 秒等待**：标准移动端等待时间，Amazon 的页面加载通常较快。
4. **类名差异**：使用 `SkiaBuildbotMobilePage` 而非大多数移动端页面集使用的 `SkiaMobilePage`，反映了不同作者或时期的命名习惯差异。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedMobilePageState`
- **存档数据**：`data/skia_amazon_mobile.json`

## 设计模式与设计决策

- **搜索结果页选择**：选择搜索结果页而非首页，因为产品列表页包含更多重复但复杂的 UI 元素（产品卡片），更能代表用户实际使用场景并测试列表渲染性能。
- **固定搜索词**：使用趣味性的固定搜索词（"nicolas cage"）确保结果可重复，同时搜索词本身不影响页面渲染特征。
- **电商场景覆盖**：与 Booking.com 形成电商类页面的多样化测试。Amazon 的产品搜索结果密度更高，图片更小但数量更多。
- **移动端优先**：Amazon 的移动端页面经过专门优化，使用不同于桌面端的响应式布局，测试了 Skia 在这种优化布局下的渲染表现。

## 性能考量

- Amazon 搜索结果包含大量产品图片缩略图，图像解码是主要的性能开销。
- 产品网格/列表布局测试了 Skia 在重复元素渲染中的效率（缓存和批处理优化的有效性）。
- 15 秒等待对于 Amazon 的快速页面加载策略通常足够。
- 移动端约束（小屏幕、受限 GPU）使渲染性能要求更为严格。
- 价格标签和评分星标涉及特殊字符和图标渲染。

## 相关文件

- `tools/skp/page_sets/data/skia_amazon_mobile.json`：WPR 存档数据
- `tools/skp/page_sets/skia_booking_mobile.py`：另一个电商类移动端页面集
- `tools/skp/page_sets/skia_facebook_mobile.py`：社交媒体移动端页面集
- `tools/skp/page_sets/skia_baidu_mobile.py`：搜索引擎移动端页面集
