# GrD3DDescriptorTableManager

> 源文件
> - src/gpu/ganesh/d3d/GrD3DDescriptorTableManager.h
> - src/gpu/ganesh/d3d/GrD3DDescriptorTableManager.cpp

## 概述

`GrD3DDescriptorTableManager` 是 Skia 图形库中 Ganesh D3D 后端的 GPU 可见描述符表管理器,负责管理着色器可见的描述符堆及其分配。在 Direct3D 12 中,着色器访问资源(如纹理、采样器)必须通过 GPU 可见的描述符堆,该管理器通过堆池化、动态增长和回收机制,高效地为每个绘制调用分配连续的描述符表空间。

该模块由三个核心组件构成:`GrD3DDescriptorTable` 表示一个连续的描述符区域,`Heap` 封装底层的描述符堆及其分配状态,`HeapPool` 管理同类型堆的池并实现动态扩展。通过这种分层设计,系统能够以最小的开销满足频繁的描述符分配需求,同时在命令列表完成后自动回收堆资源,实现高效的内存复用。

## 架构位置

`GrD3DDescriptorTableManager` 在 D3D12 资源管理层次结构中的位置:

```
Skia
└── src/gpu/ganesh/d3d
    ├── GrD3DGpu (D3D GPU 主类)
    │   └── GrD3DResourceProvider (资源提供者)
    │       └── GrD3DDescriptorTableManager (GPU 描述符表管理) ← 核心类
    │           ├── HeapPool (堆池,管理同类型堆)
    │           │   └── Heap (单个描述符堆)
    │           │       └── GrD3DDescriptorHeap (底层堆封装)
    │           └── GrD3DDescriptorTable (描述符表句柄)
    └── GrD3DCommandList (命令列表,持有堆引用)
```

该类专门管理着色器可见堆,与 `GrD3DCpuDescriptorManager`(管理 CPU 可见堆)形成互补。

## 主要类与结构体

### GrD3DDescriptorTable

**继承关系**:
- 继承自: `SkRefCnt` (提供引用计数)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDescriptorTableCpuStart` | `D3D12_CPU_DESCRIPTOR_HANDLE` | CPU 侧的描述符表起始句柄,用于写入描述符 |
| `fDescriptorTableGpuStart` | `D3D12_GPU_DESCRIPTOR_HANDLE` | GPU 侧的描述符表起始句柄,用于绑定到根签名 |
| `fHeap` | `ID3D12DescriptorHeap*` | 所属的底层 D3D12 描述符堆 |
| `fType` | `D3D12_DESCRIPTOR_HEAP_TYPE` | 堆类型(CBV_SRV_UAV 或 SAMPLER) |

**职责**: 表示堆中的连续描述符区域,携带 CPU 和 GPU 句柄,供着色器绑定和描述符拷贝使用。

### GrD3DDescriptorTableManager::Heap

**继承关系**:
- 继承自: `GrRecycledResource` (支持回收机制)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGpu` | `GrD3DGpu*` | GPU 设备指针,用于回调回收 |
| `fHeap` | `std::unique_ptr<GrD3DDescriptorHeap>` | 底层描述符堆对象 |
| `fType` | `D3D12_DESCRIPTOR_HEAP_TYPE` | 堆类型标识 |
| `fDescriptorCount` | `unsigned int` | 堆的总容量(描述符数量) |
| `fNextAvailable` | `unsigned int` | 下一个可分配的描述符索引 |

**职责**: 封装单个描述符堆,维护分配指针,提供线性分配接口,支持重置和回收。

### GrD3DDescriptorTableManager::HeapPool

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fDescriptorHeaps` | `std::vector<sk_sp<Heap>>` | 堆列表,最后一个为当前活跃堆 |
| `fHeapType` | `D3D12_DESCRIPTOR_HEAP_TYPE` | 池管理的堆类型 |
| `fCurrentHeapDescriptorCount` | `unsigned int` | 当前创建堆的容量,动态增长 |

**职责**: 管理同类型的多个堆,实现堆的动态分配、回收和容量增长策略。

### GrD3DDescriptorTableManager

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fShaderViewDescriptorPool` | `HeapPool` | 着色器资源视图池(CBV/SRV/UAV) |
| `fSamplerDescriptorPool` | `HeapPool` | 采样器池(SAMPLER) |

**职责**: 顶层管理器,协调两种类型的描述符堆池。

## 公共 API 函数

### 管理器接口

