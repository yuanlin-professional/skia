# GraphiteDawnTestContext - Graphite Dawn 测试上下文

> 源文件:
> - `tools/graphite/dawn/GraphiteDawnTestContext.h`
> - `tools/graphite/dawn/GraphiteDawnTestContext.cpp`

## 概述

GraphiteDawnTestContext 提供了基于 Dawn（WebGPU 的 Chromium 实现）后端的 Graphite 测试上下文实现。它封装了 Dawn 实例、适配器选择、设备创建等复杂流程，支持多种底层图形后端（D3D11、D3D12、Metal、Vulkan、OpenGL、OpenGLES），为 Skia 的 Graphite 渲染引擎提供统一的 Dawn 测试环境。这是三个 Graphite 后端测试上下文中最复杂的一个。

## 架构位置

```
skiatest::graphite::GraphiteTestContext (基类)
    └── skiatest::graphite::DawnTestContext (Dawn 后端实现)
         ├── 支持 D3D11 后端
         ├── 支持 D3D12 后端
         ├── 支持 Metal 后端
         ├── 支持 Vulkan 后端
         ├── 支持 OpenGL 后端
         └── 支持 OpenGLES 后端
```

Dawn 作为 WebGPU 的实现层，本身抽象了多种底层图形 API，因此 `DawnTestContext` 通过 `wgpu::BackendType` 参数支持多种后端。

## 主要类与结构体

### `DawnTestContext`

- **继承**: `GraphiteTestContext`
- **命名空间**: `skiatest::graphite`
- **成员变量**:
  - `fBackendContext` (`skgpu::graphite::DawnBackendContext`): Dawn 后端上下文，包含实例、设备和队列

## 公共 API 函数

| 函数 | 描述 |
|------|------|
| `Make(wgpu::BackendType)` | 静态工厂方法，根据指定后端类型创建测试上下文 |
| `backend()` | 返回 `skgpu::BackendApi::kDawn` |
| `contextType()` | 根据实际后端类型返回对应的 `ContextType` |
| `makeContext(const TestOptions&)` | 创建 Graphite Dawn 上下文用于测试 |
| `getBackendContext()` | 返回底层 `DawnBackendContext` 的常量引用 |
| `tick()` | 处理 Dawn 的异步事件（WebGPU 事件循环） |

## 内部实现细节

### Dawn 实例的懒初始化与缓存

使用 `static SkOnce` 确保 Dawn 实例只创建一次：

```cpp
static std::unique_ptr<dawn::native::Instance> sInstance;
static SkOnce sOnce;
sOnce([&] {
    DawnProcTable backendProcs = dawn::native::GetProcs();
    dawnProcSetProcs(&backendProcs);
    // 配置实例描述符，启用 TimedWaitAny 特性
    sInstance = std::make_unique<dawn::native::Instance>(&desc);
});
```

这一设计避免了每次测试都执行昂贵的 `EnumerateAdapters` 操作。

### 适配器选择策略

1. 根据后端类型确定特性级别（OpenGL/OpenGLES 使用 Compatibility，其他使用 Core）
2. 枚举所有适配器并按优先级排序：先按 `adapterType`（独立GPU > 集成GPU > CPU），再按 `backendType`
3. 选择第一个匹配指定后端类型的适配器

### 设备创建

- 通过 `AddPreferredFeatures` 添加推荐的设备特性
- 获取适配器的硬件限制并传递给设备
- 配置设备丢失和未捕获错误的回调函数
- 设备丢失时（非销毁原因）触发 `SK_ABORT`

### 上下文类型映射

`contextType()` 方法查询设备的实际后端类型，映射为对应的 `skgpu::ContextType`：
- D3D11 -> `kDawn_D3D11`
- D3D12 -> `kDawn_D3D12`
- Metal -> `kDawn_Metal`
- Vulkan -> `kDawn_Vulkan`
- OpenGL -> `kDawn_OpenGL`
- OpenGLES -> `kDawn_OpenGLES`

### 析构函数

显式将设备设为 `nullptr` 并调用 `tick()`，确保设备丢失事件被正确处理。这是一个临时方案，对应 crbug.com/dawn/2450。

## 依赖关系

- **内部依赖**: `GraphiteTestContext`（基类）、`TestOptions`、`ContextOptionsPriv`
- **Dawn/WebGPU**: `dawn/native/DawnNative.h`、`webgpu/webgpu_cpp.h`、`dawn/dawn_proc.h`
- **Graphite 核心**: `Context`、`ContextOptions`、`DawnBackendContext`、`DawnGraphiteTypes`
- **工具模块**: `GraphiteDawnToggles.h`（Dawn 开关配置）、`SkOnce`（一次性初始化）

## 设计模式与设计决策

- **工厂方法模式**: `Make(wgpu::BackendType)` 通过参数化后端类型，用一个工厂方法支持多种后端
- **单例缓存**: Dawn 实例和适配器枚举结果通过 `static` 变量缓存，避免重复初始化
- **回调错误处理**: 设备丢失和未捕获错误通过回调机制处理，设备意外丢失时触发 `SK_ABORT`
- **Toggle 系统**: 通过 `GetInstanceToggles()` 和 `GetAdapterToggles()` 分层配置 Dawn 开关
- **`fNeverYieldToWebGPU` 选项**: 允许在测试时禁用 WebGPU 事件循环 tick

## 性能考量

- Dawn 实例的 `EnumerateAdapters` 首次调用开销较大，缓存实例可显著减少后续测试的初始化时间
- 适配器排序优先选择独立 GPU，确保测试使用最佳硬件
- `tick()` 方法调用 `fBackendContext.fTick(fBackendContext.fInstance)` 驱动异步事件处理，在测试中需要定期调用以避免操作阻塞
- `LOG_ADAPTER` 宏默认关闭（设为 0），避免在生产测试中产生调试输出

## 相关文件

- `tools/graphite/GraphiteTestContext.h` - 测试上下文基类
- `tools/graphite/dawn/GraphiteDawnToggles.h` - Dawn 开关配置
- `tools/graphite/vk/GraphiteVulkanTestContext.h` - Vulkan 后端对应实现
- `tools/graphite/mtl/GraphiteMtlTestContext.h` - Metal 后端对应实现
- `include/gpu/graphite/dawn/DawnBackendContext.h` - Dawn 后端上下文定义
- `tools/graphite/TestOptions.h` - 测试选项定义
