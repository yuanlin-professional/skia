# GrD3DGpu

> 源文件
> - src/gpu/ganesh/d3d/GrD3DGpu.h
> - src/gpu/ganesh/d3d/GrD3DGpu.cpp

## 概述

`GrD3DGpu` 是 Skia 图形库中 Ganesh GPU 后端的 Direct3D 12 实现类,继承自抽象基类 `GrGpu`。该类是整个 D3D12 后端的核心控制器,负责管理 D3D12 设备、命令队列、资源创建、渲染操作、内存分配以及与 GPU 的同步。它封装了所有与 D3D12 API 交互的底层细节,为上层的 Skia 渲染系统提供统一的 GPU 抽象接口。

该类实现了超过 2000 行的复杂逻辑,涵盖纹理创建、缓冲区管理、像素读写、表面拷贝、渲染通道管理、命令列表提交、GPU 同步等关键功能。作为 Ganesh D3D 后端的入口点,它协调资源提供者、命令列表、描述符管理器等多个子系统,构建完整的 D3D12 渲染管线。

## 架构位置

`GrD3DGpu` 在 Skia GPU 架构中处于核心位置:

```
Skia
└── src/gpu/ganesh (Ganesh GPU 后端)
    ├── GrGpu (抽象 GPU 基类)
    │   └── GrD3DGpu (D3D12 实现) ← 核心类
    │       ├── GrD3DResourceProvider (资源提供者)
    │       ├── GrD3DCommandList (命令列表)
    │       ├── GrD3DMemoryAllocator (内存分配器)
    │       ├── GrD3DCaps (能力查询)
    │       ├── GrStagingBufferManager (暂存缓冲区)
    │       └── GrRingBuffer (常量环形缓冲区)
    └── d3d (D3D12 子系统)
        ├── GrD3DTexture
        ├── GrD3DRenderTarget
        ├── GrD3DBuffer
        ├── GrD3DOpsRenderPass
        └── GrD3DSemaphore
```

该类是 Ganesh D3D 后端的中枢,所有 D3D 相关的资源创建和命令提交都通过此类进行。

## 主要类与结构体

### GrD3DGpu

**继承关系**:
- 继承自: `GrGpu` (Ganesh GPU 抽象基类)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDevice` | `gr_cp<ID3D12Device>` | D3D12 设备对象,核心 API 入口 |
| `fQueue` | `gr_cp<ID3D12CommandQueue>` | D3D12 命令队列,用于提交命令列表 |
| `fMemoryAllocator` | `sk_sp<GrD3DMemoryAllocator>` | 内存分配器,管理 GPU 内存 |
| `fResourceProvider` | `GrD3DResourceProvider` | 资源提供者,管理管线状态、着色器等 |
| `fStagingBufferManager` | `GrStagingBufferManager` | 暂存缓冲区管理器,用于数据上传 |
| `fConstantsRingBuffer` | `GrRingBuffer` | 常量环形缓冲区,用于uniform数据 |
| `fFence` | `gr_cp<ID3D12Fence>` | D3D12 围栏对象,用于 CPU-GPU 同步 |
| `fCurrentFenceValue` | `uint64_t` | 当前围栏值,递增表示新的提交 |
| `fCurrentDirectCommandList` | `std::unique_ptr<GrD3DDirectCommandList>` | 当前活跃的命令列表 |
| `fOutstandingCommandLists` | `SkDeque` | 已提交但未完成的命令列表队列 |
| `fCachedOpsRenderPass` | `std::unique_ptr<GrD3DOpsRenderPass>` | 缓存的渲染通道对象,避免重复创建 |
| `fMipmapCPUDescriptors` | `STArray<32, CPUHandle>` | Mipmap 计算着色器使用的临时描述符 |

### OutstandingCommandList 结构体

```cpp
struct OutstandingCommandList {
    std::unique_ptr<GrD3DDirectCommandList> fCommandList;  // 命令列表对象
    uint64_t fFenceValue;                                   // 关联的围栏值
};
```

用于跟踪已提交到 GPU 的命令列表及其对应的围栏值,便于回收已完成的命令列表。

### SyncQueue 枚举

```cpp
enum class SyncQueue {
    kForce,  // 强制等待队列完成
    kSkip    // 不等待,异步提交
};
```

控制命令列表提交后的同步行为。

## 公共 API 函数

### 静态工厂方法

```cpp
static std::unique_ptr<GrGpu> Make(const GrD3DBackendContext& backendContext,
                                   const GrContextOptions& contextOptions,
                                   GrDirectContext* direct);
