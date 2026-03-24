# Skia YouTube 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_youtube_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 YouTube 桌面端页面集。YouTube 是全球最大的视频分享平台，其首页包含视频缩略图网格、侧边栏、搜索栏等丰富 UI 组件，是测试 Skia 对现代单页应用（SPA）渲染性能的重要基准。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：现代 SPA 应用渲染性能

## 主要类与结构体

### `SkiaDesktopPage`
- 继承自 `page_module.Page`，使用 `SharedDesktopPageState`
- 导航后等待 15 秒

### `SkiaYoutubeDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：`http://www.youtube.com`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaDesktopPage` | 初始化桌面端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaDesktopPage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaYoutubeDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- 15 秒等待确保 YouTube 的 JavaScript 应用框架完全初始化并渲染首屏内容
- 2019 年 SKP 更新批次（go/skia-skps-3-2019）

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_youtube_desktop.json`

## 设计模式与设计决策

- YouTube 使用 Polymer/Web Components 构建，其 Shadow DOM 和自定义元素对渲染引擎有独特要求
- 视频缩略图网格测试 Skia 的图片绘制和缩放性能

## 性能考量

- YouTube 首页渲染涉及大量图片缩放和裁剪操作
- SPA 框架的动态内容生成增加了 DOM 和渲染树的复杂度
- 视频缩略图的 WebP/JPEG 解码对 Skia 图片解码器的性能有要求

## 相关文件

- `tools/skp/page_sets/skia_youtube_mobile.py` - YouTube 移动端版本
- `tools/skp/page_sets/data/skia_youtube_desktop.json`

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（YouTube），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- YouTube 使用 Web Components 和 Shadow DOM，对渲染引擎有独特要求
- 视频缩略图网格的图片缩放和裁剪是此页面的主要渲染负载

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
