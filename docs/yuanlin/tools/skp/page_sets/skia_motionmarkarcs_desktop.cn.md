# Skia MotionMark Arcs 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_motionmarkarcs_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 MotionMark Arcs 桌面端页面集。它加载托管在 Google Cloud Storage 上的 MotionMark 圆弧动画基准测试 SVG 文件，用于测试 Skia 对 SVG 圆弧路径渲染的性能。MotionMark 是一个广泛使用的浏览器图形性能基准测试套件。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：SVG 圆弧路径渲染性能基准

## 主要类与结构体

### `SkiaBuildbotDesktopPage`
- 继承自 `page_module.Page`，使用 `SharedDesktopPageState`
- 导航后等待 20 秒以确保 SVG 动画完全加载和渲染

### `SkiaMotionmarkarcsDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：`desk_motionmark_arcs.svg`（托管于 Google Cloud Storage）
- 参考来源：skbug.com/40042884

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotDesktopPage` | 初始化页面 |
| `RunNavigateSteps(action_runner)` | `SkiaBuildbotDesktopPage` | 导航到 SVG 并等待 20 秒 |
| `__init__()` | `SkiaMotionmarkarcsDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- SVG 文件托管在 `storage.googleapis.com/skia-recreateskps-bot-hosted-pages/`，这是 Skia 团队专用的静态资源托管位置
- 20 秒等待确保 SVG 内部的动画帧全部被处理

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_motionmarkarcs_desktop.json`
- 外部资源：Google Cloud Storage 上托管的 MotionMark SVG 文件

## 设计模式与设计决策

- 使用 MotionMark 标准化基准测试场景，确保与浏览器性能测试的可比性
- SVG 圆弧路径特别测试 Skia 的 `SkPath::arcTo` 和相关曲线绘制代码路径

## 性能考量

- MotionMark Arcs 测试大量圆弧绘制操作，对 Skia 的路径 tessellation 和反锯齿性能构成挑战
- SVG 渲染涉及 DOM 解析和路径转换，测试 Skia 的 SVG 模块效率

## 相关文件

- `tools/skp/page_sets/skia_motionmarksuits_desktop.py` - MotionMark Suits 测试
- `tools/skp/page_sets/skia_motionmarkpaths_desktop.py` - MotionMark Paths 测试
- `tools/skp/page_sets/skia_motionmarksuitsclip_desktop.py` - MotionMark Suits Clip 测试

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（MotionMark Arcs SVG），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- MotionMark 系列测试是浏览器图形性能的行业标准基准
- 圆弧路径在 Skia 中通过 conic section 近似实现，测试该近似的性能和精度

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
