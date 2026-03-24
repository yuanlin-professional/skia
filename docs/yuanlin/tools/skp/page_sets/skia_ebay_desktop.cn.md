# Skia eBay 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_ebay_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 eBay 桌面端页面集。eBay 是全球最大的电子商务网站之一，其首页包含大量商品图片、卡片式布局和动态内容，是测试 Skia 对复杂电商页面渲染能力的代表性测试用例。

## 架构位置

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 设备类型：桌面端（Desktop）
- 测试用途：电商类图片密集型页面渲染性能

## 主要类与结构体

### `SkiaDesktopPage`
- 继承自 `page_module.Page`，使用 `SharedDesktopPageState`
- 导航时使用 120 秒超时参数（`timeout_in_seconds=120`），表明 eBay 页面加载可能较慢

### `SkiaEbayDesktopPageSet`
- 继承自 `story.StorySet`
- 目标 URL：`http://www.ebay.com`

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaDesktopPage` | 初始化桌面端页面 |
| `RunNavigateSteps(action_runner)` | `SkiaDesktopPage` | 导航到 eBay 并设置 120 秒超时 |
| `__init__()` | `SkiaEbayDesktopPageSet` | 初始化页面集 |

## 内部实现细节

- 120 秒导航超时是所有页面集中最长的之一，反映了 eBay 首页的加载复杂性
- 未设置额外等待时间，导航超时本身即包含了加载等待
- 2019 年 SKP 更新批次（go/skia-skps-3-2019）

## 依赖关系

- `telemetry.story`、`telemetry.page.page`、`telemetry.page.shared_page_state`
- 外部数据：`data/skia_ebay_desktop.json`

## 设计模式与设计决策

- eBay 首页包含大量动态加载的商品图片和轮播组件
- 使用长超时而非等待的设计选择表明重点在于捕获初始页面加载状态

## 性能考量

- 大量图片资源的解码和渲染测试 Skia 的图片处理吞吐量
- 卡片式布局涉及大量矩形裁剪和圆角绘制
- 页面中的广告和推荐模块增加了渲染复杂度

## 相关文件

- `tools/skp/page_sets/data/skia_ebay_desktop.json`
- `tools/skp/page_sets/skia_linkedin_desktop.py` - 另一个使用长超时的桌面端页面集

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（eBay），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 电商页面的动态内容和广告模块增加了渲染树的动态复杂度
- 商品卡片的圆角和阴影效果测试 Skia 的 RRect 和阴影渲染性能

### 归档数据管理

归档数据（WPR Archive）存储了网络请求和响应的快照，使测试能够在离线环境中确定性地重放。归档数据文件由 Skia 基础设施团队定期更新以反映目标网站的最新状态，旧版本的归档文件保存在 Google Cloud Storage 中以支持历史对比分析。
