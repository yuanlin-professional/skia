# skia_booking_mobile.py - Booking.com 移动端页面集定义

> 源文件: [tools/skp/page_sets/skia_booking_mobile.py](../../../tools/skp/page_sets/skia_booking_mobile.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于以移动端用户代理从 Booking.com 搜索结果页面录制 Skia Picture（SKP）文件。页面 URL 包含位于芬兰奥卢（坐标 65.0500N, 25.4667E）的地理搜索查询，其搜索结果页面展示了酒店卡片列表、评分和价格信息等复杂移动端电商布局。30 秒的等待时间是所有页面集中最长之一，反映了该页面大量异步内容的加载需求。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是移动端 SKP 录制测试的成员。在页面集的类型分类中，它代表了电子商务/旅行预订类移动网站的渲染场景，与 Amazon（零售电商）共同覆盖了电商类移动端测试。

## 主要类与结构体

### `SkiaMobilePage(page_module.Page)`
移动端页面定义，继承自 Telemetry `Page` 基类。

**属性**：
- `shared_page_state_class`：`SharedMobilePageState`
- `archive_data_file`：`'data/skia_booking_mobile.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到搜索结果 URL 并等待 30 秒

### `SkiaBookingMobilePageSet(story.StorySet)`
页面集合定义。

**URL**：`http://www.booking.com/searchresults.html?src=searchresults&latitude=65.0500&longitude=25.4667`
**来源**：`go/skia-skps-3-2019`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaMobilePage | URL 和父页面集 | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | SkiaMobilePage | Telemetry action_runner | 导航并等待 30 秒 |
| `__init__()` | SkiaBookingMobilePageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **地理搜索 URL**：URL 包含 `latitude=65.0500&longitude=25.4667`（芬兰奥卢）的坐标参数，直接加载特定地区的酒店搜索结果。
2. **URL 字符串连接**：因 URL 较长，使用 Python 括号内隐式字符串连接跨行书写。
3. **30 秒等待**：所有移动端页面集中最长的等待时间之一，原因是 Booking.com 搜索结果页面的渐进加载特性。
4. **HTTP 协议**：使用 HTTP（可能重定向到 HTTPS）。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedMobilePageState`
- **存档数据**：`data/skia_booking_mobile.json`

## 设计模式与设计决策

- **搜索结果页选择**：选择搜索结果页而非首页，因为结果列表包含更多重复且复杂的 UI 组件（酒店卡片），更能代表实际用户使用场景。
- **长等待时间**：Booking.com 使用渐进式加载策略，酒店卡片、图片、价格和地图可能分批异步加载，30 秒确保足够多的内容呈现。
- **特定地理查询**：使用固定坐标确保结果可重复，同时芬兰奥卢作为较小城市可能产生适中数量的搜索结果。
- **移动端电商测试**：与 Amazon 移动端共同覆盖电商场景，但 Booking.com 的卡片式布局与 Amazon 的网格式产品列表有显著差异。

## 性能考量

- Booking.com 搜索结果包含大量酒店卡片，每张卡片含图片、文本、评分星标等多种元素。
- 移动端渲染受设备性能限制，此页面是移动端性能压力测试的良好目标。
- 30 秒等待增加了整体测试时间，但确保了 SKP 内容的完整性。
- 地图嵌入（如果有）增加了额外的渲染复杂度。

## 相关文件

- `tools/skp/page_sets/data/skia_booking_mobile.json`：WPR 存档数据
- `tools/skp/page_sets/skia_amazon_mobile.py`：另一个电商类移动端页面集
- 其他移动端页面集（Facebook、百度等）

### 补充说明

- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
