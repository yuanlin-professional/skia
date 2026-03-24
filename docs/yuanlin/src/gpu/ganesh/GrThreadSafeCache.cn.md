# GrThreadSafeCache

> 源文件: src/gpu/ganesh/GrThreadSafeCache.h, src/gpu/ganesh/GrThreadSafeCache.cpp

## 概述

`GrThreadSafeCache` 是 Ganesh GPU 后端中的线程安全缓存系统，用于在直接上下文（direct context）和所有 DDL 录制上下文之间共享 GPU 纹理资源。它主要缓存实用纹理（如模糊圆角矩形遮罩、渐变等）以及顶点数据，这些资源需要在多个线程间安全共享。

该缓存的核心设计理念是：
1. **多线程安全**：使用自旋锁保护所有操作
2. **CPU 优先策略**：DDL 线程在 CPU 上创建内容，GPU 线程通过占位符拥有优先权
3. **LRU 管理**：使用最近最少使用策略管理内存
4. **透明 CPU-GPU 转换**：顶点数据可以从 CPU 侧无缝转换到 GPU 侧

## 架构位置

`GrThreadSafeCache` 位于 Skia GPU 资源管理的缓存层：

```
Skia GPU 资源管理
├── GrDirectContext              # GPU 主上下文
├── GrRecordingContext           # DDL 录制上下文（多线程）
├── GrResourceCache              # 单线程资源缓存
└── GrThreadSafeCache            # 线程安全缓存（本类）
    ├── 纹理代理视图 (GrSurfaceProxyView)
    └── 顶点数据 (VertexData)
```

在多线程场景中的使用：
```
DDL线程1 ─┐
DDL线程2 ─┼─→ GrThreadSafeCache ←─ GPU线程(DirectContext)
DDL线程3 ─┘     (线程安全)
```

## 主要类与结构体

### 关键内部类

#### VertexData 类

用于存储顶点数据的引用计数对象：

| 成员 | 类型 | 说明 |
|-----|------|------|
| fVertices | const void* | CPU 端顶点数据 |
| fNumVertices | int | 顶点数量 |
| fVertexSize | size_t | 单个顶点大小 |
| fGpuBuffer | sk_sp&lt;GrGpuBuffer&gt; | GPU 端缓冲区 |

**公共方法**：
- `vertices()`, `size()`, `numVertices()`, `vertexSize()`: 查询接口
- `gpuBuffer()`, `refGpuBuffer()`: GPU 缓冲区访问
- `setGpuBuffer()`: 设置 GPU 缓冲区
- `reset()`: 释放所有资源

#### Trampoline 类

用于惰性代理的桥接对象：

```cpp
class Trampoline : public SkRefCnt {
public:
    sk_sp<GrTextureProxy> fProxy;
};
```

允许将延迟生成的渲染结果连接到占位符代理。

#### Entry 结构体

缓存条目，使用 union 存储不同类型的数据：

| 成员 | 类型 | 说明 |
|-----|------|------|
| fKey | skgpu::UniqueKey | 唯一键 |
| fView / fVertData | union | 纹理视图或顶点数据 |
| fTag | Tag 枚举 | 类型标记（Empty/View/VertData） |
| fLastAccess | time_point | 最后访问时间（LRU） |

**辅助方法**：
- `uniquelyHeld()`: 检查是否唯一持有
- `makeEmpty()`, `set()`: 状态管理
- 实现 `SkTDynamicHash` 和 `SkTInternalLList` 接口

### 主要成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fSpinLock | SkSpinlock | 保护所有并发访问的自旋锁 |
| fUniquelyKeyedEntryMap | SkTDynamicHash&lt;Entry&gt; | 按 unique key 索引的哈希表 |
| fUniquelyKeyedEntryList | SkTInternalLList&lt;Entry&gt; | LRU 链表（头部=MRU） |
| fEntryAllocator | SkArenaAlloc | 条目的内存分配器 |
| fFreeEntryList | Entry* | 空闲条目链表（对象池） |

## 公共 API 函数

### 查找操作

```cpp
GrSurfaceProxyView find(const skgpu::UniqueKey&)
std::tuple<GrSurfaceProxyView, sk_sp<SkData>> findWithData(
    const skgpu::UniqueKey&)
```

根据 unique key 查找纹理视图，可选返回自定义数据。

### 添加操作

```cpp
GrSurfaceProxyView add(const skgpu::UniqueKey&,
                      const GrSurfaceProxyView&)
std::tuple<GrSurfaceProxyView, sk_sp<SkData>> addWithData(...)
```

添加纹理视图到缓存。如果已存在，返回现有的视图。

### 查找或添加操作

```cpp
GrSurfaceProxyView findOrAdd(const skgpu::UniqueKey&,
                             const GrSurfaceProxyView&)
std::tuple<GrSurfaceProxyView, sk_sp<SkData>> findOrAddWithData(...)
```

原子性地查找或添加，避免竞争条件。

### 顶点数据操作

