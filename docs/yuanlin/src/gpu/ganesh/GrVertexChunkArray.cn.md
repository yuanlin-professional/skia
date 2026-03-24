# GrVertexChunkArray

> 源文件: src/gpu/ganesh/GrVertexChunkArray.h, src/gpu/ganesh/GrVertexChunkArray.cpp

## 概述

`GrVertexChunkArray` 是 Skia Ganesh GPU 后端中用于管理分块顶点数据的轻量级容器。它与 `GrVertexChunkBuilder` 配合使用,用于处理在绘制时无法预先确定顶点数量的场景。该模块采用分块写入策略,动态分配 GPU 缓冲区,并以指数增长方式扩展容量,以提高内存分配效率。

核心设计理念是将顶点数据分成多个块(chunk),每个块包含一个 GPU 缓冲区引用、顶点数量和基础偏移量。这种设计允许在不预先知道总顶点数的情况下高效地构建顶点数据。

## 架构位置

`GrVertexChunkArray` 位于 Ganesh GPU 后端的顶点数据管理层:

- **上层**: 由网格绘制目标 `GrMeshDrawTarget` 调用
- **同层**: 与 `GrBuffer` 和 `BufferWriter` 协作
- **下层**: 底层使用 `SkTArray` 作为容器基础设施

该模块是 Ganesh 渲染管线中顶点数据准备阶段的关键组件,专门处理动态顶点数据的增量式构建。

## 主要类与结构体

### GrVertexChunk 结构体

表示单个顶点数据块。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBuffer` | `sk_sp<const GrBuffer>` | GPU 缓冲区的智能指针 |
| `fCount` | `int` | 该块中的顶点/实例数量 |
| `fBase` | `int` | 基础顶点或基础实例索引 |

**特性**: 标记为 `trivially_relocatable`,支持高效内存移动。

### GrVertexChunkArray 类型别名

```cpp
using GrVertexChunkArray = skia_private::STArray<1, GrVertexChunk>;
```

预分配 1 个元素的栈数组,优化单块场景。数组增长时会同时分配新的 GPU 缓冲区。

### GrVertexChunkBuilder 类

**继承关系**: 继承自 `SkNoncopyable` (禁止拷贝)

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTarget` | `GrMeshDrawTarget* const` | 网格绘制目标指针 |
| `fChunks` | `GrVertexChunkArray* const` | 输出的块数组指针 |
| `fStride` | `const size_t` | 每个顶点的字节步长 |
| `fMinVerticesPerChunk` | `int` | 每块最小顶点数(动态增长) |
| `fCurrChunkVertexWriter` | `skgpu::VertexWriter` | 当前块的顶点写入器 |
| `fCurrChunkVertexCount` | `int` | 当前块已写入的顶点数 |
| `fCurrChunkVertexCapacity` | `int` | 当前块的容量 |

## 公共 API 函数

### GrVertexChunkBuilder::GrVertexChunkBuilder

```cpp
GrVertexChunkBuilder(GrMeshDrawTarget* target,
                     GrVertexChunkArray* chunks,
                     size_t stride,
                     int minVerticesPerChunk)
```

**功能**: 构造顶点块构建器。

**参数**:
- `target`: 网格绘制目标
- `chunks`: 输出的块数组
- `stride`: 顶点步长
- `minVerticesPerChunk`: 初始最小块大小

**约束**: `minVerticesPerChunk` 必须大于 0。

### GrVertexChunkBuilder::appendVertices

```cpp
SK_ALWAYS_INLINE skgpu::VertexWriter appendVertices(int count)
```

**功能**: 追加指定数量的连续顶点。

**返回值**: 用于写入顶点数据的 `VertexWriter`。

**行为**:
- 如果当前块容量不足,自动分配新块
- 返回的顶点不保证与前后调用的顶点连续
- 分配失败时返回空的 `VertexWriter`

### GrVertexChunkBuilder::popVertices

```cpp
void popVertices(int count)
```

**功能**: 弹出最近追加的顶点。

**约束**: `count` 不能超过最近一次 `appendVertices` 的数量。

### GrVertexChunkBuilder::stride

```cpp
size_t stride() const
```

**功能**: 返回顶点步长。

## 内部实现细节

### 分块分配策略

`allocChunk` 方法实现了智能的缓冲区分配逻辑:

