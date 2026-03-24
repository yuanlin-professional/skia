# PipelineData

> 源文件
> - src/gpu/graphite/PipelineData.h

## 概述

`PipelineData.h` 定义了 Skia Graphite 渲染引擎中用于管理管线数据（uniform、纹理、图形管线描述）的核心数据结构和缓存机制。该文件包含了三个主要组件：

1. **UniformDataBlock / TextureDataBlock**：封装 uniform 数据和纹理绑定的不可变块
2. **DenseBiMap**：高效的双向映射模板，用于去重和索引
3. **UniformDataCache / TextureDataCache / GraphicsPipelineCache**：基于 `DenseBiMap` 的缓存系统

这些结构支持高效的数据去重、快速查找和内存管理，是 Graphite 渲染管线优化的关键组件。

## 架构位置

```
PipelineDataGatherer (收集 uniform 和纹理)
  ├── UniformDataBlock (uniform 数据块)
  ├── TextureDataBlock (纹理绑定块)
  └── Caches
      ├── UniformDataCache (去重 uniform 数据)
      ├── TextureDataCache (去重纹理绑定)
      └── GraphicsPipelineCache (去重管线描述)
```

这些数据结构位于渲染管线的核心，连接数据收集和 GPU 资源绑定。

## 主要类与结构体

### UniformDataBlock

```cpp
class UniformDataBlock {
public:
    static UniformDataBlock Make(UniformDataBlock toClone, SkArenaAlloc* arena);
    static UniformDataBlock Wrap(UniformManager* uniforms);
    static UniformDataBlock WrapNonShading(UniformManager* uniforms);

    bool empty() const;
    const char* data() const;
    size_t size() const;

    bool operator==(UniformDataBlock that) const;
    struct Hash { uint32_t operator()(UniformDataBlock) const; };

private:
    SkSpan<const char> fData;  // 数据由外部拥有
};
```

**用途**：封装对齐的 uniform 数据

**关键特性**：
- **不拥有数据**：`fData` 指向 `UniformManager` 或 arena 的内存
- **相等性比较**：按位比较（`memcmp`）
- **哈希计算**：`SkChecksum::Hash32` 基于数据内容

**工厂方法**：
- `Wrap`：包装 `UniformManager::finish()` 的数据
- `WrapNonShading`：包装 `UniformManager::finishMarked()` 的数据
- `Make`：在 arena 中克隆数据

### TextureDataBlock

```cpp
class TextureDataBlock {
public:
    using SampledTexture = std::pair<sk_sp<TextureProxy>, SamplerDesc>;

    static TextureDataBlock Make(TextureDataBlock toClone, SkArenaAlloc* arena);

    bool empty() const;
    int numTextures() const;
    const SampledTexture& texture(int index) const;

    bool operator==(TextureDataBlock other) const;
    struct Hash { uint32_t operator()(TextureDataBlock) const; };

private:
    SkSpan<const SampledTexture> fTextures;  // 数据由外部拥有
};
```

**用途**：封装纹理代理和采样器描述的列表

**哈希策略**：
```cpp
for (auto& [proxy, samplerDesc] : fTextures) {
    hash = Hash32(&samplerDesc, sizeof(samplerDesc), hash);
    hash = Hash32(&proxy指针, sizeof(uintptr_t), hash);
}
```

**理由**：生命周期短（单个 Recording），可以安全使用指针地址哈希

### DenseBiMap

```cpp
template <typename K,                  // 插入的键类型
          typename V = K,              // 存储的值类型
          typename S = std::monostate, // 可选的存储管理器
          typename H = SkGoodHash>     // 哈希函数
class DenseBiMap {
public:
    using Index = uint32_t;
    static constexpr Index kInvalidIndex = 4096;

    Index insert(K data);
    bool contains(K data) const;
    const V& lookup(Index index) const;
    V& lookup(Index index);
    int count() const;
    void reset();

    skia_private::TArray<V>&& detach();
    const skia_private::TArray<V>& get() const;

    // 如果 S 非 monostate，提供存储访问
    const S& storage() const;
    S& storage();
};
```

**核心功能**：

1. **K → Index 映射**：哈希表查找
2. **Index → V 映射**：连续数组存储
3. **去重**：相同的 K 返回相同的 Index
4. **持久化**：如果提供 S，调用 `S::persist(K)` 持久化数据

**存储管理器接口**：
```cpp
struct Storage {
    K persist(K data) {
        // 将 data 复制到持久存储并返回新引用
    }
};
```

**使用模式**：

```cpp
DenseBiMap<UniformDataBlock, Entry, UniformCopier, UniformDataBlock::Hash> cache;

Index idx = cache.insert(dataBlock);  // 第一次：分配新索引，调用 persist
Index idx2 = cache.insert(dataBlock); // 重复：返回相同索引
const Entry& entry = cache.lookup(idx);
```

