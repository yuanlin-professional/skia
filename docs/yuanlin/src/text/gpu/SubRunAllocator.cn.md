# SubRunAllocator - SubRun 内存分配器

> 源文件: `src/text/gpu/SubRunAllocator.h`, `src/text/gpu/SubRunAllocator.cpp`

## 概述

SubRunAllocator 为 GPU 文本渲染的 SubRun 系统提供高效的内存分配服务。它基于 BagOfBytes（字节袋）分配器，支持 POD 类型和非 POD 类型的分配，并提供对象级别和数组级别的分配接口。设计目标是最小化堆分配次数，通过内联存储和 Fibonacci 增长策略优化内存使用。

该分配器还支持一种特殊模式：将对象（如 TextBlob、SlugImpl）与其 arena 内存合并到一次 `::operator new` 调用中，实现对象和其关联数据的紧凑存储。

## 架构位置

```
sktext::gpu 命名空间
  ├── BagOfBytes — 底层字节分配器
  ├── SubRunAllocator — 类型安全的分配器包装
  ├── SubRunInitializer<T> — 对象初始化辅助
  └── STSubRunAllocator<N,A> — 带内联存储的分配器
```

- **使用者**: SubRunContainer、TextBlob、SlugImpl、GlyphVector

## 主要类与结构体

### BagOfBytes
底层字节分配器，管理分配块链表。

**关键特性**:
- 最大对齐 `kMaxAlignment = max(16, alignof(max_align_t))`
- 最大分配大小接近 INT_MAX
- Fibonacci 块大小增长策略
- 大于 32K 的分配按 4K 对齐

**分配块结构**: 每个块的末尾存储 `Block` 结构（包含前一个块指针和块起始地址），块内从低地址向高地址分配。

### SubRunAllocator
类型安全的分配器，包装 BagOfBytes。

**嵌套类型**:
- `Destroyer` — 单对象析构删除器（用于 unique_ptr）
- `ArrayDestroyer` — 数组析构删除器

**核心分配方法**:
- `makePOD<T>(args...)` — 分配并构造 POD 对象
- `makeUnique<T>(args...)` — 分配并构造非 POD 对象，返回带析构器的 unique_ptr
- `makePODArray<T>(n)` — 分配 POD 数组
- `makePODSpan<T>(span)` — 拷贝 Span 到新分配的 POD 数组
- `makePODArray<T>(src, map)` — 映射转换分配
- `makeUniqueArray<T>(n)` — 分配非 POD 数组

### SubRunInitializer\<T\>
RAII 辅助类，持有预分配的内存并提供 `initialize()` 方法在该内存上构造对象。析构时释放内存（如果未初始化）。

### STSubRunAllocator\<InlineStorageSize, Alignment\>
带内联存储的 SubRunAllocator，通过继承 `std::array` 和 `SubRunAllocator` 实现。内联存储先于 SubRunAllocator 析构，确保析构期间内存仍可访问。

## 公共 API 函数

```cpp
// 对象+Arena 联合分配
template <typename T>
static std::tuple<SubRunInitializer<T>, int, SubRunAllocator>
AllocateClassMemoryAndArena(int allocSizeHint);
```
单次 `::operator new` 分配对象内存 + Arena 内存。返回初始化器、总大小和分配器。

```cpp
static constexpr int PlatformMinimumSizeWithOverhead(int requestedSize, int assumedAlignment);
```
计算考虑对齐和块头开销后的最小分配大小。

## 内部实现细节

### BagOfBytes 分配算法
```
allocateBytes(size, alignment):
  1. 将 fCapacity 按 alignment 向下对齐
  2. 如果 fCapacity < size，调用 needMoreBytes 分配新块
  3. 返回 fEndByte - fCapacity 处的指针
  4. fCapacity -= size
```

### 新块分配（needMoreBytes）
1. 使用 Fibonacci 增长计算下一个块大小
2. 取 max(requestedSize, nextBlockSize) 确保满足请求
3. 添加平台对齐和 Block 头的开销
4. 分配新的 char[] 块
5. 在块末尾放置 Block 结构链接到前一个块

### 块内存布局
```
[分配区域 ... ] [空闲] [Block 结构]
^                       ^
|                       |
bytes                   fEndByte (最高 kMaxAlignment 对齐地址)
```

fCapacity 表示从 fEndByte 向左的可用字节数。

### POD vs 非 POD 区分
通过 `HasNoDestructor<T> = std::is_trivially_destructible<T>::value` 在编译时区分：
- POD: 直接分配，不需要析构
- 非 POD: 返回 `unique_ptr<T, Destroyer>`，确保析构器被调用

## 依赖关系

- `SkFibBlockSizes` — Fibonacci 块大小增长策略
- `SkArenaAlloc` — 相关概念的参考实现
- `SkIsPow2` / `SkAlignTo` — 对齐工具

## 设计模式与设计决策

1. **联合分配**: `AllocateClassMemoryAndArena` 将宿主对象和 Arena 合并为一次分配
2. **RAII 析构**: 非 POD 类型通过自定义删除器确保正确析构
3. **编译时类型检查**: `static_assert` 防止在 POD/非 POD 方法间的误用
4. **继承存储**: STSubRunAllocator 通过继承 std::array 确保内联存储的生命周期
5. **Fibonacci 增长**: 避免指数增长导致的内存浪费

## 性能考量

- 小分配使用内联存储，零堆分配
- Fibonacci 增长策略平衡了分配次数和内存浪费
- 大于 32K 的分配按 4K 对齐，与 JEMalloc 等分配器的行为匹配
- POD 分配无析构开销
- 联合分配模式减少了 TextBlob/Slug 创建时的分配次数

## 相关文件

- `src/base/SkArenaAlloc.h` — SkArenaAlloc 和 SkFibBlockSizes
- `src/text/gpu/SubRunContainer.h` — SubRun 系统
- `src/text/gpu/TextBlob.h` — TextBlob（使用 AllocateClassMemoryAndArena）
- `src/text/gpu/SlugImpl.h` — Slug（使用 AllocateClassMemoryAndArena）
