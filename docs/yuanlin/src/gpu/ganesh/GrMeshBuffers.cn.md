# GrMeshBuffers

> 源文件
> - src/gpu/ganesh/GrMeshBuffers.h
> - src/gpu/ganesh/GrMeshBuffers.cpp

## 概述

`GrMeshBuffers` 提供了 Ganesh GPU 后端中用于 `SkMesh` 的索引缓冲区和顶点缓冲区的 GPU 实现。它通过模板类 `GrMeshBuffer` 封装 `GrGpuBuffer`，为 Skia 的 Mesh API 提供 GPU 加速支持。该模块实现了 `SkMesh::IndexBuffer` 和 `SkMesh::VertexBuffer` 的 Ganesh 后端版本，支持缓冲区的创建、更新和生命周期管理，同时处理跨线程资源释放等复杂场景。

## 架构位置

`GrMeshBuffers` 位于 Skia Mesh API 和 Ganesh GPU 后端之间的适配层：

```
SkMesh (公共 API)
    ├── SkMesh::IndexBuffer (抽象接口)
    └── SkMesh::VertexBuffer (抽象接口)
        │
        └── GrMeshBuffer<Base, Type> (Ganesh 实现)
            ├── SkMeshPriv::GaneshIndexBuffer
            └── SkMeshPriv::GaneshVertexBuffer
                │
                └── GrGpuBuffer (GPU 缓冲区)
                    └── GrResourceCache (资源管理)
```

该模块通过 `SkMeshes` 命名空间的工厂函数暴露给外部，同时处理 CPU fallback 和 GPU 实现的选择。

## 主要类与结构体

### GrMeshBuffer<Base, GrGpuBufferType>

模板类，为特定类型的缓冲区提供 Ganesh 后端实现。

**模板参数**
- `Base`：基类类型（`SkMeshPriv::IB` 或 `SkMeshPriv::VB`）
- `GrGpuBufferType`：GPU 缓冲区类型（`kIndex` 或 `kVertex`）

**继承关系**
- 基类：`Base`（`SkMeshPriv::IB` 或 `SkMeshPriv::VB`）
- 子类：无

