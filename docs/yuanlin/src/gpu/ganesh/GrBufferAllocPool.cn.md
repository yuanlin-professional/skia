# GrBufferAllocPool

> 源文件
> - src/gpu/ganesh/GrBufferAllocPool.h
> - src/gpu/ganesh/GrBufferAllocPool.cpp

## 概述

`GrBufferAllocPool` 是 Ganesh GPU 后端中的核心缓冲区分配池类，用于高效管理动态几何数据（顶点、索引、间接绘制命令等）的 GPU 缓冲区分配。该类实现了一个池化分配器，允许客户端快速分配缓冲区空间，支持空间回收和重用，并在绘制前确保数据已上传到 GPU。

该类是一个抽象基类，提供了三个具体实现：`GrVertexBufferAllocPool`（顶点缓冲池）、`GrIndexBufferAllocPool`（索引缓冲池）和 `GrDrawIndirectBufferAllocPool`（间接绘制缓冲池）。

## 架构位置

`GrBufferAllocPool` 位于 Skia 的 GPU 渲染管线中：

- **模块**: Ganesh GPU 后端
- **层级**: 资源管理层（Resource Management Layer）
- **角色**: 缓冲区分配器和内存池管理器
- **协作对象**: 与 `GrGpu`、`GrResourceProvider`、`GrGpuBuffer`、`GrCpuBuffer` 协作

该类是连接上层绘制操作和底层 GPU 缓冲区资源的关键桥梁，负责高效的内存分配和数据传输策略。

## 主要类与结构体

### GrBufferAllocPool（基类）

继承关系：
```
SkNoncopyable (不可复制)
  └── GrBufferAllocPool (基类)
      ├── GrVertexBufferAllocPool (顶点缓冲池)
      ├── GrIndexBufferAllocPool (索引缓冲池)
      └── GrDrawIndirectBufferAllocPool (间接绘制缓冲池)
```

关键成员变量：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBlocks` | `TArray<BufferBlock>` | 已分配的缓冲区块数组 |
| `fCpuBufferCache` | `sk_sp<CpuBufferCache>` | CPU 端缓冲区缓存 |
| `fCpuStagingBuffer` | `sk_sp<GrCpuBuffer>` | CPU 暂存缓冲区 |
| `fGpu` | `GrGpu*` | GPU 接口指针 |
| `fBufferType` | `GrGpuBufferType` | 缓冲区类型（顶点/索引/间接绘制） |
| `fBufferPtr` | `void*` | 当前可写入的缓冲区指针 |
| `fBytesInUse` | `size_t` | 已使用的字节数 |

### CpuBufferCache（CPU 缓冲区缓存）

```cpp
class CpuBufferCache : public GrNonAtomicRef<CpuBufferCache>
```

用于缓存 CPU 端缓冲区，避免频繁的内存分配。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBuffers` | `unique_ptr<Buffer[]>` | 缓存的缓冲区数组 |
| `fMaxBuffersToCache` | `int` | 最大缓存数量 |

### BufferBlock（缓冲区块）

私有内部结构：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBuffer` | `sk_sp<GrBuffer>` | 缓冲区对象 |
| `fBytesFree` | `size_t` | 该块中剩余的可用字节数 |

## 公共 API 函数

### GrBufferAllocPool 基类接口

#### unmap()

```cpp
void unmap();
```

确保所有缓冲区已解除映射，所有数据已写入。必须在使用池中的缓冲区进行绘制前调用。

#### reset()

```cpp
void reset();
```

使池中所有数据失效，释放未预分配的缓冲区。

#### putBack()

```cpp
void putBack(size_t bytes);
```

以 LIFO（后进先出）方式释放通过 `makeSpace` 分配的数据空间。

### GrVertexBufferAllocPool

#### makeSpace()

```cpp
void* makeSpace(size_t vertexSize,
                int vertexCount,
                sk_sp<const GrBuffer>* buffer,
                int* startVertex);
```

**功能**: 分配空间以容纳指定数量的顶点。

**参数说明**:
- `vertexSize`: 单个顶点的大小（字节）
- `vertexCount`: 顶点数量
- `buffer`: 输出参数，返回持有数据的缓冲区
- `startVertex`: 输出参数，返回起始顶点偏移量

**返回值**: 指向可写入数据的内存指针

#### makeSpaceAtLeast()

```cpp
void* makeSpaceAtLeast(size_t vertexSize,
                       int minVertexCount,
                       int fallbackVertexCount,
                       sk_sp<const GrBuffer>* buffer,
                       int* startVertex,
                       int* actualVertexCount);
```

分配至少 `minVertexCount` 个顶点的空间，如果需要新块则分配 `fallbackVertexCount` 个顶点的空间。

### GrIndexBufferAllocPool

#### makeSpace()

```cpp
void* makeSpace(int indexCount,
                sk_sp<const GrBuffer>* buffer,
                int* startIndex);
```

为索引数据分配空间，索引大小固定为 `uint16_t`（2 字节）。

#### makeSpaceAtLeast()

```cpp
void* makeSpaceAtLeast(int minIndexCount,
                       int fallbackIndexCount,
                       sk_sp<const GrBuffer>* buffer,
                       int* startIndex,
                       int* actualIndexCount);
