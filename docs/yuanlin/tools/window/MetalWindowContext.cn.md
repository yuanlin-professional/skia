# MetalWindowContext

> 源文件: `tools/window/MetalWindowContext.h`, `tools/window/MetalWindowContext.mm`

## 概述

MetalWindowContext 是 Skia 窗口系统中基于 Ganesh 后端与 Apple Metal API 的窗口渲染上下文实现。它管理 Metal 设备、命令队列、CAMetalLayer 和 GrDirectContext，为 macOS/iOS 提供 Ganesh Metal GPU 加速渲染。

该类是抽象基类，平台特定子类通过 `onInitializeContext()` / `onDestroyContext()` 配置 CAMetalLayer。与 GraphiteMetalWindowContext 不同，它使用 Ganesh 渲染管线。

## 架构位置

```
WindowContext (基类)
  +-- MetalWindowContext  (Ganesh + Metal, 抽象) <-- 本文件
       +-- MetalWindowContext_mac  (macOS 实现)
  +-- GraphiteMetalWindowContext  (Graphite + Metal, 抽象)
```

## 主要类与结构体

### `MetalWindowContext`
- **命名空间**: `skwindow::internal`
- **继承**: `WindowContext`
- **成员**: `fDevice`, `fQueue`, `fMetalLayer`, `fDrawableHandle`, `fValid`

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `getBackbufferSurface()` | 获取后缓冲 SkSurface |
| `isValid()` | 检查有效性 |
| `setDisplayParams(params)` | 重建上下文 |

## 内部实现细节

### 初始化与 MSAA 自动降级
创建 `GrDirectContext` 后，如果失败且 MSAA > 1，自动将采样数减半并递归重试初始化。这是 Ganesh Metal 特有的容错策略。

### 后缓冲获取的双路径
- **延迟获取模式** (`delayDrawableAcquisition`): 使用 `SkSurfaces::WrapCAMetalLayer` 包装整个 layer，延迟到实际渲染时才获取 drawable
- **立即获取模式**: 立即调用 `[fMetalLayer nextDrawable]` 获取 drawable，通过 `GrBackendRenderTarget` 包装

### 上下文销毁
调用 `fContext->abandonContext()` 而非简单 reset，处理可能存在的外部引用（如 Lua 绑定）。

## 依赖关系

- **Metal**: `<Metal/Metal.h>`, `<QuartzCore/CAMetalLayer.h>`
- **Ganesh Metal**: `GrMtlBackendContext`, `GrMtlBackendSurface`, `GrMtlDirectContext`, `GrMtlTypes`
- **Ganesh 核心**: `GrDirectContext`, `GrCaps`, `GrDirectContextPriv`

## 设计模式与设计决策

1. **模板方法模式**: 与 GraphiteMetalWindowContext 相同的子类回调模式
2. **MSAA 自动降级**: 构造失败时递归尝试更低的采样数，提高兼容性
3. **延迟/立即双路获取**: 通过 `delayDrawableAcquisition` 参数切换，延迟模式可提高管线并行度

## 性能考量

- 延迟获取模式允许 GPU 在获取 drawable 之前开始处理命令
- `abandonContext()` 确保即使有外部引用也能安全释放

## 相关文件

- `tools/window/GraphiteNativeMetalWindowContext.h/.mm` - Graphite Metal 对照版本
- `tools/window/mac/GaneshMetalWindowContext_mac.mm` - macOS 平台实现
- `include/gpu/ganesh/mtl/GrMtlDirectContext.h` - Ganesh Metal 上下文创建
