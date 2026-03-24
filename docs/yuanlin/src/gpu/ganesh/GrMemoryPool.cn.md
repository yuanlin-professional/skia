# GrMemoryPool

> 源文件: src/gpu/ganesh/GrMemoryPool.h, src/gpu/ganesh/GrMemoryPool.cpp

## 概述

`GrMemoryPool` 是 Skia Ganesh GPU 后端中专门用于快速分配和释放小对象的内存池。它基于 `SkBlockAllocator` 实现,通过块分配策略优化了频繁的内存分配和释放操作,特别适合用于重载 `operator new` 和 `operator delete` 来管理大量生命周期短暂的对象。

主要特性:
- 快速分配/释放,牺牲部分内存效率换取速度
- 支持预分配和按需扩展
- 自动对齐到 `std::max_align_t` (或强制 8 字节对齐)
- Debug 模式下的内存泄漏检测
- 所有分配的对象必须在池销毁前释放

## 架构位置

`GrMemoryPool` 位于 Ganesh 的内存管理工具层,主要用于以下场景:

1. **GrOp 对象池**
   - 为 `GrOp` (渲染操作) 对象提供快速分配
   - 每个操作通常生命周期很短,在提交后即可释放
   - 通过重载 `operator new` 使用内存池

2. **临时数据结构**
   - 渲染过程中的临时节点和数据结构
   - 频繁创建和销毁的小对象

3. **线程局部池**
   - 每个 `GrDirectContext` 可能维护独立的内存池
   - 避免线程间的竞争

在架构中的位置:
```
GrDirectContext
    └── GrMemoryPool (用于 GrOp 分配)
            └── SkBlockAllocator (底层块分配器)
```

## 主要类与结构体

### 继承关系

```
GrMemoryPool (无继承,独立类)
    └── 内部依赖 SkBlockAllocator
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAllocator` | `SkBlockAllocator` | 底层块分配器,必须是最后一个字段 |
| `fDebug` | `Debug*` | Debug 模式下的追踪信息指针 |

### Header 结构体 (内部)

| 字段 | 类型 | 说明 |
|------|------|------|
| `fStart` | `int` | 分配的起始偏移 |
| `fEnd` | `int` | 分配的结束偏移 |
| `fID` | `int` | Debug 模式下的分配 ID |
| `fSentinel` | `uint32_t` | 内存保护哨兵值 |

### Debug 结构体 (Debug 模式)

| 字段 | 类型 | 说明 |
|------|------|------|
| `fAllocatedIDs` | `THashSet<int>` | 已分配对象的 ID 集合 |
| `fAllocationCount` | `int` | 当前分配计数 |

## 公共 API 函数

### 工厂函数

```cpp
// 创建内存池
// preallocSize: 预分配大小
// minAllocSize: 最小块分配大小
static std::unique_ptr<GrMemoryPool> Make(size_t preallocSize,
                                          size_t minAllocSize);
```

### 分配与释放

```cpp
// 分配指定大小的内存
// 返回的指针对齐到 kAlignment (8 或 max_align_t)
// 必须使用 release() 释放
void* allocate(size_t size);

// 释放之前分配的内存
// p 必须是 allocate() 返回的指针
void release(void* p);
```

### 状态查询

```cpp
// 检查是否所有分配都已释放
bool isEmpty() const;

// 获取池的当前大小(不包括预分配)
size_t size() const;

// 获取预分配大小
size_t preallocSize() const;
```

### 内存管理

```cpp
// 释放不再使用的临时块
void resetScratchSpace();

// Debug 模式下报告内存泄漏
void reportLeaks() const;
```

### Debug 接口

```cpp
// 验证内存池的完整性 (仅 Debug)
void validate() const;
```

## 内部实现细节

### 内存布局

每个分配的内存块前面都有一个隐藏的 `Header`:

```
[Header (fStart, fEnd, fID, fSentinel)] [用户数据 (对齐到 kAlignment)]
```

