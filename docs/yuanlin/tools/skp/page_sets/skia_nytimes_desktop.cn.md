# Skia New York Times 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_nytimes_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的纽约时报（New York Times）桌面端页面集。纽约时报是世界知名的新闻网站，其首页采用经典的报纸式多栏布局，包含头条新闻、图片、视频和广告等多种元素，是测试 Skia 对传统新闻网站渲染能力的代表性用例。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：新闻网站多栏布局渲染性能（for Clank CY）

## 主要类与结构体

### `SkiaBuildbotDesktopPage`
- 继承自 `page_module.Page`，使用 `SharedDesktopPageState`
- 导航后等待 15 秒

### `SkiaNytimesDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：`http://www.nytimes.com/`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotDesktopPage` | 初始化桌面端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaBuildbotDesktopPage` | 导航并等待 15 秒 |
| `__init__()` | `SkiaNytimesDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- 注释标注"for Clank CY"，表明此页面集与 Chrome on Android (Clank) 的性能目标相关
- 创建于 2014 年，是较早的测试页面

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_nytimes_desktop.json`

## 设计模式与设计决策

- 纽约时报代表了高质量新闻网站的排版标准，其衬线字体和精细排版对 Skia 的字体渲染质量有高要求
- 多栏布局的复杂 CSS 测试 Skia 的渲染树遍历效率

## 性能考量

- 精细排版（kerning、ligature）增加了文本渲染复杂度
- 多栏布局中的浮动和定位元素增加裁剪操作
- 高质量新闻图片的渲染测试 Skia 的图片质量和性能平衡

## 相关文件

- `tools/skp/page_sets/data/skia_nytimes_desktop.json`
- `tools/skp/page_sets/skia_cnn_mobile.py` - 另一个新闻网站页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（纽约时报），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 纽约时报的衬线字体和精细排版对 Skia 的 kerning 和 ligature 渲染有高要求
- 多栏报纸式布局代表了传统印刷排版在 Web 上的实现

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
