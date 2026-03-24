# GrD3DResourceProvider

> 源文件
> - src/gpu/ganesh/d3d/GrD3DResourceProvider.h
> - src/gpu/ganesh/d3d/GrD3DResourceProvider.cpp

## 概述

`GrD3DResourceProvider` 是 Skia 图形库中 Ganesh D3D 后端的核心资源管理类,负责创建、缓存和复用各类 D3D12 资源和对象。该类充当资源工厂和缓存管理器的角色,统一管理命令列表、根签名、管线状态、描述符、采样器等多种资源,通过缓存机制避免重复创建,显著提高渲染性能和降低驱动开销。

该类集成了多个子管理器,包括 `GrD3DCpuDescriptorManager`(CPU 描述符管理)、`GrD3DDescriptorTableManager`(GPU 描述符表管理)、`PipelineStateCache`(管线状态缓存)和 `DescriptorTableCache`(描述符表缓存)。通过统一的接口对外提供资源服务,隐藏了复杂的缓存查找和创建逻辑,简化了上层代码的资源管理。

## 架构位置

`GrD3DResourceProvider` 在 Ganesh D3D 架构中的位置:

```
Skia
└── src/gpu/ganesh/d3d
    ├── GrD3DGpu (D3D GPU 主类)
    │   └── fResourceProvider (资源提供者) ← 核心类
    │       ├── GrD3DCpuDescriptorManager (CPU 描述符)
    │       ├── GrD3DDescriptorTableManager (GPU 描述符表)
    │       ├── PipelineStateCache (管线状态缓存)
    │       ├── DescriptorTableCache (描述符表缓存)
    │       ├── 命令列表池
    │       ├── 根签名缓存
    │       ├── 命令签名缓存
    │       └── 采样器缓存
    └── 各种 D3D 资源类(使用资源提供者创建资源)
```

该类是 `GrD3DGpu` 的核心组件,几乎所有 D3D 资源的创建都通过它进行。

## 主要类与结构体

### GrD3DResourceProvider

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrD3DGpu*` | GPU 设备指针 |
| `fAvailableDirectCommandLists` | `STArray<4, unique_ptr<CommandList>>` | 可复用的命令列表池 |
| `fRootSignatures` | `STArray<4, sk_sp<RootSignature>>` | 根签名缓存数组 |
| `fCommandSignatures` | `STArray<2, sk_sp<CommandSignature>>` | 命令签名缓存数组 |
| `fCpuDescriptorManager` | `GrD3DCpuDescriptorManager` | CPU 描述符管理器 |
| `fDescriptorTableManager` | `GrD3DDescriptorTableManager` | GPU 描述符表管理器 |
| `fPipelineStateCache` | `unique_ptr<PipelineStateCache>` | 管线状态缓存 |
| `fMipmapPipeline` | `sk_sp<GrD3DPipeline>` | Mipmap 生成计算管线 |
| `fSamplers` | `THashMap<uint32_t, D3D12_CPU_DESCRIPTOR_HANDLE>` | 采样器缓存哈希表 |
| `fShaderResourceDescriptorTableCache` | `DescriptorTableCache` | 着色器资源描述符表缓存 |
| `fSamplerDescriptorTableCache` | `DescriptorTableCache` | 采样器描述符表缓存 |

### PipelineStateCache

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fMap` | `SkLRUCache<GrProgramDesc, Entry, DescHash>` | LRU 缓存,键为程序描述符 |
| `fGpu` | `GrD3DGpu*` | GPU 设备指针 |
| `fTotalRequests` | `int` (仅 Debug) | 总请求数 |
| `fCacheMisses` | `int` (仅 Debug) | 缓存未命中数 |

**职责**: 缓存编译好的管线状态对象,避免重复编译着色器和创建管线。

### DescriptorTableCache

**关键成员**:

| 成员 | 类型 | 说明 |
|------|------|------|
| `fMap` | `SkLRUCache<DescTableKey, DescTableValue>` | LRU 缓存,键为描述符句柄向量 |
| `fGpu` | `GrD3DGpu*` | GPU 设备指针 |
| `fRangeSizes` | `unsigned int[8]` | 描述符范围大小数组(固定为 1) |

**职责**: 缓存描述符表,避免重复创建和拷贝描述符。

## 公共 API 函数

### 命令列表管理

```cpp
// 查找或创建直接命令列表
std::unique_ptr<GrD3DDirectCommandList> findOrCreateDirectCommandList();

// 回收命令列表供后续复用
void recycleDirectCommandList(std::unique_ptr<GrD3DDirectCommandList> commandList);
```

### 根签名与命令签名

