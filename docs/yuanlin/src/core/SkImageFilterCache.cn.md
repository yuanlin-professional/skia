# SkImageFilterCache

> 源文件: src/core/SkImageFilterCache.h, src/core/SkImageFilterCache.cpp

## 概述

`SkImageFilterCache` 是 Skia 图形库中用于缓存图像滤镜（Image Filter）处理结果的核心组件。该缓存系统通过存储滤镜应用的中间结果，避免重复计算相同的滤镜效果，从而显著提升图像滤镜的性能表现。缓存采用 LRU（Least Recently Used）策略进行内存管理，并通过多维键值（包括滤镜 ID、变换矩阵、裁剪边界、源图像信息等）精确匹配缓存结果。

该模块的设计支持线程安全访问，使用互斥锁保护内部数据结构。缓存可以配置最大内存限制，当超过限制时自动清理最久未使用的条目。此外，系统提供了全局单例缓存和自定义缓存实例两种使用方式，满足不同场景的需求。

## 架构位置

`SkImageFilterCache` 位于 Skia 核心渲染引擎的图像处理层，属于图像滤镜处理管线的性能优化模块。它直接服务于图像滤镜系统（`SkImageFilter`），在滤镜效果应用时作为中间结果存储层使用。该模块与以下组件紧密协作：

- **图像滤镜系统（SkImageFilter）**：缓存的主要服务对象，存储滤镜处理后的结果
- **滤镜结果类型（skif::FilterResult）**：缓存存储的具体数据类型
- **特殊图像（SkSpecialImage）**：缓存结果的底层图像存储格式
- **图像滤镜类型系统（SkImageFilterTypes）**：提供滤镜类型定义和支持

该模块在图像处理管线中作为性能加速器，不参与实际的图像计算，而是通过复用已计算结果来减少 CPU/GPU 负担。

## 主要类与结构体

### SkImageFilterCacheKey

缓存键结构体，用于唯一标识一个滤镜应用操作。

**继承关系**：无（POD 结构体）

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fUniqueID | uint32_t | 图像滤镜的唯一标识符，对应特定滤镜实例 |
| fMatrix | SkMatrix | 应用滤镜时的变换矩阵（CTM） |
| fClipBounds | SkIRect | 裁剪边界矩形 |
| fSrcGenID | uint32_t | 源位图的生成 ID，用于追踪源图像变化 |
| fSrcSubset | SkIRect | 源图像的子区域矩形 |

该结构体确保紧密打包（tightly-packed），以便高效计算哈希值。构造函数会强制初始化矩阵类型并验证矩阵的有限性，保证键的比较可靠性。

### SkImageFilterCache

抽象基类，定义图像滤镜缓存接口。

**继承关系**：继承自 `SkRefCnt`（引用计数基类）

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| kDefaultTransientSize | static constexpr size_t | 默认瞬时缓存大小（32 MB） |

**主要虚函数**：
- `get()`：查询缓存，命中时返回 true 并更新结果
- `set()`：向缓存中添加滤镜处理结果
- `purge()`：清空所有缓存条目
- `purgeByImageFilter()`：清除特定图像滤镜的所有缓存结果

### CacheImpl

内部实现类，继承 `SkImageFilterCache` 并实现具体的缓存逻辑。

**继承关系**：继承自 `SkImageFilterCache`

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fLookup | SkTDynamicHash<Value, Key> | 动态哈希表，用于快速键值查找 |
| fLRU | SkTInternalLList<Value> | LRU 链表，维护访问顺序 |
| fImageFilterValues | THashMap<const SkImageFilter*, std::vector<Value*>> | 图像滤镜到缓存值的映射表 |
| fMaxBytes | size_t | 最大缓存字节数限制 |
| fCurrentBytes | size_t | 当前缓存使用的字节数 |
| fMutex | SkMutex | 互斥锁，保证线程安全 |

### CacheImpl::Value

缓存条目的内部表示，包含键、结果图像和关联滤镜。

**关键成员变量**：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fKey | Key | 缓存键（SkImageFilterCacheKey） |
| fImage | skif::FilterResult | 缓存的滤镜处理结果 |
| fFilter | const SkImageFilter* | 生成该结果的图像滤镜指针 |

## 公共 API 函数

### Create()

```cpp
static sk_sp<SkImageFilterCache> Create(size_t maxBytes)
```

**功能**：创建一个新的缓存实例，指定最大内存限制。

**参数**：
- `maxBytes`：缓存的最大字节数

**返回值**：返回智能指针指向新创建的缓存对象

**使用场景**：需要自定义缓存大小或创建独立缓存实例时使用。

### Get()

```cpp
static sk_sp<SkImageFilterCache> Get(CreateIfNecessary = CreateIfNecessary::kYes)
```

**功能**：获取全局单例缓存实例。

**参数**：
- `createIfNecessary`：枚举值，指定缓存不存在时是否创建（默认 kYes）

