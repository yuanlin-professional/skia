# GaneshMetalWindowContext_mac

> 源文件: `tools/window/mac/GaneshMetalWindowContext_mac.h`, `tools/window/mac/GaneshMetalWindowContext_mac.mm`

## 概述

GaneshMetalWindowContext_mac（实现类名为 MetalWindowContext_mac）是 Ganesh Metal 窗口上下文在 macOS 平台上的具体实现。它继承自 MetalWindowContext 抽象基类，负责在 macOS 的 NSView 上配置 CAMetalLayer 并处理 Retina 缩放。

该实现与 GraphiteMetalWindowContext_mac 几乎完全对称，区别仅在于使用 Ganesh 渲染管线而非 Graphite。

## 架构位置

```
WindowContext
  +-- MetalWindowContext (Ganesh Metal 抽象基类)
       +-- MetalWindowContext_mac (macOS Ganesh Metal) <-- 本文件
```

## 主要类与结构体

### `MetalWindowContext_mac`（匿名命名空间内）
- **继承**: `MetalWindowContext`
- **成员**: `fMainView` (NSView 指针)

### 工厂函数
- `skwindow::MakeGaneshMetalForMac(info, params)`: 创建 macOS Ganesh Metal 窗口上下文

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeGaneshMetalForMac(info, params)` | 工厂函数 |

## 内部实现细节

### CAMetalLayer 配置（onInitializeContext）
与 GraphiteMetalWindowContext_mac 几乎相同：
- `MTLPixelFormatBGRA8Unorm` 像素格式
- VSync 控制、自动布局、内容锚点、最近邻过滤
- 应用窗口色彩空间
- `framebufferOnly = false`

唯一差异：Ganesh 版本没有使用 `fMetalLayer.framebufferOnly` 属性在同一位置设置（在 Metal 层构建完成后设置）。

### Retina 缩放
与 Graphite 版本完全相同的 `GetBackingScaleFactor` 处理逻辑。

## 依赖关系

- **Cocoa**: `<Cocoa/Cocoa.h>`, `<QuartzCore/CAConstraintLayoutManager.h>`
- **父类**: `MetalWindowContext`
- **工具**: `MacWindowInfo`, `MacWindowGLUtils`

## 设计模式与设计决策

1. **与 Graphite 版本对称**: 代码结构和 CAMetalLayer 配置几乎完全一致
2. **匿名命名空间 + 工厂函数**: 隐藏实现细节

## 性能考量

- 与 Graphite 版本相同的 Retina 缩放影响

## 相关文件

- `tools/window/MetalWindowContext.h/.mm` - Ganesh Metal 抽象基类
- `tools/window/mac/GraphiteNativeMetalWindowContext_mac.mm` - Graphite 对照
- `tools/window/mac/MacWindowInfo.h` - macOS 窗口信息
