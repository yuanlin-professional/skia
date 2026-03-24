# tools/graphite/mtl - Graphite Metal 后端测试上下文

## 概述

`tools/graphite/mtl` 目录实现了 Graphite GPU 后端的 Apple Metal 测试上下文。Metal 是 Apple 平台上首选的现代图形 API，Graphite 的 Metal 后端充分利用了 Metal 的现代化特性，包括命令缓冲区管理、资源堆和管线状态对象等。

`MtlTestContext` 类继承自 `GraphiteTestContext`，封装了 `MtlBackendContext`（包含 Metal 设备和命令队列的 Objective-C 对象引用）。与 Ganesh 的 Metal 测试上下文类似，但使用了 Graphite 特有的后端上下文类型 `skgpu::graphite::MtlBackendContext`。

通过 `MtlTestContext::Make()` 静态工厂方法创建测试上下文。该方法使用 `MTLCreateSystemDefaultDevice()` 获取系统默认的 Metal 设备，并创建对应的命令队列。实现文件使用 `.mm` 扩展名（Objective-C++），以便与 Metal 的 Objective-C API 交互。

Graphite 的 Metal 后端采用了更现代的资源管理模型。与 Ganesh 不同，Graphite 通过 `Recording` 机制收集渲染命令，然后批量提交到 GPU，这更符合 Metal 的命令缓冲区设计理念。测试上下文通过 `submitRecordingAndWaitOnSync()` 方法支持这种提交模式。

所有代码受 `SK_METAL` 编译宏保护，仅在 Apple 平台（macOS、iOS）上编译。

## 目录结构

```
tools/graphite/mtl/
├── GraphiteMtlTestContext.h      # Metal 测试上下文声明
└── GraphiteMtlTestContext.mm    # Metal 测试上下文实现（Objective-C++）
```

## 关键类与函数

### MtlTestContext
- **命名空间**: `skiatest::graphite`
- **基类**: `GraphiteTestContext`
- **功能**: 封装 Graphite Metal GPU 上下文的测试基础设施
- **核心成员**:
  - `fMtl` (`skgpu::graphite::MtlBackendContext`) - Metal 后端上下文
- **核心方法**:
  - `Make()` - 静态工厂方法，创建 Metal 测试上下文
  - `backend()` - 返回 `skgpu::BackendApi::kMetal`
  - `contextType()` - 返回上下文类型
  - `makeContext(const TestOptions&)` - 创建 Graphite Context
  - `getBackendContext()` - 获取 Metal 后端上下文引用

### Metal 后端上下文组成
- `id<MTLDevice>` - Metal 设备对象（通过 `CFTypeRef` 封装）
- `id<MTLCommandQueue>` - Metal 命令队列（通过 `CFTypeRef` 封装）
- Graphite 的 `MtlBackendContext` 使用 `CFTypeRef` 而非直接的 Objective-C 类型，以便在 C++ 头文件中声明

## 依赖关系

- **上游依赖**: `tools/graphite/GraphiteTestContext.h`（基类）
- **Metal 依赖**: `include/gpu/graphite/mtl/MtlBackendContext.h`、Metal.framework
- **编译条件**: 需要定义 `SK_METAL`，仅 Apple 平台
- **被引用**: `tools/graphite/ContextFactory.cpp`（通过 Metal ContextType 使用）
- **语言**: 使用 Objective-C++（.mm 文件）与 Metal API 交互

## 相关文档与参考

- `tools/graphite/GraphiteTestContext.h` - Graphite 测试上下文基类
- `include/gpu/graphite/mtl/MtlBackendContext.h` - Metal 后端上下文数据结构
- `tools/ganesh/mtl/` - Ganesh Metal 后端测试上下文（对比参考）
- `src/gpu/graphite/mtl/` - Graphite Metal 后端核心实现
- Apple Metal 文档: https://developer.apple.com/metal/