### UniformDataCache

```cpp
class UniformDataCache {
public:
    struct Entry {
        UniformDataBlock fCpuData;
        BindBufferInfo fBufferBinding;  // GPU 缓冲区绑定（稍后填充）
    };

    using Index = uint32_t;
    static constexpr Index kInvalidIndex = 4096;

    Index insert(UniformDataBlock dataBlock);
    const Entry& lookup(Index index) const;
    Entry& lookup(Index index);
    void reset();
};
```

**实现**：
```cpp
struct UniformCopier {
    UniformDataBlock persist(UniformDataBlock data) {
        return UniformDataBlock::Make(data, &fArena);
    }
    SkArenaAlloc fArena{0};
};
using UniformDataMap = DenseBiMap<UniformDataBlock, Entry, UniformCopier, ...>;
```

**去重流程**：

1. 插入 `UniformDataBlock`
2. 检查哈希表是否已存在
3. 如果不存在：
   - 调用 `UniformCopier::persist` 复制数据到 arena
   - 创建新 `Entry`
   - 分配新索引
4. 返回索引

### TextureDataCache

```cpp
class TextureDataCache {
public:
    using Index = uint32_t;
    static constexpr Index kInvalidIndex = 4096;

    Index insert(TextureDataBlock textures);
    const TextureDataBlock& lookup(Index index) const;
    void reset();

    skia_private::TArray<sk_sp<TextureProxy>>&& detachUniqueProxies();
};
```

**实现**：
```cpp
struct TextureCopier {
    TextureDataBlock persist(TextureDataBlock textures) {
        // 1. 将所有纹理代理插入 fUniqueTextures（去重）
        for (int i = 0; i < textures.numTextures(); ++i) {
            fUniqueTextures.insert(textures.texture(i).first.get());
        }
        // 2. 复制 TextureDataBlock 到 arena
        return TextureDataBlock::Make(textures, &fArena);
    }

    TextureProxyCache fUniqueTextures;  // 去重的纹理代理集合
    SkArenaAlloc fArena{0};
};
```

**双重去重**：
1. **TextureDataBlock 去重**：避免重复的纹理绑定组合
2. **TextureProxy 去重**：收集所有唯一的纹理代理

**用途**：
- `detachUniqueProxies()`：获取所有需要的纹理代理列表，用于资源准备

### GraphicsPipelineCache

```cpp
using GraphicsPipelineCache = DenseBiMap<GraphicsPipelineDesc>;
```

**用途**：去重图形管线描述

**特殊性**：K = V（不需要转换），无存储管理器

## 公共 API 函数

### UniformDataBlock

#### Wrap

```cpp
static UniformDataBlock Wrap(UniformManager* uniforms);
```

**功能**：包装 `UniformManager::finish()` 返回的数据

#### WrapNonShading

```cpp
static UniformDataBlock WrapNonShading(UniformManager* uniforms);
```

**功能**：包装 `UniformManager::finishMarked()` 返回的标记数据

**用途**：区分着色和非着色 uniform

#### Make

```cpp
static UniformDataBlock Make(UniformDataBlock toClone, SkArenaAlloc* arena);
```

**功能**：在 arena 中复制数据，返回持久化的块

### DenseBiMap

#### insert

```cpp
Index insert(K data);
```

**功能**：插入数据，返回索引（已存在则返回现有索引）

**去重保证**：相同的 `data`（按 `operator==` 判断）总是返回相同的索引

#### lookup

```cpp
const V& lookup(Index index) const;
V& lookup(Index index);
```

**功能**：根据索引查找值

#### detach

```cpp
skia_private::TArray<V>&& detach();
```

**功能**：移出内部数组（清空 map）

**用途**：转移所有权给调用方

### UniformDataCache

#### insert

```cpp
Index insert(UniformDataBlock dataBlock);
```

**功能**：插入 uniform 数据块，返回缓存索引

**副作用**：首次插入时复制数据到内部 arena

#### lookup

```cpp
const Entry& lookup(Index index) const;
Entry& lookup(Index index);
```

**功能**：查找缓存条目

**用途**：
- 读取 CPU 数据（`fCpuData`）
- 写入 GPU 绑定信息（`fBufferBinding`）

### TextureDataCache

#### insert

```cpp
Index insert(TextureDataBlock textures);
```

**功能**：插入纹理绑定块，返回缓存索引

**副作用**：
- 复制 `TextureDataBlock` 到 arena
- 将所有纹理代理插入唯一代理集合

#### detachUniqueProxies

```cpp
skia_private::TArray<sk_sp<TextureProxy>>&& detachUniqueProxies();
```

