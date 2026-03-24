# Skia YouTube 移动端页面集

> 源文件: `tools/skp/page_sets/skia_youtube_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 YouTube 移动端页面集。与桌面端版本不同，此页面加载特定的 YouTube 视频播放页面，测试 Skia 在移动端对视频播放器 UI、评论区和推荐列表等组件的渲染性能。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：视频播放页面的移动端渲染性能

## 主要类与结构体

### `SkiaMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 15 秒

### `SkiaYoutubeMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：特定 YouTube 视频页面（`watch?v=9hBpF_Zj4OA`）

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaMobilePage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaYoutubeMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 加载特定视频而非首页，测试视频播放页面的完整 UI 渲染
- 移动端 YouTube 使用自适应布局，组件排列与桌面端显著不同

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_youtube_mobile.json`

## 设计模式与设计决策

- 选择视频播放页而非首页，因为播放页包含更多样化的 UI 组件
- 移动端 YouTube 使用大量 CSS 动画和过渡效果

## 性能考量

- 视频播放器 UI 包含圆角矩形、进度条等几何图形渲染
- 评论区域的文本滚动列表测试 Skia 的增量渲染性能
- 推荐视频缩略图列表涉及大量图片绘制

## 相关文件

- `tools/skp/page_sets/skia_youtube_desktop.py` - YouTube 桌面端版本
- `tools/skp/page_sets/data/skia_youtube_mobile.json`

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（YouTube 视频播放页），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 视频播放页包含播放器控件、评论区和推荐列表等多种 UI 组件
- 移动端 YouTube 的自适应布局与桌面版显著不同

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