### 分配流程

```cpp
void* GrMemoryPool::allocate(size_t size) {
    // 1. 从 SkBlockAllocator 分配,包括 Header 大小
    ByteRange alloc = fAllocator.allocate<kAlignment, sizeof(Header)>(size);

    // 2. 初始化 Header
    Header* header = (Header*)alloc.ptr(aligned_offset - sizeof(Header));
    header->fStart = alloc.fStart;
    header->fEnd = alloc.fEnd;

    // 3. Debug 模式: 分配唯一 ID 和哨兵值
    header->fID = nextID++;
    header->fSentinel = kAssignedMarker;
    fDebug->fAllocatedIDs.add(header->fID);

    // 4. 更新块的活跃分配计数
    alloc.fBlock->setMetadata(count + 1);

    // 5. 返回用户可见指针(跳过 Header)
    return alloc.ptr(aligned_offset);
}
```

### 释放流程

```cpp
void GrMemoryPool::release(void* p) {
    // 1. 从用户指针反向找到 Header
    Header* header = (Header*)((char*)p - sizeof(Header));

    // 2. Debug 模式: 验证哨兵值,标记为已释放
    SkASSERT(header->fSentinel == kAssignedMarker);
    header->fSentinel = kFreedMarker;

    // 3. 从 Debug 集合中移除 ID
    fDebug->fAllocatedIDs.remove(header->fID);
    fDebug->fAllocationCount--;

    // 4. 找到拥有该分配的块
    Block* block = fAllocator.owningBlock<kAlignment>(header, header->fStart);

    // 5. Debug 模式: 擦除内存防止 use-after-free
    memset(p, 0xDD, header->fEnd - aligned_offset);

    // 6. 更新块的活跃计数,如果为 0 则释放整个块
    if (block->metadata() == 1) {
        fAllocator.releaseBlock(block);
    } else {
        block->setMetadata(count - 1);
        block->release(header->fStart, header->fEnd);
    }
}
```

### 对齐处理

```cpp
// Emscripten 平台特殊处理
#ifdef SK_FORCE_8_BYTE_ALIGNMENT
    static constexpr size_t kAlignment = 8;
#else
    static constexpr size_t kAlignment = alignof(std::max_align_t);
#endif
```

### 泄漏检测

```cpp
void GrMemoryPool::reportLeaks() const {
#ifdef SK_DEBUG
    int i = 0;
    for (int id : fDebug->fAllocatedIDs) {
        if (++i == 1) {
            SkDebugf("Leaked %d IDs: %d", n, id);
        } else if (i < 11) {
            SkDebugf(", %d", id);
        } else if (i == 11) {
            SkDebugf(", ...\n");
            break;  // 只显示前 10 个
        }
    }
#endif
}
```

### isEmpty() 实现

```cpp
bool isEmpty() const {
    // 当前块是头块 && 头块的 metadata 为 0
    return fAllocator.currentBlock() == fAllocator.headBlock() &&
           fAllocator.currentBlock()->metadata() == 0;
}
```

### 块管理