**关键成员变量**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fBuffer` | `sk_sp<GrGpuBuffer>` | 底层 GPU 缓冲区 |
| `fContextID` | `GrDirectContext::DirectContextID` | 创建该缓冲区的上下文 ID |

### 类型别名

```cpp
namespace SkMeshPriv {
using GaneshIndexBuffer  = GrMeshBuffer<SkMeshPriv::IB, GrGpuBufferType::kIndex>;
using GaneshVertexBuffer = GrMeshBuffer<SkMeshPriv::VB, GrGpuBufferType::kVertex>;
}
```

## 公共 API 函数

### GrMeshBuffer 成员函数

| 函数签名 | 说明 |
|----------|------|
| `GrMeshBuffer()` | 默认构造函数 |
| `~GrMeshBuffer()` | 析构函数，跨线程安全地释放 GPU 资源 |
| `static sk_sp<Base> Make(GrDirectContext*, const void*, size_t)` | 创建缓冲区，可选初始数据 |
| `size_t size() const override` | 返回缓冲区大小 |
| `bool isGaneshBacked() const override` | 返回 true，表示由 Ganesh 支持 |
| `sk_sp<const GrGpuBuffer> asGpuBuffer() const` | 获取底层 GPU 缓冲区 |
| `bool onUpdate(GrDirectContext*, const void*, size_t, size_t) override` | 更新缓冲区内容 |

### SkMeshes 命名空间工厂函数

| 函数签名 | 说明 |
|----------|------|
| `sk_sp<SkMesh::IndexBuffer> MakeIndexBuffer(GrDirectContext*, const void*, size_t)` | 创建索引缓冲区，nullptr 时回退到 CPU |
| `sk_sp<SkMesh::IndexBuffer> CopyIndexBuffer(GrDirectContext*, sk_sp<SkMesh::IndexBuffer>)` | 复制索引缓冲区 |
| `sk_sp<SkMesh::VertexBuffer> MakeVertexBuffer(GrDirectContext*, const void*, size_t)` | 创建顶点缓冲区，nullptr 时回退到 CPU |
| `sk_sp<SkMesh::VertexBuffer> CopyVertexBuffer(GrDirectContext*, sk_sp<SkMesh::VertexBuffer>)` | 复制顶点缓冲区 |

## 内部实现细节

### 缓冲区创建逻辑

`Make` 方法实现了缓冲区的创建流程：

```cpp
template <typename Base, GrGpuBufferType Type>
sk_sp<Base> GrMeshBuffer<Base, Type>::Make(GrDirectContext* dc,
                                            const void* data,
                                            size_t size) {
    SkASSERT(dc);

    // 创建 GPU 缓冲区
    sk_sp<GrGpuBuffer> buffer = dc->priv().resourceProvider()->createBuffer(
            size,
            Type,
            kStatic_GrAccessPattern,  // 静态访问模式
            data ? GrResourceProvider::ZeroInit::kNo
                 : GrResourceProvider::ZeroInit::kYes);
    if (!buffer) {
        return nullptr;
    }

    // 如果有初始数据，上传
    if (data && !buffer->updateData(data, 0, size, /*preserve=*/false)) {
        return nullptr;
    }

    // 创建包装对象
    auto result = new GrMeshBuffer;
    result->fBuffer = std::move(buffer);
    result->fContextID = dc->directContextID();
    return sk_sp<Base>(result);
}
```

关键特性：
- 使用 `kStatic_GrAccessPattern`，表示缓冲区内容不常变化
- 无初始数据时自动零初始化
- 记录创建时的上下文 ID，用于跨线程资源释放

### 缓冲区更新逻辑

`onUpdate` 方法支持两种更新路径：

#### 路径 1：直接更新（不支持 buffer-to-buffer 传输）

```cpp
if (!dc->priv().caps()->transferFromBufferToBufferSupport()) {
    auto ownedData = SkData::MakeWithCopy(data, size);
    dc->priv().drawingManager()->newBufferUpdateTask(
            std::move(ownedData), fBuffer, offset);
    return true;
}
```

- 复制数据到 `SkData`
- 通过绘图管理器创建缓冲区更新任务
- 数据在适当时机上传

#### 路径 2：暂存缓冲区传输（支持 buffer-to-buffer）

```cpp
// 首先尝试从暂存缓冲区管理器分配
sk_sp<GrGpuBuffer> tempBuffer;
size_t tempOffset = 0;
if (auto* sbm = dc->priv().getGpu()->stagingBufferManager()) {
    auto alignment = dc->priv().caps()->transferFromBufferToBufferAlignment();
    auto [sliceBuffer, sliceOffset, ptr] = sbm->allocateStagingBufferSlice(size, alignment);
    if (sliceBuffer) {
        std::memcpy(ptr, data, size);
        tempBuffer.reset(SkRef(sliceBuffer));
        tempOffset = sliceOffset;
    }
}

// 如果暂存缓冲区不可用，创建临时缓冲区
if (!tempBuffer) {
    tempBuffer = dc->priv().resourceProvider()->createBuffer(
            size,
            GrGpuBufferType::kXferCpuToGpu,
            kDynamic_GrAccessPattern,
            GrResourceProvider::ZeroInit::kNo);
    if (!tempBuffer->updateData(data, 0, size, /*preserve=*/false)) {
        return false;
    }
}

// 创建 buffer-to-buffer 传输任务
dc->priv().drawingManager()->newBufferTransferTask(
        std::move(tempBuffer), tempOffset, fBuffer, offset, size);
