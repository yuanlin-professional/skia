# GrD3DCommandList

> 源文件
> - src/gpu/ganesh/d3d/GrD3DCommandList.h
> - src/gpu/ganesh/d3d/GrD3DCommandList.cpp

## 概述

`GrD3DCommandList` 是 Skia 图形库中 Ganesh D3D 后端的命令列表封装类,负责记录和管理提交到 GPU 的绘制命令。在 Direct3D 12 中,所有 GPU 操作必须通过命令列表记录,然后批量提交到命令队列执行。该类封装了 D3D12 的 `ID3D12GraphicsCommandList` 和 `ID3D12CommandAllocator`,提供了类型安全的接口和资源生命周期管理。

该模块定义了三个主要类:`GrD3DCommandList` 为基类提供通用的命令记录和资源追踪功能,`GrD3DDirectCommandList` 扩展了图形和计算命令接口,`GrD3DCopyCommandList` 专用于拷贝操作。通过批处理资源屏障、追踪资源依赖和管理命令分配器,该类实现了高效的 GPU 命令提交和资源复用。

## 架构位置

`GrD3DCommandList` 在 D3D12 命令记录层次结构中的位置:

```
Skia
└── src/gpu/ganesh/d3d
    ├── GrD3DGpu (D3D GPU 主类)
    │   └── fCurrentDirectCommandList (当前活跃命令列表)
    ├── GrD3DCommandList (命令列表基类) ← 核心类
    │   ├── GrD3DDirectCommandList (图形命令列表)
    │   └── GrD3DCopyCommandList (拷贝命令列表)
    ├── GrD3DOpsRenderPass (渲染通道,使用命令列表)
    └── GrD3DResourceProvider (资源提供者,管理命令列表池)
```

命令列表是 Ganesh 与 D3D12 API 交互的核心桥梁,所有 GPU 操作都通过它记录和提交。

## 主要类与结构体

### GrD3DCommandList (基类)

**继承关系**:
- 无继承(基类)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCommandList` | `gr_cp<ID3D12GraphicsCommandList>` | D3D12 图形命令列表对象 |
| `fAllocator` | `gr_cp<ID3D12CommandAllocator>` | D3D12 命令分配器,管理命令内存 |
| `fTrackedResources` | `STArray<32, sk_sp<GrManagedResource>>` | 追踪的资源列表,保证生命周期 |
| `fTrackedRecycledResources` | `STArray<32, sk_sp<GrRecycledResource>>` | 可回收资源列表 |
| `fTrackedGpuBuffers` | `STArray<32, sk_sp<const GrBuffer>>` | GPU 缓冲区引用 |
| `fResourceBarriers` | `STArray<4, D3D12_RESOURCE_BARRIER>` | 待提交的资源屏障列表 |
| `fFinishedCallbacks` | `TArray<sk_sp<RefCntedCallback>>` | 完成回调列表 |
| `fHasWork` | `bool` | 标记是否有实际命令记录 |
| `fIsActive` | `bool` (仅 Debug) | 标记命令列表是否处于记录状态 |

### GrD3DDirectCommandList

**继承关系**:
- 继承自: `GrD3DCommandList`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCurrentPipeline` | `const GrD3DPipeline*` | 当前绑定的图形管线 |
| `fCurrentGraphicsRootSignature` | `const GrD3DRootSignature*` | 当前图形根签名 |
| `fCurrentComputeRootSignature` | `const GrD3DRootSignature*` | 当前计算根签名 |
| `fCurrentVertexBuffer` | `const GrBuffer*` | 当前顶点缓冲区 |
| `fCurrentVertexStride` | `size_t` | 顶点步长 |
| `fCurrentInstanceBuffer` | `const GrBuffer*` | 当前实例缓冲区 |
| `fCurrentInstanceStride` | `size_t` | 实例步长 |
| `fCurrentIndexBuffer` | `const GrBuffer*` | 当前索引缓冲区 |
| `fCurrentGraphicsConstantBufferAddress` | `D3D12_GPU_VIRTUAL_ADDRESS` | 图形常量缓冲区地址 |
| `fCurrentComputeConstantBufferAddress` | `D3D12_GPU_VIRTUAL_ADDRESS` | 计算常量缓冲区地址 |
| `fCurrentGraphicsRootDescTable` | `D3D12_GPU_DESCRIPTOR_HANDLE[kParamIndexCount]` | 图形根描述符表 |
| `fCurrentComputeRootDescTable` | `D3D12_GPU_DESCRIPTOR_HANDLE[kParamIndexCount]` | 计算根描述符表 |
| `fCurrentSRVCRVDescriptorHeap` | `const ID3D12DescriptorHeap*` | 当前 SRV/CBV/UAV 堆 |
| `fCurrentSamplerDescriptorHeap` | `const ID3D12DescriptorHeap*` | 当前采样器堆 |
| `fResolveSubregionSupported` | `bool` | 硬件是否支持子区域解析 |