```cpp
// 构造函数
GrD3DDescriptorTableManager(GrD3DGpu* gpu);

// 创建着色器资源视图表(纹理、常量缓冲区等)
sk_sp<GrD3DDescriptorTable> createShaderViewTable(GrD3DGpu* gpu, unsigned int count);

// 创建采样器表
sk_sp<GrD3DDescriptorTable> createSamplerTable(GrD3DGpu* gpu, unsigned int count);

// 提交前准备:清理当前堆,准备下一帧
void prepForSubmit(GrD3DGpu* gpu);
```

### 描述符表接口

```cpp
// 获取 CPU 句柄指针(用于描述符拷贝)
const D3D12_CPU_DESCRIPTOR_HANDLE* baseCpuDescriptorPtr();

// 获取 GPU 句柄(用于根签名绑定)
const D3D12_GPU_DESCRIPTOR_HANDLE baseGpuDescriptor();

// 访问底层堆和类型
ID3D12DescriptorHeap* heap() const;
D3D12_DESCRIPTOR_HEAP_TYPE type() const;
```

### Heap 接口

```cpp
// 创建堆
static sk_sp<Heap> Make(GrD3DGpu* gpu,
                        D3D12_DESCRIPTOR_HEAP_TYPE type,
                        unsigned int numDescriptors);

// 从堆中分配描述符表
sk_sp<GrD3DDescriptorTable> allocateTable(unsigned int count);

// 检查是否可以分配指定数量的描述符
bool canAllocate(unsigned int count) const;

// 重置分配指针(回收时调用)
void reset();

// 检查堆是否已被使用
bool used();
```

### HeapPool 接口

```cpp
// 从池中分配描述符表(自动管理堆)
sk_sp<GrD3DDescriptorTable> allocateTable(GrD3DGpu* gpu, unsigned int count);

// 回收堆到池中
void recycle(sk_sp<Heap> heap);

// 提交前准备
void prepForSubmit(GrD3DGpu* gpu);
```

## 内部实现细节

### 描述符表分配流程

`createShaderViewTable` 和 `createSamplerTable` 的实现非常简洁,直接委托给对应的池:

```cpp
sk_sp<GrD3DDescriptorTable>
GrD3DDescriptorTableManager::createShaderViewTable(GrD3DGpu* gpu, unsigned int size) {
    return fShaderViewDescriptorPool.allocateTable(gpu, size);
}
```

核心逻辑在 `HeapPool::allocateTable` 中:

```cpp
sk_sp<GrD3DDescriptorTable> HeapPool::allocateTable(GrD3DGpu* gpu, unsigned int count) {
    // 1. 从后向前遍历堆列表,寻找有足够空间的堆
    while (fDescriptorHeaps.size() > 0) {
        auto& heap = fDescriptorHeaps[fDescriptorHeaps.size() - 1];

        if (heap->canAllocate(count)) {
            // 2. 首次使用堆时,添加到命令列表的回收列表
            if (!heap->used()) {
                gpu->currentCommandList()->addRecycledResource(heap);
            }
            // 3. 从堆中分配
            return heap->allocateTable(count);
        }

        // 4. 当前堆空间不足,弹出(等待回收)
        fDescriptorHeaps.pop_back();
    }

    // 5. 所有堆都已满,创建新堆(容量倍增,最大 2048)
    fCurrentHeapDescriptorCount = std::min(2 * fCurrentHeapDescriptorCount, 2048u);
    sk_sp<Heap> heap = Heap::Make(gpu, fHeapType, fCurrentHeapDescriptorCount);

    // 6. 添加到命令列表回收列表和池列表
    gpu->currentCommandList()->addRecycledResource(heap);
    fDescriptorHeaps.push_back(heap);

    // 7. 从新堆分配
    return fDescriptorHeaps[fDescriptorHeaps.size() - 1]->allocateTable(count);
}
```

关键设计点:
- **线性分配**: 每个堆维护 `fNextAvailable` 指针,分配时直接递增
- **延迟添加**: 只有实际使用的堆才添加到命令列表的资源追踪
- **容量增长**: 初始 256 个描述符,不足时倍增至最大 2048

### 堆内分配实现

`Heap::allocateTable` 执行简单的指针递增分配:

