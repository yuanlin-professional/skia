# Skia TechCrunch 移动端页面集

> 源文件: `tools/skp/page_sets/skia_techcrunch_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 TechCrunch 移动端页面集。TechCrunch 是知名科技新闻网站，其移动端页面包含新闻文章列表、特色图片和广告组件，代表了典型的新闻媒体网站渲染场景。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：新闻媒体网站的移动端渲染性能

## 主要类与结构体

### `SkiaMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 15 秒

### `SkiaTechcrunchMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：`http://techcrunch.com`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaMobilePage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaTechcrunchMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 标准 15 秒等待时间
- 2019 年 SKP 更新批次（go/skia-skps-3-2019）

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_techcrunch_mobile.json`

## 设计模式与设计决策

- TechCrunch 代表了使用 WordPress 构建的现代新闻网站
- 新闻列表页包含文字和图片的混合布局，是常见的渲染模式

## 性能考量

- 新闻列表中的特色图片需要缩放渲染，测试 Skia 的图片采样质量
- 广告组件的 iframe 增加了渲染层次复杂度
- WordPress 主题的 CSS 效果对 Skia 的渲染管道有基础性测试

## 相关文件

- `tools/skp/page_sets/data/skia_techcrunch_mobile.json`
- `tools/skp/page_sets/skia_theverge_mobile.py` - 类似的科技媒体页面集
- `tools/skp/page_sets/skia_cnnarticle_mobile.py` - 新闻类移动端页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（TechCrunch），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- WordPress 构建的新闻网站代表了互联网上大量站点的典型渲染模式
- 新闻列表的图文混排是 Skia 文本和图片协同渲染的常见场景

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
