# Skia Gujarati Wiki 桌面端页面集

> 源文件: `tools/skp/page_sets/skia_gujuratiwiki_desktop.py`

## 概述

此文件定义了用于 Skia 性能测试的 Gujarati Wiki 桌面端页面集。它使用 Chromium Telemetry 框架加载维基百科上关于古吉拉特语音韵学（Gujarati Phonology）的页面，录制 SKP（Skia Picture）文件以供后续渲染性能分析。该页面集主要用于测试 Skia 对含有复杂非拉丁文字体的网页渲染能力。

## 架构位置

该文件位于 Skia 工具链的 SKP 页面集目录中，属于 Skia 自动化性能测试基础设施的一部分。在整体架构中，它处于测试流水线的最前端——负责定义需要捕获的网页场景，生成的 SKP 文件随后被 Skia 渲染后端用于基准性能测试。

- 所属模块：`tools/skp/page_sets/`（SKP 录制页面集）
- 上游依赖：Chromium Telemetry 测试框架
- 下游消费者：Skia buildbot 基准测试系统

## 主要类与结构体

### `SkiaBuildbotDesktopPage`
- 继承自 `page_module.Page`
- 表示一个桌面端页面实例，配置了 `SharedDesktopPageState` 共享状态
- 绑定归档数据文件 `data/skia_gujuratiwiki_desktop.json`
- 定义导航步骤：打开 URL 后等待 20 秒确保页面完全加载
- 定义页面交互：执行 `ScrollPage()` 滚动操作以触发完整渲染

### `SkiaGujuratiwikiDesktopPageSet`
- 继承自 `story.StorySet`
- 页面集容器类，包含目标 URL 列表
- 目标 URL：`https://en.wikipedia.org/wiki/Gujarati_phonology`（参见 skbug.com/40042887）

## 公共 API 函数

| 方法 | 所属类 | 描述 |
|------|--------|------|
| `__init__(url, page_set)` | `SkiaBuildbotDesktopPage` | 初始化页面，设置桌面共享状态和归档数据文件 |
| `RunNavigateSteps(action_runner)` | `SkiaBuildbotDesktopPage` | 导航到目标 URL 并等待 20 秒 |
| `RunPageInteractions(action_runner)` | `SkiaBuildbotDesktopPage` | 创建滚动手势交互并执行页面滚动 |
| `__init__()` | `SkiaGujuratiwikiDesktopPageSet` | 初始化页面集，添加所有目标 URL |

## 内部实现细节

- 页面加载后等待 20 秒（`action_runner.Wait(20)`），这是为了确保页面的字体资源和复杂排版布局完全渲染完成
- 使用 `CreateGestureInteraction('ScrollAction')` 上下文管理器包裹滚动操作，以便 Telemetry 能够正确录制交互事件
- 归档数据文件路径采用相对路径 `data/skia_gujuratiwiki_desktop.json`，该 JSON 文件存储了 Web Page Replay (WPR) 的归档信息

## 依赖关系

- `telemetry.story`：Telemetry 故事（Story）基础框架
- `telemetry.page.page`：页面基类模块
- `telemetry.page.shared_page_state`：提供 `SharedDesktopPageState`，管理桌面端浏览器状态
- 外部数据：`data/skia_gujuratiwiki_desktop.json`（WPR 归档数据）

## 设计模式与设计决策

- **模板方法模式**：通过覆写 `RunNavigateSteps` 和 `RunPageInteractions` 定义页面特定的行为，父类控制整体执行流程
- **故事集模式**：采用 Telemetry 的 Story/StorySet 架构，将页面组织为可迭代的测试故事
- 选择古吉拉特语维基页面是为了覆盖 Skia 在复杂 Unicode 脚本和字体 shaping 方面的渲染路径

## 性能考量

- 20 秒等待时间确保复杂字体的懒加载和 shaping 完成，避免录制不完整的 SKP
- 页面滚动操作用于触发视口外内容的渲染，确保 SKP 捕获完整页面
- 此页面包含大量 Unicode 字符和复杂排版，对字体渲染子系统构成压力测试

## 相关文件

- `tools/skp/page_sets/data/skia_gujuratiwiki_desktop.json` - WPR 归档数据文件
- `tools/skp/page_sets/skia_wikipedia_desktop.py` - 类似的维基百科桌面端页面集
- `tools/skp/skp_benchmark_flow.py` - 页面集的上层调度脚本

### 测试执行流程

此页面集在 Skia 的持续集成（CI）环境中按以下流程执行：

1. **Web Page Replay 准备**：加载预录制的 WPR 归档数据，确保测试可离线重复执行
2. **浏览器启动**：通过 Telemetry 框架启动 Chromium 浏览器实例，配置桌面端状态
3. **页面导航**：加载目标 URL（古吉拉特语维基页面），归档数据提供离线内容
4. **等待与交互**：执行预定义的等待和交互步骤，确保页面完全渲染
5. **SKP 录制**：Chromium 将渲染命令序列化为 SKP 格式文件
6. **SKP 分析**：生成的 SKP 文件由 Skia 基准测试工具加载和重放，测量渲染性能

### Telemetry 框架集成

此页面集遵循 Chromium Telemetry 框架的标准页面集定义模式：
- 继承层级： -> 
- 共享状态类管理浏览器实例的生命周期和配置
- 归档数据文件使 WPR 能够重放网络请求，保证测试确定性
- 此页面的复杂 Unicode 脚本对 Skia 的 HarfBuzz 集成是重要的回归检测点