### SubmitResult 枚举

```cpp
enum class SubmitResult {
    kNoWork,   // 无命令,直接完成
    kSuccess,  // 提交成功
    kFailure,  // 提交失败
};
```

## 公共 API 函数

### 基类接口 (GrD3DCommandList)

```cpp
// 提交命令列表到队列
SubmitResult submit(ID3D12CommandQueue* queue);

// 关闭命令列表(提交前必须调用)
bool close();

// 重置命令列表供下次使用
void reset();

// 资源屏障
void resourceBarrier(sk_sp<GrManagedResource> resource,
                     int numBarriers,
                     const D3D12_RESOURCE_TRANSITION_BARRIER* barriers);

void uavBarrier(sk_sp<GrManagedResource> resource,
                ID3D12Resource* uavResource);

void aliasingBarrier(sk_sp<GrManagedResource> beforeResource,
                     ID3D12Resource* before,
                     sk_sp<GrManagedResource> afterResource,
                     ID3D12Resource* after);

// 拷贝操作
void copyBufferToTexture(ID3D12Resource* srcBuffer,
                        const GrD3DTextureResource* dstTexture,
                        uint32_t subresourceCount,
                        D3D12_PLACED_SUBRESOURCE_FOOTPRINT* bufferFootprints,
                        int left, int top);

void copyTextureRegionToTexture(sk_sp<GrManagedResource> dst,
                                const D3D12_TEXTURE_COPY_LOCATION* dstLocation,
                                UINT dstX, UINT dstY,
                                sk_sp<GrManagedResource> src,
                                const D3D12_TEXTURE_COPY_LOCATION* srcLocation,
                                const D3D12_BOX* srcBox);

void copyBufferToBuffer(sk_sp<GrD3DBuffer> dst, uint64_t dstOffset,
                        ID3D12Resource* src, uint64_t srcOffset,
                        uint64_t numBytes);

// 资源追踪
void addGrBuffer(sk_sp<const GrBuffer> buffer);
void addRecycledResource(sk_sp<GrRecycledResource> resource);

// 完成回调
void addFinishedCallback(sk_sp<skgpu::RefCntedCallback> callback);

// 查询状态
bool hasWork() const;
```

### 图形命令接口 (GrD3DDirectCommandList)

```cpp
// 静态工厂方法
static std::unique_ptr<GrD3DDirectCommandList> Make(GrD3DGpu* gpu);

// 管线状态
void setPipelineState(const sk_sp<GrD3DPipeline>& pipeline);
void setGraphicsRootSignature(const sk_sp<GrD3DRootSignature>& rootSignature);
void setComputeRootSignature(const sk_sp<GrD3DRootSignature>& rootSignature);

// 渲染状态
void setStencilRef(unsigned int stencilRef);
void setBlendFactor(const float blendFactor[4]);
void setPrimitiveTopology(D3D12_PRIMITIVE_TOPOLOGY primitiveTopology);
void setScissorRects(unsigned int numRects, const D3D12_RECT* rects);
void setViewports(unsigned int numViewports, const D3D12_VIEWPORT* viewports);

// 缓冲区绑定
void setVertexBuffers(unsigned int startSlot,
                     sk_sp<const GrBuffer> vertexBuffer, size_t vertexStride,
                     sk_sp<const GrBuffer> instanceBuffer, size_t instanceStride);
void setIndexBuffer(sk_sp<const GrBuffer> indexBuffer);

// 绘制命令
void drawInstanced(unsigned int vertexCount, unsigned int instanceCount,
                  unsigned int startVertex, unsigned int startInstance);

void drawIndexedInstanced(unsigned int indexCount, unsigned int instanceCount,
                         unsigned int startIndex, unsigned int baseVertex,
                         unsigned int startInstance);

void executeIndirect(const sk_sp<GrD3DCommandSignature> commandSig,
                    unsigned int maxCommandCnt,
                    const GrD3DBuffer* argumentBuffer,
                    size_t argumentBufferOffset);

// 计算调度
void dispatch(unsigned int threadGroupCountX,
             unsigned int threadGroupCountY,
             unsigned int threadGroupCountZ = 1);

// 渲染目标
void setRenderTarget(const GrD3DRenderTarget* renderTarget);
void clearRenderTargetView(const GrD3DRenderTarget* renderTarget,
                          std::array<float, 4> color,
                          const D3D12_RECT* rect);
void clearDepthStencilView(const GrD3DAttachment* attachment,
                          uint8_t stencilClearValue,
                          const D3D12_RECT* rect);

// MSAA 解析
void resolveSubresourceRegion(const GrD3DTextureResource* dstTexture,
                             unsigned int dstX, unsigned int dstY,
                             const GrD3DTextureResource* srcTexture,
                             D3D12_RECT* srcRect);

// 根参数绑定
void setGraphicsRootConstantBufferView(unsigned int rootParameterIndex,
                                      D3D12_GPU_VIRTUAL_ADDRESS bufferLocation);

void setGraphicsRootDescriptorTable(unsigned int rootParameterIndex,
                                   D3D12_GPU_DESCRIPTOR_HANDLE bufferLocation);

void setDescriptorHeaps(ID3D12DescriptorHeap* srvDescriptorHeap,
                       ID3D12DescriptorHeap* samplerDescriptorHeap);
```