```

创建 `GrD3DGpu` 实例的工厂方法:
- 自动创建内存分配器(如果未提供)
- 初始化设备、队列、能力对象
- 返回基类指针,符合多态设计

### 核心访问器

```cpp
ID3D12Device* device() const;
ID3D12CommandQueue* queue() const;
GrD3DMemoryAllocator* memoryAllocator() const;
GrD3DResourceProvider& resourceProvider();
GrD3DDirectCommandList* currentCommandList() const;
const GrD3DCaps& d3dCaps() const;
```

提供对核心 D3D 对象和子系统的访问。

### 纹理创建

```cpp
// 创建普通纹理
sk_sp<GrTexture> onCreateTexture(SkISize dimensions,
                                 const GrBackendFormat& format,
                                 GrRenderable renderable,
                                 int renderTargetSampleCnt,
                                 skgpu::Budgeted budgeted,
                                 GrProtected isProtected,
                                 int mipLevelCount,
                                 uint32_t levelClearMask,
                                 std::string_view label) override;

// 创建压缩纹理
sk_sp<GrTexture> onCreateCompressedTexture(SkISize dimensions,
                                           const GrBackendFormat& format,
                                           skgpu::Budgeted budgeted,
                                           skgpu::Mipmapped mipmapped,
                                           GrProtected isProtected,
                                           const void* data,
                                           size_t dataSize) override;
```

### 纹理包装

```cpp
sk_sp<GrTexture> onWrapBackendTexture(const GrBackendTexture&,
                                      GrWrapOwnership,
                                      GrWrapCacheable,
                                      GrIOType) override;

sk_sp<GrTexture> onWrapRenderableBackendTexture(const GrBackendTexture&,
                                                int sampleCnt,
                                                GrWrapOwnership,
                                                GrWrapCacheable) override;
```

包装外部创建的 D3D12 纹理,支持互操作性。

### 缓冲区管理

```cpp
sk_sp<GrGpuBuffer> onCreateBuffer(size_t sizeInBytes,
                                  GrGpuBufferType type,
                                  GrAccessPattern pattern) override;

void takeOwnershipOfBuffer(sk_sp<GrGpuBuffer> buffer) override;
```

### 像素传输

```cpp
bool onReadPixels(GrSurface* surface, SkIRect rect,
                  GrColorType surfaceColorType,
                  GrColorType dstColorType,
                  void* buffer, size_t rowBytes) override;

bool onWritePixels(GrSurface* surface, SkIRect rect,
                   GrColorType surfaceColorType,
                   GrColorType srcColorType,
                   const GrMipLevel[] texels,
                   int mipLevelCount,
                   bool prepForTexSampling) override;
```

### 表面拷贝与解析

```cpp
bool onCopySurface(GrSurface* dst, const SkIRect& dstRect,
                   GrSurface* src, const SkIRect& srcRect,
                   GrSamplerState::Filter filter) override;

void onResolveRenderTarget(GrRenderTarget* target,
                           const SkIRect& resolveRect) override;
```

### 命令提交与同步

```cpp
void submit(GrOpsRenderPass* renderPass) override;
bool submitDirectCommandList(SyncQueue sync);
void checkForFinishedCommandLists();
void waitForQueueCompletion();
void finishOutstandingGpuWork() override;
```

### 资源屏障

```cpp
void addResourceBarriers(sk_sp<GrManagedResource> resource,
                        int numBarriers,
                        D3D12_RESOURCE_TRANSITION_BARRIER* barriers) const;

