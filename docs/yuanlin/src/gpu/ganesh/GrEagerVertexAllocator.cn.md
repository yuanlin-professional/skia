# GrEagerVertexAllocator

> 源文件: src/gpu/ganesh/GrEagerVertexAllocator.h, src/gpu/ganesh/GrEagerVertexAllocator.cpp

## 概述

`GrEagerVertexAllocator` 是 Ganesh GPU 后端中用于顶点数据急切分配(eager allocation)的抽象接口和实现集合。该模块解决了在精确顶点数量未知的情况下预先分配顶点缓冲区的问题,支持先分配上界、后缩减到实际大小的工作流程。

主要功能包括:
- **急切分配模式**: 允许先分配上界数量的顶点空间,写入数据后再缩减到实际使用量
- **动态 GPU 分配**: `GrEagerDynamicVertexAllocator` 直接从 GPU 缓冲池分配动态顶点数据
- **CPU 侧分配**: `GrCpuVertexAllocator` 在 CPU 内存中分配顶点,支持线程安全缓存
- **写入器集成**: 提供 `lockWriter` 方法与 `VertexWriter` 工具类集成

该设计在几何生成、曲面细分等场景中特别有用,这些场景中顶点数量依赖于复杂计算。

## 架构位置

该模块位于 Ganesh 渲染管线的顶点数据管理层:

```
src/gpu/ganesh/
├── GrEagerVertexAllocator.h/cpp     # 急切顶点分配器(当前模块)
├── GrMeshDrawTarget.h/cpp           # 网格绘制目标,提供底层分配
├── GrBuffer.h/cpp                   # GPU 缓冲区抽象
├── GrThreadSafeCache.h              # 线程安全缓存
└── ops/
    └── GrOp.cpp                     # 绘制操作使用顶点分配器
```

**使用场景**:
- 几何生成操作(如 tessellation ops)
- 路径渲染器的顶点生成
- 动态网格生成

## 主要类与结构体

### GrEagerVertexAllocator
抽象基类,定义急切分配接口。

```cpp
class GrEagerVertexAllocator {
public:
    virtual void* lock(size_t stride, int eagerCount) = 0;
    virtual void unlock(int actualCount) = 0;
    skgpu::VertexWriter lockWriter(size_t stride, int eagerCount);
};
```

**使用模式**:
1. 调用 `lock(stride, eagerCount)` 分配上界数量的顶点
2. 写入顶点数据到返回的指针
3. 调用 `unlock(actualCount)` 提供实际写入的顶点数量

### GrEagerDynamicVertexAllocator
动态 GPU 缓冲区分配实现,使用 `GrMeshDrawTarget` 的顶点空间分配机制。

```cpp
class GrEagerDynamicVertexAllocator : public GrEagerVertexAllocator {
public:
    GrEagerDynamicVertexAllocator(GrMeshDrawTarget* target,
                                  sk_sp<const GrBuffer>* vertexBuffer,
                                  int* baseVertex);

    void* lock(size_t stride, int eagerCount) final;
    void unlock(int actualCount) final;

private:
    GrMeshDrawTarget* const fTarget;
    sk_sp<const GrBuffer>* const fVertexBuffer;
    int* const fBaseVertex;
    size_t fLockStride;
    int fLockCount = 0;
};
```

**成员变量**:
- `fTarget`: 网格绘制目标,提供底层缓冲区分配
- `fVertexBuffer`: 输出参数,接收分配的顶点缓冲区
- `fBaseVertex`: 输出参数,接收顶点起始偏移
- `fLockStride`: 锁定时的顶点步长
- `fLockCount`: 锁定时分配的顶点数量

### GrCpuVertexAllocator
CPU 内存分配实现,支持线程安全缓存的顶点数据。

```cpp
class GrCpuVertexAllocator : public GrEagerVertexAllocator {
public:
    void* lock(size_t stride, int eagerCount) override;
    void unlock(int actualCount) override;
    sk_sp<GrThreadSafeCache::VertexData> detachVertexData();

private:
    sk_sp<GrThreadSafeCache::VertexData> fVertexData;
    void* fVertices = nullptr;
    size_t fLockStride = 0;
};
```

**成员变量**:
- `fVertices`: 临时分配的顶点数据指针
- `fVertexData`: 封装后的顶点数据对象,可用于缓存
- `fLockStride`: 锁定时的顶点步长

## 公共 API 函数

### GrEagerVertexAllocator::lockWriter
创建 `VertexWriter` 对象用于类型安全的顶点写入。

```cpp
skgpu::VertexWriter lockWriter(size_t stride, int eagerCount)
```

