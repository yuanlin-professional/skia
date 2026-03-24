# GrResourceProvider

> 源文件
> - src/gpu/ganesh/GrResourceProvider.h
> - src/gpu/ganesh/GrResourceProvider.cpp

## 概述

`GrResourceProvider` 是 Skia Ganesh GPU 后端的资源工厂和提供者,负责创建、查找和管理各种 GPU 资源,包括纹理、缓冲区、附件、信号量等。它是 `GrResourceCache` 的高级封装,提供了类型安全的资源创建接口,支持 scratch 资源复用、静态资源缓存、后端资源包装等功能。该类是 Skia GPU 资源管理架构中连接上层绘制逻辑和底层 GPU 接口的关键桥梁。

## 架构位置

在 Skia GPU 架构中的位置:

```
GrDirectContext
    ├── GrResourceProvider (资源工厂)
    │   ├── 创建和查找资源
    │   ├── GrResourceCache (资源缓存)
    │   └── GrGpu (底层 GPU 接口)
    ├── GrDrawingManager (使用资源)
    └── GrResourceAllocator (资源分配策略)
```

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `GrResourceProvider` | 无 | 资源提供者主类 |
| `GrResourceProviderPriv` | 无 | 提供内部访问的特权接口 |

### 关键成员变量

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fCache` | `GrResourceCache*` | 资源缓存 |
| `fGpu` | `GrGpu*` | GPU 接口 |
| `fCaps` | `sk_sp<const GrCaps>` | GPU 能力对象 |
| `fNonAAQuadIndexBuffer` | `sk_sp<const GrGpuBuffer>` | 非抗锯齿四边形索引缓冲 |
| `fAAQuadIndexBuffer` | `sk_sp<const GrGpuBuffer>` | 抗锯齿四边形索引缓冲 |

### 类型定义

```cpp
enum class ZeroInit : bool { kNo = false, kYes = true };
using InitializeBufferFn = void(*)(skgpu::VertexWriter, size_t bufferSize);
```

## 公共 API 函数

### 纹理创建

```cpp
// 创建近似大小的纹理
sk_sp<GrTexture> createApproxTexture(
    SkISize dimensions,
    const GrBackendFormat& format,
    GrTextureType textureType,
    skgpu::Renderable renderable,
    int renderTargetSampleCnt,
    skgpu::Protected isProtected,
    std::string_view label);

// 创建精确大小的纹理(无数据)
sk_sp<GrTexture> createTexture(
    SkISize dimensions,
    const GrBackendFormat& format,
    GrTextureType textureType,
    skgpu::Renderable renderable,
    int renderTargetSampleCnt,
    skgpu::Mipmapped mipmapped,
    skgpu::Budgeted budgeted,
    skgpu::Protected isProtected,
    std::string_view label);

// 创建纹理并初始化数据
sk_sp<GrTexture> createTexture(
    SkISize dimensions,
    const GrBackendFormat& format,
    GrTextureType textureType,
    GrColorType colorType,
    skgpu::Renderable renderable,
    int renderTargetSampleCnt,
    skgpu::Budgeted budgeted,
    skgpu::Mipmapped mipmapped,
    skgpu::Protected isProtected,
    const GrMipLevel texels[],
    std::string_view label);

// 创建压缩纹理
sk_sp<GrTexture> createCompressedTexture(
    SkISize dimensions,
    const GrBackendFormat& format,
    skgpu::Budgeted budgeted,
    skgpu::Mipmapped mipmapped,
    skgpu::Protected isProtected,
    SkData* data,
    std::string_view label);
```

### Scratch 纹理查找

```cpp
sk_sp<GrTexture> findAndRefScratchTexture(
    const skgpu::ScratchKey& scratchKey,
    std::string_view label);

sk_sp<GrTexture> findAndRefScratchTexture(
    SkISize dimensions,
    const GrBackendFormat& format,
    GrTextureType textureType,
    skgpu::Renderable renderable,
    int renderTargetSampleCnt,
    skgpu::Mipmapped mipmapped,
    skgpu::Protected isProtected,
    std::string_view label);
