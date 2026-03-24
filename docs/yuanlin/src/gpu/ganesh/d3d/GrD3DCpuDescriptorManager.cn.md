# GrD3DCpuDescriptorManager

> 源文件
> - src/gpu/ganesh/d3d/GrD3DCpuDescriptorManager.h
> - src/gpu/ganesh/d3d/GrD3DCpuDescriptorManager.cpp

## 概述

`GrD3DCpuDescriptorManager` 是 Skia 图形库中 Ganesh D3D 后端的 CPU 可见描述符管理器,负责管理非着色器可见的描述符堆,包括渲染目标视图(RTV)、深度模板视图(DSV)、着色器资源视图(SRV)、常量缓冲视图(CBV)、无序访问视图(UAV)和采样器(Sampler)。与 `GrD3DDescriptorTableManager` 管理 GPU 可见堆不同,该类管理的描述符主要用于命令列表的资源绑定和视图创建。

该类通过位集(SkBitSet)实现描述符的精确分配和回收,避免浪费。每种描述符类型维护独立的堆池(`HeapPool`),堆池按需创建新堆并动态扩展容量。通过封装 D3D12 视图创建 API,该类为上层提供了类型安全的描述符分配接口,简化了资源视图的管理。

## 架构位置

`GrD3DCpuDescriptorManager` 在 D3D12 资源管理层次结构中的位置:

```
Skia
└── src/gpu/ganesh/d3d
    ├── GrD3DGpu (D3D GPU 主类)
    │   └── GrD3DResourceProvider (资源提供者)
    │       ├── GrD3DCpuDescriptorManager (CPU 描述符管理) ← 核心类
    │       │   ├── HeapPool (RTV/DSV/SRV/Sampler 池)
    │       │   │   └── Heap (单个堆,使用位集分配)
    │       │   │       └── GrD3DDescriptorHeap (底层堆封装)
    │       │   └── SkBitSet (空闲块追踪)
    │       └── GrD3DDescriptorTableManager (GPU 描述符表管理)
    └── GrD3DTexture/GrD3DRenderTarget (使用视图)
```

该类专注于 CPU 端的视图创建和管理,与 GPU 可见的描述符表形成互补。

## 主要类与结构体

### GrD3DCpuDescriptorManager

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fRTVDescriptorPool` | `HeapPool` | 渲染目标视图池 |
| `fDSVDescriptorPool` | `HeapPool` | 深度模板视图池 |
| `fShaderViewDescriptorPool` | `HeapPool` | 着色器视图池(CBV/SRV/UAV) |
| `fSamplerDescriptorPool` | `HeapPool` | 采样器池 |

**职责**: 顶层管理器,协调四种类型的描述符堆池。

### GrD3DCpuDescriptorManager::Heap

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fHeap` | `std::unique_ptr<GrD3DDescriptorHeap>` | 底层描述符堆对象 |
| `fFreeBlocks` | `SkBitSet` | 空闲块位集,标记哪些描述符可用 |
| `fFreeCount` | `unsigned int` | 空闲描述符数量,快速检查是否可分配 |

**职责**: 封装单个描述符堆,使用位集实现精确的空闲块追踪和分配。

### GrD3DCpuDescriptorManager::HeapPool

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDescriptorHeaps` | `std::vector<std::unique_ptr<Heap>>` | 堆列表 |
| `fMaxAvailableDescriptors` | `int` | 下次创建堆的容量,动态增长 |
| `fHeapType` | `D3D12_DESCRIPTOR_HEAP_TYPE` | 池管理的堆类型 |

**职责**: 管理同类型的多个堆,实现堆的按需分配和容量增长。

## 公共 API 函数

### 渲染目标视图管理

```cpp
// 创建渲染目标视图(RTV)
GrD3DDescriptorHeap::CPUHandle createRenderTargetView(
    GrD3DGpu* gpu,
    ID3D12Resource* textureResource);

// 回收渲染目标视图
void recycleRenderTargetView(const GrD3DDescriptorHeap::CPUHandle& handle);
```

### 深度模板视图管理

```cpp
// 创建深度模板视图(DSV)
GrD3DDescriptorHeap::CPUHandle createDepthStencilView(
    GrD3DGpu* gpu,
    ID3D12Resource* textureResource);

// 回收深度模板视图
void recycleDepthStencilView(const GrD3DDescriptorHeap::CPUHandle& handle);
```

### 着色器资源视图管理

```cpp
// 创建常量缓冲视图(CBV)
GrD3DDescriptorHeap::CPUHandle createConstantBufferView(
    GrD3DGpu* gpu,
    ID3D12Resource* bufferResource,
    size_t offset,
    size_t size);