## 内部实现细节

### 命令列表提交流程

`submit` 方法实现了完整的提交流程:

```cpp
SubmitResult GrD3DCommandList::submit(ID3D12CommandQueue* queue) {
    SkASSERT(fIsActive);

    // 1. 检查是否有实际工作
    if (!this->hasWork()) {
        this->callFinishedCallbacks();
        return SubmitResult::kNoWork;
    }

    // 2. 关闭命令列表
    if (!this->close()) {
        return SubmitResult::kFailure;
    }

    // 3. 提交到队列
    ID3D12CommandList* ppCommandLists[] = { fCommandList.get() };
    queue->ExecuteCommandLists(1, ppCommandLists);

    return SubmitResult::kSuccess;
}
```

### 命令列表关闭

`close` 方法提交待处理的屏障并关闭命令列表:

```cpp
bool GrD3DCommandList::close() {
    SkASSERT(fIsActive);

    // 1. 提交所有待处理的资源屏障
    this->submitResourceBarriers();

    // 2. 关闭命令列表
    HRESULT hr = fCommandList->Close();
    SkDEBUGCODE(fIsActive = false;)

    return SUCCEEDED(hr);
}
```

关闭后的命令列表不可再记录命令,必须先 `reset`。

### 命令列表重置

`reset` 方法复用命令列表和分配器:

```cpp
void GrD3DCommandList::reset() {
    SkASSERT(!fIsActive);

    // 1. 重置分配器(释放旧命令内存)
    GR_D3D_CALL_ERRCHECK(fAllocator->Reset());

    // 2. 重置命令列表
    GR_D3D_CALL_ERRCHECK(fCommandList->Reset(fAllocator.get(), nullptr));

    // 3. 调用子类重置逻辑
    this->onReset();

    // 4. 释放资源引用
    this->releaseResources();

    // 5. 重置状态标志
    SkDEBUGCODE(fIsActive = true;)
    fHasWork = false;
}
```

### 资源屏障批处理

资源屏障被缓存,延迟提交以优化性能:

```cpp
void GrD3DCommandList::resourceBarrier(sk_sp<GrManagedResource> resource,
                                       int numBarriers,
                                       const D3D12_RESOURCE_TRANSITION_BARRIER* barriers) {
    SkASSERT(fIsActive);

    // 1. 添加屏障到缓存列表
    for (int i = 0; i < numBarriers; ++i) {
        D3D12_RESOURCE_BARRIER& newBarrier = fResourceBarriers.push_back();
        newBarrier.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
        newBarrier.Flags = D3D12_RESOURCE_BARRIER_FLAG_NONE;
        newBarrier.Transition = barriers[i];
    }

    fHasWork = true;

    // 2. 追踪资源引用
    if (resource) {
        this->addResource(std::move(resource));
    }
}

void GrD3DCommandList::submitResourceBarriers() {
    if (fResourceBarriers.size()) {
        fCommandList->ResourceBarrier(fResourceBarriers.size(),
                                      fResourceBarriers.begin());
        fResourceBarriers.clear();
    }
}
```

