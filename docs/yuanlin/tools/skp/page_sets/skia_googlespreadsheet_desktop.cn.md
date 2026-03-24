# Skia Google Spreadsheet 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_googlespreadsheet_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 Google Spreadsheet（谷歌电子表格）桌面端页面集。通过加载 Google Docs 电子表格页面来测试 Skia 对复杂 Web 应用程序的渲染性能。电子表格包含大量网格线、单元格和文本内容，对 Skia 的线条绘制和文本渲染提出高要求。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：复杂 Web 应用渲染性能

## 主要类与结构体

### `SkiaBuildbotDesktopPage`
- 继承自 `page_module.Page`，使用 `SharedDesktopPageState`
- 未覆写导航和交互方法

### `SkiaGooglespreadsheetDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：Google Docs 上的特定电子表格

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotDesktopPage` | 初始化桌面端页面 |
| `__init__()` | `SkiaGooglespreadsheetDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- URL 使用字符串拼接处理超长 Google Docs URL
- 来源于"Tom W's list"，是团队成员提供的具有代表性的测试页面

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_googlespreadsheet_desktop.json`

## 设计模式与设计决策

- Google 电子表格使用 Canvas 2D 渲染大量内容，是测试 Skia Canvas 后端性能的理想场景
- 电子表格包含规则的网格结构，测试 Skia 的直线绘制和裁剪优化

## 性能考量

- 电子表格渲染涉及大量规则几何图形（网格线、边框），测试 Skia 的批处理和硬件加速能力
- 大量小文本渲染（单元格内容）对字形缓存命中率有高要求

## 相关文件

- `tools/skp/page_sets/data/skia_googlespreadsheet_desktop.json`
- `tools/skp/page_sets/skia_googlesearch_mobile.py` - 另一个 Google 产品页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（Google 电子表格），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 电子表格使用 Canvas 2D API 进行自定义渲染，而非标准 DOM 布局
- 大量规则网格线的绘制对 Skia 的直线渲染路径进行了集中测试
- 单元格文本渲染涉及大量小字号文本的精确定位

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
