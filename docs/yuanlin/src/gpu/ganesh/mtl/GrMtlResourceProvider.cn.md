# GrMtlResourceProvider

> 源文件
> - `src/gpu/ganesh/mtl/GrMtlResourceProvider.h`
> - `src/gpu/ganesh/mtl/GrMtlResourceProvider.mm`

## 概述

`GrMtlResourceProvider` 是 Ganesh 图形后端中 Metal 实现的资源提供者类,负责管理和缓存各种 Metal 渲染资源。该类作为资源工厂和缓存管理器,提供管道状态(Pipeline State)、深度模板状态(Depth Stencil State)、采样器(Sampler)以及 MSAA 加载管道等资源的查找、创建和复用功能。通过资源缓存机制,避免重复创建相同的渲染状态对象,显著提升渲染性能。

## 架构位置

`GrMtlResourceProvider` 位于 Skia 图形库的 GPU 后端层次结构中:

```
Skia 图形库
└── GPU 后端 (src/gpu)
    └── Ganesh 渲染引擎 (ganesh)
        └── Metal 后端实现 (mtl)
            ├── GrMtlGpu (Metal GPU 接口)
            ├── GrMtlResourceProvider (资源提供者) ← 当前类
            ├── GrMtlPipelineState (管道状态)
            ├── GrMtlDepthStencil (深度模板状态)
            └── GrMtlSampler (采样器)
```

作为资源管理中心,该类与 `GrMtlGpu` 紧密协作,为渲染操作提供各种 Metal 状态对象。

## 主要类与结构体

### GrMtlResourceProvider 类

主资源提供者类,负责管理所有 Metal 渲染资源。

**继承关系:**
- 无继承关系,独立的资源管理类

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrMtlGpu*` | 指向 Metal GPU 对象的指针 |
| `fPipelineStateCache` | `std::unique_ptr<PipelineStateCache>` | 管道状态缓存 |
| `fSamplers` | `SkTDynamicHash<GrMtlSampler, Key>` | 采样器哈希表 |
| `fDepthStencilStates` | `SkTDynamicHash<GrMtlDepthStencil, Key>` | 深度模板状态哈希表 |
| `fMSAALoadLibrary` | `id<MTLLibrary>` | MSAA 加载着色器库 |
| `fMSAALoadPipelines` | `TArray<MSAALoadPipelineEntry>` | MSAA 加载管道数组 |

### PipelineStateCache 内部类

管道状态缓存类,继承自 `GrThreadSafePipelineBuilder`。

**继承关系:**
- 继承: `GrThreadSafePipelineBuilder`

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fMap` | `SkLRUCache<GrProgramDesc, Entry*, DescHash>` | LRU 缓存映射 |
| `fGpu` | `GrMtlGpu*` | GPU 对象指针 |

### Entry 结构体

缓存条目结构,存储管道状态或预编译库。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPipelineState` | `std::unique_ptr<GrMtlPipelineState>` | 管道状态对象 |
| `fPrecompiledLibraries` | `GrMtlPrecompiledLibraries` | 预编译着色器库 |

### MSAALoadPipelineEntry 结构体

MSAA 加载管道条目。

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPipeline` | `sk_sp<const GrMtlRenderPipeline>` | 渲染管道智能指针 |
| `fColorFormat` | `MTLPixelFormat` | 颜色格式 |
| `fSampleCount` | `int` | 采样数量 |
| `fStencilFormat` | `MTLPixelFormat` | 模板格式 |

## 公共 API 函数

### 构造与销毁

```cpp
GrMtlResourceProvider(GrMtlGpu* gpu)
```
构造函数,初始化资源提供者并创建管道状态缓存。

```cpp
void destroyResources()
```
销毁所有缓存的资源,在释放 Metal 设备前调用。

### 管道状态管理

```cpp
GrMtlPipelineState* findOrCreateCompatiblePipelineState(
    const GrProgramDesc& programDesc,
    const GrProgramInfo& programInfo,
    Stats::ProgramCacheResult* stat = nullptr)
```
查找或创建兼容的管道状态。如果缓存中存在则返回,否则创建新的管道状态。

```cpp
bool precompileShader(const SkData& key, const SkData& data)
```
预编译着色器,用于延迟显示列表(DDL)优化场景。

### 状态对象管理

```cpp
GrMtlDepthStencil* findOrCreateCompatibleDepthStencilState(
    const GrStencilSettings& stencil,
    GrSurfaceOrigin origin)
```
查找或创建兼容的深度模板状态对象。

```cpp
GrMtlSampler* findOrCreateCompatibleSampler(GrSamplerState params)
```
查找或创建兼容的采样器对象。

### MSAA 支持

```cpp
const GrMtlRenderPipeline* findOrCreateMSAALoadPipeline(
    MTLPixelFormat colorFormat,
    int sampleCount,
    MTLPixelFormat stencilFormat)
```
查找或创建 MSAA 加载管道,用于从 resolve 纹理加载 MSAA 数据。

## 内部实现细节

### 管道状态缓存机制

`PipelineStateCache` 使用 LRU (Least Recently Used) 缓存策略管理管道状态:

1. **缓存查找**: 使用程序描述符 (`GrProgramDesc`) 作为键,通过哈希查找
2. **三种缓存结果**:
   - `kHit`: 完整管道状态存在于缓存中
   - `kPartial`: 预编译着色器存在,需要创建管道状态
   - `kMiss`: 缓存未命中,需要完整编译