```

优点：
- 利用暂存缓冲区避免额外分配
- GPU 端的 buffer-to-buffer 复制更高效
- 尊重硬件对齐要求

### 跨线程资源释放

析构函数实现了安全的跨线程资源释放：

```cpp
template <typename Base, GrGpuBufferType Type>
GrMeshBuffer<Base, Type>::~GrMeshBuffer() {
    GrResourceCache::ReturnResourceFromThread(std::move(fBuffer), fContextID);
}
```

`ReturnResourceFromThread` 确保：
- 如果在创建线程上析构，直接释放
- 如果在其他线程上析构，将资源推送回原上下文的消息队列
- 避免跨线程访问 GPU 资源的竞争条件

### 工厂函数与 Fallback

工厂函数智能处理 GPU 不可用的情况：

```cpp
sk_sp<SkMesh::IndexBuffer> MakeIndexBuffer(GrDirectContext* dc,
                                           const void* data,
                                           size_t size) {
    if (!dc) {
        // Fallback to a CPU buffer.
        return MakeIndexBuffer(data, size);  // 调用 CPU 版本
    }
    return SkMeshPriv::GaneshIndexBuffer::Make(dc, data, size);
}
```

这种设计允许 API 在没有 GPU 上下文时优雅降级到 CPU 实现。

### 缓冲区复制

复制函数通过 `peek()` 方法获取源缓冲区的 CPU 映射：

```cpp
sk_sp<SkMesh::IndexBuffer> CopyIndexBuffer(GrDirectContext* dc,
                                           sk_sp<SkMesh::IndexBuffer> src) {
    if (!src) {
        return nullptr;
    }
    auto* ib = static_cast<SkMeshPriv::IB*>(src.get());
    const void* data = ib->peek();
    if (!data) {
        return nullptr;  // 无法访问数据
    }
    if (!dc) {
        return MakeIndexBuffer(data, ib->size());
    }
    return MakeIndexBuffer(dc, data, ib->size());
}
```

注意：如果源缓冲区无法提供 CPU 访问（例如纯 GPU 缓冲区），复制会失败。

## 依赖关系

### 依赖的模块

| 模块名 | 用途 |
|--------|------|
| `GrGpuBuffer` | 底层 GPU 缓冲区实现 |
| `GrDirectContext` | GPU 上下文管理 |
| `GrResourceProvider` | 资源创建 |
| `GrResourceCache` | 资源缓存和跨线程释放 |
| `GrDrawingManager` | 缓冲区更新任务管理 |
| `GrStagingBufferManager` | 暂存缓冲区管理 |
| `GrCaps` | GPU 能力查询 |
| `SkMeshPriv` | Mesh 私有类型定义 |
| `SkData` | 数据封装 |

### 被依赖的模块

| 模块名 | 使用方式 |
|--------|----------|
| `SkMesh` | 通过工厂函数创建 Ganesh 后端的缓冲区 |
| 绘制代码 | 渲染使用 Mesh 的场景 |
| 测试代码 | 测试 Mesh 功能 |

## 设计模式与设计决策

### 模板策略模式（Template Strategy Pattern）

使用模板类 `GrMeshBuffer<Base, Type>` 为索引和顶点缓冲区提供统一实现，通过模板参数区分类型：

```cpp
template <typename Base, GrGpuBufferType> class GrMeshBuffer final : public Base { ... }
```

优点：
- 代码重用，避免重复
- 类型安全，编译时确定
- 零运行时开销

### 桥接模式（Bridge Pattern）

`GrMeshBuffer` 作为 Skia 公共 API（`SkMesh::IndexBuffer/VertexBuffer`）和 Ganesh 内部实现（`GrGpuBuffer`）之间的桥梁。

### 工厂方法模式（Factory Method Pattern）

通过 `SkMeshes` 命名空间的工厂函数创建缓冲区，隐藏具体实现类型：

```cpp
namespace SkMeshes {
sk_sp<SkMesh::IndexBuffer> MakeIndexBuffer(GrDirectContext*, const void*, size_t);
sk_sp<SkMesh::VertexBuffer> MakeVertexBuffer(GrDirectContext*, const void*, size_t);
}
```

### 资源获取即初始化（RAII）

使用智能指针 `sk_sp<GrGpuBuffer>` 管理 GPU 资源生命周期，确保资源正确释放。

### 上下文 ID 跟踪

记录 `fContextID` 支持安全的跨线程资源释放：

```cpp
GrDirectContext::DirectContextID fContextID;
```

这是 Skia 处理多线程 GPU 资源的关键设计，确保资源返回到正确的上下文。

### 延迟任务执行

缓冲区更新不是立即执行，而是创建任务提交给绘图管理器：

```cpp
dc->priv().drawingManager()->newBufferUpdateTask(...);
dc->priv().drawingManager()->newBufferTransferTask(...);
```

这允许：
- 批处理多个更新
- 与绘制操作正确排序
- 在刷新时统一执行

### 自适应传输策略

根据 GPU 能力选择最优的缓冲区更新路径：
- 支持 buffer-to-buffer：使用暂存缓冲区和 GPU 复制
- 不支持：使用直接上传任务

### Fallback 机制

当 GPU 上下文不可用时，自动降级到 CPU 实现：

```cpp
if (!dc) {
    return MakeIndexBuffer(data, size);  // CPU 版本
}
```

## 性能考量

### 静态访问模式

缓冲区创建时使用 `kStatic_GrAccessPattern`：

```cpp
kStatic_GrAccessPattern
```

这告诉驱动程序缓冲区不会频繁更新，允许：
- 将缓冲区放置在 GPU 本地内存
- 优化内存布局
- 减少同步开销

### 暂存缓冲区优化

优先使用暂存缓冲区管理器：

```cpp
if (auto* sbm = dc->priv().getGpu()->stagingBufferManager()) {
    auto [sliceBuffer, sliceOffset, ptr] = sbm->allocateStagingBufferSlice(size, alignment);
    ...
}
```

优点：
- 重用预分配的暂存缓冲区
- 减少缓冲区创建开销
- 更好的内存局部性

### Buffer-to-Buffer 传输

当硬件支持时，使用 GPU 端的 buffer-to-buffer 复制：

```cpp
dc->priv().drawingManager()->newBufferTransferTask(
        std::move(tempBuffer), tempOffset, fBuffer, offset, size);
