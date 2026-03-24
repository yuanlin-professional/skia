# MetalWindowContext_ios - iOS Ganesh Metal 窗口上下文

> 源文件: `tools/window/ios/MetalWindowContext_ios.mm`

## 概述

`MetalWindowContext_ios` 实现了 iOS 平台上使用 Metal 图形 API 和 Ganesh 渲染后端的窗口上下文。它与 Graphite 版本 (`GraphiteMetalWindowContext_ios`) 结构几乎完全相同，唯一区别在于继承自 Ganesh 的 `MetalWindowContext` 基类。通过自定义的 `MetalView` 将 `CAMetalLayer` 集成到 UIKit 视图层级中。

## 架构位置

- 继承自 `skwindow::internal::MetalWindowContext`（Ganesh Metal 基类）
- 由工厂函数 `MakeMetalForIOS` 创建
- 与 Graphite 版本平行，使用 Ganesh 渲染路径

## 主要类与结构体

### `MetalView`（Objective-C）
- 继承自 `MainView`，覆盖 `+layerClass` 返回 `CAMetalLayer`

### `MetalWindowContext_ios`（匿名命名空间）
- 继承自 `MetalWindowContext`
- 成员：`fWindow`, `fViewController`, `fMetalView`

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeMetalForIOS(IOSWindowInfo&, params)` | 工厂函数 |

## 内部实现细节

初始化、销毁和 resize 逻辑与 Graphite 版本几乎完全相同：
- 创建 `MetalView`，配置 `CAMetalLayer`（BGRA8Unorm 像素格式）
- `framebufferOnly = false` 以支持像素读回
- `contentsGravity = kCAGravityTopLeft`

## 依赖关系

- `tools/window/MetalWindowContext.h` - Ganesh Metal 基类
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 工厂声明
- `<Metal/Metal.h>`, `<UIKit/UIKit.h>`

## 设计模式与设计决策

- 与 Graphite 版本保持代码结构一致，便于维护
- Ganesh/Graphite 的差异完全由基类处理

## 性能考量

与 Graphite 版本相同，适用于 iOS 测试应用场景。

## 相关文件

- `tools/window/ios/GraphiteMetalWindowContext_ios.mm` - Graphite 版本
- `tools/window/MetalWindowContext.h` - Ganesh Metal 基类
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 工厂声明
