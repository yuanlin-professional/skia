# Skia Google 搜索移动端页面集

> 源文件: `tools/skp/page_sets/skia_googlesearch_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 Google 搜索结果移动端页面集。通过加载 Google UK 搜索结果页面（搜索词"barack obama"）来测试 Skia 在移动设备上对搜索结果页面的渲染性能。搜索结果页包含文本、链接、知识图谱卡片等多种 UI 元素。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：搜索结果页面的移动端渲染性能

## 主要类与结构体

### `SkiaMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 15 秒

### `SkiaGooglesearchMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：`https://www.google.co.uk/search?hl=en&q=barack+obama&cad=h`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaMobilePage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaGooglesearchMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 使用 Google UK 域名（google.co.uk）而非 google.com，可能是为了获取特定的搜索结果布局
- 搜索词"barack obama"会触发 Google 知识图谱卡片，增加渲染复杂度

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_googlesearch_mobile.json`

## 设计模式与设计决策

- Google 搜索结果页是最广泛访问的网页类型之一，具有极高的代表性
- 知识图谱卡片包含图片、信息面板等丰富组件，测试多种渲染路径

## 性能考量

- 搜索结果页的文本密集布局测试 Skia 的文本渲染吞吐量
- 移动端视口限制下的响应式布局渲染
- Google 搜索页面通常高度优化，为 Skia 提供了"最佳实践"的渲染基准

## 相关文件

- `tools/skp/page_sets/data/skia_googlesearch_mobile.json`
- `tools/skp/page_sets/skia_googleimagesearch_desktop.py` - Google 图片搜索桌面端版本

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（Google 搜索结果），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- Google 知识图谱卡片包含图片、信息面板等丰富组件
- 搜索结果页的高度优化使其成为 Skia 渲染效率的良好参照基准

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
