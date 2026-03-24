# GraphiteNativeMetalWindowContext

> 源文件: `tools/window/GraphiteNativeMetalWindowContext.h`, `tools/window/GraphiteNativeMetalWindowContext.mm`

## 概述

GraphiteMetalWindowContext 是 Skia 窗口系统中基于 Graphite 后端与 Apple Metal API 的窗口渲染上下文实现。它管理 Metal 设备、命令队列、CAMetalLayer，以及 Graphite Context 和 Recorder，为 macOS/iOS 平台提供基于 Metal 的 Graphite GPU 加速渲染能力。

该类是一个抽象基类，平台特定子类（如 macOS 版本）需要实现 `onInitializeContext()` 和 `onDestroyContext()` 来配置 CAMetalLayer 并关联到具体的视图。

## 架构位置

```
WindowContext (基类)
  +-- GraphiteMetalWindowContext  (Graphite + Metal, 抽象)
       +-- GraphiteMetalWindowContext_mac  (macOS 平台实现)
       +-- ...其他平台实现
```

## 主要类与结构体

### `GraphiteMetalWindowContext`
- **命名空间**: `skwindow::internal`
- **继承**: `WindowContext`
- **性质**: 抽象基类（protected 构造函数，纯虚方法）
- **成员**:
  - `fDevice`: Metal 设备 (`id<MTLDevice>`)
  - `fQueue`: Metal 命令队列 (`id<MTLCommandQueue>`)
  - `fMetalLayer`: CAMetalLayer 引用
  - `fDrawableHandle`: 当前 drawable 的 CFTypeRef
  - `fValid`: 有效性标志

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `getBackbufferSurface()` | 从 CAMetalLayer 获取下一个 drawable 并包装为 SkSurface |
| `isValid()` | 检查上下文有效性 |
| `setDisplayParams(params)` | 销毁并重建上下文 |
| `activate(isActive)` | 活动状态回调（当前为空实现） |

## 内部实现细节

### 初始化流程
1. 创建系统默认 Metal 设备和命令队列
2. 检查设备是否支持请求的 MSAA 采样数
3. 调用子类 `onInitializeContext()` 配置 CAMetalLayer
4. 构建 `MtlBackendContext` 并创建 Graphite Context
5. 启用有序 Recording 和 `fStoreContextRefInRecorder`（支持同步 readPixels）

### MSAA 圆整
构造函数使用 `DisplayParamsBuilder::roundUpMSAA()` 将 MSAA 采样数向上圆整到设备支持的值。

### 后缓冲获取
通过 `[fMetalLayer nextDrawable]` 获取 drawable，将其纹理包装为 Graphite BackendTexture，再通过 `SkSurfaces::WrapBackendTexture` 创建 SkSurface。使用 `CFRetain` 保持 drawable 引用。

### 缓冲交换
1. 调用 `submitToGpu()` 提交 Graphite 工作
2. 创建命令缓冲区并调用 `presentDrawable`
3. `CFRelease` 释放 drawable 引用（ARC 关闭环境）

## 依赖关系

- **Metal**: `<Metal/Metal.h>`, `<QuartzCore/CAMetalLayer.h>`
- **Graphite**: `Context`, `Recorder`, `Recording`, `Surface`, `BackendTexture`
- **Graphite Metal**: `MtlBackendContext`, `MtlGraphiteTypes`
- **工具**: `WindowContext`, `GraphiteToolUtils`, `GraphiteDisplayParams`

## 设计模式与设计决策

1. **模板方法模式**: `initializeContext()` / `destroyContext()` 定义骨架流程，子类通过 `onInitializeContext()` / `onDestroyContext()` 提供平台特定实现
2. **手动内存管理**: 由于 ARC 关闭，需要手动 `CFRetain` / `CFRelease` 管理 drawable 生命周期
3. **TestOptions 集成**: 通过 `GraphiteDisplayParams` 和 `TestOptions` 传递 Graphite 上下文配置

## 性能考量

- MSAA 圆整避免不必持的降级和重试
- `framebufferOnly = false`（在子类中设置）允许读回像素但可能降低性能

## 相关文件

- `tools/window/MetalWindowContext.h/.mm` - Ganesh Metal 对照版本
- `tools/window/mac/GraphiteNativeMetalWindowContext_mac.mm` - macOS 平台实现
- `tools/window/GraphiteDisplayParams.h` - Graphite 显示参数
