# DawnBuffer

> 源文件
> - src/gpu/graphite/dawn/DawnBuffer.h
> - src/gpu/graphite/dawn/DawnBuffer.cpp

## 概述

`DawnBuffer` 是 Skia Graphite 渲染引擎中专门为 WebGPU/Dawn 后端实现的 GPU 缓冲区管理类。该类继承自 `Buffer` 基类,封装了 `wgpu::Buffer` 对象,提供了统一的缓冲区创建、映射、解映射和资源管理接口。它支持多种缓冲区类型(顶点、索引、统一、存储、传输等),并处理异步映射操作和资源回收机制。

`DawnBuffer` 的核心职责包括:将 Graphite 的缓冲区抽象转换为 Dawn 特定的实现、管理 CPU-GPU 内存映射状态、处理异步映射回调、支持缓冲区缓存池复用。该类还处理了 Emscripten 和原生 Dawn API 之间的差异,提供了跨平台的统一接口。

## 架构位置

`DawnBuffer` 位于 Skia Graphite 的 Dawn 后端实现层,在架构中的位置如下:

```
skgpu::graphite
├── Buffer (基类 - 跨后端抽象)
├── ResourceProvider (资源管理)
└── dawn/
    ├── DawnBuffer (Dawn 缓冲区实现)
    ├── DawnSharedContext (Dawn 上下文)
    ├── DawnResourceProvider (Dawn 资源提供者)
    └── DawnAsyncWait (异步等待工具)
```

`DawnBuffer` 实现了 Graphite 的 `Buffer` 接口,与 `DawnSharedContext` 协作获取 Dawn 设备,与 `DawnAsyncWait` 协作处理异步操作。它是 Dawn 后端中所有需要 GPU 缓冲区功能的组件的基础,包括顶点缓冲区、索引缓冲区、统一缓冲区等。

## 主要类与结构体

### DawnBuffer 类

```cpp
class DawnBuffer final : public Buffer {
public:
    // 静态工厂方法创建缓冲区
    static sk_sp<DawnBuffer> Make(const DawnSharedContext*,
                                  size_t,
                                  BufferType,
                                  AccessPattern,
                                  std::string_view label);

    // 查询缓冲区是否可解映射
    bool isUnmappable() const override;

    // 获取底层 Dawn 缓冲区对象
    const wgpu::Buffer& dawnBuffer() const { return fBuffer; }

private:
    // 缓冲区映射回调处理
    template <typename StatusT, typename MessageT>
    void mapCallback(StatusT status, MessageT message);

    // 资源回收准备
    bool prepareForReturnToCache(Resource::TakeRefFunc, void*) override;

    wgpu::Buffer fBuffer;                                      // Dawn 缓冲区对象
    skia_private::STArray<1, AutoCallback> fAsyncMapCallbacks; // 异步映射回调队列
    SingleOwner fSingleAsyncMapCallbacksOwner;                 // 线程安全保护
};
```

### 主要枚举和常量

- **BufferType**: 缓冲区类型(Vertex, Index, Uniform, Storage, XferCpuToGpu, XferGpuToCpu, Query, Indirect, VertexStorage, IndexStorage)
- **AccessPattern**: 访问模式(HostVisible, GpuOnlyCopySrc)
- **wgpu::BufferUsage**: Dawn 缓冲区用途标志(Vertex, Index, Uniform, Storage, MapRead, MapWrite, CopySrc, CopyDst, Indirect, QueryResolve)
- **wgpu::BufferMapState**: 缓冲区映射状态(Mapped, Unmapped, Pending)

## 公共 API 函数

### 缓冲区创建

```cpp
sk_sp<DawnBuffer> DawnBuffer::Make(const DawnSharedContext* sharedContext,
                                   size_t size,
                                   BufferType type,
                                   AccessPattern accessPattern,
                                   std::string_view label)
```
静态工厂方法,根据指定参数创建 Dawn 缓冲区。该方法将 Graphite 的 `BufferType` 和 `AccessPattern` 转换为 Dawn 的 `wgpu::BufferUsage` 标志,并处理特殊情况(如可映射缓冲区、MSAA 支持等)。

### 缓冲区查询

```cpp
bool isUnmappable() const
```
检查缓冲区当前是否处于不可解映射状态(已映射或映射待定状态)。

```cpp
const wgpu::Buffer& dawnBuffer() const
```
获取底层 `wgpu::Buffer` 对象的常量引用,供 Dawn 特定操作使用。

## 内部实现细节

### 缓冲区创建逻辑

`DawnBuffer::Make()` 方法包含复杂的缓冲区用途标志计算逻辑:

1. **基础用途映射**: 将 `BufferType` 映射到 Dawn 的 `wgpu::BufferUsage`:
   - `kVertex` → `Vertex | CopyDst`
   - `kIndex` → `Index | CopyDst`
   - `kUniform` → `Uniform | CopyDst`
   - `kStorage` → `Storage | CopyDst | CopySrc`
   - `kXferCpuToGpu` → `CopySrc | MapWrite`
   - `kXferGpuToCpu` → `CopyDst | MapRead`

2. **可映射缓冲区优化**: 如果设备支持绘制缓冲区映射(`drawBufferCanBeMapped()`)且访问模式为 `kHostVisible`,则添加 `MapWrite` 并移除 `CopyDst`,避免 CPU 和 GPU 同时写入。

3. **创建时映射**: 为可映射写入的缓冲区设置 `mappedAtCreation = true`,避免 GPU 清零操作导致的性能问题。

### 异步映射机制

`DawnBuffer` 支持异步映射操作,通过 `onAsyncMap()` 方法实现:

```cpp
void DawnBuffer::onAsyncMap(GpuFinishedProc proc, GpuFinishedContext ctx)
```