**功能**:
1. 调用 `lock` 获取顶点数据指针
2. 计算总缓冲区大小 `stride * eagerCount`
3. 构造并返回 `VertexWriter` 对象

**优势**: `VertexWriter` 提供模板化的写入方法,支持自动步进和类型检查。

### GrEagerDynamicVertexAllocator::lock
从 GPU 动态缓冲池分配顶点空间。

```cpp
void* GrEagerDynamicVertexAllocator::lock(size_t stride, int eagerCount)
```

**实现流程**:
1. 断言当前未处于锁定状态(`fLockCount == 0`)
2. 调用 `fTarget->makeVertexSpace` 从缓冲池分配
3. 成功时记录 `fLockStride` 和 `fLockCount`
4. 失败时重置输出参数并返回 `nullptr`

**返回**: 成功返回可写顶点数据指针,失败返回 `nullptr`

### GrEagerDynamicVertexAllocator::unlock
释放未使用的顶点空间。

```cpp
void GrEagerDynamicVertexAllocator::unlock(int actualCount)
```

**实现流程**:
1. 断言 `actualCount <= fLockCount`
2. 调用 `fTarget->putBackVertices` 归还多余空间
3. 如果 `actualCount == 0`,重置顶点缓冲区引用
4. 清空 `fLockCount` 标记

**优化**: 通过归还未使用空间,提高缓冲池的利用效率。

### GrCpuVertexAllocator::lock
在 CPU 内存中分配顶点空间。

```cpp
void* GrCpuVertexAllocator::lock(size_t stride, int eagerCount)
```

**实现流程**:
1. 断言当前未锁定
2. 使用 `sk_malloc_throw(stride, eagerCount)` 分配内存
3. 记录 `fLockStride`
4. 返回分配的指针

**安全性**: `sk_malloc_throw` 在分配失败时抛出异常,避免返回 `nullptr`。

### GrCpuVertexAllocator::unlock
缩减内存到实际大小并封装为 `VertexData`。

```cpp
void GrCpuVertexAllocator::unlock(int actualCount)
```

**实现流程**:
1. 使用 `sk_realloc_throw` 缩减内存到实际大小
2. 调用 `GrThreadSafeCache::MakeVertexData` 封装数据
3. 清空 `fVertices` 和 `fLockStride`

**内存管理**: 缩减后的数据由 `VertexData` 持有,调用者需要通过 `detachVertexData` 获取所有权。

### GrCpuVertexAllocator::detachVertexData
获取封装后的顶点数据对象。

```cpp
sk_sp<GrThreadSafeCache::VertexData> GrCpuVertexAllocator::detachVertexData()
```

**功能**: 通过 `std::move` 转移 `fVertexData` 的所有权。

**使用场景**: 将顶点数据放入线程安全缓存,避免重复计算。

## 内部实现细节

### 锁定状态管理

两个实现都使用成员变量追踪锁定状态:
- `GrEagerDynamicVertexAllocator::fLockCount`: 非零表示已锁定
- `GrCpuVertexAllocator::fLockStride`: 非零表示已锁定

析构函数中断言未锁定状态:

```cpp
#ifdef SK_DEBUG
~GrEagerDynamicVertexAllocator() override {
    SkASSERT(!fLockCount);
}
#endif
```

**目的**: 检测使用错误,确保每个 `lock` 都有对应的 `unlock`。

### 输出参数模式

`GrEagerDynamicVertexAllocator` 使用指针传递输出参数:

```cpp
GrEagerDynamicVertexAllocator(GrMeshDrawTarget* target,
                              sk_sp<const GrBuffer>* vertexBuffer,
                              int* baseVertex)
```

**原因**: 允许在 `lock` 时直接更新调用者的缓冲区引用,避免额外的拷贝。

### 内存缩减策略

`GrCpuVertexAllocator::unlock` 使用 `sk_realloc_throw` 缩减内存:

```cpp
fVertices = sk_realloc_throw(fVertices, actualCount * fLockStride);
```

**权衡**: 缩减操作可能触发内存复制,但对于大型顶点数据(如曲面细分结果),节省的内存通常超过复制成本。

### final 关键字优化

`GrEagerDynamicVertexAllocator` 的虚函数标记为 `final`:

```cpp
void* lock(size_t stride, int eagerCount) final;
void unlock(int actualCount) final;
```

**优化**: 提示编译器不使用虚函数表,允许内联调用提高性能。

## 依赖关系

