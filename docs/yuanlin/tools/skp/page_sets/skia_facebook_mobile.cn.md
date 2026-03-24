# skia_facebook_mobile.py - Facebook 移动端页面集定义

> 源文件: [tools/skp/page_sets/skia_facebook_mobile.py](../../../tools/skp/page_sets/skia_facebook_mobile.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于以移动端用户代理从 Facebook 的 Barack Obama 公开页面（`https://facebook.com/barackobama`）录制 Skia Picture（SKP）文件。Facebook 移动网站是全球访问量最高的社交媒体平台之一，其复杂的信息流布局、内嵌图片和视频缩略图、互动元素和动态加载机制为移动端渲染测试提供了极具代表性的社交媒体场景。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是移动端社交媒体类网站的代表性测试用例。在移动端页面集的类型分布中：
- **社交媒体**：Facebook（本文件）
- **搜索引擎**：百度、Google News
- **电商**：Amazon、Booking.com
- **新闻/内容**：CNN、Reddit 等

Facebook 的信息流渲染是移动端最具挑战性的场景之一，因为它包含高度异构的内容类型。

## 主要类与结构体

### `SkiaMobilePage(page_module.Page)`
移动端页面定义类。

**属性**：
- `shared_page_state_class`：`SharedMobilePageState`
- `archive_data_file`：`'data/skia_facebook_mobile.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 Facebook 页面并等待 30 秒

### `SkiaFacebookMobilePageSet(story.StorySet)`
页面集合定义。

**URL**：`https://facebook.com/barackobama`
**来源**：`go/skia-skps-3-2019`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaMobilePage | URL 和父页面集 | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | SkiaMobilePage | Telemetry action_runner | 导航并等待 30 秒 |
| `__init__()` | SkiaFacebookMobilePageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **公开页面选择**：使用 Barack Obama 的公开 Facebook 页面，避免了需要登录的复杂性（与 Google Docs 页面集形成对比）。
2. **HTTPS 协议**：使用安全的 HTTPS 连接。
3. **30 秒等待**：与 Booking.com 和 Digg 并列最长的等待时间，原因是 Facebook 的渐进式内容加载策略。
4. **无域名前缀**：URL 直接使用 `facebook.com` 而非 `www.facebook.com`。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedMobilePageState`
- **存档数据**：`data/skia_facebook_mobile.json`

## 设计模式与设计决策

- **公开页面规避认证**：选择公开的名人页面而非私人信息流，避免了认证复杂性和隐私问题。公开页面无需登录即可访问大量帖子内容。
- **社交媒体代表性**：Facebook 是全球最大的社交平台，其移动版网页的渲染特征对 Skia 在 Android Chrome 中的表现有直接影响。
- **长等待时间策略**：Facebook 使用复杂的客户端渲染框架（React），初始 HTML 较轻量但 JavaScript 渲染后内容丰富，30 秒确保 JS 应用完全启动。
- **信息流异构性**：Facebook 信息流包含文字帖子、图片、视频缩略图、链接预览、互动按钮等多种异构内容类型，是对 Skia 多功能渲染的全面测试。

## 性能考量

- Facebook 是最复杂的移动端测试页面之一，对 Skia 渲染性能是严苛的测试。
- 信息流中大量图片缩略图的解码和渲染是主要性能热点。
- React 框架的虚拟 DOM 更新可能导致频繁的重绘操作。
- 30 秒等待确保足够多的内容加载，但可能仍无法加载所有懒加载内容。
- 移动端设备的性能限制使这个测试尤为关键。

## 相关文件

- `tools/skp/page_sets/data/skia_facebook_mobile.json`：WPR 存档数据
- `tools/skp/page_sets/skia_amazon_mobile.py`：另一个移动端页面集
- `tools/skp/page_sets/skia_googlenews_mobile.py`：移动端新闻页面集

### 补充说明

- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