- 使用 `SkBlockAllocator` 的 `metadata` 字段存储活跃分配计数
- 当块中最后一个分配被释放时,整个块被释放
- 支持块的复用 (通过 `resetScratchSpace()`)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkBlockAllocator` | 底层块分配和管理 |
| `SkTHash.h` | Debug 模式的 ID 追踪 |
| `SkDebug.h` | 断言和调试输出 |
| `<atomic>` | 分配 ID 的原子生成 |
| `<memory>` | 智能指针支持 |

### 被依赖的模块

| 模块 | 关系 |
|------|------|
| `GrOp` | 使用内存池分配操作对象 |
| `GrDirectContext` | 持有内存池实例 |
| `GrRecordingContext` | 管理内存池生命周期 |
| `GrOpFlushState` | 操作提交和清理 |

## 设计模式与设计决策

### 设计模式

1. **对象池模式 (Object Pool)**
   - 预分配内存块,复用已释放的内存
   - 避免频繁的系统内存分配

2. **工厂模式 (Factory Method)**
   - `Make()` 静态工厂函数创建内存池
   - 隐藏构造细节,在预分配空间中构造对象

3. **RAII (Resource Acquisition Is Initialization)**
   - 析构函数自动检测泄漏
   - 确保资源正确释放

4. **调试代理模式 (Debug Proxy)**
   - `Debug` 结构仅在 Debug 模式存在
   - 条件编译隔离调试开销

### 关键设计决策

1. **为何不使用标准 allocator?**
   - 需要极致的分配/释放速度
   - 标准 allocator 需要处理任意大小,开销较大
   - 内存池专注于小对象,可以做更多假设

2. **为何 fAllocator 必须是最后一个字段?**
   - `SkBlockAllocator` 使用灵活数组成员技巧
   - 预分配空间紧跟在 `GrMemoryPool` 对象后
   - `offsetof(GrMemoryPool, fAllocator)` 计算对象大小

3. **使用 placement new 创建池对象**
   ```cpp
   void* mem = operator new(preallocSize);
   return std::unique_ptr<GrMemoryPool>(
       new (mem) GrMemoryPool(preallocSize, minAllocSize)
   );
   ```
   - 一次性分配包含对象本身和预分配空间
   - 减少内存碎片

4. **Header 设计的权衡**
   - 每个分配额外占用 12-16 字节
   - 换取快速释放和调试能力
   - 小对象开销比例较高,但总体性能仍优于通用分配器

5. **活跃计数存储在块的 metadata**
   - 利用 `SkBlockAllocator` 的 metadata 字段
   - 避免额外的数据结构
   - 快速判断块是否可以释放

6. **Emscripten 8 字节对齐**
   - Emscripten 的 `max_align_t` 可能是 16 字节(long double)
   - Skia 不使用 long double,强制 8 字节对齐
   - 减少内存浪费

7. **泄漏报告限制 10 个**
   - 避免海量泄漏信息淹没控制台
   - 快速定位问题

## 性能考量

### 分配速度优化

1. **块分配策略**
   - 预分配避免启动时的分配开销
   - 固定增长策略 (`GrowthPolicy::kFixed`) 预测性强

2. **无锁设计**
   - 假设单线程使用
   - 避免互斥锁开销
   - 每个上下文独立的池

3. **对齐优化**
   - `kAlignment` 对齐减少 CPU 访问开销
   - Header 对齐确保用户数据对齐

### 内存效率权衡

1. **Header 开销**
   - 16 字节 Header (64位系统)
   - 对于 32 字节以下的小对象,开销比例 >50%
   - 但总体仍优于通用分配器的 bookkeeping

2. **块内碎片**
   - 块中可能有未使用的空间
   - 通过 `resetScratchSpace()` 定期清理

3. **块大小选择**
   - `kMinAllocationSize = 1024` 字节
   - 平衡块管理开销和内存浪费

### 调试开销隔离

- ID 哨兵、内存擦除仅在 Debug 模式
- Release 版本接近零开销
- ASAN 模式的内存毒化检测

### 缓存友好性

- 连续分配的对象在同一块中
- 提高缓存命中率
- 特别适合遍历大量相似对象

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/base/SkBlockAllocator.h` | 依赖 | 底层块分配器 |
| `src/core/SkTHash.h` | 依赖 | 哈希集合,用于 Debug 追踪 |
| `src/gpu/ganesh/GrOp.h` | 使用 | 渲染操作对象池 |
| `src/gpu/ganesh/GrDirectContext.cpp` | 使用 | 创建和管理内存池 |
| `src/gpu/ganesh/GrRecordingContext.h` | 使用 | 上下文持有内存池 |
| `src/gpu/ganesh/GrOpFlushState.h` | 使用 | 操作提交后的清理 |
| `include/private/base/SkDebug.h` | 依赖 | 调试宏和断言 |