**返回值**：返回全局缓存实例的智能指针

**使用场景**：大多数情况下使用全局缓存实例，无需手动管理缓存生命周期。不同平台有不同的默认缓存大小：iOS 为 2 MB，其他平台为 128 MB。

### get()

```cpp
virtual bool get(const SkImageFilterCacheKey& key,
                 skif::FilterResult* result) const = 0
```

**功能**：根据键查询缓存，命中时返回结果。

**参数**：
- `key`：缓存查询键
- `result`：输出参数，缓存命中时写入结果

**返回值**：缓存命中返回 true，未命中返回 false

**线程安全**：该函数在 `CacheImpl` 中使用互斥锁保护，线程安全。访问缓存时会更新 LRU 链表，将命中条目移到链表头部。

### set()

```cpp
virtual void set(const SkImageFilterCacheKey& key, const SkImageFilter* filter,
                 const skif::FilterResult& result) = 0
```

**功能**：向缓存中添加滤镜处理结果。

**参数**：
- `key`：缓存键
- `filter`：生成结果的图像滤镜指针（用于后续清理）
- `result`：要缓存的滤镜结果

**行为**：如果键已存在，先删除旧条目再添加新条目。添加后检查缓存大小，超过限制时从 LRU 链表尾部删除旧条目。同时维护滤镜到缓存值的反向映射。

### purge()

```cpp
virtual void purge() = 0
```

**功能**：清空所有缓存条目。

**使用场景**：内存压力大时可主动清理缓存，或在测试场景中重置缓存状态。

### purgeByImageFilter()

```cpp
virtual void purgeByImageFilter(const SkImageFilter*) = 0
```

**功能**：清除特定图像滤镜的所有缓存结果。

**参数**：
- `filter`：要清除缓存的图像滤镜指针

**使用场景**：当图像滤镜对象被销毁或参数发生变化时，需要清理其相关的所有缓存结果。该函数通过 `fImageFilterValues` 映射表快速定位并删除所有相关条目。

## 内部实现细节

### 哈希表与 LRU 链表双重索引

`CacheImpl` 采用哈希表和双向链表的组合数据结构：

- **哈希表（fLookup）**：使用 `SkTDynamicHash` 实现 O(1) 的键值查找
- **LRU 链表（fLRU）**：使用 `SkTInternalLList` 维护访问顺序，新访问或新添加的条目移至链表头部，尾部为最久未使用的条目

这种设计兼顾了查找速度和淘汰效率：查询时通过哈希表快速定位，淘汰时直接从链表尾部移除。

### 键的哈希计算

缓存键的哈希值通过 `SkChecksum::Hash32()` 计算整个结构体的内存布局。为保证哈希结果的一致性：

1. 结构体使用 `static_assert` 验证紧密打包，避免填充字节影响哈希
2. 构造函数中调用 `fMatrix.getType()` 强制初始化矩阵类型字段
3. 验证矩阵的有限性（`isFinite()`），确保浮点数比较可靠

### 滤镜到缓存值的反向映射

`fImageFilterValues` 维护从 `SkImageFilter` 指针到其所有缓存条目的映射。这样当滤镜对象销毁时，可以高效地清理所有相关缓存，避免悬空指针和内存泄漏。删除缓存条目时需要同步更新该映射表。

### 内存管理与淘汰策略

缓存使用字节数计数（`fCurrentBytes`）跟踪内存使用：

1. 添加条目时累加图像大小（`result.image()->getSize()`）
2. 超过 `fMaxBytes` 限制时，循环删除 LRU 链表尾部条目
3. 特殊处理：刚添加的条目即使超过限制也不会被立即删除

### 线程安全机制

所有公共接口在 `CacheImpl` 中使用 `SkAutoMutexExclusive` 进行互斥锁保护，支持多线程并发访问。`fMutex` 声明为 `mutable`，允许在 `const` 方法中加锁。

### 全局单例的惰性初始化

`Get()` 函数使用 `SkOnce` 保证线程安全的单次初始化。首次调用时创建全局缓存对象，后续调用直接返回引用。支持 `CreateIfNecessary::kNo` 参数查询缓存是否已创建。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkRefCnt | 提供引用计数基类，管理缓存对象生命周期 |
| SkMatrix | 表示变换矩阵，作为缓存键的一部分 |
| SkRect/SkIRect | 表示矩形区域，用于裁剪边界和子区域 |
| skif::FilterResult | 存储滤镜处理结果的数据类型 |
| SkImageFilter | 图像滤镜接口，缓存的服务对象 |
| SkMutex | 提供互斥锁，保证线程安全 |
| SkOnce | 提供单次初始化工具，用于全局单例 |
| SkTDynamicHash | 动态哈希表容器，用于快速查找 |
| SkTInternalLList | 双向链表容器，维护 LRU 顺序 |
| THashMap | 哈希映射容器，维护滤镜到缓存值的映射 |
| SkChecksum | 提供哈希计算函数 |
| SkSpecialImage | 特殊图像类型，缓存结果的底层存储 |

