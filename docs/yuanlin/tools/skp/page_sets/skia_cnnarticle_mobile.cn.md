# Skia CNN Article 移动端页面集

> 源文件: `tools/skp/page_sets/skia_cnnarticle_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 CNN 文章移动端页面集。加载 CNN 上关于《生活大爆炸》大结局的特定新闻文章页面，测试 Skia 在移动端渲染长篇新闻文章（包含正文、图片、广告和相关推荐）的性能。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：长篇新闻文章的移动端渲染性能

## 主要类与结构体

### `SkiaMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 15 秒

### `SkiaCnnarticleMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：CNN 特定文章页面

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaMobilePage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaCnnarticleMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 使用字符串拼接处理超长 URL
- 特定文章而非首页，确保测试内容稳定可复现

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_cnnarticle_mobile.json`

## 设计模式与设计决策

- 选择长篇文章而非新闻首页，因为文章页面更能代表用户实际阅读体验
- 文章页的文本排版、内嵌图片和广告提供了多样化的渲染测试场景

## 性能考量

- 长文本排版测试 Skia 的文本布局和行断裂性能
- 文章内嵌图片的渲染测试 Skia 的图文混排能力
- 广告 iframe 增加了页面渲染层级复杂度

## 相关文件

- `tools/skp/page_sets/skia_cnn_mobile.py` - CNN 首页移动端版本
- `tools/skp/page_sets/data/skia_cnnarticle_mobile.json`

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（CNN 文章），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 长篇新闻文章的连续文本排版测试 Skia 的段落布局和行断裂性能
- 文章内嵌的图片和视频预览增加了渲染内容的多样性

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
