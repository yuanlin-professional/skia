# tools/graphite - Graphite GPU 后端测试工具集

## 概述

`tools/graphite` 目录包含了 Skia Graphite GPU 后端的测试基础设施和辅助工具。Graphite 是 Skia 的新一代 GPU 渲染后端，采用了现代化的架构设计，支持 Dawn（WebGPU）、Vulkan 和 Metal 三种图形 API 后端。与传统的 Ganesh 后端相比，Graphite 在架构上更加模块化，提供了更好的多线程支持和资源管理。

核心功能围绕 `ContextFactory` 和 `GraphiteTestContext` 两个关键类展开。`ContextFactory` 是 Graphite 的上下文工厂类，负责创建和管理不同后端类型的 `skgpu::graphite::Context` 实例。`GraphiteTestContext` 是所有 Graphite 测试上下文的抽象基类，定义了 Recording 提交、GPU 同步等核心测试接口。

本目录还提供了多个重要的测试辅助工具：`GraphiteToolUtils` 提供测试用的 Recorder 选项创建；`UniqueKeyUtils` 提供图形管线唯一键的提取和验证工具；`GraphiteMemoryPipelineStorage` 提供内存中的管线数据持久化存储；`PipelineCallbackHandler` 提供管线编译回调处理，支持 Android 风格的预编译键收集和管线跟踪。

`TestOptions` 结构体扩展了 `ContextOptions`，为测试场景提供了额外的配置选项，包括 Dawn 特有的 Tint 符号重命名禁用、WebGPU 让步控制等。此外，`ProtectedUtils_Graphite.cpp` 提供了受保护内容（DRM）的测试辅助函数。

## 目录结构

```
tools/graphite/
├── BUILD.bazel                            # Bazel 构建配置
├── ContextFactory.h/.cpp                  # Graphite 上下文工厂
├── GraphiteTestContext.h/.cpp             # Graphite 测试上下文基类
├── GraphiteToolUtils.h/.cpp               # Graphite 工具辅助函数
├── UniqueKeyUtils.h/.cpp                  # 管线唯一键工具
├── GraphiteMemoryPipelineStorage.h/.cpp   # 内存管线存储
├── PipelineCallbackHandler.h/.cpp         # 管线编译回调处理器
├── TestOptions.h                          # 测试选项配置
├── ProtectedUtils_Graphite.cpp            # 受保护内容测试工具
├── dawn/                                  # Dawn/WebGPU 后端
├── vk/                                    # Vulkan 后端
├── mtl/                                   # Metal 后端
└── precompile/                            # 预编译测试工具
```

## 关键类与函数

### ContextFactory
- **命名空间**: `skiatest::graphite`
- **功能**: 创建和管理不同 Graphite 后端的 Context 实例
- **核心方法**:
  - `getContextInfo(skgpu::ContextType)` - 获取指定类型的上下文信息
- **返回值**: `ContextInfo` 结构体，包含 `GraphiteTestContext*` 和 `Context*`

### GraphiteTestContext
- **命名空间**: `skiatest::graphite`
- **功能**: Graphite 离屏 3D 上下文的抽象基类
- **核心方法**:
  - `backend()` - 返回后端 API 类型
  - `contextType()` - 返回上下文类型
  - `makeContext(const TestOptions&)` - 创建 Graphite Context
  - `submitRecordingAndWaitOnSync()` - 提交 Recording 并等待 GPU 同步
  - `syncedSubmit()` - 同步提交（忙等循环或直接同步）
  - `tick()` - 允许 GPU API 推进提交工作的处理

### PipelineCallBackHandler
- **命名空间**: `skiatools::graphite`
- **功能**: 管线编译回调处理器，用于预编译测试
- **核心方法**:
  - `CallBack()` - 静态回调函数，处理管线缓存操作
  - `retrieveKeys()` - 获取收集到的 Android 风格预编译键
  - `report()` - 打印管线标签列表

### UniqueKeyUtils
- `FetchUniqueKeys()` - 从 PrecompileContext 获取所有管线唯一键
- `ExtractKeyDescs()` - 将唯一键分解为 GraphicsPipelineDesc 和 RenderPassDesc

### GraphiteMemoryPipelineStorage
- 实现 `PersistentPipelineStorage` 接口
- 提供内存中的管线数据存储，支持加载/存储统计

## 依赖关系

- **上游依赖**: `include/gpu/graphite/`（Context、ContextOptions、GraphiteTypes）
- **内部依赖**: `src/gpu/graphite/`（ContextOptionsPriv、GlobalCache、ShaderCodeDictionary）
- **同级依赖**: `tools/gpu/`（ContextType、BackendSurfaceFactory、FlushFinishTracker）
- **下游依赖**: `tests/`（Graphite 单元测试）、`dm/`（测试驱动）
- **条件依赖**: Dawn（`SK_DAWN`）、Vulkan（`SK_VULKAN`）、Metal（`SK_METAL`）

## Ganesh 与 Graphite 测试框架对比

| 特性 | Ganesh | Graphite |
|------|--------|----------|
| 上下文工厂 | `GrContextFactory` | `ContextFactory` |
| 测试上下文基类 | `TestContext` | `GraphiteTestContext` |
| 上下文类型 | `GrDirectContext` | `skgpu::graphite::Context` |
| 命令提交 | flush + sync | Recording + submit |
| 后端支持 | GL, Vulkan, Metal, D3D, Mock | Dawn, Vulkan, Metal |
| 命名空间 | `sk_gpu_test` | `skiatest::graphite` |
| 上下文切换 | `makeCurrent()` | 不需要（现代 API 模型） |
| 共享上下文 | 支持 | 不适用 |

## TestOptions 详细说明

`TestOptions` 结构体封装了 Graphite 测试专用的配置选项：
- `fContextOptions` - 标准 Graphite 上下文选项
- `fOptionsPriv` - 私有选项（如内部调试标志）
- Dawn 专属选项（受 `SK_DAWN` 保护）：
  - `fDisableTintSymbolRenaming` - 禁用 Tint 编译器的符号重命名
  - `fNeverYieldToWebGPU` - 禁止向 WebGPU 让步
  - `fUseWGPUTextureView` - 使用 WGPU 纹理视图

## 相关文档与参考

- `tools/graphite/dawn/` - Dawn/WebGPU 后端测试上下文
- `tools/graphite/vk/` - Vulkan 后端测试上下文
- `tools/graphite/mtl/` - Metal 后端测试上下文
- `tools/graphite/precompile/` - 预编译效果工厂
- `include/gpu/graphite/Context.h` - Graphite Context 公共 API
- `include/gpu/graphite/ContextOptions.h` - 上下文配置选项
- `tools/ganesh/` - Ganesh 后端测试工具集（对比参考）
