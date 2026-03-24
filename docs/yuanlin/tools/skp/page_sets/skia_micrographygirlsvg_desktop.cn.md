# skia_micrographygirlsvg_desktop.py - Micrography Girl SVG 桌面端页面集定义

> 源文件: [tools/skp/page_sets/skia_micrographygirlsvg_desktop.py](../../../tools/skp/page_sets/skia_micrographygirlsvg_desktop.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于录制一个复杂 SVG 文件（micrography.svg）的渲染 SKP。该 SVG 文件托管在 Google Cloud Storage 上，是一个包含微缩字体艺术（micrography）的女孩图案 SVG，由大量精细路径和文本字形组成。其极高的路径复杂度使其成为测试 Skia SVG 渲染性能和路径栅格化能力的极佳压力测试用例。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是 SVG 渲染专项测试页面集家族的成员。与常规网页页面集不同，SVG 页面集直接加载矢量图形文件，专门测试 Skia 的 SVG 解析器、路径处理和渲染流水线。

SVG 测试页面集家族包括：
- `skia_micrographygirlsvg_desktop.py` — 微缩字体艺术 SVG（本文件）
- `skia_ynevsvg_desktop.py` — YNEV SVG
- `skia_carsvg_desktop.py` — 汽车矢量图 SVG

## 主要类与结构体

### `SkiaBuildbotDesktopPage(page_module.Page)`
桌面浏览器页面定义，继承自 Telemetry `Page` 基类。

**属性**：
- `shared_page_state_class`：`SharedDesktopPageState`
- `archive_data_file`：`'data/skia_micrographygirlsvg_desktop.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 SVG URL 并等待 15 秒

### `SkiaMicrographygirlsvgDesktopPageSet(story.StorySet)`
页面集合定义。

**URL**：`https://storage.googleapis.com/skia-recreateskps-bot-hosted-pages/micrography.svg`
**来源**：`skbug.com/40042116`

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaBuildbotDesktopPage | URL 和父页面集 | 初始化页面 |
| `RunNavigateSteps(action_runner)` | SkiaBuildbotDesktopPage | Telemetry action_runner | 导航并等待 15 秒 |
| `__init__()` | SkiaMicrographygirlsvgDesktopPageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **SVG 文件托管**：文件位于 `storage.googleapis.com/skia-recreateskps-bot-hosted-pages/` GCS 存储桶，这是 Skia 团队专门为 SKP 录制 bot 维护的静态资源托管位置。
2. **URL 拼接**：因 URL 较长，使用 Python 括号内隐式字符串连接跨行书写。
3. **15 秒等待**：SVG 文件在浏览器中的渲染可能涉及大量路径计算，15 秒确保复杂 SVG 完全渲染。
4. **2020 年添加**：版权标注为 2020 年，是较新添加的测试用例。
5. **Bug 驱动**：添加此页面集是为了解决或监控 skbug.com/40042116 中报告的渲染问题。

## 依赖关系

- **Telemetry 框架**：`telemetry.story`、`telemetry.page`、`telemetry.page.shared_page_state`
- **外部资源**：Google Cloud Storage 上的 `micrography.svg` 文件
- **存档数据**：`data/skia_micrographygirlsvg_desktop.json`

## 设计模式与设计决策

- **自托管测试资源**：将 SVG 文件托管在 Skia 控制的 GCS 存储桶中（而非引用第三方网站），确保测试资源长期稳定可用，不受外部网站变更或下线影响。
- **Bug 驱动测试添加**：因特定 Skia bug 而添加，确保该类渲染问题修复后有持续的回归监控。这是一种常见的质量保证实践。
- **SVG 作为渲染压力测试**：SVG 文件不同于普通网页，它直接测试矢量图形渲染路径，包括路径解析、贝塞尔曲线处理、填充规则和反锯齿等核心功能。
- **桌面端渲染**：使用桌面端配置以获得最大视口尺寸，使 SVG 以最大细节渲染。

## 性能考量

- 微缩字体艺术 SVG 包含极大量的细小路径和文本字形，对路径栅格化器是严苛的性能测试。
- 15 秒等待时间可能对于非常复杂的 SVG 仍然不够，但在实践中通常足够。
- 此类 SVG 可能生成非常大的 SKP 文件，因为每个路径和字形都会被记录为独立的绘图命令。
- SVG 渲染性能对于浏览器用例特别重要，因为 Web 上大量使用 SVG 图标和插图。

## 相关文件

- `tools/skp/page_sets/skia_ynevsvg_desktop.py`：YNEV SVG 测试页面集
- `tools/skp/page_sets/skia_carsvg_desktop.py`：汽车 SVG 测试页面集
- `tools/skp/page_sets/data/skia_micrographygirlsvg_desktop.json`：WPR 存档
- Skia 的 SVG 解析和渲染相关源码

### 补充说明

- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
- 此页面集是 Skia 渲染性能回归检测系统的重要测试资产，通过录制的 SKP 文件确保 Skia 渲染引擎在代码变更后保持稳定的渲染质量和性能。