```

比 CPU 到 GPU 的上传更快，尤其在大数据量时。

### 对齐要求

遵守硬件的传输对齐要求：

```cpp
auto alignment = dc->priv().caps()->transferFromBufferToBufferAlignment();
```

不正确的对齐可能导致性能下降或功能失败。

### 零初始化优化

仅在无初始数据时零初始化：

```cpp
data ? GrResourceProvider::ZeroInit::kNo
     : GrResourceProvider::ZeroInit::kYes
```

避免不必要的内存写入。

### 跨线程释放开销

`ReturnResourceFromThread` 虽然安全，但有额外开销：
- 检查线程 ID
- 可能的消息队列操作

建议在创建线程上释放缓冲区以获得最佳性能。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkMesh.h` | 公共 API | SkMesh 和缓冲区接口定义 |
| `src/core/SkMeshPriv.h` | 私有接口 | Mesh 私有类型和工具 |
| `include/gpu/ganesh/SkMeshGanesh.h` | Ganesh 扩展 | Ganesh 特定的 Mesh API |
| `src/gpu/ganesh/GrGpuBuffer.h` | 底层实现 | GPU 缓冲区基类 |
| `src/gpu/ganesh/GrResourceProvider.h` | 资源管理 | 资源创建接口 |
| `src/gpu/ganesh/GrResourceCache.h` | 缓存管理 | 资源缓存和跨线程释放 |
| `src/gpu/ganesh/GrDrawingManager.h` | 任务管理 | 缓冲区更新/传输任务 |
| `src/gpu/ganesh/GrStagingBufferManager.h` | 暂存缓冲 | 暂存缓冲区管理 |
| `src/gpu/ganesh/GrDirectContext.h` | 上下文 | GPU 上下文 |
| `src/gpu/ganesh/GrCaps.h` | 能力查询 | GPU 能力信息 |
| `include/core/SkData.h` | 数据封装 | 数据容器 |