```cpp
// 查找或创建根签名
sk_sp<GrD3DRootSignature> findOrCreateRootSignature(int numTextureSamplers,
                                                     int numUAVs = 0);

// 查找或创建命令签名(用于间接绘制)
sk_sp<GrD3DCommandSignature> findOrCreateCommandSignature(
    GrD3DCommandSignature::ForIndexed indexed,
    unsigned int slot);
```

### CPU 描述符管理

```cpp
// 渲染目标视图
GrD3DDescriptorHeap::CPUHandle createRenderTargetView(ID3D12Resource* textureResource);
void recycleRenderTargetView(const GrD3DDescriptorHeap::CPUHandle& handle);

// 深度模板视图
GrD3DDescriptorHeap::CPUHandle createDepthStencilView(ID3D12Resource* textureResource);
void recycleDepthStencilView(const GrD3DDescriptorHeap::CPUHandle& handle);

// 着色器资源视图
GrD3DDescriptorHeap::CPUHandle createConstantBufferView(ID3D12Resource* bufferResource,
                                                         size_t offset,
                                                         size_t size);

GrD3DDescriptorHeap::CPUHandle createShaderResourceView(ID3D12Resource* resource,
                                                         unsigned int mostDetailedMip = 0,
                                                         unsigned int mipLevels = -1);

GrD3DDescriptorHeap::CPUHandle createUnorderedAccessView(ID3D12Resource* resource,
                                                         unsigned int mipSlice);

void recycleShaderView(const GrD3DDescriptorHeap::CPUHandle& handle);
```

### 采样器管理

```cpp
// 查找或创建兼容的采样器
D3D12_CPU_DESCRIPTOR_HANDLE findOrCreateCompatibleSampler(const GrSamplerState& params);
```

### GPU 描述符表管理

```cpp
// 查找或创建着色器视图描述符表
sk_sp<GrD3DDescriptorTable> findOrCreateShaderViewTable(
    const std::vector<D3D12_CPU_DESCRIPTOR_HANDLE>& shaderViews);

// 查找或创建采样器描述符表
sk_sp<GrD3DDescriptorTable> findOrCreateSamplerTable(
    const std::vector<D3D12_CPU_DESCRIPTOR_HANDLE>& samplers);

// 访问描述符表管理器
GrD3DDescriptorTableManager* descriptorTableMgr();
```

### 管线状态管理

```cpp
// 查找或创建兼容的管线状态
GrD3DPipelineState* findOrCreateCompatiblePipelineState(GrD3DRenderTarget* renderTarget,
                                                         const GrProgramInfo& programInfo);

// 查找或创建 mipmap 生成计算管线
sk_sp<GrD3DPipeline> findOrCreateMipmapPipeline();

// 标记管线状态的 uniform 数据为脏
void markPipelineStateUniformsDirty();
```

### 常量数据上传

```cpp
// 上传常量数据到 GPU,返回 GPU 虚拟地址
D3D12_GPU_VIRTUAL_ADDRESS uploadConstantData(void* data, size_t size);

// 提交前准备
void prepForSubmit();
```

### 资源销毁

```cpp
// 销毁所有资源
void destroyResources();
```

## 内部实现细节

### 命令列表池化

`findOrCreateDirectCommandList` 实现命令列表复用:

```cpp
std::unique_ptr<GrD3DDirectCommandList>
GrD3DResourceProvider::findOrCreateDirectCommandList() {
    // 1. 检查池中是否有可用命令列表
    if (fAvailableDirectCommandLists.size()) {
        // 取出最后一个
        std::unique_ptr<GrD3DDirectCommandList> list =
            std::move(fAvailableDirectCommandLists.back());
        fAvailableDirectCommandLists.pop_back();
        return list;
    }

    // 2. 池为空,创建新命令列表
    return GrD3DDirectCommandList::Make(fGpu);
}
```

`recycleDirectCommandList` 回收命令列表:

```cpp
void GrD3DResourceProvider::recycleDirectCommandList(
    std::unique_ptr<GrD3DDirectCommandList> commandList) {
    // 1. 重置命令列表状态
    commandList->reset();

    // 2. 放回池中
    fAvailableDirectCommandLists.push_back(std::move(commandList));
}
```

### 根签名查找与创建

`findOrCreateRootSignature` 实现简单的线性查找缓存:

```cpp
sk_sp<GrD3DRootSignature>
GrD3DResourceProvider::findOrCreateRootSignature(int numTextureSamplers, int numUAVs) {
    // 1. 遍历缓存查找兼容的根签名
    for (int i = 0; i < fRootSignatures.size(); ++i) {
        if (fRootSignatures[i]->isCompatible(numTextureSamplers, numUAVs)) {
            return fRootSignatures[i];
        }
    }

    // 2. 未找到,创建新根签名
    auto rootSig = GrD3DRootSignature::Make(fGpu, numTextureSamplers, numUAVs);
    if (!rootSig) return nullptr;

    // 3. 添加到缓存
    fRootSignatures.push_back(rootSig);
    return rootSig;
}
```

