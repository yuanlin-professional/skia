# Skia WoW Wiki 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_wowwiki_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 WoW Wiki（魔兽世界维基）桌面端页面集。通过 Chromium Telemetry 框架加载 Fandom 平台上的魔兽世界维基页面，录制 SKP 文件。该页面以内容极其丰富、页面长度极长为特点，是 Skia 大页面滚动渲染性能的重要测试用例。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：超长页面滚动渲染性能

## 主要类与结构体

### `SkiaBuildbotDesktopPage`
- 继承自 `page_module.Page`
- 使用 `SharedDesktopPageState` 桌面端共享状态
- 导航后执行 600 万像素的大规模滚动，然后等待 60 秒

### `SkiaWowwikiDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：魔兽世界巫妖王之怒 Wiki 页面

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotDesktopPage` | 初始化桌面端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaBuildbotDesktopPage` | 导航、滚动 6000000 像素并等待 60 秒 |
| `__init__()` | `SkiaWowwikiDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- `ScrollPage(distance=6000000)`：执行超大距离滚动（600 万像素），目的是触发整个超长页面的完整渲染
- 60 秒等待时间远超其他页面集（通常 5-20 秒），因为大规模滚动会触发大量懒加载内容
- URL 使用字符串拼接来处理超长 URL 的代码可读性

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_wowwiki_desktop.json`

## 设计模式与设计决策

- 选择 WoW Wiki 页面是因为它是互联网上内容最为丰富的单页面之一，包含大量图片、表格和文本
- 大距离滚动（600 万像素）确保 Skia 需要处理页面中所有可见区域的渲染

## 性能考量

- 此页面是所有页面集中最耗时的测试之一（60 秒等待）
- 测试 Skia 对超大 SKP 文件的处理能力，包括内存管理和渲染吞吐量
- 大规模滚动触发 Skia 的图块管理和纹理缓存策略

## 相关文件

- `tools/skp/page_sets/data/skia_wowwiki_desktop.json`
- `tools/skp/page_sets/skia_wikipedia_desktop.py` - 另一个桌面端维基页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（WoW Wiki），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 超长页面的 SKP 文件大小可能显著大于普通页面，测试 Skia 的大文件处理能力
- 600 万像素的滚动距离确保页面内所有懒加载内容被触发

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
