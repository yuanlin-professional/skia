# DawnSharedContext

> 源文件:
> - `src/gpu/graphite/dawn/DawnSharedContext.h`
> - `src/gpu/graphite/dawn/DawnSharedContext.cpp`

## 概述

`DawnSharedContext` 是 Skia Graphite 渲染引擎 Dawn (WebGPU) 后端的共享上下文实现。它继承自 `SharedContext` 基类，封装了 Dawn/WebGPU 的核心对象（`wgpu::Device`、`wgpu::Queue`、`wgpu::Instance`），并负责创建图形管线、资源提供者以及预定义的绑定组布局。该类在整个 Graphite 上下文生命周期内只存在一个实例，被所有 Recorder 共享。

## 架构位置

```
Graphite Context
  └── SharedContext (平台无关基类)
        └── DawnSharedContext (Dawn/WebGPU 后端)
              ├── DawnCaps (Dawn 能力查询)
              ├── DawnResourceProvider (资源创建，每个 Recorder 一个)
              ├── DawnThreadSafeResourceProvider (线程安全资源提供者)
              └── DawnGraphicsPipeline (图形管线创建)
```

## 主要类与结构体

### `DawnSharedContext`
- 继承自 `SharedContext`，是 Dawn 后端的上下文核心。
- 持有 WebGPU 核心对象：`wgpu::Instance`、`wgpu::Device`、`wgpu::Queue`。
- 持有一个空操作（noop）片段着色器模块 `fNoopFragment`，用于绕过 Dawn 对无片段着色器管线的验证错误。
- 预创建两个通用绑定组布局：`fUniformBuffersBindGroupLayout` 和 `fSingleTextureSamplerBindGroupLayout`。
- 持有可选的 `fTick` 函数指针（`DawnTickFunction*`），用于驱动 Dawn 实例的事件处理。

### `DawnThreadSafeResourceProvider`
- 继承自 `ThreadSafeResourceProvider`。
- 提供线程安全的资源访问能力，封装了一个 `ResourceProvider` 实例。

## 公共 API 函数

### 工厂方法
- **`static Make(const DawnBackendContext&, const ContextOptions&) -> sk_sp<SharedContext>`**：创建 `DawnSharedContext` 实例。验证 `fDevice` 和 `fQueue` 有效性，创建 noop 片段着色器和 `DawnCaps`。

### 访问器
- **`dawnCaps()`**：返回 `DawnCaps` 指针，提供 Dawn 后端的能力查询。
- **`device()`**：返回底层 `wgpu::Device` 引用。
- **`queue()`**：返回底层 `wgpu::Queue` 引用。
- **`instance()`**：返回底层 `wgpu::Instance` 引用。
- **`noopFragment()`**：返回空操作片段着色器模块，供管线创建使用。
- **`hasTick()`**：检查是否有 tick 回调函数。
- **`tick()`**：执行 Dawn 实例的 tick 操作。
- **`getUniformBuffersBindGroupLayout()`**：返回统一缓冲区绑定组布局。
- **`getSingleTextureSamplerBindGroupLayout()`**：返回单纹理+采样器绑定组布局。

### 资源管理
- **`threadSafeResourceProvider()`**：返回线程安全资源提供者。
- **`makeResourceProvider(SingleOwner*, uint32_t, size_t)`**：创建新的 `DawnResourceProvider` 实例，每个 Recorder 拥有独立的资源提供者。
- **`deviceTick(Context*)`**：在非 Emscripten 环境中调用 `device.Tick()` 并检查异步任务完成状态。

## 内部实现细节

### Noop 片段着色器
Dawn 要求有颜色附件的管线必须有片段着色器，但某些渲染步骤可能只需要顶点处理。为此，`DawnSharedContext` 在初始化时创建一个最简 WGSL 片段着色器：
```wgsl
@fragment
fn main() {}
```
该着色器在 Emscripten 和原生环境下使用不同的描述符类型（`ShaderModuleWGSLDescriptor` vs `ShaderSourceWGSL`）。

### 绑定组布局预创建
构造函数中预创建两种绑定组布局：

1. **统一缓冲区绑定组布局**（3 个绑定点）：
   - 绑定 0：内部常量 uniform 缓冲区，`Vertex | Fragment` 可见，动态偏移。
   - 绑定 1：组合 uniform 缓冲区，类型取决于是否支持存储缓冲区（`ReadOnlyStorage` 或 `Uniform`），动态偏移。
   - 绑定 2：渐变缓冲区，仅 `Fragment` 可见，类型同样取决于存储缓冲区支持。

2. **单纹理+采样器绑定组布局**（2 个绑定点）：
   - 绑定 0：过滤采样器。
   - 绑定 1：2D 浮点纹理。

### 资源清理顺序
析构时先重置线程安全资源提供者，然后删除全局缓存中的资源，确保正确的销毁顺序。

### 图形管线创建
`createGraphicsPipeline()` 委托给 `DawnGraphicsPipeline::Make()`，传入运行时效果字典、管线描述、渲染通道描述等参数。

## 依赖关系

- **基类**: `SharedContext`
- **Dawn 后端类**: `DawnCaps`、`DawnResourceProvider`、`DawnGraphicsPipeline`
- **WebGPU API**: `wgpu::Device`、`wgpu::Queue`、`wgpu::Instance`、`wgpu::ShaderModule`、`wgpu::BindGroupLayout`
- **Graphite 核心**: `Context`、`ContextOptions`、`DawnBackendContext`、`ThreadSafeResourceProvider`

## 设计模式与设计决策

1. **工厂方法模式**：通过静态 `Make()` 函数创建实例，在构造前进行验证和预处理。
2. **共享上下文模式**：在所有 Recorder 间共享 Dawn 设备和队列，减少资源重复和同步开销。
3. **预创建绑定组布局**：将常用的绑定组布局在上下文初始化时一次性创建，所有后续的绑定组创建都复用这些布局，提高管线兼容性和创建效率。
4. **Noop 着色器变通方案**：优雅地处理了 Dawn 验证规则与 Skia 管线模型之间的不匹配。
5. **平台适配**：通过 `__EMSCRIPTEN__` 宏区分 WebAssembly 和原生 Dawn 环境，适配不同的 API 差异（如 `Tick()` 和着色器描述符类型）。

## 性能考量

- **绑定组布局复用**：预创建的绑定组布局在所有管线中共享，避免每次创建管线时重新创建布局。
- **线程安全资源提供者**：允许多线程场景下的安全资源访问，减少锁竞争。
- **存储缓冲区自适应**：根据设备能力选择 `ReadOnlyStorage` 或 `Uniform` 缓冲区类型，在支持存储缓冲区的设备上获得更好的性能。
- **deviceTick**：非 Emscripten 平台需要显式调用 `device.Tick()` 来推进 GPU 任务完成回调。

## 相关文件

- `src/gpu/graphite/SharedContext.h` - 基类定义
- `src/gpu/graphite/dawn/DawnCaps.h` - Dawn 能力查询
- `src/gpu/graphite/dawn/DawnResourceProvider.h` - Dawn 资源提供者
- `src/gpu/graphite/dawn/DawnGraphicsPipeline.h` - Dawn 图形管线
- `include/gpu/graphite/dawn/DawnBackendContext.h` - Dawn 后端上下文数据
- `include/gpu/graphite/ContextOptions.h` - 上下文配置选项
- `src/gpu/graphite/ThreadSafeResourceProvider.h` - 线程安全资源提供者基类
