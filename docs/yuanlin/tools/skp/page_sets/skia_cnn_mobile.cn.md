# Skia CNN 移动端页面集

> 源文件: `tools/skp/page_sets/skia_cnn_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 CNN 首页移动端页面集。CNN 作为全球最大的新闻网站之一，其首页包含新闻标题、特色图片、视频预览和多个内容分区，是测试 Skia 在移动端渲染新闻门户网站的代表性场景。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：新闻门户网站首页的移动端渲染性能

## 主要类与结构体

### `SkiaMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 15 秒

### `SkiaCnnMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：`http://www.cnn.com`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaMobilePage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaCnnMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 加载 CNN 首页而非特定文章，与 `skia_cnnarticle_mobile.py` 形成互补
- 首页包含更多图片和多栏布局

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_cnn_mobile.json`

## 设计模式与设计决策

- CNN 首页与文章页分别作为独立测试用例，覆盖不同的渲染模式
- 首页代表"浏览式"渲染，文章页代表"阅读式"渲染

## 性能考量

- 新闻首页的多栏布局在移动端需要响应式重排
- 大量新闻缩略图的批量加载和渲染测试 Skia 的图片处理并发能力
- 动态广告内容增加了渲染层级复杂度

## 相关文件

- `tools/skp/page_sets/skia_cnnarticle_mobile.py` - CNN 文章页版本
- `tools/skp/page_sets/skia_nytimes_desktop.py` - 另一个新闻网站桌面端页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（CNN 首页），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- CNN 首页与文章页分别测试不同类型的渲染模式（浏览式 vs 阅读式）
- 新闻首页的多栏布局在移动端需要响应式重排

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
