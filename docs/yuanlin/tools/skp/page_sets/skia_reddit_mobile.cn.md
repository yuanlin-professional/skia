# Skia Reddit 移动端页面集

> 源文件: `tools/skp/page_sets/skia_reddit_mobile.py`

## 概述

此文件定义了用于 Skia 性能测试的 Reddit 移动端页面集。加载 Reddit 编程板块的一篇特定长帖子，该页面包含大量嵌套评论、文本内容和用户头像，是测试 Skia 移动端渲染深层嵌套布局和长文本列表能力的典型场景。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：移动端（Mobile）
- 测试用途：嵌套评论布局和长列表渲染性能

## 主要类与结构体

### `SkiaMobilePage`
- 继承自 `page_module.Page`，使用 `SharedMobilePageState`
- 导航后等待 30 秒

### `SkiaRedditMobilePageSet`
- 继承自 `story.StorySet`
- 目标 URL：Reddit r/programming 中一篇关于 Gmail 内存管理的帖子

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaMobilePage` | 初始化移动端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaMobilePage` | 导航并等待 30 秒 |
| `__init__()` | `SkiaRedditMobilePageSet` | 初始化页面集 |

## 内部实现细节

- 30 秒等待适应 Reddit 页面的评论树懒加载机制
- 选择了一个热门编程帖子，确保页面中有大量嵌套评论

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_reddit_mobile.json`

## 设计模式与设计决策

- Reddit 的嵌套评论树使用递增缩进布局，对 Skia 的裁剪栈和画布变换有独特要求
- 选择特定帖子而非首页，确保测试内容的稳定性和可复现性

## 性能考量

- 深层嵌套的评论布局涉及大量 canvas save/restore 操作
- 大量小头像图片的解码和绘制测试 Skia 的小图片处理效率
- 长文本列表的滚动渲染是移动端的关键性能指标

## 相关文件

- `tools/skp/page_sets/data/skia_reddit_mobile.json`
- `tools/skp/page_sets/skia_slashdot_mobile.py` - 类似的社区移动端页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置移动端状态
3. **页面导航**：加载目标 URL（Reddit 帖子页面），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- Reddit 的深层嵌套评论树对 Skia 的 canvas save/restore 栈有较高要求
- 评论区的用户头像缩略图涉及大量小图片的解码和绘制

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