```cpp
sk_sp<GrD3DDescriptorTable> Heap::allocateTable(unsigned int count) {
    SkASSERT(fDescriptorCount - fNextAvailable >= count);

    // 1. 记录起始索引
    unsigned int startIndex = fNextAvailable;

    // 2. 递增分配指针
    fNextAvailable += count;

    // 3. 创建描述符表对象,携带 CPU/GPU 句柄
    return sk_sp<GrD3DDescriptorTable>(
        new GrD3DDescriptorTable(
            fHeap->getCPUHandle(startIndex).fHandle,  // CPU 句柄
            fHeap->getGPUHandle(startIndex).fHandle,  // GPU 句柄
            fHeap->descriptorHeap(),                   // 堆指针
            fType                                      // 类型
        )
    );
}
```

这是一个典型的 bump allocator(碰撞分配器),O(1) 时间复杂度,无碎片。

### 堆回收机制

`Heap` 继承自 `GrRecycledResource`,实现 `onRecycle` 回调:

```cpp
void Heap::onRecycle() const {
    // 通过 GPU 的资源提供者回调到管理器
    fGpu->resourceProvider().descriptorTableMgr()->recycle(const_cast<Heap*>(this));
}
```

管理器根据堆类型路由到对应的池:

```cpp
void GrD3DDescriptorTableManager::recycle(Heap* heap) {
    sk_sp<Heap> wrappedHeap(heap);  // 接管所有权

    switch (heap->type()) {
        case D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV:
            fShaderViewDescriptorPool.recycle(std::move(wrappedHeap));
            break;
        case D3D12_DESCRIPTOR_HEAP_TYPE_SAMPLER:
            fSamplerDescriptorPool.recycle(std::move(wrappedHeap));
            break;
    }
}
```

`HeapPool::recycle` 执行实际回收:

```cpp
void HeapPool::recycle(sk_sp<Heap> heap) {
    // 只回收与当前容量匹配的堆(淘汰旧容量的堆)
    if (heap->descriptorCount() == fCurrentHeapDescriptorCount) {
        heap->reset();  // 重置分配指针为 0
        fDescriptorHeaps.push_back(heap);
    }
    // 不匹配的堆被丢弃,引用计数归零后自动销毁
}
```

### 提交前准备

`prepForSubmit` 在命令列表提交前调用,清理当前帧状态:

```cpp
void HeapPool::prepForSubmit(GrD3DGpu* gpu) {
    // 1. 如果当前堆已使用,弹出(等待回收)
    if (fDescriptorHeaps[fDescriptorHeaps.size() - 1]->used()) {
        fDescriptorHeaps.pop_back();
    }

    // 2. 如果池为空,创建新堆供下一帧使用
    if (fDescriptorHeaps.size() == 0) {
        fCurrentHeapDescriptorCount = std::min(fCurrentHeapDescriptorCount, 2048u);
        sk_sp<Heap> heap = Heap::Make(gpu, fHeapType, fCurrentHeapDescriptorCount);
        fDescriptorHeaps.push_back(heap);
    }
}
```

确保下一帧开始时有可用的堆。

### 堆创建流程

`Heap::Make` 封装堆创建:

```cpp
sk_sp<Heap> Heap::Make(GrD3DGpu* gpu,
                       D3D12_DESCRIPTOR_HEAP_TYPE type,
                       unsigned int descriptorCount) {
    // 1. 创建底层的 GPU 可见堆
    std::unique_ptr<GrD3DDescriptorHeap> heap =
        GrD3DDescriptorHeap::Make(gpu, type, descriptorCount,
                                  D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE);
    if (!heap) return nullptr;

    // 2. 封装为 Heap 对象
    return sk_sp<Heap>(new Heap(gpu, heap, type, descriptorCount));
}
```

关键是设置 `SHADER_VISIBLE` 标志,使堆对 GPU 可见。

### 容量增长策略

初始容量 256,每次不足时倍增,上限 2048:

```cpp
inline static constexpr int kInitialHeapDescriptorCount = 256;

// 增长公式
fCurrentHeapDescriptorCount = std::min(2 * fCurrentHeapDescriptorCount, 2048u);
```

这种策略在以下场景平衡:
- 小型应用: 避免过度分配
- 大型应用: 快速达到合理容量
- 上限保护: 防止单个堆过大导致内存浪费

### 堆生命周期

1. **创建**: `HeapPool` 按需创建新堆
2. **添加到命令列表**: 首次使用时通过 `addRecycledResource` 关联
3. **命令列表提交**: 堆随命令列表提交到 GPU
4. **GPU 完成**: 命令列表完成后触发 `onRecycle` 回调
5. **回收**: 堆被重置并返回池中
6. **复用**: 后续帧可以重新使用该堆