根签名类型少,使用线性查找足够高效。

### 采样器查找与创建

`findOrCreateCompatibleSampler` 使用哈希表缓存:

```cpp
D3D12_CPU_DESCRIPTOR_HANDLE
GrD3DResourceProvider::findOrCreateCompatibleSampler(const GrSamplerState& params) {
    // 1. 计算采样器参数的哈希键
    uint32_t key = params.asKey(/*anisoIsOrthogonal=*/false);

    // 2. 查找缓存
    D3D12_CPU_DESCRIPTOR_HANDLE* samplerPtr = fSamplers.find(key);
    if (samplerPtr) {
        return *samplerPtr;
    }

    // 3. 未找到,创建新采样器
    D3D12_FILTER filter = d3d_filter(params);
    float maxLOD = params.mipmapped() == skgpu::Mipmapped::kYes
                   ? std::numeric_limits<float>::max()
                   : 0.f;
    D3D12_TEXTURE_ADDRESS_MODE addressModeU = wrap_mode_to_d3d_address_mode(params.wrapModeX());
    D3D12_TEXTURE_ADDRESS_MODE addressModeV = wrap_mode_to_d3d_address_mode(params.wrapModeY());
    unsigned int maxAnisotropy = params.maxAniso();

    D3D12_CPU_DESCRIPTOR_HANDLE sampler =
        fCpuDescriptorManager.createSampler(fGpu, filter, maxLOD,
                                            maxAnisotropy, addressModeU, addressModeV).fHandle;

    // 4. 添加到缓存
    fSamplers.set(key, sampler);
    return sampler;
}
```

### 采样器参数转换

辅助函数将 Skia 的采样器参数转换为 D3D12 枚举:

```cpp
// 包装模式转换
static D3D12_TEXTURE_ADDRESS_MODE wrap_mode_to_d3d_address_mode(GrSamplerState::WrapMode wrapMode) {
    switch (wrapMode) {
        case GrSamplerState::WrapMode::kClamp:        return D3D12_TEXTURE_ADDRESS_MODE_CLAMP;
        case GrSamplerState::WrapMode::kRepeat:       return D3D12_TEXTURE_ADDRESS_MODE_WRAP;
        case GrSamplerState::WrapMode::kMirrorRepeat: return D3D12_TEXTURE_ADDRESS_MODE_MIRROR;
        case GrSamplerState::WrapMode::kClampToBorder: return D3D12_TEXTURE_ADDRESS_MODE_BORDER;
    }
}

// 过滤模式转换
static D3D12_FILTER d3d_filter(GrSamplerState sampler) {
    if (sampler.isAniso()) {
        return D3D12_FILTER_ANISOTROPIC;
    }
    switch (sampler.mipmapMode()) {
        case GrSamplerState::MipmapMode::kNone:
        case GrSamplerState::MipmapMode::kNearest:
            switch (sampler.filter()) {
                case GrSamplerState::Filter::kNearest: return D3D12_FILTER_MIN_MAG_MIP_POINT;
                case GrSamplerState::Filter::kLinear:  return D3D12_FILTER_MIN_MAG_LINEAR_MIP_POINT;
            }
        case GrSamplerState::MipmapMode::kLinear:
            switch (sampler.filter()) {
                case GrSamplerState::Filter::kNearest: return D3D12_FILTER_MIN_MAG_POINT_MIP_LINEAR;
                case GrSamplerState::Filter::kLinear:  return D3D12_FILTER_MIN_MAG_MIP_LINEAR;
            }
    }
}
```

### 描述符表缓存

`DescriptorTableCache` 使用 LRU 缓存管理描述符表:

```cpp
sk_sp<GrD3DDescriptorTable> findOrCreateDescTable(
    const std::vector<D3D12_CPU_DESCRIPTOR_HANDLE>& handles,
    CreateFunc createFunc) {

    // 1. 查找 LRU 缓存
    DescTableValue* cachedTable = fMap.find(handles);
    if (cachedTable) {
        return *cachedTable;
    }

    // 2. 未命中,创建新描述符表
    sk_sp<GrD3DDescriptorTable> table = createFunc(fGpu, handles.size());

    // 3. 拷贝描述符到表中
    if (table) {
        fGpu->device()->CopyDescriptors(
            1, table->baseCpuDescriptorPtr(), &handles.size(),
            handles.size(), handles.data(), fRangeSizes,
            table->type());
    }

    // 4. 插入缓存
    fMap.insert(handles, table);
    return table;
}
```