3. **统计追踪**: 跟踪编译成功、失败、部分编译等统计信息

### MSAA 加载着色器

当需要 MSAA 加载功能时,动态生成 Metal 着色器代码:

```metal
vertex VertexOutput vertexMain(...)
fragment float4 fragmentMain(...)
```

着色器实现从 resolve 纹理读取并写入 MSAA 目标,支持颜色和模板附件。

### 资源哈希策略

- **深度模板状态**: 使用 `GrMtlDepthStencil::Key` 生成唯一键
- **采样器**: 使用 `GrMtlSampler::GenerateKey()` 基于采样参数生成键
- **管道状态**: 使用 `SkChecksum::Hash32()` 对程序描述符进行哈希

### 预编译支持

支持着色器预编译以优化启动性能:

1. 通过 `precompileShader()` 接收序列化的着色器数据
2. 创建 Metal 着色器库但不创建完整管道
3. 首次使用时,利用预编译库快速创建管道状态

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrMtlGpu` | Metal GPU 接口,提供设备访问 |
| `GrMtlPipelineStateBuilder` | 构建管道状态对象 |
| `GrMtlPipelineState` | 管道状态表示 |
| `GrMtlDepthStencil` | 深度模板状态对象 |
| `GrMtlSampler` | 采样器对象 |
| `GrMtlPipeline` | 渲染管道包装 |
| `GrProgramDesc` | 程序描述符 |
| `GrProgramInfo` | 程序信息 |
| `SkLRUCache` | LRU 缓存实现 |
| `SkTDynamicHash` | 动态哈希表 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `GrMtlGpu` | 通过资源提供者获取渲染状态 |
| `GrMtlOpsRenderPass` | 使用管道状态和采样器 |
| `GrMtlCommandBuffer` | 获取 MSAA 加载管道 |

## 设计模式与设计决策

### 1. 工厂模式 (Factory Pattern)

所有资源创建都通过 `findOrCreate*` 方法,封装复杂的创建逻辑,提供统一接口。

### 2. 缓存代理模式 (Cache Proxy Pattern)

资源提供者作为缓存代理,在返回资源前检查缓存,避免重复创建。

### 3. 懒加载 (Lazy Initialization)

MSAA 加载着色器库仅在首次需要时创建:

```cpp
if (!fMSAALoadLibrary) {
    // 编译着色器代码
    fMSAALoadLibrary = GrCompileMtlShaderLibrary(...);
}
```

### 4. LRU 缓存策略

管道状态缓存使用 LRU 策略,自动淘汰最少使用的条目,控制内存占用。

### 5. 两阶段编译

支持预编译和完整编译两阶段:
- **阶段一**: 预编译着色器到 Metal 库
- **阶段二**: 使用预编译库创建完整管道

这种设计支持 DDL (Deferred Display List) 优化场景。

### 6. 资源生命周期管理

使用智能指针 (`std::unique_ptr`, `sk_sp`) 管理资源生命周期,确保资源正确释放。

## 性能考量

### 1. 缓存命中率优化

通过精确的哈希键设计和 LRU 策略,最大化缓存命中率,减少昂贵的管道创建开销。

### 2. 动态哈希表

使用 `SkTDynamicHash` 提供 O(1) 查找性能,适合高频查询的采样器和深度模板状态。

### 3. 预编译支持

支持着色器预编译显著减少首次渲染延迟,特别适用于复杂场景启动。

### 4. MSAA 着色器复用

MSAA 加载管道按格式和采样数缓存,避免重复编译相同配置的着色器。

### 5. 内存管理

- LRU 缓存自动限制缓存大小(通过 `fRuntimeProgramCacheSize` 配置)
- `destroyResources()` 提供显式资源清理,避免设备释放后的悬挂引用

### 6. 统计追踪

编译统计信息用于性能分析和调试:
- 编译成功/失败次数
- 缓存命中类型分布
- 内联编译失败计数

### 7. 线程安全

`PipelineStateCache` 继承自 `GrThreadSafePipelineBuilder`,支持多线程场景下的管道编译。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` | 拥有关系 | GPU 对象拥有资源提供者 |
| `src/gpu/ganesh/mtl/GrMtlPipelineState.h/mm` | 创建关系 | 创建管道状态对象 |
| `src/gpu/ganesh/mtl/GrMtlPipelineStateBuilder.h/mm` | 使用关系 | 通过构建器创建管道 |
| `src/gpu/ganesh/mtl/GrMtlDepthStencil.h/mm` | 缓存关系 | 缓存深度模板状态 |
| `src/gpu/ganesh/mtl/GrMtlSampler.h/mm` | 缓存关系 | 缓存采样器对象 |
| `src/gpu/ganesh/mtl/GrMtlPipeline.h` | 缓存关系 | 缓存渲染管道 |
| `src/gpu/ganesh/mtl/GrMtlUtil.h/mm` | 使用关系 | 使用工具函数编译着色器 |
| `src/gpu/ganesh/GrProgramDesc.h` | 使用关系 | 程序描述符作为缓存键 |
| `src/gpu/ganesh/GrThreadSafePipelineBuilder.h` | 继承关系 | 缓存类继承基类 |
| `src/core/SkLRUCache.h` | 使用关系 | LRU 缓存容器 |
| `src/core/SkTDynamicHash.h` | 使用关系 | 动态哈希表容器 |