// 创建着色器资源视图(SRV)
GrD3DDescriptorHeap::CPUHandle createShaderResourceView(
    GrD3DGpu* gpu,
    ID3D12Resource* resource,
    unsigned int mostDetailedMip,
    unsigned int mipLevels);

// 创建无序访问视图(UAV)
GrD3DDescriptorHeap::CPUHandle createUnorderedAccessView(
    GrD3DGpu* gpu,
    ID3D12Resource* resource,
    unsigned int mipSlice);

// 回收着色器视图
void recycleShaderView(const GrD3DDescriptorHeap::CPUHandle& handle);
```

### 采样器管理

```cpp
// 创建采样器
GrD3DDescriptorHeap::CPUHandle createSampler(
    GrD3DGpu* gpu,
    D3D12_FILTER filter,
    float maxLOD,
    unsigned int maxAnisotropy,
    D3D12_TEXTURE_ADDRESS_MODE addressModeU,
    D3D12_TEXTURE_ADDRESS_MODE addressModeV);

// 回收采样器
void recycleSampler(const GrD3DDescriptorHeap::CPUHandle& handle);
```

### Heap 内部接口

```cpp
// 创建堆
static std::unique_ptr<Heap> Make(GrD3DGpu* gpu,
                                  D3D12_DESCRIPTOR_HEAP_TYPE type,
                                  unsigned int numDescriptors);

// 分配描述符
GrD3DDescriptorHeap::CPUHandle allocateCPUHandle();

// 释放描述符
void freeCPUHandle(const GrD3DDescriptorHeap::CPUHandle& handle);

// 检查是否可分配
bool canAllocate();

// 检查是否拥有该句柄
bool ownsHandle(const GrD3DDescriptorHeap::CPUHandle& handle);
```

## 内部实现细节

### 构造函数初始化

构造函数初始化四个堆池,每个池初始容量 32 个描述符:

```cpp
GrD3DCpuDescriptorManager::GrD3DCpuDescriptorManager(GrD3DGpu* gpu)
    : fRTVDescriptorPool(gpu, D3D12_DESCRIPTOR_HEAP_TYPE_RTV)
    , fDSVDescriptorPool(gpu, D3D12_DESCRIPTOR_HEAP_TYPE_DSV)
    , fShaderViewDescriptorPool(gpu, D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV)
    , fSamplerDescriptorPool(gpu, D3D12_DESCRIPTOR_HEAP_TYPE_SAMPLER) {}
