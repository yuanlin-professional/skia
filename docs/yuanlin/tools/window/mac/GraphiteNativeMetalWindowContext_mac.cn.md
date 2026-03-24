# GraphiteNativeMetalWindowContext_mac

> 源文件: `tools/window/mac/GraphiteNativeMetalWindowContext_mac.h`, `tools/window/mac/GraphiteNativeMetalWindowContext_mac.mm`

## 概述

GraphiteNativeMetalWindowContext_mac 是 Graphite Metal 窗口上下文在 macOS 平台上的具体实现。它继承自 GraphiteMetalWindowContext 抽象基类，负责将 CAMetalLayer 配置并附加到 macOS 的 NSView 上，处理 Retina 显示器的缩放，并提供工厂函数 `MakeGraphiteNativeMetalForMac` 供上层调用。

## 架构位置

```
WindowContext
  +-- GraphiteMetalWindowContext (抽象基类)
       +-- GraphiteMetalWindowContext_mac (macOS 实现) <-- 本文件
```

## 主要类与结构体

### `GraphiteMetalWindowContext_mac`（匿名命名空间内）
- **继承**: `GraphiteMetalWindowContext`
- **成员**: `fMainView` (NSView 指针)

### 工厂函数
- `skwindow::MakeGraphiteNativeMetalForMac(info, params)`: 创建 macOS Graphite Metal 窗口上下文

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeGraphiteNativeMetalForMac(info, params)` | 工厂函数，创建并验证窗口上下文 |

## 内部实现细节

### CAMetalLayer 配置（onInitializeContext）
- 创建 CAMetalLayer 并绑定 Metal 设备
- 像素格式设为 `MTLPixelFormatBGRA8Unorm`
- 配置 VSync（通过 `displaySyncEnabled`）
- 设置自动布局管理器和自动调整大小掩码
- 内容锚点设为左上角（`kCAGravityTopLeft`）
- 禁用放大过滤中的插值（`kCAFilterNearest`）
- `framebufferOnly = false` 允许从 drawable 读回像素
- 应用窗口色彩空间到 Metal 层

### Retina 缩放处理（resize）
使用 `skwindow::GetBackingScaleFactor` 获取缩放因子，将视图逻辑尺寸乘以缩放因子得到物理像素尺寸，同时更新 `drawableSize` 和 `contentsScale`。

## 依赖关系

- **Cocoa**: `<Cocoa/Cocoa.h>`, `<QuartzCore/CAConstraintLayoutManager.h>`
- **父类**: `GraphiteMetalWindowContext`
- **工具**: `MacWindowInfo`

## 设计模式与设计决策

1. **匿名命名空间封装**: 实现类在匿名命名空间中，仅暴露工厂函数
2. **resize 忽略参数**: `resize(w, h)` 直接从 fMainView 读取实际尺寸，忽略传入的宽高参数
3. **工厂方法验证**: 创建后检查 `isValid()`，失败返回 nullptr

## 性能考量

- Retina 显示器上物理像素数是逻辑像素数的 2-3 倍，影响渲染负载

## 相关文件

- `tools/window/GraphiteNativeMetalWindowContext.h/.mm` - 抽象基类
- `tools/window/mac/MacWindowInfo.h` - macOS 窗口信息结构
- `tools/window/mac/GaneshMetalWindowContext_mac.mm` - Ganesh Metal macOS 对照