```

### 后端资源包装

```cpp
// 包装后端纹理
sk_sp<GrTexture> wrapBackendTexture(
    const GrBackendTexture& tex,
    GrWrapOwnership ownership,
    GrWrapCacheable cacheable,
    GrIOType ioType);

// 包装压缩后端纹理
sk_sp<GrTexture> wrapCompressedBackendTexture(
    const GrBackendTexture& tex,
    GrWrapOwnership ownership,
    GrWrapCacheable cacheable);

// 包装可渲染的后端纹理
sk_sp<GrTexture> wrapRenderableBackendTexture(
    const GrBackendTexture& tex,
    int sampleCnt,
    GrWrapOwnership ownership,
    GrWrapCacheable cacheable);

// 包装后端渲染目标
sk_sp<GrRenderTarget> wrapBackendRenderTarget(
    const GrBackendRenderTarget& backendRT);

// 包装 Vulkan Secondary Command Buffer
sk_sp<GrRenderTarget> wrapVulkanSecondaryCBAsRenderTarget(
    const SkImageInfo& imageInfo,
    const GrVkDrawableInfo& vkInfo);
```

### 缓冲区管理

```cpp
// 创建通用缓冲区
sk_sp<GrGpuBuffer> createBuffer(
    size_t size,
    GrGpuBufferType type,
    GrAccessPattern pattern,
    ZeroInit zeroInit);

// 创建带初始数据的缓冲区
sk_sp<GrGpuBuffer> createBuffer(
    const void* data,
    size_t size,
    GrGpuBufferType type,
    GrAccessPattern pattern);

// 查找或创建静态缓冲区
sk_sp<const GrGpuBuffer> findOrMakeStaticBuffer(
    GrGpuBufferType intendedType,
    size_t size,
    const void* staticData,
    const skgpu::UniqueKey& key);

sk_sp<const GrGpuBuffer> findOrMakeStaticBuffer(
    GrGpuBufferType intendedType,
    size_t size,
    const skgpu::UniqueKey& uniqueKey,
    InitializeBufferFn initializeBufferFn);

// 查找或创建模式化索引缓冲区
sk_sp<const GrGpuBuffer> findOrCreatePatternedIndexBuffer(
    const uint16_t* pattern,
    int patternSize,
    int reps,
    int vertCount,
    const skgpu::UniqueKey& key);
```

### 预定义缓冲区

```cpp
// 非抗锯齿四边形索引缓冲区
sk_sp<const GrGpuBuffer> refNonAAQuadIndexBuffer();
static int MaxNumNonAAQuads();
static int NumVertsPerNonAAQuad();
static int NumIndicesPerNonAAQuad();

// 抗锯齿四边形索引缓冲区
sk_sp<const GrGpuBuffer> refAAQuadIndexBuffer();
static int MaxNumAAQuads();
static int NumVertsPerAAQuad();
static int NumIndicesPerAAQuad();
```

### 附件管理

```cpp
// 附加模板附件
bool attachStencilAttachment(GrRenderTarget* rt, bool useMSAASurface);

// 创建 MSAA 附件
sk_sp<GrAttachment> makeMSAAAttachment(
    SkISize dimensions,
    const GrBackendFormat& format,
    int sampleCnt,
    skgpu::Protected isProtected,
    GrMemoryless isMemoryless);

// 获取可丢弃的 MSAA 附件
sk_sp<GrAttachment> getDiscardableMSAAAttachment(
    SkISize dimensions,
    const GrBackendFormat& format,
    int sampleCnt,
    skgpu::Protected isProtected,
    GrMemoryless memoryless);
```

### 资源键管理

```cpp
// 通过 unique key 查找资源
template <typename T = GrGpuResource>
sk_sp<T> findByUniqueKey(const skgpu::UniqueKey& key);

// 为资源分配 unique key
void assignUniqueKeyToResource(const skgpu::UniqueKey& key,
                               GrGpuResource* resource);
