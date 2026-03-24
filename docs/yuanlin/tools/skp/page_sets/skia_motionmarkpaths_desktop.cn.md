# Skia MotionMark Paths 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_motionmarkpaths_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 MotionMark Paths 桌面端页面集。加载 MotionMark 基准测试中的路径渲染（Paths）SVG 动画，专门用于测试 Skia 对大量复杂路径的描边和填充渲染性能。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：SVG 路径渲染性能基准

## 主要类与结构体

### `SkiaBuildbotDesktopPage`
- 继承自 `page_module.Page`，使用 `SharedDesktopPageState`
- 导航后等待 20 秒

### `SkiaMotionmarkpathsDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：`motionmark_paths.svg`
- 参考来源：skbug.com/40042619

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotDesktopPage` | 初始化页面 |
| `RunNavigateSteps(action_runner)` | `SkiaBuildbotDesktopPage` | 导航并等待 20 秒 |
| `__init__()` | `SkiaMotionmarkpathsDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- SVG 路径渲染涉及大量贝塞尔曲线的 tessellation
- 20 秒等待确保所有路径动画帧被充分处理

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_motionmarkpaths_desktop.json`

## 设计模式与设计决策

- MotionMark Paths 直接测试 Skia 最核心的路径渲染引擎
- 路径渲染是 2D 图形库最基础也是最重要的功能之一

## 性能考量

- 路径 tessellation 的计算复杂度高，是 CPU 密集型操作
- 大量路径的抗锯齿渲染测试 Skia 的覆盖率计算效率
- 路径缓存策略对重复路径的渲染性能有显著影响

## 相关文件

- `tools/skp/page_sets/skia_motionmarkarcs_desktop.py` - MotionMark 圆弧版本
- `tools/skp/page_sets/skia_motionmarksuits_desktop.py` - MotionMark Suits 版本

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（MotionMark Paths SVG），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 路径渲染是 Skia 最核心的功能之一，此测试直接测量路径 tessellation 性能
- 大量路径的抗锯齿渲染对覆盖率计算算法提出挑战

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