### CPU 描述符委托

资源提供者将 CPU 描述符操作委托给 `fCpuDescriptorManager`:

```cpp
GrD3DDescriptorHeap::CPUHandle
GrD3DResourceProvider::createRenderTargetView(ID3D12Resource* textureResource) {
    return fCpuDescriptorManager.createRenderTargetView(fGpu, textureResource);
}

void GrD3DResourceProvider::recycleRenderTargetView(
    const GrD3DDescriptorHeap::CPUHandle& rtvDescriptor) {
    fCpuDescriptorManager.recycleRenderTargetView(rtvDescriptor);
}
```

### 管线状态缓存

`PipelineStateCache::refPipelineState` 查找或创建管线状态:

```cpp
GrD3DPipelineState* refPipelineState(GrD3DRenderTarget* rt, const GrProgramInfo& info) {
    // 1. 生成程序描述符键
    GrProgramDesc desc = GrProgramDesc::Build(info, ...);

    // 2. 查找 LRU 缓存
    Entry* entry = fMap.find(desc);
    if (entry) {
        #ifdef GR_PIPELINE_STATE_CACHE_STATS
        ++fTotalRequests;
        #endif
        return entry->pipelineState.get();
    }

    // 3. 缓存未命中,构建新管线状态
    #ifdef GR_PIPELINE_STATE_CACHE_STATS
    ++fCacheMisses;
    ++fTotalRequests;
    #endif

    GrD3DPipelineState* newState =
        GrD3DPipelineStateBuilder::CreatePipelineState(fGpu, rt, info, &desc);

    // 4. 插入缓存
    fMap.insert(desc, std::make_unique<Entry>(newState));
    return newState;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrD3DGpu` | GPU 设备接口 |
| `GrD3DCpuDescriptorManager` | CPU 描述符管理 |
| `GrD3DDescriptorTableManager` | GPU 描述符表管理 |
| `GrD3DCommandList` | 命令列表 |
| `GrD3DRootSignature` | 根签名 |
| `GrD3DCommandSignature` | 命令签名 |
| `GrD3DPipelineState` | 管线状态 |
| `SkLRUCache` | LRU 缓存数据结构 |
| `SkTHash` | 哈希表数据结构 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DGpu` | 通过 `resourceProvider()` 访问 |
| `GrD3DOpsRenderPass` | 获取管线状态、描述符表 |
| `GrD3DTexture/GrD3DRenderTarget` | 创建视图 |
| `GrD3DBuffer` | 创建常量缓冲视图 |

## 设计模式与设计决策

### 外观模式(Facade)

资源提供者作为统一入口,隐藏多个子管理器的复杂性:
- 简化上层API
- 集中管理缓存策略
- 便于修改内部实现

### 对象池模式

命令列表池化避免重复创建:
- 减少D3D对象创建开销
- 降低内存分配压力
- 提高帧间性能一致性

### 缓存策略分层

不同资源使用不同缓存策略:
- 根签名: 线性数组(类型少)
- 采样器: 哈希表(快速查找)
- 管线状态: LRU缓存(限制大小)
- 描述符表: LRU缓存(限制大小)

### 委托模式

描述符操作委托给专门的管理器:
- 职责分离
- 代码组织清晰
- 便于单独测试

## 性能考量

### LRU缓存限制

管线状态和描述符表使用LRU:
- 限制缓存大小,避免内存膨胀
- 自动淘汰最少使用项
- 平衡命中率和内存开销

### 哈希表快速查找

采样器缓存使用哈希表:
- O(1)平均查找时间
- 采样器数量通常几十个
- 避免LRU的链表开销

### 命令列表复用

池化命令列表显著减少开销:
- 避免每帧创建分配器
- 减少D3D驱动调用
- 提高帧率稳定性

### 统计信息(Debug模式)

管线状态缓存收集统计:
- 追踪命中率
- 识别性能瓶颈
- 优化缓存大小

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 拥有者 | GPU设备持有资源提供者 |
| `src/gpu/ganesh/d3d/GrD3DCpuDescriptorManager.h/cpp` | 组件 | CPU描述符管理 |
| `src/gpu/ganesh/d3d/GrD3DDescriptorTableManager.h/cpp` | 组件 | GPU描述符表管理 |
| `src/gpu/ganesh/d3d/GrD3DPipelineState.h/cpp` | 管理对象 | 管线状态 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h/cpp` | 管理对象 | 命令列表 |
| `src/core/SkLRUCache.h` | 工具 | LRU缓存实现 |
