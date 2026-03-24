# skia_googlenews_mobile.py - Google News 移动端页面集定义

> 源文件: [tools/skp/page_sets/skia_googlenews_mobile.py](../../../tools/skp/page_sets/skia_googlenews_mobile.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于以移动端用户代理从 Google News（`https://news.google.com/`）录制 Skia Picture（SKP）文件。Google News 的移动版页面包含新闻卡片布局、图片缩略图和动态加载内容，是测试 Skia 移动端渲染性能的典型新闻聚合应用场景。作为 Google 自家产品，其页面结构相对稳定，是可靠的长期测试目标。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是移动端 SKP 录制测试的一部分。与桌面端页面集使用 `SharedDesktopPageState` 不同，此文件使用 `SharedMobilePageState` 模拟移动浏览器环境，包括较小的视口尺寸和移动端用户代理字符串。

移动端页面集在 Skia 性能测试中特别重要，因为：
- 移动设备的 GPU 和 CPU 资源更有限
- 移动端布局触发不同的 CSS 响应式路径
- 触摸交互可能导致不同的渲染模式

## 主要类与结构体

### `SkiaMobilePage(page_module.Page)`
移动端页面定义，继承自 Telemetry `Page` 基类。

**属性**：
- `shared_page_state_class`：`SharedMobilePageState`（模拟移动浏览器）
- `archive_data_file`：`'data/skia_googlenews_mobile.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 URL 并等待 15 秒

### `SkiaGooglenewsMobilePageSet(story.StorySet)`
页面集合定义。

**URL**：`https://news.google.com/`
**来源**：`go/skia-skps-3-2019`（2019 年 3 月 SKP 更新计划）

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaMobilePage | URL 和父页面集 | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | SkiaMobilePage | Telemetry action_runner | 导航并等待 15 秒 |
| `__init__()` | SkiaGooglenewsMobilePageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **移动端模拟**：`SharedMobilePageState` 配置浏览器以移动设备模式运行，包括设置移动端 viewport（通常 360px 宽）和 User-Agent 字符串。
2. **导航等待**：15 秒等待时间确保 Google News 的 JavaScript 应用完全初始化并加载新闻卡片内容。
3. **HTTPS 协议**：使用安全的 HTTPS 连接。
4. **2019 年添加**：版权为 2019 年，属于 `go/skia-skps-3-2019` 批次更新的一部分。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`：故事集基类
  - `telemetry.page.page.Page`：页面基类
  - `telemetry.page.shared_page_state.SharedMobilePageState`：移动端浏览器状态
- **存档数据**：`data/skia_googlenews_mobile.json`

## 设计模式与设计决策

- **移动端页面集标准模式**：使用 `SkiaMobilePage` + `SharedMobilePageState` 的标准组合，与其他移动端页面集保持一致。
- **Google 产品选择**：Google News 作为 Google 自家产品，页面结构变更频率可控，测试可靠性较高。
- **新闻卡片布局**：Google News 的卡片式信息流布局是移动端的典型 UI 模式，测试了列表渲染、图片加载和滚动性能等关键路径。
- **与桌面版本差异**：移动版 Google News 的布局与桌面版显著不同，单独测试确保移动端渲染路径被覆盖。

## 性能考量

- 移动端渲染通常比桌面端有更严格的性能要求，因为设备硬件能力有限。
- 15 秒等待确保动态新闻卡片和缩略图完全加载。
- Google News 使用 JavaScript 框架进行客户端渲染，初始加载后可能有大量 DOM 变更。
- 新闻图片缩略图的解码和渲染对 Skia 的图像处理路径是有效的测试。

## 相关文件

- `tools/skp/page_sets/data/skia_googlenews_mobile.json`：WPR 存档数据
- `tools/skp/page_sets/skia_facebook_mobile.py`：另一个移动端页面集（社交）
- `tools/skp/page_sets/skia_amazon_mobile.py`：另一个移动端页面集（电商）
- `tools/skp/page_sets/skia_baidu_mobile.py`：另一个移动端页面集（搜索）
- `tools/skp/page_sets/skia_booking_mobile.py`：另一个移动端页面集（旅行）

### 补充说明

- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
