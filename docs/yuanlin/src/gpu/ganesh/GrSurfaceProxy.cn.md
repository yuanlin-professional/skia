# GrSurfaceProxy

> 源文件: src/gpu/ganesh/GrSurfaceProxy.h, src/gpu/ganesh/GrSurfaceProxy.cpp

## 概述

`GrSurfaceProxy` 是 Ganesh GPU 后端中的核心抽象类，用于代理 GPU surface 资源。它实现了延迟资源实例化（lazy instantiation）机制，允许在实际需要之前推迟 GPU 资源的创建。这种设计使得 Skia 可以更高效地管理 GPU 内存，优化资源分配，并支持命令缓冲和跨线程操作。

Proxy 模式在 Ganesh 中扮演着关键角色：它既可以代理已存在的 GPU surface（wrapped），也可以代理尚未创建的资源（deferred），还支持通过回调函数动态创建资源（lazy）。这种灵活性使得资源管理既高效又可预测。

## 架构位置

`GrSurfaceProxy` 位于 Ganesh GPU 后端的资源管理层核心：

- **基类地位**: 是 `GrTextureProxy` 和 `GrRenderTargetProxy` 的抽象基类
- **上游调用者**: `GrSurfaceProxyView`、`SurfaceContext`、`GrRenderTask`、resource allocator
- **下游依赖**: `GrSurface` 及其子类（实际的 GPU 资源）
- **协作组件**: `GrResourceProvider` 负责实际创建资源，`GrResourceAllocator` 负责资源分配调度

该类是 Skia GPU 层"代理-实体"分离架构的核心，使得命令记录和命令执行可以分离。

## 主要类与结构体

### GrSurfaceProxy 类

**继承关系:**
- 基类: `SkNVRefCnt<GrSurfaceProxy>`（非虚拟引用计数）
- 派生类: `GrTextureProxy`、`GrRenderTargetProxy`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTarget` | `sk_sp<GrSurface>` | 实例化后的实际 surface，未实例化时为 null |
| `fFormat` | `const GrBackendFormat` | GPU 后端格式（不可变） |
| `fDimensions` | `SkISize` | Surface 尺寸，fully lazy 时为负值 |
| `fFit` | `SkBackingFit` | kExact 或 kApprox（允许稍大的分配） |
| `fBudgeted` | `skgpu::Budgeted` | 是否计入资源预算 |
| `fUniqueID` | `const UniqueID` | 唯一标识符 |
| `fLazyInstantiateCallback` | `LazyInstantiateCallback` | 延迟实例化回调函数 |
| `fSurfaceFlags` | `GrInternalSurfaceFlags` | Surface 标志（只读、framebuffer-only 等） |
| `fIsProtected` | `GrProtected` | 是否是受保护的内存 |
| `fGpuMemorySize` | `std::atomic<size_t>` | GPU 内存大小（原子类型支持多线程） |
| `fUseAllocator` | `UseAllocator` | 是否使用资源分配器 |
| `fTaskTargetCount` | `int` | 作为渲染任务目标的次数 |

### 嵌套类型

#### UniqueID
```cpp
class UniqueID {
    uint32_t fID;
    // 支持 wrapped、deferred、lazy-callback 三种来源
};
```

#### ResolveFlags（枚举）
- `kNone`: 无需 resolve
- `kMSAA`: MSAA resolve
- `kMipMaps`: 重新生成 mipmap

#### LazyInstantiationKeyMode（枚举）
- `kUnsynced`: proxy 和 surface 的 key 不同步
- `kSynced`: proxy 的 key 会同步到 surface

#### LazySurfaceDesc（结构体）
描述延迟实例化时的期望属性（尺寸、格式、sample count 等）。

#### LazyCallbackResult（结构体）
延迟回调的返回值，包含创建的 surface、key 模式和是否释放回调。

## 公共 API 函数

### 查询方法

```cpp
bool isLazy() const  // 是否是延迟实例化
bool isFullyLazy() const  // 是否尺寸未知（宽高 < 0）
SkISize dimensions() const  // 获取尺寸
SkISize backingStoreDimensions() const  // 获取实际后备存储尺寸
bool isFunctionallyExact() const  // 检查是否功能上精确匹配
const GrBackendFormat& backendFormat() const  // 获取后端格式
UniqueID uniqueID() const  // 获取唯一 ID
UniqueID underlyingUniqueID() const  // 获取底层资源的 ID
```

### 状态检查

```cpp
bool isInstantiated() const  // 是否已实例化
bool canSkipResourceAllocator() const  // 是否可跳过资源分配器
skgpu::Budgeted isBudgeted() const  // 是否计入预算
bool readOnly() const  // 是否只读
bool framebufferOnly() const  // 是否仅用于 framebuffer
bool requiresManualMSAAResolve() const  // 是否需要手动 MSAA resolve
size_t gpuMemorySize() const  // GPU 内存占用
```

### 实例化相关

```cpp
virtual bool instantiate(GrResourceProvider*) = 0  // 纯虚函数，实例化 proxy
void deinstantiate()  // 解除实例化
void isUsedAsTaskTarget()  // 标记为任务目标
int getTaskTargetCount() const  // 获取任务目标计数
```

### 资源访问

```cpp
GrSurface* peekSurface() const  // 查看实例化的 surface（可能为 null）
GrTexture* peekTexture() const  // 查看纹理（如果是）
GrRenderTarget* peekRenderTarget() const  // 查看渲染目标（如果是）
```

### 类型转换

```cpp
virtual GrTextureProxy* asTextureProxy()  // 转换为纹理 proxy
virtual GrRenderTargetProxy* asRenderTargetProxy()  // 转换为渲染目标 proxy
virtual const skgpu::UniqueKey& getUniqueKey() const  // 获取唯一键（基类返回无效键）
```

### 静态工具方法

```cpp
static sk_sp<GrSurfaceProxy> Copy(GrRecordingContext*, sk_sp<GrSurfaceProxy> src,
                                   GrSurfaceOrigin, skgpu::Mipmapped, SkIRect srcRect,
                                   SkBackingFit, skgpu::Budgeted, std::string_view label,
                                   RectsMustMatch, sk_sp<GrRenderTask>* outTask)