屏障在 `addingWork` 或 `close` 时批量提交。

### 资源生命周期管理

命令列表追踪所有使用的资源,确保在 GPU 完成前不被销毁:

```cpp
void GrD3DCommandList::releaseResources() {
    if (fTrackedResources.size() == 0 && fTrackedRecycledResources.size() == 0) {
        return;
    }
    SkASSERT(!fIsActive);

    // 1. 回收可复用资源
    for (int i = 0; i < fTrackedRecycledResources.size(); ++i) {
        auto resource = fTrackedRecycledResources[i].release();
        resource->recycle();
    }

    // 2. 清空所有追踪列表(释放引用计数)
    fTrackedResources.clear();
    fTrackedRecycledResources.clear();
    fTrackedGpuBuffers.clear();

    // 3. 调用完成回调
    this->callFinishedCallbacks();
}
```

### 拷贝命令实现

缓冲区到纹理拷贝支持多个子资源:

```cpp
void GrD3DCommandList::copyBufferToTexture(ID3D12Resource* srcBuffer,
                                           const GrD3DTextureResource* dstTexture,
                                           uint32_t subresourceCount,
                                           D3D12_PLACED_SUBRESOURCE_FOOTPRINT* bufferFootprints,
                                           int left, int top) {
    this->addingWork();
    this->addResource(dstTexture->resource());

    for (uint32_t subresource = 0; subresource < subresourceCount; ++subresource) {
        D3D12_TEXTURE_COPY_LOCATION src = {};
        src.pResource = srcBuffer;
        src.Type = D3D12_TEXTURE_COPY_TYPE_PLACED_FOOTPRINT;
        src.PlacedFootprint = bufferFootprints[subresource];

        D3D12_TEXTURE_COPY_LOCATION dst = {};
        dst.pResource = dstTexture->d3dResource();
        dst.Type = D3D12_TEXTURE_COPY_TYPE_SUBRESOURCE_INDEX;
        dst.SubresourceIndex = subresource;

        fCommandList->CopyTextureRegion(&dst, left, top, 0, &src, nullptr);
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrManagedResource` | 资源管理基类,提供引用计数 |
| `GrRecycledResource` | 可回收资源基类 |
| `ID3D12GraphicsCommandList` | D3D12 命令列表 COM 接口 |
| `ID3D12CommandAllocator` | D3D12 命令分配器 COM 接口 |
| `ID3D12CommandQueue` | D3D12 命令队列 COM 接口 |
| `GrD3DGpu` | GPU 设备接口 |
| `GrD3DPipeline` | 图形管线对象 |
| `GrD3DRootSignature` | 根签名对象 |
| `GrD3DTexture/GrD3DRenderTarget` | 纹理和渲染目标 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DGpu` | 持有当前命令列表,提交命令 |
| `GrD3DOpsRenderPass` | 记录渲染命令 |
| `GrD3DResourceProvider` | 管理命令列表池 |

## 设计模式与设计决策

### 延迟屏障提交

批处理资源屏障可减少 API 调用:
- 屏障缓存在数组中
- `addingWork` 时批量提交
- D3D 驱动可优化连续屏障

### 资源追踪机制

通过智能指针自动管理资源生命周期:
- 命令记录时添加资源引用
- 命令完成后自动释放
- 防止过早销毁导致的 GPU 错误

### 命令分配器复用

分配器与命令列表绑定复用:
- `Reset` 后重用内存
- 避免频繁创建/销毁
- 减少驱动开销

### 回调机制

支持命令完成回调:
- 用于资源清理
- 性能追踪
- 同步原语

## 性能考量

### 批处理优化

- 延迟屏障提交减少 API 调用
- 单次 `ResourceBarrier` 提交多个屏障
- 驱动可优化批量屏障

### 内存复用

- 命令分配器复用减少内存分配
- 资源追踪数组预分配 32 个槽位
- 避免动态增长开销

### 状态缓存

`GrD3DDirectCommandList` 缓存当前状态:
- 避免冗余的状态设置
- 减少 D3D API 调用
- 优化 CPU 开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 使用者 | GPU 设备接口 |
| `src/gpu/ganesh/d3d/GrD3DResourceProvider.h/cpp` | 管理者 | 命令列表池化 |
| `src/gpu/ganesh/d3d/GrD3DOpsRenderPass.h/cpp` | 使用者 | 渲染命令记录 |
| `src/gpu/ganesh/GrManagedResource.h` | 依赖 | 资源管理基类 |