## 依赖关系

### 依赖的模块

| 模块 | 说明 |
|------|------|
| `GrD3DDescriptorHeap` | 底层描述符堆封装 |
| `GrRecycledResource` | 提供资源回收框架 |
| `SkRefCnt` | 引用计数基类 |
| `GrD3DGpu` | GPU 设备接口 |
| `GrD3DCommandList` | 命令列表,持有堆引用 |
| `ID3D12DescriptorHeap` | D3D12 描述符堆 COM 接口 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| `GrD3DResourceProvider` | 通过 `descriptorTableMgr()` 访问管理器 |
| `GrD3DPipelineState` | 绑定描述符表到根签名 |
| `GrD3DOpsRenderPass` | 渲染过程中分配描述符表 |
| `GrD3DCommandList` | 追踪使用的堆,确保生命周期 |

## 设计模式与设计决策

### 三层架构

- **顶层(Manager)**: 协调不同类型的池
- **中层(HeapPool)**: 管理同类型堆的池化和增长
- **底层(Heap)**: 封装单个堆的线性分配

分层设计使各层职责清晰,便于维护和扩展。

### Bump Allocator 模式

堆内使用简单的指针递增分配:
- **优点**: O(1) 分配,无碎片,代码简单
- **限制**: 无法释放单个分配,必须整体重置
- **适用性**: 描述符表生命周期与命令列表一致,满足使用场景

### 对象池化

通过回收已完成的堆避免重复创建:
- 减少 D3D API 调用开销
- 降低内存分配压力
- 提高帧间性能一致性

### 容量淘汰策略

只回收与当前容量匹配的堆:
- **自适应**: 容量增长后自动淘汰小堆
- **防碎片**: 避免池中存在多种尺寸的堆
- **简化逻辑**: 不需要复杂的堆选择算法

### 延迟绑定

只在堆首次使用时添加到命令列表:
- 避免追踪空堆
- 减少命令列表的资源依赖
- 优化回收列表的大小

### GrRecycledResource 集成

利用 Ganesh 的资源回收框架:
- 自动处理引用计数
- 统一的回收接口
- 与命令列表生命周期自动同步

## 性能考量

### 线性分配性能

Bump allocator 提供最快的分配速度:
- 无需查找空闲块
- 无需维护复杂数据结构
- CPU 缓存友好(顺序访问)

### 容量预测

倍增策略快速适应负载:
- 初始 256 适合小场景
- 几次倍增后达到 2048,覆盖大多数应用
- 上限保护防止内存浪费

### 堆复用率

回收机制最大化堆复用:
- 稳定负载下,池达到稳态,无新分配
- GPU 完成时机与回收时机良好匹配
- 避免每帧创建/销毁堆的开销

### 内存开销

- **描述符大小**: CBV/SRV/UAV 通常 32 字节,SAMPLER 通常 16 字节
- **单堆开销**: 2048 × 32 = 64KB (CBV/SRV/UAV) 或 32KB (SAMPLER)
- **池开销**: 通常 1-3 个堆活跃,总开销可控

### 命令列表关联

通过 `addRecycledResource` 自动管理生命周期:
- 堆在命令列表完成前不会被销毁
- 无需手动追踪依赖关系
- 防止 use-after-free 错误

### 批量回收

命令列表完成时批量回收所有关联堆:
- 减少回收调用次数
- 利用 GPU 完成的自然批处理点
- 降低同步开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/d3d/GrD3DDescriptorHeap.h/cpp` | 依赖 | 底层描述符堆封装 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h/cpp` | 使用者 | GPU 设备接口 |
| `src/gpu/ganesh/d3d/GrD3DResourceProvider.h/cpp` | 拥有者 | 资源提供者持有管理器实例 |
| `src/gpu/ganesh/d3d/GrD3DCommandList.h/cpp` | 协作 | 追踪堆生命周期 |
| `src/gpu/ganesh/d3d/GrD3DPipelineState.h/cpp` | 使用者 | 绑定描述符表到根签名 |
| `src/gpu/ganesh/d3d/GrD3DOpsRenderPass.h/cpp` | 使用者 | 渲染过程中分配描述符表 |
| `src/gpu/ganesh/GrRecycledResource.h` | 基类 | 提供资源回收框架 |
| `include/private/base/SkRefCnt.h` | 基类 | 引用计数支持 |
