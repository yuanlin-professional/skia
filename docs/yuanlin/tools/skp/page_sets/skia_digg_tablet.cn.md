# skia_digg_tablet.py - Digg 平板端页面集定义

> 源文件: [tools/skp/page_sets/skia_digg_tablet.py](../../../tools/skp/page_sets/skia_digg_tablet.py)

## 概述

此文件定义了一个 Chromium Telemetry 页面集，用于以平板设备用户代理从 Digg 社交新闻聚合网站（`http://digg.com/`）录制 Skia Picture（SKP）文件。这是 Skia 页面集合中少数使用平板（tablet）用户代理的测试之一，填补了桌面端和移动端之间的设备类型覆盖空白。Digg 的卡片式内容布局在平板设备的中等屏幕尺寸下提供了独特的响应式渲染场景。

## 架构位置

该文件属于 Skia SKP 页面集合（`tools/skp/page_sets/`），是页面集中唯一的平板端测试。在 Skia 的设备类型覆盖中：
- **桌面端**：多数页面集使用 `SharedDesktopPageState`
- **移动端**：部分页面集使用 `SharedMobilePageState`
- **平板端**：仅此文件和极少数其他文件使用 `SharedTabletPageState`

平板端测试的特殊价值在于其视口尺寸（通常 768-1024px 宽）会触发与桌面端和移动端不同的 CSS 响应式断点，导致不同的布局渲染路径。

## 主要类与结构体

### `SkiaBuildbotDesktopPage(page_module.Page)`
页面定义类。

**注意**：尽管类名包含 "Desktop"，实际使用 `SharedTabletPageState` 而非 `SharedDesktopPageState`。这是一个历史遗留的命名不一致。

**属性**：
- `shared_page_state_class`：`SharedTabletPageState`（平板浏览器配置）
- `archive_data_file`：`'data/skia_digg_tablet.json'`

**方法**：
- `RunNavigateSteps(action_runner)`：导航到 URL 并等待 30 秒

### `SkiaDiggTabletPageSet(story.StorySet)`
页面集合定义。

**URL**：`http://digg.com/`
**来源**：`# Why: from Clank CY.`（来自 Chrome on Android 的兼容性测试集）

## 公共 API 函数

| 方法 | 所属类 | 参数 | 描述 |
|------|--------|------|------|
| `__init__(url, page_set)` | SkiaBuildbotDesktopPage | URL 和父页面集 | 初始化平板端页面 |
| `RunNavigateSteps(action_runner)` | SkiaBuildbotDesktopPage | Telemetry action_runner | 导航并等待 30 秒 |
| `__init__()` | SkiaDiggTabletPageSet | 无 | 初始化页面集 |

## 内部实现细节

1. **类名不一致**：类名 `SkiaBuildbotDesktopPage` 与实际使用的 `SharedTabletPageState` 不匹配，可能是从桌面端模板复制后仅修改了 `shared_page_state_class` 参数而未更新类名。
2. **30 秒等待**：较长的等待时间（与 Booking.com 和 Facebook 并列最长），可能因为 Digg 的内容加载机制较慢。
3. **HTTP 协议**：使用不安全的 HTTP。
4. **2014 年版权**：这是较早添加的页面集之一。
5. **Clank CY 来源**：源自 Chrome on Android（内部代号 Clank）的 CY（兼容性测试）测试套件。

## 依赖关系

- **Telemetry 框架**：
  - `telemetry.story.StorySet`
  - `telemetry.page.page.Page`
  - `telemetry.page.shared_page_state.SharedTabletPageState`
- **存档数据**：`data/skia_digg_tablet.json`

## 设计模式与设计决策

- **平板端独占地位**：作为页面集中极少数平板测试之一，确保 Skia 对平板设备的响应式渲染得到验证。
- **Clank 来源**：测试页面来源于 Chrome Android 团队的兼容性测试集，表明 Digg 在 Android 平板上有特殊的渲染意义或曾触发过兼容性问题。
- **命名不一致未修复**：类名的不一致虽然不影响功能（Python 类名不决定行为），但可能造成代码阅读时的困惑。这反映了早期页面集的代码质量标准与后期有所不同。
- **较长等待时间**：30 秒的等待可能过于保守，但确保了内容完整性。

## 性能考量

- 平板视口（通常 768px 宽）介于桌面和手机之间，可能触发独特的 CSS 媒体查询断点。
- 30 秒等待增加了单个测试的运行时间。
- 卡片式布局在平板尺寸下可能有不同的列数和卡片大小，测试了 Skia 在不同布局参数下的表现。
- Digg 的无限滚动模式可能在等待期间加载更多内容。

## 相关文件

- `tools/skp/page_sets/data/skia_digg_tablet.json`：WPR 存档数据
- 其他桌面端和移动端页面集（作为设备类型覆盖的互补）
- Chrome on Android（Clank）的兼容性测试相关文档
