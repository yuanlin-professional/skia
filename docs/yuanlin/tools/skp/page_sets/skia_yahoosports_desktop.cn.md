# skia_yahoosports_desktop.py - Yahoo Sports 桌面端页面集定义

> 源文件: [tools/skp/page_sets/skia_yahoosports_desktop.py](../../../tools/skp/page_sets/skia_yahoosports_desktop.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于从 Yahoo Sports 网站（`http://sports.yahoo.com`）录制 Skia Picture（SKP）文件。Yahoo Sports 是一个主流体育新闻和数据网站，其页面包含丰富的体育赛事数据表格、实时比分、图片和动态内容，为桌面端渲染测试提供了数据密集型布局的测试场景。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是桌面端 SKP 录制测试的标准成员。在 Skia 的页面集分类中，它与 ESPN 共同覆盖了体育类网站的渲染场景，而 Yahoo Sports 相比 ESPN 可能有不同的页面结构和渲染复杂度。

该文件与 `skia_yahooanswers_desktop.py` 同属 Yahoo 系列测试，覆盖了 Yahoo 产品线中不同类型的页面。

## 主要类与结构体

### `SkiaDesktopPage(page_module.Page)`
桌面端页面定义类。

**属性**：
- `shared_page_state_class`：`SharedDesktopPageState`
- `archive_data_file`：`'data/skia_yahoosports_desktop.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 URL 并等待 15 秒

### `SkiaYahoosportsDesktopPageSet(story.StorySet)`
页面集合定义。

**URL**：`http://sports.yahoo.com`
**来源**：`go/skia-skps-3-2019`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaDesktopPage | URL 和父页面集 | 初始化桌面端页面 |
| `RunNavigateSteps(action_runner)` | SkiaDesktopPage | Telemetry action_runner | 导航并等待 15 秒 |
| `__init__()` | SkiaYahoosportsDesktopPageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **HTTP 协议**：使用不安全的 HTTP 协议（可能会被重定向到 HTTPS）。
2. **标准等待**：15 秒标准桌面端等待时间。
3. **首页访问**：直接访问 `sports.yahoo.com` 首页（而非特定赛事页面），获得综合性的体育新闻布局。
4. **添加于 2019 年**：属于 `go/skia-skps-3-2019` 批次。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedDesktopPageState`
- **存档数据**：`data/skia_yahoosports_desktop.json`

## 设计模式与设计决策

- **体育网站多样性**：与 ESPN 共同测试体育类网站，但 Yahoo Sports 可能使用不同的前端框架和布局策略，测试了 Skia 对不同实现方式的兼容性。
- **遵循标准模式**：使用与同批次其他桌面端页面集完全一致的代码结构。
- **首页选择**：选择首页而非深层页面，因为首页通常是访问量最高、内容最丰富的页面。
- **Yahoo 系列覆盖**：Yahoo Sports + Yahoo Answers 覆盖了 Yahoo 不同产品线的渲染特征。

## 性能考量

- 体育网站首页通常包含大量实时数据表格和图片，渲染复杂度较高。
- 数据表格对 Skia 的文本度量和网格布局渲染是有效的测试。
- 15 秒等待确保异步加载的比分数据和广告内容完成渲染。

## 相关文件

- `tools/skp/page_sets/skia_espn_desktop.py`：另一个体育类桌面端页面集
- `tools/skp/page_sets/skia_yahooanswers_desktop.py`：另一个 Yahoo 桌面端页面集
- `tools/skp/page_sets/data/skia_yahoosports_desktop.json`：WPR 存档

### 补充说明

- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