### 被依赖的模块

| 模块 | 关系说明 |
|------|---------|
| SkImageFilter | 图像滤镜系统使用缓存存储和检索处理结果 |
| 图像滤镜子类 | 各种具体滤镜实现（如模糊、颜色矩阵等）通过缓存提升性能 |
| 滤镜处理管线 | 滤镜效果组合和应用时依赖缓存避免重复计算 |

## 设计模式与设计决策

### 抽象工厂模式

`SkImageFilterCache` 定义抽象接口，`CacheImpl` 提供具体实现。通过 `Create()` 工厂方法创建实例，隐藏实现细节，便于后续扩展其他缓存策略（如多级缓存、持久化缓存等）。

### 单例模式

`Get()` 方法提供全局单例访问，配合 `SkOnce` 实现线程安全的惰性初始化。这种设计简化了大多数场景的使用，避免手动管理缓存实例。

### 策略模式

通过 `CreateIfNecessary` 枚举参数，`Get()` 方法支持两种策略：按需创建或仅查询。这种设计允许调用者在不同场景下灵活控制缓存的创建时机。

### 桥接模式（Pimpl）

头文件仅暴露抽象接口，具体实现类 `CacheImpl` 定义在 `.cpp` 文件的匿名命名空间中。这种设计隔离了实现细节，减少编译依赖，提升封装性。

### 设计决策：键的精细粒度

缓存键包含五个维度：滤镜 ID、变换矩阵、裁剪边界、源生成 ID 和源子区域。这种精细粒度的设计确保：

1. **正确性**：任何参数变化都会导致缓存未命中，避免返回错误结果
2. **命中率**：相同参数的滤镜应用能够精确匹配缓存
3. **注意事项**：缓存绑定到特定滤镜实例（通过 `fUniqueID`），即使参数完全相同的滤镜副本也无法共享缓存

### 设计决策：滤镜指针的维护

`set()` 方法中存储滤镜指针，`purgeByImageFilter()` 时需要清理。这种设计的权衡：

- **优点**：滤镜销毁时能够自动清理缓存，避免悬空指针
- **缺点**：需要额外的反向映射表（`fImageFilterValues`），增加内存开销和维护复杂度
- **实现细节**：删除条目时将 `fFilter` 置空，避免迭代器失效问题

### 设计决策：平台差异化的缓存大小

iOS 平台默认 2 MB 缓存，其他平台 128 MB。这种设计考虑了移动设备的内存限制，平衡性能和资源占用。

## 性能考量

### 时间复杂度

- **查询（get）**：O(1) 平均时间，哈希表查找 + LRU 链表调整
- **插入（set）**：O(1) 平均时间，可能触发淘汰时为 O(k)，k 为需淘汰的条目数
- **清理（purgeByImageFilter）**：O(n)，n 为该滤镜的缓存条目数

### 空间复杂度

- 主要开销：缓存图像本身（受 `fMaxBytes` 限制）
- 辅助结构：哈希表、LRU 链表、反向映射表的元数据开销

### 缓存命中率影响因素

1. **滤镜参数稳定性**：参数频繁变化导致命中率下降
2. **图像内容变化**：源图像生成 ID 变化使缓存失效
3. **变换矩阵变化**：动画场景中 CTM 持续变化降低命中率
4. **内存限制**：缓存过小导致频繁淘汰，限制过大占用过多内存

### 线程竞争

互斥锁保护整个缓存操作，高并发场景下可能成为瓶颈。未来优化方向可考虑细粒度锁或无锁数据结构。

### 内存局部性

LRU 链表按访问顺序组织，热点数据集中在链表头部，有利于 CPU 缓存局部性。哈希表采用开放寻址法，内存访问模式较为友好。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| include/core/SkImageFilter.h | 图像滤镜抽象基类，缓存的主要服务对象 |
| src/core/SkImageFilterTypes.h | 图像滤镜类型定义和支持工具 |
| src/core/SkSpecialImage.h | 特殊图像类型，缓存结果的底层存储格式 |
| src/base/SkTInternalLList.h | 双向链表容器实现，用于 LRU 链表 |
| src/core/SkTDynamicHash.h | 动态哈希表容器实现，用于快速查找 |
| src/core/SkTHash.h | 哈希映射容器实现，用于反向映射表 |
| src/core/SkChecksum.h | 哈希计算工具，用于缓存键的哈希 |
| include/private/base/SkMutex.h | 互斥锁实现，保证线程安全 |
| include/private/base/SkOnce.h | 单次初始化工具，用于全局单例 |
| include/core/SkMatrix.h | 变换矩阵类型，缓存键的组成部分 |
| include/core/SkRect.h | 矩形类型，用于裁剪边界和子区域 |
