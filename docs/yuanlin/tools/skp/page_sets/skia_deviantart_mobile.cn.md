# Skia DeviantArt 移动端页面集

> 源文件: `tools/skp/page_sets/skia_deviantart_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 DeviantArt 移动端页面集。DeviantArt 是全球最大的在线艺术社区之一，其"热门作品"页面包含大量高质量图片、画廊网格和丰富的视觉特效，是测试 Skia 移动端渲染图片画廊类页面的极端场景。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：图片画廊类页面的移动端渲染性能

## 主要类与结构体

### `SkiaMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 45 秒（所有移动端页面集中最长的等待时间之一）

### `SkiaDeviantartMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：`https://www.deviantart.com/whats-hot/`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaMobilePage` | 导航并等待 45 秒 |
| `__init__()` | `SkiaDeviantartMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 45 秒等待时间反映了 DeviantArt 页面大量高分辨率图片的加载需求
- "What's Hot"页面使用瀑布流布局，包含不同尺寸的图片网格

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_deviantart_mobile.json`

## 设计模式与设计决策

- DeviantArt 的瀑布流布局是现代 Web 中常见的设计模式，对 Skia 的不规则裁剪区域处理有要求
- 高分辨率艺术作品的缩放和显示是对 Skia 图片质量和性能的双重测试

## 性能考量

- 大量不同尺寸图片的解码和缩放对 Skia 的图片处理流水线构成极端压力
- 瀑布流布局的不规则图片网格增加了裁剪和合成复杂度
- 45 秒等待确保所有懒加载的高分辨率图片完全渲染
- 移动端内存限制下的大量图片管理对 Skia 的缓存驱逐策略提出挑战

## 相关文件

- `tools/skp/page_sets/data/skia_deviantart_mobile.json`
- `tools/skp/page_sets/skia_capitalvolkswagen_mobile.py` - 另一个图片密集型页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（DeviantArt），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 瀑布流布局中不同宽高比图片的裁剪和缩放测试 Skia 的图片变换精度
- 45 秒等待是所有移动端页面集中最长的，确保大量高分辨率图片完全加载

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
