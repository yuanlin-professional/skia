# Skia The Verge 移动端页面集

> 源文件: `tools/skp/page_sets/skia_theverge_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 The Verge 移动端页面集。The Verge 是一个以多媒体丰富内容和现代 Web 设计著称的科技媒体网站，其页面包含大量图片、动画和复杂 CSS 布局，是测试 Skia 移动端渲染多媒体密集型页面能力的理想场景。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：多媒体密集型页面的移动端渲染性能

## 主要类与结构体

### `SkiaBuildbotMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 15 秒
- 注意类名使用"Mobile"而非其他页面集中的泛化命名

### `SkiaThevergeMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：`http://theverge.com/`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaBuildbotMobilePage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaThevergeMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 15 秒等待确保 The Verge 页面的大量图片和动画资源完全加载
- 2019 年 SKP 更新批次中添加（go/skia-skps-3-2019）

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_theverge_mobile.json`

## 设计模式与设计决策

- The Verge 页面以视觉丰富性著称，其现代 Web 设计使用大量 CSS 渐变、阴影和图片叠加效果
- 移动端视口下这些效果对 Skia 的合成和混合操作要求更高

## 性能考量

- 大量图片解码和纹理上传测试 Skia 的图片处理流水线
- 复杂 CSS 效果（阴影、模糊、渐变）测试 Skia 的滤镜和着色器性能
- 移动端内存约束下的大图片处理对缓存策略提出挑战

## 相关文件

- `tools/skp/page_sets/data/skia_theverge_mobile.json`
- `tools/skp/page_sets/skia_techcrunch_mobile.py` - 类似的科技媒体移动端页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（The Verge），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- The Verge 的现代 Web 设计大量使用 CSS Grid 和 Flexbox 布局
- 大量高分辨率图片在移动端的解码和渲染是关键性能瓶颈

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