```

创建 surface 副本的静态方法，支持完整或部分复制。

## 内部实现细节

### 三种构造模式

#### Deferred（延迟）
```cpp
GrSurfaceProxy(const GrBackendFormat&, SkISize, SkBackingFit, skgpu::Budgeted, ...)
```
- 尺寸和格式已知，但资源未创建
- 分配新的 uniqueID

#### Lazy（回调）
```cpp
GrSurfaceProxy(LazyInstantiateCallback&&, const GrBackendFormat&, SkISize, ...)
```
- 通过回调函数延迟创建
- 支持 fully lazy（尺寸未知）和 partially lazy
- 分配新的 uniqueID

#### Wrapped（包装）
```cpp
GrSurfaceProxy(sk_sp<GrSurface>, SkBackingFit, UseAllocator)
```
- 包装已存在的 surface
- 使用 surface 的 uniqueID
- 立即处于已实例化状态

### 实例化流程

`instantiateImpl()` 方法的核心逻辑：
1. 检查是否已实例化，如果是则直接返回
2. 调用 `createSurfaceImpl()` 创建 surface
   - kApprox fit: 调用 `createApproxTexture()`
   - kExact fit: 调用 `createTexture()`
3. 如果有 unique key，分配给创建的 surface
4. 调用 `assign()` 关联 surface 和 proxy

### Lazy 实例化流程

由 `GrSurfaceProxyPriv::doLazyInstantiation()` 实现：
1. 如果有 unique key，先尝试从缓存中查找
2. 如果没找到，调用 `fLazyInstantiateCallback`
3. 对于 fully lazy proxy，从创建的 surface 获取尺寸
4. 处理 key 同步（根据 `LazyInstantiationKeyMode`）
5. 如果回调指定 `fReleaseCallback = true`，释放回调函数

### Copy 实现

`Copy()` 静态方法的实现策略：
1. **优先尝试 SurfaceContext copy**: 使用 `dstContext->copy()` 进行高效拷贝
2. **备选方案 blit**: 对于纹理，使用 `SurfaceFillContext::blitTexture()`
3. **确保格式一致**: 使用 `makeTexture2D()` 确保目标格式正确
4. **矩形处理**: 支持部分区域复制和完整复制

### 内存大小计算

`gpuMemorySize()` 使用延迟计算和缓存：
```cpp
if (kInvalidGpuMemorySize == fGpuMemorySize) {
    fGpuMemorySize = this->onUninstantiatedGpuMemorySize();
}
return fGpuMemorySize;
```
- 使用原子变量支持多线程访问
- 只计算一次，结果缓存
- 子类实现 `onUninstantiatedGpuMemorySize()` 提供具体计算

### Scratch Key 计算

`computeScratchKey()` 综合考虑多个因素：
- Backend format
- 尺寸（使用 backing store 尺寸）
- 是否可渲染
- Sample count
- Mipmap 状态
- Protected 内存标志

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrSurface` | 实际的 GPU surface 资源 |
| `GrResourceProvider` | 创建 GPU 资源 |
| `GrBackendFormat` | 描述后端格式 |
| `GrCaps` | 查询 GPU 能力 |
| `SurfaceContext` | 用于 Copy 操作 |
| `GrRenderTask` | 记录渲染操作 |
| `skgpu::UniqueKey` | 唯一键管理 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrSurfaceProxyView` | 视图包装 |
| `GrTextureProxy` | 纹理代理子类 |
| `GrRenderTargetProxy` | 渲染目标代理子类 |
| `GrResourceAllocator` | 资源分配调度 |
| `GrOpsTask` | 渲染任务 |
| `GrRenderTask` | 各类渲染任务 |

## 设计模式与设计决策

### Proxy 模式

**为什么使用 Proxy**:
1. **延迟实例化**: 推迟资源创建到真正需要时
2. **资源共享**: 多个 proxy 可能共享同一个实例
3. **内存优化**: 资源分配器可以全局优化内存使用
4. **线程安全**: 命令记录和执行可以分离

### 三态设计

Proxy 有三种状态：
- **Deferred**: 知道规格但未创建
- **Lazy**: 通过回调创建（可能尺寸未知）
- **Wrapped**: 已存在的资源

这种设计涵盖了所有资源来源场景。

### Unique Key vs Scratch Key

- **Unique Key**: 标识特定内容的资源（如特定图像的纹理）
- **Scratch Key**: 标识可复用的资源（基于格式和尺寸）

两级 key 系统支持精确缓存和近似复用。

### 抽象基类设计

`GrSurfaceProxy` 是抽象基类：
- `instantiate()` 是纯虚函数
- `asTextureProxy()` / `asRenderTargetProxy()` 返回 nullptr
- 子类提供具体实现

这种设计支持多态和类型安全的转换。

### Budgeted 设计为 mutable

```cpp
mutable skgpu::Budgeted fBudgeted;
```
允许运行时改变预算状态（用于 SkSurface/SkImage 的预算切换）。

### 原子内存大小

```cpp
mutable std::atomic<size_t> fGpuMemorySize;
```
使用原子变量支持多线程访问，避免加锁开销。

## 性能考量

### 延迟实例化优势

1. **减少内存峰值**: 资源只在需要时创建
2. **优化分配顺序**: 资源分配器可以全局优化
3. **避免不必要创建**: 如果渲染被跳过，资源不会创建
4. **支持资源复用**: Scratch key 机制允许复用现有资源

### kApprox vs kExact

- **kApprox**: 允许使用稍大的资源（提高复用率）
- **kExact**: 精确尺寸（用于必须精确匹配的场景）

大多数场景使用 kApprox 以提高内存利用率。

### Fully Lazy Proxy

对于尺寸在创建时未知的场景（如 readPixels 目标）：
- 使用负尺寸标记
- 在实例化时确定尺寸
- 减少预估和浪费

### Resource Allocator 集成

`canSkipResourceAllocator()` 优化：
- Wrapped 且不可复用的资源跳过分配器
- `fUseAllocator = kNo` 的资源（如 atlas）跳过
- 减少分配器的工作量

### Copy 操作优化

两级策略：
1. **高效路径**: 使用 GPU copy 命令
2. **备选路径**: 使用 blit（适用于纹理）

避免了 CPU 往返。

### 引用计数优化

使用 `SkNVRefCnt`（非虚拟引用计数）：
- 避免虚函数调用开销
- 更小的对象大小
- 更好的缓存局部性

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrTextureProxy.h` | 派生类 | 纹理代理 |
| `src/gpu/ganesh/GrRenderTargetProxy.h` | 派生类 | 渲染目标代理 |
| `src/gpu/ganesh/GrSurface.h` | 被代理类 | 实际 GPU surface |
| `src/gpu/ganesh/GrResourceProvider.h` | 创建者 | 资源创建 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 调度器 | 资源分配调度 |
| `src/gpu/ganesh/GrSurfaceProxyView.h` | 使用者 | 视图包装 |
| `src/gpu/ganesh/GrSurfaceProxyPriv.h` | 友元类 | 私有 API 访问 |
| `src/gpu/ganesh/SurfaceContext.h` | 使用者 | Surface 操作上下文 |
| `src/gpu/ganesh/GrRenderTask.h` | 使用者 | 渲染任务 |
| `include/gpu/ganesh/GrBackendSurface.h` | 依赖 | 后端 surface 描述 |
