# tools/ganesh/mtl - Ganesh Metal 后端测试上下文

## 概述

`tools/ganesh/mtl` 目录实现了 Ganesh GPU 后端的 Apple Metal 测试上下文。Metal 是 Apple 开发的现代低级图形和计算 API，在 macOS、iOS、iPadOS 和 tvOS 上提供接近硬件级别的 GPU 控制能力。随着 Apple 弃用 OpenGL/OpenGL ES，Metal 已成为 Apple 平台上的首选图形 API。

`MtlTestContext` 类继承自 `TestContext`，封装了 Metal 后端上下文的核心状态。与 Vulkan 的多组件上下文不同，Metal 的后端上下文（`GrMtlBackendContext`）相对简洁，主要包含 `MTLDevice` 和 `MTLCommandQueue` 两个核心对象。

本目录的头文件 `MtlTestContext.h` 和实现文件 `MtlTestContext.mm`（Objective-C++ 源文件）提供了 `MtlTestContext` 类的定义和 `CreatePlatformMtlTestContext()` 工厂函数。由于 Metal API 是 Objective-C 风格的，实现文件使用 `.mm` 扩展名以支持 Objective-C++ 混合编程。

Metal 的上下文管理比 OpenGL 简单得多——Metal 没有"当前上下文"的概念，命令通过 `MTLCommandBuffer` 显式提交到 `MTLCommandQueue`，因此 `onPlatformMakeCurrent()` 和 `onPlatformMakeNotCurrent()` 在 Metal 测试上下文中实际上是空操作。

所有代码受 `SK_METAL` 编译宏保护，仅在启用 Metal 支持的 Apple 平台上编译。

## 目录结构

```
tools/ganesh/mtl/
├── BUILD.bazel          # Bazel 构建配置
├── MtlTestContext.h     # Metal 测试上下文声明
└── MtlTestContext.mm    # Metal 测试上下文实现（Objective-C++）
```

## 关键类与函数

### MtlTestContext
- **命名空间**: `sk_gpu_test`
- **基类**: `TestContext`
- **功能**: 封装 Apple Metal GPU 上下文的测试基础设施
- **核心成员**:
  - `fMtl` (`GrMtlBackendContext`) - Metal 后端上下文，包含 MTLDevice 和 MTLCommandQueue
- **核心方法**:
  - `backend()` - 返回 `GrBackendApi::kMetal`
  - `getMtlBackendContext()` - 获取 Metal 后端上下文的常量引用
- **特点**: Metal 无"当前上下文"概念，上下文切换为空操作

### CreatePlatformMtlTestContext
- **签名**: `MtlTestContext* CreatePlatformMtlTestContext(MtlTestContext* shareContext)`
- **功能**: 创建绑定到原生 Metal 库的平台 Metal 测试上下文
- **参数**: `shareContext` - 可选的共享上下文
- **实现**: 使用 `MTLCreateSystemDefaultDevice()` 获取默认 Metal 设备

## 依赖关系

- **上游依赖**: `tools/ganesh/TestContext.h`（基类）
- **Metal 依赖**: `include/gpu/ganesh/mtl/GrMtlBackendContext.h`、Metal.framework
- **编译条件**: 需要定义 `SK_METAL`，仅 Apple 平台
- **被引用**: `tools/ganesh/GrContextFactory.cpp`（通过 `ContextType::kMetal` 使用）
- **语言**: 使用 Objective-C++（.mm 文件）与 Metal API 交互

## Metal 上下文创建流程

1. **获取 Metal 设备**: 调用 `MTLCreateSystemDefaultDevice()` 获取默认 GPU 设备
2. **创建命令队列**: 调用 `[device newCommandQueue]` 创建命令提交队列
3. **初始化后端上下文**: 将 device 和 queue 封装到 `GrMtlBackendContext`
4. **创建 GrDirectContext**: 通过 `GrDirectContexts::MakeMetal()` 创建 Ganesh 上下文

## Metal vs OpenGL 的上下文管理差异

Metal 和 OpenGL 在上下文管理模型上有根本性的区别：

| 特性 | OpenGL | Metal |
|------|--------|-------|
| 当前上下文 | 线程绑定的全局状态 | 不存在 |
| 命令提交 | 隐式（通过 API 调用） | 显式（CommandBuffer） |
| 资源绑定 | 全局状态机 | 显式编码到 CommandEncoder |
| 多线程 | 受限 | 原生支持 |
| 上下文切换开销 | 较高 | 无需切换 |

因此，`MtlTestContext` 的 `onPlatformMakeCurrent()` 和 `onPlatformMakeNotCurrent()` 实现为空操作。Metal 命令通过 `MTLCommandBuffer` 显式提交到 `MTLCommandQueue`，不需要设置"当前"上下文。

## 支持的平台

- macOS 10.11 (El Capitan) 及以上
- iOS 9.0 及以上
- iPadOS 9.0 及以上
- tvOS 9.0 及以上
- Apple Silicon (M1+) 和 Intel Mac 均支持

## 相关文档与参考

- `tools/ganesh/TestContext.h` - 测试上下文基类
- `include/gpu/ganesh/mtl/GrMtlBackendContext.h` - Metal 后端上下文数据结构
- `src/gpu/ganesh/mtl/` - Ganesh Metal 后端核心实现
- `tools/graphite/mtl/` - Graphite Metal 后端测试上下文（对比参考）
- Apple Metal 文档: https://developer.apple.com/metal/