```cpp
static sk_sp<VertexData> MakeVertexData(const void* vertices,
                                        int vertexCount,
                                        size_t vertexSize)
static sk_sp<VertexData> MakeVertexData(sk_sp<GrGpuBuffer> buffer,
                                        int vertexCount,
                                        size_t vertexSize)
```

创建顶点数据对象。

```cpp
std::tuple<sk_sp<VertexData>, sk_sp<SkData>> findVertsWithData(
    const skgpu::UniqueKey&)

typedef bool (*IsNewerBetter)(SkData* incumbent, SkData* challenger);

std::tuple<sk_sp<VertexData>, sk_sp<SkData>> addVertsWithData(
    const skgpu::UniqueKey&,
    sk_sp<VertexData>,
    IsNewerBetter)
```

查找/添加顶点数据。添加时可提供比较函数决定是否替换现有数据。

### 移除操作

```cpp
void remove(const skgpu::UniqueKey&)
```

从缓存中移除指定条目。

### 资源管理

```cpp
void dropAllRefs()
void dropUniqueRefs(GrResourceCache* resourceCache)
void dropUniqueRefsOlderThan(skgpu::StdSteadyClock::time_point purgeTime)
```

- `dropAllRefs()`: 丢弃所有引用
- `dropUniqueRefs()`: 丢弃唯一持有的引用直到低于预算
- `dropUniqueRefsOlderThan()`: 丢弃超过指定时间的唯一引用

### 惰性视图创建

```cpp
static std::tuple<GrSurfaceProxyView, sk_sp<Trampoline>>
CreateLazyView(GrDirectContext*,
               GrColorType,
               SkISize dimensions,
               GrSurfaceOrigin,
               SkBackingFit)
```

创建惰性代理和 trampoline 对象，用于 GPU 线程优先策略。

## 内部实现细节

### 查找实现（internalFind）

```cpp
std::tuple<GrSurfaceProxyView, sk_sp<SkData>>
internalFind(const skgpu::UniqueKey& key)
```

**流程**：
1. 在 `fUniquelyKeyedEntryMap` 中查找
2. 如果找到，调用 `makeExistingEntryMRU()` 更新 LRU
3. 返回视图和自定义数据

### 添加实现（internalAdd）

```cpp
std::tuple<GrSurfaceProxyView, sk_sp<SkData>>
internalAdd(const skgpu::UniqueKey& key,
           const GrSurfaceProxyView& view)
```

**流程**：
1. 查找是否已存在
2. 如果不存在，调用 `getEntry()` 获取新条目
3. 返回视图和数据

### Entry 管理

**getEntry()**：
- 优先从 `fFreeEntryList` 获取（对象池复用）
- 否则使用 `fEntryAllocator` 分配新对象
- 调用 `makeNewEntryMRU()` 加入缓存

**recycleEntry()**：
- 清空条目内容
- 加入 `fFreeEntryList` 供复用

**makeExistingEntryMRU()**：
- 更新 `fLastAccess` 时间戳
- 从链表中移除并加到头部（MRU 位置）

**makeNewEntryMRU()**：
- 设置当前时间戳
- 加入链表头部
- 加入哈希表

### 顶点数据管理

**internalFindVerts()**：
与 `internalFind()` 类似，但返回 `VertexData`。

**internalAddVerts()**：
```cpp
std::tuple<sk_sp<VertexData>, sk_sp<SkData>>
internalAddVerts(const skgpu::UniqueKey& key,
                sk_sp<VertexData> vertData,
                IsNewerBetter isNewerBetter)
```

**特殊逻辑**：
- 如果条目已存在且 `isNewerBetter` 返回 true，替换数据
- 这允许更新为更高质量的版本
- 旧引用继续有效（孤立但可用）

### 资源清理

**dropUniqueRefs()**：
```cpp
void dropUniqueRefs(GrResourceCache* resourceCache)
```

**LRU 清理流程**：
1. 从链表尾部（LRU）向头部（MRU）遍历
2. 检查 `resourceCache->overBudget()`
3. 如果条目唯一持有（`uniquelyHeld()`），删除它
4. 重复直到预算满足

**dropUniqueRefsOlderThan()**：
类似流程，但检查 `fLastAccess >= purgeTime` 提前退出。

### CreateLazyView 实现

```cpp
std::tuple<GrSurfaceProxyView, sk_sp<Trampoline>>
CreateLazyView(GrDirectContext*, GrColorType, SkISize, ...)
```

**实现步骤**：
1. 获取回退颜色类型和格式
2. 创建 `Trampoline` 对象
3. 创建惰性渲染目标代理，回调函数：
   ```cpp
   [trampoline](...) {
       return trampoline->fProxy->peekTexture();
   }
   ```
4. 返回视图和 trampoline

**使用模式**：
- GPU 线程预先在缓存中放置惰性代理
- 后续排队渲染任务填充 `trampoline->fProxy`
- 延迟实例化时使用渲染结果

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|-----|---------|------|
| GrSurfaceProxyView | 存储 | 缓存的主要数据类型 |
| GrTextureProxy | 使用 | 纹理代理 |
| GrGpuBuffer | 使用 | GPU 顶点缓冲区 |
| skgpu::UniqueKey | 索引 | 缓存键 |
| GrResourceCache | 协作 | 资源预算管理 |
| GrDirectContext | 使用 | 创建惰性视图 |
| SkSpinlock | 同步 | 线程安全保护 |
| SkArenaAlloc | 内存管理 | 条目分配 |
| SkTDynamicHash | 数据结构 | 哈希表 |
| SkTInternalLList | 数据结构 | LRU 链表 |