void addBufferResourceBarriers(GrD3DBuffer* buffer,
                              int numBarriers,
                              D3D12_RESOURCE_TRANSITION_BARRIER* barriers) const;
```

### 信号量操作

```cpp
std::unique_ptr<GrSemaphore> makeSemaphore(bool isOwned) override;
void insertSemaphore(GrSemaphore* semaphore) override;
void waitSemaphore(GrSemaphore* semaphore) override;
```

### Attachment 创建

```cpp
sk_sp<GrAttachment> makeStencilAttachment(const GrBackendFormat& colorFormat,
                                         SkISize dimensions,
                                         int numStencilSamples) override;

GrBackendFormat getPreferredStencilFormat(const GrBackendFormat&) override;
```

## 内部实现细节

### 初始化流程

构造函数执行完整的 D3D12 后端初始化:

1. **保存核心对象**: 存储设备、队列、内存分配器
2. **初始化子系统**:
   - `fResourceProvider`: 管理管线状态、着色器、描述符堆
   - `fStagingBufferManager`: 创建暂存缓冲区用于数据传输
   - `fConstantsRingBuffer`: 128KB 环形缓冲区,256字节对齐
   - `fOutstandingCommandLists`: 预分配 8 个槽位的双端队列
3. **初始化能力**: 创建 `GrD3DCaps` 查询硬件能力
4. **创建命令列表**: 通过资源提供者获取首个命令列表
5. **创建围栏**: 初始围栏值为 0,用于 CPU-GPU 同步
6. **调试工具**: 可选地初始化 PIX 图形分析工具

### 命令列表提交机制

`submitDirectCommandList` 实现了完整的命令提交流程:

```cpp
bool GrD3DGpu::submitDirectCommandList(SyncQueue sync) {
    // 1. 准备提交
    fResourceProvider.prepForSubmit();

    // 2. 回收临时描述符
    for (int i = 0; i < fMipmapCPUDescriptors.size(); ++i) {
        fResourceProvider.recycleShaderView(fMipmapCPUDescriptors[i]);
    }

    // 3. 提交命令列表到队列
    GrD3DDirectCommandList::SubmitResult result =
        fCurrentDirectCommandList->submit(fQueue.get());

    // 4. 处理提交结果
    if (result == SubmitResult::kFailure) {
        // 重新创建命令列表
        fCurrentDirectCommandList = fResourceProvider.findOrCreateDirectCommandList();
        return false;
    }

    if (result == SubmitResult::kNoWork) {
        // 没有实际工作,可选同步
        if (sync == SyncQueue::kForce) {
            this->waitForQueueCompletion();
        }
        return true;
    }

    // 5. 标记 uniform 数据为脏(防止跨命令列表复用)
    fResourceProvider.markPipelineStateUniformsDirty();

    // 6. 发送围栏信号
    fQueue->Signal(fFence.get(), ++fCurrentFenceValue);

    // 7. 记录为未完成的命令列表
    new (fOutstandingCommandLists.push_back())
        OutstandingCommandList(std::move(fCurrentDirectCommandList), fCurrentFenceValue);

    // 8. 可选同步等待
    if (sync == SyncQueue::kForce) {
        this->waitForQueueCompletion();
    }

    // 9. 获取新的命令列表
    fCurrentDirectCommandList = fResourceProvider.findOrCreateDirectCommandList();

    // 10. 回收已完成的命令列表
    this->checkForFinishedCommandLists();

    return true;
}
```

### 已完成命令列表的回收

```cpp
void GrD3DGpu::checkForFinishedCommandLists() {
    uint64_t completedValue = fFence->GetCompletedValue();

    // 从最旧的命令列表开始检查
    OutstandingCommandList* front =
        (OutstandingCommandList*)fOutstandingCommandLists.front();

    while (front && front->fFenceValue <= completedValue) {
        // GPU 已完成此命令列表
        std::unique_ptr<GrD3DDirectCommandList> list(std::move(front->fCommandList));

        // 手动调用析构函数(使用了 placement new)
        front->~OutstandingCommandList();
        fOutstandingCommandLists.pop_front();

        // 回收命令列表供后续使用
        fResourceProvider.recycleDirectCommandList(std::move(list));

        front = (OutstandingCommandList*)fOutstandingCommandLists.front();
    }
}
```

利用围栏值的单调递增特性,批量回收已完成的命令列表。

### GPU 同步等待

```cpp
void GrD3DGpu::waitForQueueCompletion() {
    if (fFence->GetCompletedValue() < fCurrentFenceValue) {
        // 创建 Windows 事件对象
        HANDLE fenceEvent = CreateEvent(nullptr, FALSE, FALSE, nullptr);

        // 设置围栏完成回调
        fFence->SetEventOnCompletion(fCurrentFenceValue, fenceEvent);

        // 阻塞等待
        WaitForSingleObject(fenceEvent, INFINITE);

        // 清理事件对象
        CloseHandle(fenceEvent);
    }
}
```

使用 Windows 事件机制实现高效的 CPU-GPU 同步。

### 纹理创建流程

```cpp
sk_sp<GrD3DTexture> GrD3DGpu::createD3DTexture(SkISize dimensions,
                                               DXGI_FORMAT dxgiFormat,
                                               GrRenderable renderable,
                                               int renderTargetSampleCnt,
                                               skgpu::Budgeted budgeted,
                                               GrProtected isProtected,
                                               int mipLevelCount,
                                               GrMipmapStatus mipmapStatus,
                                               std::string_view label) {
    // 1. 配置资源标志
    D3D12_RESOURCE_FLAGS usageFlags = D3D12_RESOURCE_FLAG_NONE;
    if (renderable == GrRenderable::kYes) {
        usageFlags |= D3D12_RESOURCE_FLAG_ALLOW_RENDER_TARGET;
    }

    // 2. 配置资源描述符
    D3D12_RESOURCE_DESC resourceDesc = {};
    resourceDesc.Dimension = D3D12_RESOURCE_DIMENSION_TEXTURE2D;
    resourceDesc.Width = dimensions.fWidth;
    resourceDesc.Height = dimensions.fHeight;
    resourceDesc.DepthOrArraySize = 1;
    resourceDesc.MipLevels = mipLevelCount;
    resourceDesc.Format = dxgiFormat;
    resourceDesc.SampleDesc.Count = 1;  // 解析后的纹理总是单采样
    resourceDesc.Layout = D3D12_TEXTURE_LAYOUT_UNKNOWN;  // 驱动选择布局
    resourceDesc.Flags = usageFlags;

    // 3. 根据可渲染性创建不同类型的纹理
    if (renderable == GrRenderable::kYes) {
        return GrD3DTextureRenderTarget::MakeNewTextureRenderTarget(
            this, budgeted, dimensions, renderTargetSampleCnt,
            resourceDesc, isProtected, mipmapStatus, label);
    } else {
        return GrD3DTexture::MakeNewTexture(
            this, budgeted, dimensions, resourceDesc,
            isProtected, mipmapStatus, label);
    }
}
```

### 表面拷贝实现

```cpp
bool GrD3DGpu::onCopySurface(GrSurface* dst, const SkIRect& dstRect,
                             GrSurface* src, const SkIRect& srcRect,
                             GrSamplerState::Filter filter) {
    // 1. 验证拷贝条件
    if (srcRect.size() != dstRect.size()) return false;
    if (src->isProtected() && !dst->isProtected()) return false;

    // 2. 获取纹理资源(处理 MSAA 情况)
    GrD3DTextureResource* dstTexResource = /* 提取纹理资源 */;
    GrD3DTextureResource* srcTexResource = /* 提取纹理资源 */;

    // 3. 查询格式和采样数
    DXGI_FORMAT dstFormat = dstTexResource->dxgiFormat();
    DXGI_FORMAT srcFormat = srcTexResource->dxgiFormat();
    int dstSampleCnt = get_surface_sample_cnt(dst);
    int srcSampleCnt = get_surface_sample_cnt(src);

    // 4. 选择拷贝方法
    if (this->d3dCaps().canCopyAsResolve(dstFormat, dstSampleCnt,
                                         srcFormat, srcSampleCnt)) {
        // 使用 ResolveSubresource (MSAA 解析)
        this->copySurfaceAsResolve(dst, src, srcRect, dstPoint);
        return true;
    }

    if (this->d3dCaps().canCopyTexture(dstFormat, dstSampleCnt,
                                       srcFormat, srcSampleCnt)) {
        // 使用 CopyTextureRegion (直接拷贝)
        this->copySurfaceAsCopyTexture(dst, src, dstTexResource,
                                       srcTexResource, srcRect, dstPoint);
        return true;
    }

    return false;
}
```

根据格式兼容性和采样数选择最优拷贝路径。

### 压缩纹理上传

对于压缩纹理,使用暂存缓冲区进行数据传输:

1. **计算布局**: 调用 `GetCopyableFootprints` 获取每个 mip 级别的布局信息
2. **分配暂存缓冲区**: 从 `GrStagingBufferManager` 分配足够大小的缓冲区
3. **拷贝数据**: 使用 `SkRectMemcpy` 将压缩数据拷贝到暂存缓冲区,处理行对齐
4. **执行拷贝命令**: 通过 `copyBufferToTexture` 将数据从缓冲区传输到纹理
5. **资源状态转换**: 自动插入必要的资源屏障

### 资源屏障管理

```cpp
void GrD3DGpu::addResourceBarriers(sk_sp<GrManagedResource> resource,
                                   int numBarriers,
                                   D3D12_RESOURCE_TRANSITION_BARRIER* barriers) const {
    fCurrentDirectCommandList->resourceBarrier(resource, numBarriers, barriers);
}
```

所有资源状态转换都通过当前命令列表记录,确保正确的同步。

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrGpu` | 抽象基类,定义 GPU 后端接口 |
| `GrD3DCaps` | D3D12 能力查询,硬件特性检测 |
| `GrD3DResourceProvider` | 资源提供者,管理管线、着色器、描述符 |
| `GrD3DCommandList` | 命令列表封装,记录 GPU 命令 |
| `GrD3DMemoryAllocator` | 内存分配器,管理 GPU 内存 |
| `GrStagingBufferManager` | 暂存缓冲区管理,用于数据上传 |
| `GrRingBuffer` | 环形缓冲区,用于 uniform 数据 |
| `GrD3DTexture` | D3D12 纹理对象 |
| `GrD3DRenderTarget` | D3D12 渲染目标 |
| `GrD3DBuffer` | D3D12 缓冲区对象 |
| `GrD3DOpsRenderPass` | D3D12 渲染通道 |
| `ID3D12Device` | D3D12 设备 COM 接口 |
| `ID3D12CommandQueue` | D3D12 命令队列 COM 接口 |
| `ID3D12Fence` | D3D12 围栏 COM 接口 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrDirectContext` | 通过 `GrDirectContextPriv` 访问 GPU 对象 |
| `GrResourceProvider` | 创建和管理 Ganesh 资源 |
| `GrThreadSafePipelineBuilder` | 线程安全的管线构建(D3D 暂未实现) |
| `GrOpsRenderPass` | 渲染操作记录 |
| `GrSurface/GrTexture/GrRenderTarget` | 表面资源 |

## 设计模式与设计决策

### 工厂模式

使用静态 `Make` 方法:
- 封装复杂的初始化逻辑
- 自动创建默认内存分配器
- 返回基类指针支持多态
- 失败时返回 `nullptr`

### 命令列表池化

通过资源提供者实现命令列表复用:
- 已完成的命令列表被回收而非销毁
- 减少 D3D 对象创建开销
- 使用 `placement new` 优化队列内存管理

### 围栏同步机制

利用 D3D12 围栏实现精确的 CPU-GPU 同步:
- 单调递增的围栏值表示时间线
- 批量回收已完成的命令列表
- Windows 事件对象实现阻塞等待
- 避免轮询,减少 CPU 开销

### 暂存缓冲区策略

使用中间暂存缓冲区进行数据上传:
- CPU 写入快速的 UPLOAD 堆内存
- GPU 通过拷贝命令异步传输到默认堆
- 支持跨命令列表的异步上传
- `GrStagingBufferManager` 自动管理生命周期

### 环形缓冲区用于常量

`fConstantsRingBuffer` 实现高效的 uniform 数据传输:
- 预分配 128KB 环形缓冲区
- 256 字节对齐满足 D3D12 要求
- 避免每帧创建缓冲区的开销
- 老数据被自动覆盖

### 懒加载渲染通道

缓存 `GrD3DOpsRenderPass` 对象:
- 首次使用时创建,后续复用
- 减少内存分配
- 避免虚函数表指针初始化开销

### 描述符临时存储

`fMipmapCPUDescriptors` 存储特殊用途的描述符:
- Mipmap 生成计算着色器的临时视图
- 不通过正常的描述符管理器追踪
- 提交后立即回收

## 性能考量

### 命令列表批处理

延迟提交命令列表直到必要时刻:
- 多个渲染操作记录到同一命令列表
- 减少 GPU 上下文切换
- 降低驱动开销

### 异步 GPU 执行

提交后不立即等待(除非 `SyncQueue::kForce`):
- CPU 继续准备下一帧
- 最大化 CPU-GPU 并行
- 通过围栏值检查完成状态

### 资源状态缓存

D3D12 资源对象缓存当前状态:
- 避免冗余的资源屏障
- 延迟屏障插入直到实际使用
- 批量提交屏障减少 API 调用

### 内存对齐优化

常量缓冲区 256 字节对齐:
- 满足 D3D12 硬件要求
- 避免未对齐访问的性能损失
- 使用 `kConstantAlignment` 常量确保一致性

### 暂存缓冲区复用

`GrStagingBufferManager` 实现缓冲区池化:
- 避免频繁创建/销毁缓冲区
- 减少内存碎片
- 大块分配提高效率

### 对象池化策略

多个子系统采用对象池:
- 命令列表池(通过 `GrD3DResourceProvider`)
- 管线状态缓存
- 描述符堆复用
- 减少 D3D 驱动开销

### 早期剔除

在 `onCopySurface` 等操作中早期检查条件:
- 避免不必要的状态转换
- 减少命令列表记录
- 提前返回失败情况

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpu.h` | 基类 | 定义 GPU 后端抽象接口 |
| `src/gpu/ganesh/d3d/GrD3DCaps.h/cpp` | 能力查询 | 硬件特性检测 |
| `src/gpu/ganesh/d3d/GrD3DResourceProvider.h/cpp` | 资源管理 | 管理管线、着色器、描述符 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h/cpp` | 命令记录 | 封装 D3D12 命令列表 |
| `src/gpu/ganesh/d3d/GrD3DOpsRenderPass.h/cpp` | 渲染通道 | 记录渲染操作 |
| `src/gpu/ganesh/d3d/GrD3DTexture.h/cpp` | 纹理对象 | D3D12 纹理封装 |
| `src/gpu/ganesh/d3d/GrD3DRenderTarget.h/cpp` | 渲染目标 | D3D12 渲染目标封装 |
| `src/gpu/ganesh/d3d/GrD3DBuffer.h/cpp` | 缓冲区 | D3D12 缓冲区封装 |
| `src/gpu/ganesh/d3d/GrD3DMemoryAllocator.h` | 内存分配 | GPU 内存管理接口 |
| `src/gpu/ganesh/d3d/GrD3DAMDMemoryAllocator.h/cpp` | AMD 分配器 | AMD 内存管理实现 |
| `src/gpu/ganesh/d3d/GrD3DSemaphore.h/cpp` | 同步原语 | D3D12 信号量封装 |
| `src/gpu/ganesh/d3d/GrD3DUtil.h` | 工具函数 | D3D12 辅助函数 |
| `src/gpu/ganesh/GrStagingBufferManager.h` | 暂存缓冲区 | 数据上传管理 |
| `include/gpu/ganesh/d3d/GrD3DBackendContext.h` | 上下文 | D3D12 后端初始化参数 |