```

### 渲染目标视图创建

`createRenderTargetView` 封装了 D3D12 API:

```cpp
GrD3DDescriptorHeap::CPUHandle
GrD3DCpuDescriptorManager::createRenderTargetView(GrD3DGpu* gpu,
                                                   ID3D12Resource* textureResource) {
    // 1. 从池中分配描述符
    const GrD3DDescriptorHeap::CPUHandle& descriptor =
        fRTVDescriptorPool.allocateHandle(gpu);

    // 2. 创建 RTV 到分配的描述符
    gpu->device()->CreateRenderTargetView(textureResource, nullptr, descriptor.fHandle);

    return descriptor;
}
```

使用默认视图描述符(nullptr),自动根据资源格式创建视图。

### 着色器资源视图创建

`createShaderResourceView` 支持 mipmap 范围:

```cpp
GrD3DDescriptorHeap::CPUHandle
GrD3DCpuDescriptorManager::createShaderResourceView(GrD3DGpu* gpu,
                                                     ID3D12Resource* resource,
                                                     unsigned int mostDetailedMip,
                                                     unsigned int mipLevels) {
    // 1. 分配描述符
    const GrD3DDescriptorHeap::CPUHandle& descriptor =
        fShaderViewDescriptorPool.allocateHandle(gpu);

    // 2. 配置 SRV 描述符
    D3D12_SHADER_RESOURCE_VIEW_DESC desc = {};
    desc.Format = resource->GetDesc().Format;
    desc.ViewDimension = D3D12_SRV_DIMENSION_TEXTURE2D;
    desc.Texture2D.MostDetailedMip = mostDetailedMip;
    desc.Texture2D.MipLevels = mipLevels;
    desc.Shader4ComponentMapping = D3D12_DEFAULT_SHADER_4_COMPONENT_MAPPING;

    // 3. 创建 SRV
    gpu->device()->CreateShaderResourceView(resource, &desc, descriptor.fHandle);

    return descriptor;
}
```

可以创建部分 mipmap 范围的视图,用于 LOD 控制。

### 采样器创建

`createSampler` 配置完整的采样器状态:

```cpp
GrD3DDescriptorHeap::CPUHandle
GrD3DCpuDescriptorManager::createSampler(GrD3DGpu* gpu,
                                         D3D12_FILTER filter,
                                         float maxLOD,
                                         unsigned int maxAnisotropy,
                                         D3D12_TEXTURE_ADDRESS_MODE addressModeU,
                                         D3D12_TEXTURE_ADDRESS_MODE addressModeV) {
    const GrD3DDescriptorHeap::CPUHandle& descriptor =
        fSamplerDescriptorPool.allocateHandle(gpu);

    D3D12_SAMPLER_DESC desc = {};
    desc.Filter = filter;
    desc.AddressU = addressModeU;
    desc.AddressV = addressModeV;
    desc.AddressW = D3D12_TEXTURE_ADDRESS_MODE_CLAMP;  // 固定 W 轴
    desc.MipLODBias = 0;
    desc.MaxAnisotropy = maxAnisotropy;
    desc.ComparisonFunc = D3D12_COMPARISON_FUNC_ALWAYS;
    desc.MinLOD = 0;
    desc.MaxLOD = maxLOD;

    gpu->device()->CreateSampler(&desc, descriptor.fHandle);
    return descriptor;
}
```

### 堆的位集分配

`Heap::allocateCPUHandle` 使用位集查找空闲块:

```cpp
GrD3DDescriptorHeap::CPUHandle Heap::allocateCPUHandle() {
    // 1. 查找第一个空闲块
    SkBitSet::OptionalIndex freeBlock = fFreeBlocks.findFirst();
    SkASSERT(freeBlock.has_value());

    // 2. 标记为已使用
    fFreeBlocks.reset(*freeBlock);
    --fFreeCount;

    // 3. 返回对应索引的 CPU 句柄
    return fHeap->getCPUHandle(*freeBlock);
}
```

`SkBitSet::findFirst()` 高效地找到第一个设置的位(空闲块)。

### 堆的描述符回收

`Heap::freeCPUHandle` 释放描述符:

```cpp
void Heap::freeCPUHandle(const GrD3DDescriptorHeap::CPUHandle& handle) {
    SkASSERT(this->ownsHandle(handle));

    // 1. 从句柄计算索引
    size_t index = fHeap->getIndex(handle);

    // 2. 标记为空闲
    fFreeBlocks.set(index);
    ++fFreeCount;
}
```

### 堆池的分配策略

`HeapPool::allocateHandle` 实现了堆的按需分配:

```cpp
GrD3DDescriptorHeap::CPUHandle HeapPool::allocateHandle(GrD3DGpu* gpu) {
    // 1. 遍历现有堆,寻找有空闲空间的
    for (unsigned int i = 0; i < fDescriptorHeaps.size(); ++i) {
        if (fDescriptorHeaps[i]->canAllocate()) {
            return fDescriptorHeaps[i]->allocateCPUHandle();
        }
    }

    // 2. 所有堆都满了,创建新堆
    std::unique_ptr<Heap> heap =
        Heap::Make(gpu, fHeapType, fMaxAvailableDescriptors);
    SkASSERT(heap);

    fDescriptorHeaps.push_back(std::move(heap));

    // 3. 容量倍增
    fMaxAvailableDescriptors *= 2;

    // 4. 从新堆分配
    return fDescriptorHeaps[fDescriptorHeaps.size() - 1]->allocateCPUHandle();
}
```

容量增长序列: 32 → 64 → 128 → 256 → ...

### 堆池的释放实现

`HeapPool::releaseHandle` 找到拥有该句柄的堆并释放:

```cpp
void HeapPool::releaseHandle(const GrD3DDescriptorHeap::CPUHandle& handle) {
    // 遍历所有堆,找到拥有者
    for (unsigned int i = 0; i < fDescriptorHeaps.size(); ++i) {
        if (fDescriptorHeaps[i]->ownsHandle(handle)) {
            fDescriptorHeaps[i]->freeCPUHandle(handle);
            return;
        }
    }
    SkASSERT(false);  // 未找到拥有者,错误
}
```

通过 `ownsHandle` 检查句柄的 `fHeapID` 是否匹配。

### 堆创建流程

`Heap::Make` 创建 CPU 可见堆:

```cpp
std::unique_ptr<Heap> Heap::Make(GrD3DGpu* gpu,
                                 D3D12_DESCRIPTOR_HEAP_TYPE type,
                                 unsigned int numDescriptors) {
    // 1. 创建 CPU 可见堆(无 SHADER_VISIBLE 标志)
    std::unique_ptr<GrD3DDescriptorHeap> heap =
        GrD3DDescriptorHeap::Make(gpu, type, numDescriptors,
                                  D3D12_DESCRIPTOR_HEAP_FLAG_NONE);
    if (!heap) return nullptr;

    // 2. 封装为 Heap 对象,初始化位集
    return std::unique_ptr<Heap>(new Heap(heap, numDescriptors));
}
```

`Heap` 构造函数初始化位集,所有位设置为 1(空闲):

```cpp
Heap(std::unique_ptr<GrD3DDescriptorHeap>& heap, unsigned int numDescriptors)
    : fHeap(std::move(heap))
    , fFreeBlocks(numDescriptors)
    , fFreeCount(numDescriptors) {
    for (unsigned int i = 0; i < numDescriptors; ++i) {
        fFreeBlocks.set(i);  // 标记为空闲
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrD3DDescriptorHeap` | 底层描述符堆封装 |
| `SkBitSet` | 位集,用于空闲块追踪 |
| `GrD3DGpu` | GPU 设备接口 |
| `ID3D12Device` | D3D12 设备对象(用于创建视图) |
| `ID3D12Resource` | D3D12 资源对象 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DResourceProvider` | 通过 `cpuDescriptorManager()` 访问 |
| `GrD3DTexture` | 创建纹理的 SRV |
| `GrD3DRenderTarget` | 创建渲染目标的 RTV 和 DSV |
| `GrD3DBuffer` | 创建缓冲区的 CBV |
| `GrD3DSampler` | 创建采样器 |

## 设计模式与设计决策

### 位集精确分配

使用 `SkBitSet` 而非简单的 bump allocator:
- **优点**: 支持任意顺序的分配和释放,避免碎片
- **成本**: 查找空闲块需要扫描位集
- **适用性**: CPU 描述符生命周期不规则,需要精确回收

### 类型化堆池

为每种描述符类型维护独立的池:
- 避免不同类型混用
- 符合 D3D12 的堆类型限制
- 简化代码逻辑

### 容量倍增策略

与 `GrD3DDescriptorTableManager` 类似的增长策略:
- 初始 32,快速适应小负载
- 倍增增长,减少扩展次数
- 无上限(GPU 描述符表有 2048 上限,CPU 描述符无此限制)

### 延迟回收

描述符不会立即销毁,而是标记为空闲供后续复用:
- 减少 D3D 对象创建开销
- 避免内存碎片
- 堆本身不回收,持续增长

### 封装 D3D API

隐藏 D3D12 视图创建的复杂性:
- 提供类型安全的接口
- 统一的错误处理
- 自动管理描述符生命周期

## 性能考量

### 位集查找性能

`SkBitSet::findFirst()` 通过位运算快速查找:
- 现代 CPU 提供 `__builtin_ffs` 等指令
- 通常 O(1) 或 O(log N)
- 相比线性扫描,性能更优

### 堆复用避免创建开销

描述符回收后立即可用:
- 避免调用 `CreateRenderTargetView` 等 API
- 减少驱动开销
- 提高帧间性能一致性

### 堆遍历开销

`allocateHandle` 和 `releaseHandle` 需要遍历堆列表:
- 堆数量通常较少(1-3 个)
- 遍历开销可忽略
- 可通过记录最后使用的堆优化

### 内存增长特性

堆只增长不收缩:
- 优点: 稳定性能,避免抖动
- 缺点: 峰值内存长期占用
- 适用性: 渲染应用通常保持稳定的描述符使用量

### 初始容量选择

32 个描述符的初始容量:
- RTV/DSV: 通常 1-4 个(帧缓冲)
- SRV: 几十到上百个(纹理)
- 采样器: 几个到十几个
- 平衡初始开销和扩展频率

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DDescriptorHeap.h/cpp` | 依赖 | 底层描述符堆封装 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 使用者 | GPU 设备接口 |
| `src/gpu/ganesh/d3d/GrD3DResourceProvider.h/cpp` | 拥有者 | 资源提供者持有管理器实例 |
| `src/gpu/ganesh/d3d/GrD3DTexture.h/cpp` | 使用者 | 创建纹理视图 |
| `src/gpu/ganesh/d3d/GrD3DRenderTarget.h/cpp` | 使用者 | 创建渲染目标视图 |
| `src/gpu/ganesh/d3d/GrD3DBuffer.h/cpp` | 使用者 | 创建缓冲区视图 |
| `src/utils/SkBitSet.h` | 工具 | 位集数据结构 |
| `src/gpu/ganesh/d3d/GrD3DDescriptorTableManager.h/cpp` | 相关 | GPU 可见描述符表管理(互补) |