该方法处理 Emscripten 和原生 Dawn 的 API 差异:
- **Emscripten**: 使用 C 风格回调 `WGPUBufferMapAsyncStatus`
- **原生 Dawn**: 使用 C++ 风格回调和 `wgpu::CallbackMode::AllowSpontaneous` 允许立即触发

映射完成后,`mapCallback()` 模板方法统一处理成功和失败情况,更新 `fMapPtr` 指针并触发所有注册的回调。

### 资源回收与缓存复用

`prepareForReturnToCache()` 方法为缓冲区回收到缓存池做准备:

1. 检查缓冲区是否已映射,若已映射则拒绝回收
2. 持有缓冲区引用(`takeRef`)以防止提前释放
3. 发起异步映射操作,映射完成后缓冲区可供复用
4. 若映射失败,标记缓冲区为立即删除(`setDeleteASAP()`)

这种机制确保缓冲区在缓存池中始终处于映射状态,可立即使用而无需等待异步映射完成。

### 跨平台兼容性处理

代码通过条件编译和模板函数处理 Emscripten 和原生 Dawn 的差异:

- **错误日志**: `log_map_error()` 函数根据平台使用不同的状态枚举
- **映射成功检查**: `is_map_succeeded()` 函数统一处理两种平台的成功状态
- **回调签名**: 模板方法 `mapCallback()` 接受不同的状态和消息类型

## 依赖关系

### 对外依赖

| 依赖类/模块 | 用途 | 依赖类型 |
|------------|------|---------|
| `wgpu::Buffer` | 底层 WebGPU 缓冲区对象 | 强依赖 |
| `DawnSharedContext` | 获取 Dawn 设备和上下文信息 | 强依赖 |
| `DawnAsyncWait` | 异步操作等待机制 | 强依赖 |
| `Buffer` | Graphite 缓冲区基类 | 继承 |
| `RefCntedCallback` | 回调管理工具 | 辅助 |

### 被依赖关系

- **DawnCommandBuffer**: 使用 `DawnBuffer` 进行绘制和计算操作
- **DawnResourceProvider**: 创建和管理 `DawnBuffer` 实例
- **Graphite 渲染管线**: 使用缓冲区存储顶点、索引、统一和存储数据

## 设计模式与设计决策

### 工厂方法模式

使用静态 `Make()` 方法而非公开构造函数,提供灵活的对象创建逻辑:
- 参数验证(size <= 0 检查)
- 复杂的用途标志计算
- 平台特定的初始化逻辑
- 失败时返回 nullptr 而非抛出异常

### 模板方法模式

`mapCallback()` 使用模板方法模式统一处理不同平台的回调:
```cpp
template <typename StatusT, typename MessageT>
void DawnBuffer::mapCallback(StatusT status, MessageT message)
```
这种设计消除了代码重复,同时保持类型安全。

### RAII 资源管理

缓冲区的生命周期通过 `sk_sp` 智能指针管理,`freeGpuData()` 方法确保 GPU 资源释放:
```cpp
void DawnBuffer::freeGpuData() {
    if (fBuffer) {
        fBuffer.Destroy();  // 显式销毁
        fBuffer = nullptr;
    }
}
```

显式调用 `Destroy()` 的原因:缓冲区可能被缓存的绑定组引用,不会立即释放,显式销毁确保 GPU 资源及时回收。

### 线程安全设计

使用 `SingleOwner` 保护 `fAsyncMapCallbacks` 访问,防止多线程竞争:
```cpp
[[maybe_unused]] SingleOwner fSingleAsyncMapCallbacksOwner;
SKGPU_ASSERT_SINGLE_OWNER(&fSingleAsyncMapCallbacksOwner)
```

## 性能考量

### 创建时映射优化

对于可映射写入的缓冲区,设置 `mappedAtCreation = true`:
```cpp
desc.mappedAtCreation = SkToBool(usage & wgpu::BufferUsage::MapWrite);
```
这避免了 GPU 清零操作,`MapAsync` 不必等待 GPU 执行完成,显著提升性能。

### 缓存池复用

`prepareForReturnToCache()` 确保缓冲区在缓存池中保持映射状态:
- 减少重复的异步映射等待时间
- 提高缓冲区分配速度
- 降低 CPU-GPU 同步开销

### 用途标志优化

代码智能处理缓冲区用途标志:
- 可映射缓冲区移除 `CopyDst`,避免 CPU/GPU 写入冲突
- Query 缓冲区添加 `MapRead`,直接读取结果无需传输缓冲区
- 按需添加 `CopySrc`,减少不必要的权限

### 同步映射限制

Dawn 不支持同步映射,`onMap()` 直接记录警告:
```cpp
void DawnBuffer::onMap() {
    SKGPU_LOG_W("Synchronous buffer mapping not supported in Dawn.");
}
```
这引导开发者使用异步 API,符合 WebGPU 的异步设计哲学。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/Buffer.h` | 基类定义 | Graphite 缓冲区抽象接口 |
| `src/gpu/graphite/dawn/DawnSharedContext.h` | 协作类 | 提供 Dawn 设备和上下文 |
| `src/gpu/graphite/dawn/DawnAsyncWait.h` | 辅助工具 | 异步操作等待机制 |
| `src/gpu/graphite/dawn/DawnResourceProvider.h` | 创建者 | 负责创建 DawnBuffer 实例 |
| `src/gpu/graphite/dawn/DawnCommandBuffer.h` | 使用者 | 使用 DawnBuffer 执行渲染命令 |
| `src/gpu/RefCntedCallback.h` | 辅助工具 | 回调生命周期管理 |
| `include/private/base/SingleOwner.h` | 辅助工具 | 线程安全断言工具 |
| `webgpu/webgpu_cpp.h` | 外部依赖 | WebGPU C++ API 头文件 |
