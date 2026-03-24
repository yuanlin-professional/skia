# WindowContextFactory_ios - iOS 窗口上下文工厂声明

> 源文件: `tools/window/ios/WindowContextFactory_ios.h`

## 概述

此头文件声明了 iOS 平台上所有可用渲染后端的窗口上下文工厂函数。它定义了 `IOSWindowInfo` 结构体用于传递 iOS 窗口信息，并通过条件编译宏控制各后端的可用性。特别地，Vulkan 在 iOS 上被标记为不支持，其工厂函数直接内联返回 `nullptr`。

## 架构位置

- 属于 `skwindow` 命名空间
- 是 iOS 平台窗口上下文的统一入口
- 被 `sk_app::Window_ios` 调用

## 主要类与结构体

### `IOSWindowInfo`
- `fWindow` (`sk_app::Window_ios*`) - iOS 窗口对象指针
- `fViewController` (`UIViewController*`) - 视图控制器指针

## 公共 API 函数

| 函数 | 条件 | 说明 |
|------|------|------|
| `MakeVulkanForIOS` | `SK_VULKAN` | 内联返回 nullptr（不支持） |
| `MakeMetalForIOS` | `SK_METAL` | 创建 Ganesh Metal 上下文 |
| `MakeGraphiteMetalForIOS` | `SK_METAL && SK_GRAPHITE` | 创建 Graphite Metal 上下文 |
| `MakeGLForIOS` | `SK_GL` | 创建 OpenGL ES 上下文 |
| `MakeRasterForIOS` | `SK_GL` | 创建光栅化上下文（依赖 GL） |

## 内部实现细节

- `MakeVulkanForIOS` 使用 `inline` 直接返回 `nullptr`，避免链接不存在的实现
- `MakeRasterForIOS` 被放在 `SK_GL` 条件下，因为 iOS 光栅化实现依赖 OpenGL ES 进行呈现
- 所有函数接受 `IOSWindowInfo` 引用和 `unique_ptr<const DisplayParams>`

## 依赖关系

- `tools/sk_app/ios/Window_ios.h` - iOS 窗口类
- `tools/window/WindowContext.h` - 窗口上下文基类
- `<UIKit/UIKit.h>` - UIViewController

## 设计模式与设计决策

- **显式不支持**: Vulkan 工厂函数存在但内联返回 nullptr，保持接口一致性
- **GL 依赖光栅化**: iOS 光栅化依赖 GL 进行最终呈现，因此受 SK_GL 保护
- **统一接口**: 使用 `IOSWindowInfo` 结构体封装 iOS 特有的窗口信息

## 性能考量

仅为声明文件，不影响运行时性能。

## 相关文件

- `tools/window/win/WindowContextFactory_win.h` - Windows 版本
- `tools/window/ios/MetalWindowContext_ios.mm` - Metal 实现
- `tools/window/ios/GLWindowContext_ios.mm` - GL 实现
- `tools/window/ios/RasterWindowContext_ios.mm` - 光栅化实现
