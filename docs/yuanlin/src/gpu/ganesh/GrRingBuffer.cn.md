# GrRingBuffer

> 源文件
> - src/gpu/ganesh/GrRingBuffer.h
> - src/gpu/ganesh/GrRingBuffer.cpp

## 概述

`GrRingBuffer` 是一个环形缓冲区包装器,用于管理 GPU 缓冲区的子分配。它采用连续环形分配策略,支持在单个大缓冲区中分配多个小的切片(slice),避免频繁创建和销毁小缓冲区。该类特别适用于动态缓冲区场景,如顶点缓冲、索引缓冲和 uniform 缓冲。设计上考虑了多线程环境,允许分配和提交在不同线程执行。

## 架构位置

在 Skia GPU 架构中的位置:

```
GrGpu
    └── 动态缓冲区管理
        └── GrRingBuffer
            ├── 子分配管理
            ├── 缓冲区增长策略
            └── 提交时同步
```

`GrRingBuffer` 是 GPU 缓冲区管理的基础设施,被各种绘制操作用于分配临时缓冲区空间。

## 主要类与结构体

### 核心类

| 类名 | 继承关系 | 作用 |
|------|---------|------|
| `GrRingBuffer` | 无 | 环形缓冲区管理器 |

### GrRingBuffer 关键成员变量

| 成员变量 | 类型 | 作用 |
|---------|------|------|
| `fGpu` | `GrGpu*` | GPU 接口指针 |
| `fCurrentBuffer` | `sk_sp<GrGpuBuffer>` | 当前使用的缓冲区 |
| `fPreviousBuffers` | `std::vector<sk_sp<GrGpuBuffer>>` | 当前提交中的旧缓冲区 |
| `fTotalSize` | `size_t` | 缓冲区总大小(2 的幂次) |
| `fAlignment` | `size_t` | 分配对齐要求 |
| `fType` | `GrGpuBufferType` | 缓冲区类型(顶点/索引/uniform) |
| `fHead` | `size_t` | 分配头指针(无界递增) |
| `fTail` | `size_t` | 回收尾指针(在完成回调中更新) |
| `fGenID` | `uint64_t` | 缓冲区世代 ID |
| `fNewAllocation` | `bool` | 本次提交是否有新分配 |

### 辅助结构

```cpp
struct Slice {
    GrGpuBuffer* fBuffer;  // 缓冲区指针
    size_t fOffset;        // 在缓冲区中的偏移
};

struct SubmitData {
    GrRingBuffer* fOwner;  // 拥有者指针
    size_t fLastHead;      // 提交时的头位置
    size_t fGenID;         // 提交时的世代 ID
};
```

## 公共 API 函数

### 构造函数

```cpp
GrRingBuffer(GrGpu* gpu, size_t size, size_t alignment,
             GrGpuBufferType intendedType);
```

**参数**:
- `gpu`: GPU 接口
- `size`: 初始大小(必须是 2 的幂次)
- `alignment`: 分配对齐要求
- `intendedType`: 缓冲区类型

### 分配函数

```cpp
Slice suballocate(size_t size);
```

在环形缓冲区中分配指定大小的切片:
- 返回缓冲区和偏移量
- 如果空间不足,自动增长缓冲区
- 对齐到指定的边界

### 提交管理

```cpp
void startSubmit(GrGpu* gpu);
```

在命令缓冲区提交时调用:
- 取消旧缓冲区的映射
- 转移旧缓冲区的所有权给 GPU
- 注册完成回调以更新 `fTail`

### 查询函数

```cpp
size_t size() const;  // 返回当前缓冲区大小
```

## 内部实现细节

### 环形分配算法

```cpp
size_t getAllocationOffset(size_t size)
```

该函数实现了环形缓冲区的核心分配逻辑:

**关键思想**:
- `fHead` 和 `fTail` 无界递增,通过溢出自然环绕
- 使用 `& (fTotalSize - 1)` 将无界索引映射到实际偏移
- 通过比较取模后的值判断缓冲区是否已满

**分配策略**:

1. **计算实际偏移**:
```cpp
size_t modHead = head & (fTotalSize - 1);
size_t modTail = tail & (fTotalSize - 1);
```

2. **判断缓冲区状态**:
```cpp
bool full = (head != tail && modHead == modTail);
```

3. **空间分配**:
   - **情况 1**: 自由空间在末尾和/或开头
     - 如果末尾空间不足,尝试从开头分配
     - 需要调整 `head` 跳过末尾碎片
   - **情况 2**: 自由空间在中间
     - 检查中间是否有足够空间
   - 如果都不满足,返回 `fTotalSize` 表示失败

4. **对齐处理**:
```cpp
fHead = SkAlignTo(head + size, fAlignment);
```

### 缓冲区增长策略

在 `suballocate` 中,如果当前缓冲区空间不足:

```cpp
if (offset < fTotalSize) {
    return { fCurrentBuffer.get(), offset };
}

// 空间不足,增长缓冲区
fTotalSize *= 2;  // 倍增策略
fPreviousBuffers.push_back(std::move(fCurrentBuffer));
fCurrentBuffer = resourceProvider->createBuffer(fTotalSize, ...);
fHead = 0;
fTail = 0;
fGenID++;
```

**增长特点**:
- 采用倍增策略(2x)
- 旧缓冲区移入 `fPreviousBuffers`,等待 GPU 完成使用
- 重置头尾指针,从新缓冲区开始分配
- 递增世代 ID 以区分不同缓冲区

### 同步机制

`GrRingBuffer` 通过回调机制实现跨线程同步:

**提交时** (`startSubmit`):
```cpp
void startSubmit(GrGpu* gpu) {
    // 转移旧缓冲区所有权
    for (auto& buffer : fPreviousBuffers) {
        buffer->unmap();
        gpu->takeOwnershipOfBuffer(std::move(buffer));
    }
    fPreviousBuffers.clear();

    // 注册完成回调
    if (fNewAllocation) {
        SubmitData* submitData = new SubmitData();
        submitData->fOwner = this;
        submitData->fLastHead = fHead;
        submitData->fGenID = fGenID;
        gpu->addFinishedCallback(skgpu::AutoCallback(FinishSubmit, submitData));
        fNewAllocation = false;
    }
}
```

**完成时** (`FinishSubmit`):
```cpp
static void FinishSubmit(void* finishedContext) {
    SubmitData* submitData = (SubmitData*)finishedContext;
    if (submitData && submitData->fOwner &&
        submitData->fGenID == submitData->fOwner->fGenID) {
        // 更新尾指针,释放已使用的空间
        submitData->fOwner->fTail = submitData->fLastHead;
        submitData->fOwner = nullptr;
    }
    delete submitData;
}
```

**世代 ID 的作用**:
- 如果缓冲区已被替换(fGenID 改变),忽略旧的回调
- 避免对已销毁或替换的缓冲区进行操作

### 平台特定处理

**macOS 特殊处理**:
```cpp
#ifdef SK_BUILD_FOR_MAC
    fCurrentBuffer->unmap();  // Managed buffer 需要 unmap 以写回 GPU
#endif
```

这是因为 macOS 上使用 Managed 模式的缓冲区,需要显式 unmap 才能将数据传输到 GPU。

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGpu` | GPU 接口,创建缓冲区和注册回调 |
| `GrGpuBuffer` | 底层 GPU 缓冲区 |
| `GrResourceProvider` | 创建新缓冲区 |
| `GrDirectContext` | 访问资源提供者 |
| `skgpu::AutoCallback` | 完成回调机制 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| Vulkan/Metal/D3D 后端 | 使用环形缓冲区管理动态资源 |
| 绘制操作 | 分配临时顶点/索引/uniform 缓冲区 |

## 设计模式与设计决策

### 设计模式

1. **环形缓冲区模式**:
   - 经典的无界索引环形队列
   - 通过取模映射到有界空间

2. **对象池模式**:
   - 复用大缓冲区而非频繁创建小缓冲区
   - 减少分配和释放开销

3. **回调模式**:
   - 使用回调实现异步空间回收
   - 解耦提交和完成逻辑

4. **倍增增长策略**:
   - 类似 `std::vector` 的增长策略
   - 平摊分配成本

### 关键设计决策

**为何使用无界索引**:
```cpp
// 使用无界递增而非取模递增
fHead++;  // 而非 fHead = (fHead + 1) % fTotalSize
```
优点:
- 溢出自动环绕,无需显式取模
- 判断"满"状态更简单
- 避免头尾指针二义性(相等时是空还是满)

**为何要求大小是 2 的幂次**:
```cpp
SkASSERT(SkIsPow2(size));
```
原因:
- 使用位运算 `& (size - 1)` 代替取模,性能更好
- 简化对齐计算

**为何有 fPreviousBuffers**:
- 缓冲区增长时,旧缓冲区可能仍在被 GPU 使用
- 必须等待 GPU 完成后才能释放
- 通过 `takeOwnershipOfBuffer` 转移所有权给 GPU

**世代 ID 的必要性**:
- 完成回调可能在缓冲区已被替换后才触发
- 使用世代 ID 避免更新错误的缓冲区

## 性能考量

### 时间复杂度

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| `suballocate` | O(1) 均摊 | 通常是 O(1),增长时是 O(1) |
| `getAllocationOffset` | O(1) | 简单的算术运算 |
| `startSubmit` | O(k) | k 是旧缓冲区数量,通常很小 |

### 空间效率

**优点**:
- 避免每次分配都创建新缓冲区
- 减少内存碎片
- 提高缓冲区复用率

**缺点**:
- 可能分配大于实际需求的空间
- 增长策略可能导致短期内存峰值

### 性能优化

**对齐优化**:
```cpp
fHead = SkAlignTo(head + size, fAlignment);
```
确保分配地址满足 GPU 对齐要求,避免性能损失。

**批量释放**:
```cpp
for (auto& buffer : fPreviousBuffers) {
    gpu->takeOwnershipOfBuffer(std::move(buffer));
}
```
一次性处理所有旧缓冲区,减少调用开销。

**早期返回**:
```cpp
if (offset < fTotalSize) {
    return { fCurrentBuffer.get(), offset };
}
```
快速路径处理常见情况。

### 性能权衡

**大小 vs 复用率**:
- 大缓冲区提高复用率,但可能浪费空间
- 小缓冲区减少浪费,但增加创建频率
- 动态增长策略在两者间取得平衡

**同步开销**:
- 使用回调机制有一定开销
- 但避免了阻塞等待和锁竞争
- 总体上异步模型性能更好

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrGpuBuffer.h` | 依赖 | 底层缓冲区类型 |
| `src/gpu/ganesh/GrGpu.h` | 依赖 | GPU 接口 |
| `src/gpu/ganesh/GrResourceProvider.h` | 依赖 | 创建缓冲区 |
| `src/gpu/RefCntedCallback.h` | 依赖 | 回调机制 |
| `src/gpu/ganesh/vk/GrVkGpu.cpp` | 使用者 | Vulkan 后端使用 |
| `src/gpu/ganesh/mtl/GrMtlGpu.mm` | 使用者 | Metal 后端使用 |
| `src/gpu/ganesh/d3d/GrD3DGpu.cpp` | 使用者 | D3D 后端使用 |