### 外部依赖
```cpp
#include "src/gpu/BufferWriter.h"            // VertexWriter 工具类
#include "src/gpu/ganesh/GrMeshDrawTarget.h" // 网格绘制目标
#include "src/gpu/ganesh/GrBuffer.h"         // GPU 缓冲区抽象
#include "src/gpu/ganesh/GrThreadSafeCache.h" // 线程安全缓存
```

### 被依赖模块
- `src/gpu/ganesh/ops/GrTessellationOp.cpp` - 曲面细分操作
- `src/gpu/ganesh/geometry/GrStyledShape.cpp` - 几何形状渲染
- `src/gpu/ganesh/ops/PathInnerTriangulateOp.cpp` - 路径三角化
- `src/gpu/ganesh/ops/StrokeTessellateOp.cpp` - 描边曲面细分

## 设计模式与设计决策

### 1. 策略模式
`GrEagerVertexAllocator` 定义抽象接口,两个实现提供不同的分配策略:
- **动态 GPU 分配**: 直接从 GPU 缓冲池分配,适合即时渲染
- **CPU 分配**: 在 CPU 内存分配,支持缓存和预计算

### 2. RAII 语义
虽然接口使用显式 `lock`/`unlock`,但鼓励使用 RAII 包装器:

```cpp
class ScopedVertexLock {
    void* fData;
    GrEagerVertexAllocator* fAllocator;
public:
    ScopedVertexLock(GrEagerVertexAllocator* alloc, size_t stride, int count)
        : fAllocator(alloc), fData(alloc->lock(stride, count)) {}
    ~ScopedVertexLock() { fAllocator->unlock(actualCount); }
};
```

### 3. 两阶段提交
分配分为两个阶段:
1. **Lock 阶段**: 分配上界空间,返回可写指针
2. **Unlock 阶段**: 提交实际使用量,释放多余空间

**优势**: 避免在不确定数量时进行保守估计浪费内存。

### 4. 输出参数注入
构造函数接收输出参数指针:

```cpp
GrEagerDynamicVertexAllocator(GrMeshDrawTarget* target,
                              sk_sp<const GrBuffer>* vertexBuffer,
                              int* baseVertex)
```

**优势**: 调用者提前准备接收容器,分配器直接更新,减少临时对象。

### 5. 零拷贝转移
`GrCpuVertexAllocator::detachVertexData` 使用 `std::move`:

```cpp
return std::move(fVertexData);
```

**优势**: 避免引用计数的原子操作,提高性能。

## 性能考量

### 1. 内存池化
`GrEagerDynamicVertexAllocator` 依赖 `GrMeshDrawTarget` 的缓冲池:
- **快速分配**: 池化避免频繁的 GPU 内存分配
- **空间回收**: `putBackVertices` 立即回收多余空间

### 2. 缓冲区对齐
底层分配器保证缓冲区对齐要求,避免性能下降。

### 3. 内联优化
使用 `final` 关键字允许编译器内联虚函数调用:

```cpp
void* lock(size_t stride, int eagerCount) final;
```

在热路径(如曲面细分循环)中,内联消除虚调用开销。

### 4. 延迟缩减
`GrCpuVertexAllocator` 在 `unlock` 时才缩减内存:
- **优势**: 如果后续 `lock` 需要更大空间,可以直接复用
- **权衡**: 需要在 `unlock` 后立即 `detachVertexData`,否则持有多余内存

### 5. 缓存友好性
`VertexWriter` 提供顺序写入接口:

```cpp
auto writer = allocator.lockWriter(stride, count);
writer << vertex1 << vertex2 << vertex3;
```

顺序写入利用 CPU 缓存预取,提高写入吞吐量。

### 6. 错误检测开销
调试模式下的断言检查:

```cpp
SkASSERT(!fLockCount);  // 检测重复锁定
SkASSERT(actualCount <= fLockCount);  // 检测越界
```

发布模式下编译为空操作,无性能损失。

## 相关文件

### 核心依赖
- `src/gpu/ganesh/GrMeshDrawTarget.h/cpp` - 提供底层顶点空间分配
- `src/gpu/BufferWriter.h` - `VertexWriter` 工具类
- `src/gpu/ganesh/GrThreadSafeCache.h` - 线程安全顶点数据缓存

### 使用场景
- `src/gpu/ganesh/ops/TessellationPathOps.cpp` - 路径曲面细分
- `src/gpu/ganesh/ops/StrokeTessellateOp.cpp` - 描边曲面细分
- `src/gpu/ganesh/geometry/GrPathTessellator.cpp` - 路径细分器

### 相关类型
- `src/gpu/ganesh/GrBuffer.h` - GPU 缓冲区抽象
- `src/gpu/ganesh/GrResourceProvider.h` - 资源提供者