```

分配至少 `minIndexCount` 个索引的空间。

### GrDrawIndirectBufferAllocPool

#### makeSpace()

```cpp
GrDrawIndirectWriter makeSpace(int drawCount,
                               sk_sp<const GrBuffer>* buffer,
                               size_t* offset);
```

为 `GrDrawIndirectCommand` 分配空间，返回类型化的写入器。

#### makeIndexedSpace()

```cpp
GrDrawIndexedIndirectWriter makeIndexedSpace(int drawCount,
                                             sk_sp<const GrBuffer>* buffer,
                                             size_t* offset);
```

为 `GrDrawIndexedIndirectCommand` 分配空间。

## 内部实现细节

### 缓冲区分配策略

1. **优先使用当前块**: 如果当前块有足够空间且满足对齐要求，直接在当前块中分配
2. **创建新块**: 空间不足时创建新块，大小至少为 `kDefaultBufferSize`（32KB）
3. **缓冲区类型选择**:
   - 优先使用 GPU 缓冲区（GrGpuBuffer）
   - 某些平台（如移动设备）使用 CPU 缓冲区（GrCpuBuffer）

### 映射与暂存策略

```cpp
bool createBlock(size_t requestSize);
```

创建新块时的策略：
1. **CPU 缓冲区**: 直接映射，无额外开销
2. **GPU 缓冲区**:
   - 如果支持映射且大小超过阈值，直接映射 GPU 缓冲区
   - 否则使用 CPU 暂存缓冲区，稍后通过 `flushCpuData()` 传输数据

### 数据刷新机制

```cpp
void flushCpuData(const BufferBlock& block, size_t flushSize);
```

将 CPU 暂存缓冲区的数据传输到 GPU 缓冲区：
1. 如果缓冲区支持映射，使用 `map()` + `memcpy()` + `unmap()`
2. 否则使用 `updateData()` 更新缓冲区

### 对齐处理

```cpp
static inline size_t align_up_pad(size_t x, size_t alignment);
static inline size_t align_down(size_t x, uint32_t alignment);
```

- `align_up_pad()`: 计算需要填充的字节数以满足对齐要求
- `align_down()`: 向下对齐到指定边界

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGpu` | 创建缓冲区和执行 GPU 操作 |
| `GrResourceProvider` | 资源创建和管理 |
| `GrGpuBuffer` | GPU 端缓冲区对象 |
| `GrCpuBuffer` | CPU 端缓冲区对象 |
| `GrCaps` | 查询 GPU 能力和配置 |
| `GrDirectContext` | 访问上下文和资源提供者 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| `GrOpsTask` | 使用缓冲池分配顶点和索引数据 |
| `GrOp` 子类 | 各种绘制操作使用缓冲池 |
| `GrMeshDrawOp` | 网格绘制操作的主要客户端 |

## 设计模式与设计决策

### 1. 对象池模式

核心设计模式，通过池化管理减少频繁的缓冲区创建和销毁开销。

### 2. 策略模式

根据平台能力选择不同的缓冲区策略：
- GPU 缓冲区 vs CPU 缓冲区
- 直接映射 vs 暂存传输

### 3. 模板方法模式

基类 `GrBufferAllocPool` 定义算法框架，派生类重写特定方法以适应不同类型的缓冲区。

### 4. 缓存策略

`CpuBufferCache` 实现了 LRU 风格的缓存，避免频繁的 CPU 内存分配。

### 5. RAII 原则

使用智能指针自动管理缓冲区生命周期。

### 6. 懒惰初始化

缓冲区按需创建，避免预先分配过多资源。

## 性能考量

### 1. 减少分配次数

- 使用大块缓冲区（默认 32KB）
- 池化重用避免频繁创建/销毁

### 2. 减少 GPU 同步

- 缓冲区映射避免 CPU-GPU 数据拷贝
- 延迟刷新，批量传输数据

### 3. 内存对齐优化

- 严格遵守对齐要求，避免性能损失
- 填充字节清零，避免未定义行为

### 4. 避免内存碎片

- LIFO 回收策略
- 块级管理减少碎片

### 5. 平台适配

- 移动设备优先使用 CPU 缓冲区（`preferClientSideDynamicBuffers`）
- 桌面 GPU 优先使用 GPU 缓冲区

### 6. 缓存友好

- 连续分配提高缓存命中率
- `CpuBufferCache` 避免频繁系统调用

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/GrGpu.h` | GPU 接口定义 |
| `src/gpu/ganesh/GrGpuBuffer.h` | GPU 缓冲区类 |
| `src/gpu/ganesh/GrCpuBuffer.h` | CPU 缓冲区类 |
| `src/gpu/ganesh/GrBuffer.h` | 缓冲区基类 |
| `src/gpu/ganesh/GrResourceProvider.h` | 资源提供者 |
| `src/gpu/ganesh/GrCaps.h` | GPU 能力查询 |
| `src/gpu/ganesh/GrDrawIndirectCommand.h` | 间接绘制命令定义 |
| `include/gpu/ganesh/GrDirectContext.h` | GPU 上下文 |