### 被依赖的模块

| 模块 | 使用方式 | 说明 |
|-----|---------|------|
| GrDirectContext | 持有 | 直接上下文拥有缓存实例 |
| GrRecordingContext | 访问 | DDL 上下文访问缓存 |
| Skia 高层 API | 间接使用 | 通过上下文访问 |

## 设计模式与设计决策

### 线程安全策略

**细粒度锁设计**：
- 使用 `SkSpinlock` 而非 `std::mutex`
- 适合短临界区和低争用场景
- 所有公共方法使用 `SK_EXCLUDES(fSpinLock)` 注解
- 内部方法使用 `SK_REQUIRES(fSpinLock)` 注解

### LRU 缓存策略

**实现方式**：
- 链表 + 哈希表组合（经典 LRU）
- 链表维护访问顺序（头部 = MRU，尾部 = LRU）
- 哈希表提供 O(1) 查找
- 时间戳用于时间基准的清理

**清理优先级**：
```
LRU → MRU (从最旧到最新清理)
```

### 对象池模式

**fFreeEntryList 设计**：
- 避免频繁分配/释放 `Entry` 对象
- 减少内存碎片
- 提高性能（分配是锁内操作）

### Arena 分配器

**fEntryAllocator**：
- 预分配 64 * sizeof(Entry) 的栈缓冲区
- 小缓存无堆分配
- 增长时保持 64 Entry 的块大小

### CPU-GPU 渐进转换

**VertexData 设计**：
- 初始只有 CPU 数据（`fVertices`）
- 后续可设置 GPU 缓冲区（`fGpuBuffer`）
- 两者可共存（支持 DDL 去实例化）
- 引用计数管理生命周期

### 竞争胜者保留策略

**DDL 场景**：
1. DDL 线程检查缓存（未找到）
2. DDL 线程在 CPU 创建内容
3. DDL 线程尝试添加
4. 如果另一线程已添加，使用已存在的（丢弃自己的工作）

**GPU 线程优先**：
1. GPU 线程添加占位符（惰性代理）
2. DDL 线程找到占位符，使用它
3. GPU 线程异步完成渲染填充占位符

### 版本比较策略

**addVertsWithData 的 IsNewerBetter**：
- 允许替换为更高质量的版本
- 例如：低精度路径 → 高精度路径
- 自定义数据存储版本信息

## 性能考量

### 自旋锁选择

- 临界区非常短（查找、插入、LRU 更新）
- 预期争用低（多数读操作）
- 自旋锁避免上下文切换开销

### 内存局部性

**Arena 分配器优势**：
- Entry 对象连续分配
- 更好的缓存局部性
- 减少缓存缺失

**栈缓冲区优化**：
```cpp
static const int kInitialArenaSize = 64 * sizeof(Entry);
char fStorage[kInitialArenaSize];
```
小缓存完全栈分配。

### LRU 链表效率

- 双向链表支持 O(1) 移除和插入
- 只在访问时更新（不需要全局时间戳更新）
- 清理从尾部开始，通常只需遍历少数节点

### 哈希表性能

- `SkTDynamicHash` 提供 O(1) 查找
- 使用 `UniqueKey::hash()` 作为哈希函数
- 动态调整大小避免过度碰撞

### 对象复用

- `fFreeEntryList` 避免重复分配
- 减少分配器锁争用
- 减少构造/析构开销

### 预算管理

`dropUniqueRefs()` 与 `GrResourceCache` 协作：
- 只在资源缓存超预算时清理
- 优先清理线程安全缓存的唯一引用
- 保护共享资源优先于孤立资源

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/gpu/ganesh/GrSurfaceProxyView.h | 存储类型 | 缓存的视图类型 |
| src/gpu/ganesh/GrTextureProxy.h | 使用 | 纹理代理 |
| src/gpu/ganesh/GrGpuBuffer.h | 使用 | GPU 缓冲区 |
| src/gpu/ganesh/GrResourceCache.h | 协作 | 资源预算管理 |
| src/gpu/ganesh/GrDirectContext.h | 持有者 | 直接上下文 |
| src/gpu/ganesh/GrRecordingContext.h | 访问者 | 录制上下文 |
| src/gpu/ganesh/GrProxyProvider.h | 使用 | 创建惰性代理 |
| src/base/SkSpinlock.h | 同步 | 自旋锁实现 |
| src/base/SkArenaAlloc.h | 内存管理 | Arena 分配器 |
| src/core/SkTDynamicHash.h | 数据结构 | 动态哈希表 |
| src/base/SkTInternalLList.h | 数据结构 | 双向链表 |
| src/gpu/ResourceKey.h | 索引 | UniqueKey 定义 |
