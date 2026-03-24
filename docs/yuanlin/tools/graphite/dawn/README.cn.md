# tools/graphite/dawn - Graphite Dawn/WebGPU 后端测试上下文

## 概述

`tools/graphite/dawn` 目录实现了 Graphite GPU 后端的 Dawn 测试上下文。Dawn 是 Google 开发的 WebGPU 原生实现，作为跨平台图形 API 抽象层，可以在底层使用 Vulkan、Metal、Direct3D 12 或 OpenGL 等多种图形 API。在 Skia 中，Dawn 后端使得 Graphite 能够通过 WebGPU 接口访问 GPU。

`DawnTestContext` 类继承自 `GraphiteTestContext`，封装了 `DawnBackendContext`（包含 `wgpu::Device` 和 `wgpu::Queue` 等 WebGPU 核心对象）。通过 `DawnTestContext::Make(wgpu::BackendType)` 静态工厂方法，可以创建基于不同底层 API（Vulkan、Metal、D3D12 等）的 Dawn 测试上下文。

该实现的一个重要特性是 `tick()` 方法的实现。由于 WebGPU 使用异步回调模型，Dawn 后端需要定期调用 `tick()` 来推进 GPU 工作的完成和回调的执行，这与 Vulkan 和 Metal 可以在独立线程上处理的方式不同。

`GraphiteDawnToggles` 提供了 Dawn 特有的配置控制，包括实例级和适配器级的 toggles（开关）设置，以及首选特性（Preferred Features）的管理。这些 toggles 用于控制 Dawn 的内部行为，例如启用或禁用特定的优化或验证。

所有代码受 `SK_DAWN` 编译宏保护。

## 目录结构

```
tools/graphite/dawn/
├── GraphiteDawnTestContext.h      # Dawn 测试上下文声明
├── GraphiteDawnTestContext.cpp    # Dawn 测试上下文实现
├── GraphiteDawnToggles.h          # Dawn toggles 配置声明
└── GraphiteDawnToggles.cpp        # Dawn toggles 配置实现
```

## 关键类与函数

### DawnTestContext
- **命名空间**: `skiatest::graphite`
- **基类**: `GraphiteTestContext`
- **功能**: 封装 Dawn/WebGPU GPU 上下文的测试基础设施
- **核心成员**:
  - `fBackendContext` (`skgpu::graphite::DawnBackendContext`) - Dawn 后端上下文
- **核心方法**:
  - `Make(wgpu::BackendType)` - 静态工厂方法，创建指定底层 API 的 Dawn 上下文
  - `backend()` - 返回 `skgpu::BackendApi::kDawn`
  - `contextType()` - 返回上下文类型
  - `makeContext(const TestOptions&)` - 创建 Graphite Context
  - `tick()` - 推进 Dawn 的异步工作处理（关键方法）
  - `getBackendContext()` - 获取 Dawn 后端上下文引用

### Dawn Toggles 配置
- **GetInstanceToggles()** - 获取创建 `wgpu::Instance` 时使用的 toggles
- **GetAdapterToggles()** - 获取创建 `wgpu::Adapter` 时使用的 toggles
- **AddPreferredFeatures()** - 向特性列表中追加适配器支持的首选特性

### Dawn 后端上下文组成
- `wgpu::Device` - WebGPU 设备对象
- `wgpu::Queue` - WebGPU 命令队列
- `dawn::native::Instance` - Dawn 原生实例（用于设备发现）

## 依赖关系

- **上游依赖**: `tools/graphite/GraphiteTestContext.h`（基类）
- **Dawn 依赖**: `include/gpu/graphite/dawn/DawnBackendContext.h`、`webgpu/webgpu_cpp.h`、`dawn/native/DawnNative.h`
- **编译条件**: 需要定义 `SK_DAWN`
- **被引用**: `tools/graphite/ContextFactory.cpp`（通过 Dawn ContextType 使用）
- **TestOptions 支持**: `fDisableTintSymbolRenaming`、`fNeverYieldToWebGPU`、`fUseWGPUTextureView`

## 相关文档与参考

- `tools/graphite/GraphiteTestContext.h` - Graphite 测试上下文基类
- `include/gpu/graphite/dawn/DawnBackendContext.h` - Dawn 后端上下文数据结构
- `src/gpu/graphite/dawn/` - Graphite Dawn 后端核心实现
- Dawn 项目: https://dawn.googlesource.com/dawn
- WebGPU 规范: https://www.w3.org/TR/webgpu/
- `tools/graphite/TestOptions.h` - Dawn 特有的测试选项
