# Skia Wikipedia 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_wikipedia_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 Wikipedia 桌面端页面集。通过加载维基百科首页来进行字体压力测试。维基百科首页包含数十种语言的文本内容，是测试 Skia 多语言字体 shaping 和渲染性能的理想场景。此页面集自 2015 年起一直是 Skia 字体子系统的关键基准测试之一。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：多语言字体渲染压力测试（参见 skbug.com/40034705）

## 主要类与结构体

### `SkiaBuildbotDesktopPage`
- 继承自 `page_module.Page`，使用 `SharedDesktopPageState`
- 未覆写导航和交互方法，使用默认行为

### `SkiaWikipediaDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：`http://www.wikipedia.org/`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotDesktopPage` | 初始化桌面端页面 |
| `__init__()` | `SkiaWikipediaDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- 维基百科首页在同一页面上展示多种语言和文字系统（拉丁文、中文、阿拉伯文、日文、韩文等）
- 未设置额外等待和交互，因为首页内容相对较少但字体多样性高

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_wikipedia_desktop.json`

## 设计模式与设计决策

- 注释明确标注此页面为"字体压力测试"（stress tests for fonts），来源于 skbug.com/40034705
- 选择维基百科首页而非特定语言版本，以覆盖最多种文字系统

## 性能考量

- 同时加载数十种字体对 Skia 的字体缓存管理和字形查找表构成压力
- 多种文字系统的 shaping 规则不同，测试 HarfBuzz 等文本 shaping 引擎的集成性能
- 页面较轻量（无长等待），适合快速迭代测试

## 相关文件

- `tools/skp/page_sets/skia_gujuratiwiki_desktop.py` - 特定语言字体测试
- `tools/skp/page_sets/skia_worldjournal_tablet.py` - CJK 字体测试

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（维基百科首页），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 维基百科首页展示数十种语言，是全互联网上文字系统多样性最高的页面之一
- 字体回退（font fallback）机制在此页面上被频繁触发

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