1. **完成当前块**: 将当前块的顶点数记录到 `fCount`
2. **创建新块**: 在数组中添加新的 `GrVertexChunk`
3. **请求缓冲区**: 调用 `fTarget->makeVertexWriterAtLeast` 分配 GPU 内存
4. **容量增长**: 成功分配后,将 `fMinVerticesPerChunk` 翻倍,最大不超过 `INT_MAX / fStride`

### 指数增长算法

```cpp
if (maxVerticesPerChunk / 2 > fMinVerticesPerChunk) {
    fMinVerticesPerChunk *= 2;  // 翻倍增长
} else {
    fMinVerticesPerChunk = maxVerticesPerChunk;  // 达到上限
}
```

这种策略在避免频繁分配的同时,防止单个块过大导致的内存浪费。

### 析构时的资源回收

析构函数确保将未使用的顶点空间归还给绘制目标:

```cpp
~GrVertexChunkBuilder() {
    if (!fChunks->empty()) {
        fTarget->putBackVertices(fCurrChunkVertexCapacity - fCurrChunkVertexCount, fStride);
        fChunks->back().fCount = fCurrChunkVertexCount;
    }
}
```

### 内存优化

- **栈优化**: `STArray<1>` 使单块场景避免堆分配
- **原地构造**: 使用 `std::exchange` 避免不必要的拷贝
- **智能指针**: `sk_sp` 自动管理 GPU 缓冲区生命周期

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrMeshDrawTarget` | 分配 GPU 缓冲区和顶点空间 |
| `GrBuffer` | 表示 GPU 缓冲区资源 |
| `skgpu::VertexWriter` | 提供类型安全的顶点写入接口 |
| `skia_private::STArray` | 提供栈优化的动态数组容器 |
| `SkRefCnt` | 提供引用计数机制 |

### 被依赖的模块

该模块被需要动态构建顶点数据的绘制操作使用,特别是:
- 路径渲染器(无法预知三角化后的顶点数)
- 文本渲染(字形数量动态变化)
- 复杂几何体的实例化绘制

## 设计模式与设计决策

### Builder 模式

`GrVertexChunkBuilder` 使用构建器模式,通过渐进式调用构建最终的顶点块数组。

**优点**:
- 隐藏复杂的内存管理逻辑
- 提供简洁的 API 接口
- 确保资源正确释放(RAII)

### 不可拷贝设计

继承 `SkNoncopyable` 防止意外拷贝,因为:
- 构建器持有外部指针,拷贝语义不明确
- 避免双重释放资源的风险

### 预分配策略

选择 `STArray<1>` 而非普通 `TArray`:
- 绝大多数情况下只需一个块
- 避免小对象的堆分配开销
- 增长时的性能损失可接受(因为同时要分配 GPU 缓冲区)

### Debug 模式追踪

使用 `fLastAppendAmount` 在调试模式下验证 `popVertices` 的正确性:

```cpp
SkDEBUGCODE(int fLastAppendAmount = 0;)
```

## 性能考量

### 分配频率优化

- **初始容量**: 由调用者指定,避免过小的初始分配
- **指数增长**: 减少分配次数,摊销成本接近 O(1)
- **延迟分配**: 只在需要时才请求 GPU 缓冲区

### 内联优化

关键路径函数使用 `SK_ALWAYS_INLINE`:

```cpp
SK_ALWAYS_INLINE skgpu::VertexWriter appendVertices(int count)
```

在热循环中消除函数调用开销。

### 内存局部性

`GrVertexChunk` 结构体小且连续存储,利于 CPU 缓存。

### 失败处理

分配失败时优雅降级,返回空 `VertexWriter` 而非崩溃:

```cpp
if (!fCurrChunkVertexWriter || !chunk->fBuffer || ...) SK_UNLIKELY {
    SkDebugf("WARNING: Failed to allocate vertex buffer for GrVertexChunk.\n");
    fChunks->pop_back();
    return false;
}
```

使用 `SK_UNLIKELY` 提示编译器优化正常路径。

### 避免过度分配

析构时将未使用的空间归还,避免浪费:

```cpp
fTarget->putBackVertices(fCurrChunkVertexCapacity - fCurrChunkVertexCount, fStride);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/gpu/ganesh/GrMeshDrawTarget.h` | 提供缓冲区分配接口 |
| `src/gpu/ganesh/GrBuffer.h` | GPU 缓冲区资源定义 |
| `src/gpu/BufferWriter.h` | 顶点写入工具 |
| `include/private/base/SkTArray.h` | 动态数组容器 |
| `include/core/SkRefCnt.h` | 智能指针基础设施 |
| `include/private/base/SkNoncopyable.h` | 禁止拷贝基类 |