```

### 信号量

```cpp
std::unique_ptr<GrSemaphore> makeSemaphore(bool isOwned = true);
std::unique_ptr<GrSemaphore> wrapBackendSemaphore(
    const GrBackendSemaphore& semaphore,
    GrSemaphoreWrapType wrapType,
    GrWrapOwnership ownership = kBorrow_GrWrapOwnership);
```

### 状态查询

```cpp
uint32_t contextUniqueID() const;
const GrCaps* caps() const;
bool overBudget() const;
void abandon();  // 放弃所有资源
```

## 内部实现细节

### 纹理创建策略

**Exact vs Approx**:
- Exact: 精确匹配大小,用于重要内容
- Approx: 允许稍大的尺寸,提高复用率

**创建流程**:
1. 尝试从 scratch cache 查找
2. 如果找到且无数据,直接返回
3. 如果需要上传数据,调用 `writePixels`
4. 否则调用 GPU 创建新纹理

### Scratch 资源查找

```cpp
sk_sp<GrTexture> getExactScratch(...)
```

查找流程:
1. 调用 `findAndRefScratchTexture`
2. 如果找到且预算不匹配,调整预算标志
3. 返回纹理或 nullptr

**复用条件**:
- GPU 支持 scratch 纹理复用或是渲染目标
- Scratch key 匹配
- 尺寸、格式、采样数等参数匹配

### 数据准备与转换

```cpp
GrColorType prepareLevels(
    const GrBackendFormat& format,
    GrColorType colorType,
    SkISize baseSize,
    const GrMipLevel texels[],
    int mipLevelCount,
    TempLevels* tempLevels,
    TempLevelDatas* tempLevelDatas) const
