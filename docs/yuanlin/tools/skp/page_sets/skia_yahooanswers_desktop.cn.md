# skia_yahooanswers_desktop.py - Yahoo Answers 桌面端页面集定义

> 源文件: [tools/skp/page_sets/skia_yahooanswers_desktop.py](../../../tools/skp/page_sets/skia_yahooanswers_desktop.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于从 Yahoo Answers 网站（`http://answers.yahoo.com`）录制 Skia Picture（SKP）文件。Yahoo Answers 作为典型的问答社区网站，包含大量用户生成的文本内容、问答列表和社区投票元素，为桌面端文本密集型页面的渲染测试提供了测试用例。页面使用桌面用户代理访问，等待 15 秒加载。

注意：Yahoo Answers 服务已于 2021 年 5 月 4 日正式关闭。此页面集目前依赖 Web Page Replay 存档数据进行测试回放。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是桌面端 SKP 录制测试的标准成员。它与其他 Yahoo 页面集（Yahoo Sports）以及其他文本密集型页面集共同覆盖了问答类和内容类网站的渲染场景。

## 主要类与结构体

### `SkiaDesktopPage(page_module.Page)`
桌面端页面定义类。

**属性**：
- `shared_page_state_class`：`SharedDesktopPageState`
- `archive_data_file`：`'data/skia_yahooanswers_desktop.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 URL 并等待 15 秒

### `SkiaYahooanswersDesktopPageSet(story.StorySet)`
页面集合定义。

**URL**：`http://answers.yahoo.com`
**来源**：`go/skia-skps-3-2019`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaDesktopPage | URL 和父页面集 | 初始化桌面端页面 |
| `RunNavigateSteps(action_runner)` | SkiaDesktopPage | Telemetry action_runner | 导航并等待 15 秒 |
| `__init__()` | SkiaYahooanswersDesktopPageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **HTTP 协议**：使用不安全的 HTTP 协议访问。
2. **标准等待**：15 秒等待时间是桌面端页面集的标准值。
3. **WPR 依赖**：由于 Yahoo Answers 已关闭，此页面集完全依赖 WPR 存档进行回放测试。
4. **类命名**：使用 `SkiaDesktopPage` 而非 `SkiaBuildbotDesktopPage`，与 2019 年批次的其他页面集一致。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedDesktopPageState`
- **存档数据**：`data/skia_yahooanswers_desktop.json`（WPR 存档，此处存档特别重要因为原始网站已关闭）

## 设计模式与设计决策

- **WPR 存档的价值**：此页面集完美展示了 Web Page Replay 机制的价值 -- 即使原始网站已不存在，测试仍可基于存档数据继续运行。
- **文本密集型测试**：问答网站以文本为主，测试了 Skia 的文本布局、字体渲染和文本度量等功能。
- **遵循标准模式**：使用与其他 2019 年批次桌面端页面集相同的代码结构。
- **历史测试保留**：即使 Yahoo Answers 已关闭，保留此页面集仍有价值，因为其 WPR 存档代表了一种特定类型的网页布局。

## 性能考量

- 问答页面通常以文本为主，SKP 文件大小适中（相比图片密集型页面较小）。
- 文本渲染涉及字形缓存、文本整形（text shaping）和子像素定位等操作。
- 15 秒标准等待时间对文本页面通常绰绰有余。

## 相关文件

- `tools/skp/page_sets/data/skia_yahooanswers_desktop.json`：WPR 存档（关键依赖）
- `tools/skp/page_sets/skia_yahoosports_desktop.py`：另一个 Yahoo 桌面端页面集
- `tools/skp/page_sets/skia_cnn_desktop.py`：另一个桌面端内容页面集

### 补充说明

- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
