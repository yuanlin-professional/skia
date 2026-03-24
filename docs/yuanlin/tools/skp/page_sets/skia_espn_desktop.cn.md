# skia_espn_desktop.py - ESPN 桌面端页面集定义

> 源文件: [tools/skp/page_sets/skia_espn_desktop.py](../../../tools/skp/page_sets/skia_espn_desktop.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于从 ESPN NFL 记分板页面（`https://www.espn.com/nfl/scoreboard`）录制 Skia Picture（SKP）文件。ESPN 是全球排名第一的体育网站，其记分板页面包含实时比分数据表、球队标识、动态更新元素和复杂的网格布局，为 Skia 桌面端渲染性能测试提供了数据密集型的体育网站测试场景。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是 Skia 渲染性能测试基础设施的一部分。它通过 Chromium Telemetry 框架驱动浏览器访问目标网页，录制的 SKP 文件用于 Skia 的渲染回归测试和性能基准测试。

在桌面端媒体类页面集中的定位：
- **体育**：ESPN（本文件）、Yahoo Sports
- **新闻**：CNN
- **科技媒体**：The Verge
- **问答社区**：Yahoo Answers

## 主要类与结构体

### `SkiaBuildbotDesktopPage(page_module.Page)`
继承自 Telemetry 的 `Page` 基类，定义单个桌面端网页的访问配置。

**属性**：
- `url`：页面 URL（通过构造函数传入）
- `name`：页面名称（与 URL 相同）
- `shared_page_state_class`：设置为 `SharedDesktopPageState`
- `archive_data_file`：`'data/skia_espn_desktop.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 URL 并等待 5 秒

### `SkiaEspnDesktopPageSet(story.StorySet)`
继承自 Telemetry 的 `StorySet` 基类。

**属性**：
- `archive_data_file`：`'data/skia_espn_desktop.json'`
- URL 列表仅包含 ESPN NFL 记分板
- 描述：`"Pages designed to represent the median, not highly optimized web"`
- 注释：`# Why: #1 sports.`（ESPN 作为排名第一的体育网站）

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaBuildbotDesktopPage | URL 和父页面集 | 初始化桌面端页面 |
| `RunNavigateSteps(action_runner)` | SkiaBuildbotDesktopPage | Telemetry action_runner | 导航并等待 5 秒 |
| `__init__()` | SkiaEspnDesktopPageSet | 无 | 初始化页面集并添加 URL |

## 内部实现细节

1. **特定子页面**：选择 `/nfl/scoreboard` 子页面而非 ESPN 首页，因为记分板页面包含更多数据表格和实时更新元素。
2. **短等待时间**：仅 5 秒（其他页面集通常 15-30 秒），可能因为记分板页面以静态数据为主，不需要等待大量异步加载。
3. **HTTPS 协议**：使用安全的 HTTPS 连接。
4. **2014 年版权**：这是最早一批添加的页面集之一。
5. **中位数代表**：StorySet 的文档字符串表明这些页面旨在代表"中位数性能、非高度优化"的网页。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedDesktopPageState`
- **存档数据**：`data/skia_espn_desktop.json`

## 设计模式与设计决策

- **行业领导者选择**：注释 `#1 sports` 表明选择标准是各类别中的领导者网站，这确保了测试的代表性和影响力。
- **Telemetry Story 标准模式**：遵循 Chromium Telemetry 的 StorySet/Page 模式。
- **Web Page Replay**：通过 `archive_data_file` 集成 WPR，确保测试可重复。
- **保守的等待策略**：5 秒可能不足以加载所有动态内容，但避免了过长的测试时间。

## 性能考量

- 5 秒是所有页面集中最短的等待时间之一，使测试运行快速。
- 记分板数据表格涉及大量文本渲染和网格布局计算。
- 球队标识图标测试了小图像的渲染效率。
- SKP 录制期间会捕获所有绘图命令，复杂页面可能生成较大的 SKP 文件。

## 相关文件

- `tools/skp/page_sets/data/skia_espn_desktop.json`：WPR 存档数据
- `tools/skp/page_sets/skia_yahoosports_desktop.py`：另一个体育类页面集
- `tools/skp/generate_page_set.py`：页面集生成工具
- `tools/skp/webpages_playback.py`：SKP 录制脚本