**功能**：获取所有唯一纹理代理的列表

**用途**：资源准备阶段，确保所有需要的纹理已实例化

## 内部实现细节

### 哈希表 + 连续数组

`DenseBiMap` 使用双重数据结构：

```cpp
skia_private::THashMap<K, Index, H> fDataToIndex;  // K → Index 快速查找
skia_private::TArray<V> fIndexToData;               // Index → V 连续存储
```

**优势**：
- 查找：O(1) 平均时间
- 遍历：缓存友好的连续内存
- 去重：哈希表自动去重

### 数据持久化

`DenseBiMap` 的 insert 逻辑：

```cpp
Index insert(K data) {
    Index* index = fDataToIndex.find(data);
    if (!index) {
        // 持久化数据（如果需要）
        if constexpr (!std::is_same_v<S, std::monostate>) {
            data = fStorage.persist(data);  // 调用存储管理器
        }

        index = fDataToIndex.set(data, fIndexToData.size());
        fIndexToData.emplace_back(data);  // V(K) 构造
    }
    return *index;
}
```

### UniformDataBlock 相等性比较

```cpp
bool operator==(UniformDataBlock that) const {
    return this->size() == that.size() &&
           (this->data() == that.data() ||  // 快捷路径：相同指针
            memcmp(this->data(), that.data(), this->size()) == 0);
}
```

**优化**：
1. 先比较大小（快速失败）
2. 指针相等检查（相同数据）
3. 逐字节比较（`memcmp`）

### TextureDataBlock 哈希计算

```cpp
uint32_t Hash::operator()(TextureDataBlock block) const {
    uint32_t hash = 0;
    for (auto& [proxy, samplerDesc] : block.fTextures) {
        hash = SkChecksum::Hash32(&samplerDesc, sizeof(samplerDesc), hash);
        uintptr_t proxyPtr = reinterpret_cast<uintptr_t>(proxy.get());
        hash = SkChecksum::Hash32(&proxyPtr, sizeof(proxyPtr), hash);
    }
    return hash;
}
```

**关键点**：使用代理指针而非代理内容

**安全性**：生命周期保证（Recording 范围内）

## 依赖关系

### 核心依赖

| 依赖项 | 作用 |
|--------|------|
| `UniformManager` | 生成对齐的 uniform 数据 |
| `TextureProxy` | 纹理代理 |
| `SkArenaAlloc` | Arena 分配器 |
| `SkChecksum` | 哈希计算 |

### 工具类

| 类型 | 用途 |
|------|------|
| `SkSpan` | 轻量级数组视图 |
| `skia_private::THashMap` | 哈希表 |
| `skia_private::TArray` | 动态数组 |

## 设计模式与设计决策

### 1. 享元模式（Flyweight）

通过缓存去重相同的数据块，多个绘制调用共享相同的 uniform/纹理数据。

### 2. 代理模式

`UniformDataBlock` 和 `TextureDataBlock` 不拥有数据，仅持有视图。

### 3. 工厂模式

静态工厂方法 `Make`、`Wrap` 控制对象创建。

### 4. 策略模式

`DenseBiMap` 通过模板参数 S 支持可选的存储管理策略。

### 5. 双向映射

`DenseBiMap` 提供 K → Index 和 Index → V 的双向查找。

### 6. Arena 分配

使用 `SkArenaAlloc` 批量分配，避免频繁的 malloc/free。

## 性能考量

### 去重效率

1. **哈希表查找**：O(1) 平均时间
2. **快速相等性**：先比较大小和指针
3. **高效哈希**：`SkChecksum::Hash32` 优化

### 内存管理

1. **Arena 分配**：减少碎片和分配开销
2. **共享数据**：去重减少内存使用
3. **移动语义**：`detach()` 零拷贝转移所有权

### 缓存友好

1. **连续存储**：`TArray` 遍历缓存友好
2. **索引访问**：紧凑的 `uint32_t` 索引

### 指针哈希合理性

对于 `TextureDataBlock`，使用代理指针哈希是安全的：
- 生命周期：单个 Recording
- 引用计数：`sk_sp` 保持代理存活
- 唯一性：相同代理有相同指针

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `src/gpu/graphite/UniformManager.h` | Uniform 管理器 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/graphite/BufferManager.h` | 缓冲区管理器 |
| `src/gpu/graphite/GraphicsPipelineDesc.h` | 图形管线描述 |
| `src/gpu/graphite/DrawTypes.h` | 绘制类型定义 |
| `src/base/SkArenaAlloc.h` | Arena 分配器 |
| `src/core/SkChecksum.h` | 哈希计算 |
| `src/core/SkTHash.h` | 哈希表 |