```

功能:
- 检查颜色类型是否支持
- 处理行字节对齐
- 必要时进行颜色格式转换
- 为每个 mip level 准备临时缓冲区

### 动态缓冲区分箱策略

```cpp
sk_sp<GrGpuBuffer> createBuffer(..., kDynamic_GrAccessPattern)
```

优化策略:
1. 对请求大小向上取整到特定档位
2. 使用 2 的幂次 + 中点的分箱策略
3. 根据 scratch key 查找已有缓冲区
4. 提高缓冲区复用率

分箱算法:
```cpp
size_t ceilPow2 = SkNextSizePow2(allocSize);
size_t floorPow2 = ceilPow2 >> 1;
size_t mid = floorPow2 + (floorPow2 >> 1);
allocSize = (allocSize <= mid) ? mid : ceilPow2;
```

示例:
- 请求 5KB → 分配 6KB (4KB + 2KB)
- 请求 8KB → 分配 8KB
- 请求 10KB → 分配 12KB (8KB + 4KB)

### 预定义索引缓冲区

**非抗锯齿四边形**:
```cpp
static const uint16_t kNonAAQuadIndexPattern[] = {
    0, 1, 2, 2, 1, 3
};
```
- 每个四边形 4 个顶点,6 个索引
- 最多支持 4096 个四边形
- 模式化生成,避免手动创建

**抗锯齿四边形**:
```cpp
static const uint16_t kAAQuadIndexPattern[] = {
    0, 1, 2, 1, 3, 2,
    0, 4, 1, 4, 5, 1,
    0, 6, 4, 0, 2, 6,
    2, 3, 6, 3, 7, 6,
    1, 5, 3, 3, 5, 7,
};
```
- 每个四边形 8 个顶点,30 个索引
- 外围 4 个顶点 + 内部 4 个顶点
- 支持边缘抗锯齿

### 模板附件管理

```cpp
bool attachStencilAttachment(GrRenderTarget* rt, bool useMSAASurface)
```

流程:
1. 检查是否已有模板附件
2. 计算需要的采样数(考虑 DMSAA)
3. 生成 unique key 查找共享附件
4. 如果不存在,创建新的模板附件
5. 附加到渲染目标

**共享策略**:
- 相同尺寸、格式、采样数的模板可以共享
- 使用 unique key 实现共享

### MSAA 附件管理

**可丢弃 MSAA 附件** (`getDiscardableMSAAAttachment`):
- 用于临时 MSAA 渲染
- 可以在多个绘制间共享
- 内容不保证保留

**独占 MSAA 附件** (`makeMSAAAttachment`):
- 为特定用途创建
- 不在缓存中查找
- 优先从 scratch cache 获取

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrResourceCache` | 资源查找和缓存管理 |
| `GrGpu` | 底层 GPU 资源创建 |
| `GrCaps` | GPU 能力查询 |
| `GrTexture/GrRenderTarget/GrAttachment` | 具体资源类型 |
| `GrDataUtils` | 数据格式转换 |
| `SkMipmap` | Mipmap 计算 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrResourceAllocator` | 创建和查找 scratch 纹理 |
| `GrSurfaceProxy` | 通过 proxy 请求创建资源 |
| `GrDrawingManager` | 请求各种 GPU 资源 |
| `GrOpsTask` | 获取缓冲区和纹理 |

## 设计模式与设计决策

### 设计模式

1. **工厂模式**:
   - 提供多种 `create*` 方法
   - 封装复杂的创建逻辑

2. **享元模式**:
   - Scratch 资源复用
   - 共享模板附件和 MSAA 附件

3. **外观模式**:
   - 简化 GrGpu 和 GrResourceCache 的使用
   - 提供高级接口

4. **模板方法模式**:
   - `createTexture` 的多个重载版本
   - 共享核心逻辑,变化细节

### 关键设计决策

**为何分离 Provider 和 Cache**:
- Provider: 面向创建和逻辑
- Cache: 面向存储和策略
- 职责分离,便于维护

**为何支持多种纹理创建方式**:
- Exact vs Approx: 平衡精度和效率
- With/Without data: 优化上传流程
- Scratch vs Unique: 不同的复用策略

**为何预创建四边形索引缓冲区**:
- 四边形是最常用的图元
- 预创建避免重复工作
- 模式化生成保证一致性

**为何使用 unique key 共享附件**:
- 减少内存占用
- 提高资源利用率
- 相同配置的附件可以安全共享

**为何区分可丢弃和独占 MSAA**:
- 可丢弃:优化常见临时渲染场景
- 独占:保证特殊场景的正确性

## 性能考量

### Scratch 缓冲区分箱

**优点**:
- 提高缓冲区复用率
- 减少创建和销毁开销
- 减少内存碎片

**权衡**:
- 可能分配略大于需求的内存
- 分箱策略在大小和复用率间取得平衡

### 数据转换优化

```cpp
if (origColorType == allowedColorType && (actualRB == minRB || rowBytesSupport)) {
    // 快速路径:直接使用原始数据
    outLevel->fRowBytes = actualRB;
    outLevel->fPixels = inLevel.fPixels;
    return true;
}
```

- 尽量避免不必要的数据复制
- 只在必要时进行格式转换

### 批量操作

**模式化索引缓冲区**:
- 一次性生成大量索引
- 避免逐个创建四边形

**共享资源**:
- 模板附件共享减少内存
- MSAA 附件共享减少创建开销

### 延迟创建

**四边形索引缓冲区**:
```cpp
sk_sp<const GrGpuBuffer> refNonAAQuadIndexBuffer() {
    if (!fNonAAQuadIndexBuffer) {
        fNonAAQuadIndexBuffer = this->createNonAAQuadIndexBuffer();
    }
    return fNonAAQuadIndexBuffer;
}
```

- 按需创建,避免不必要的初始化
- 缓存实例,后续快速返回

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrResourceCache.h` | 依赖 | 资源缓存 |
| `src/gpu/ganesh/GrGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/GrTexture.h` | 创建 | 纹理类型 |
| `src/gpu/ganesh/GrRenderTarget.h` | 创建 | 渲染目标 |
| `src/gpu/ganesh/GrAttachment.h` | 创建 | 附件类型 |
| `src/gpu/ganesh/GrGpuBuffer.h` | 创建 | 缓冲区类型 |
| `src/gpu/ganesh/GrResourceProviderPriv.h` | 配套 | 特权访问接口 |
| `src/gpu/ganesh/GrResourceAllocator.h` | 使用者 | 资源分配器 |
| `src/gpu/ganesh/GrSurfaceProxy.h` | 使用者 | Surface 代理 |
