# TextStrike

> 源文件
> - `src/gpu/graphite/text/TextStrike.h`
> - `src/gpu/graphite/text/TextStrike.cpp`

## 概述

`TextStrike` 是 Skia Graphite 文本渲染系统中用于管理字形缓存的核心类。它为特定的字体 strike（字体、大小、变换的组合）维护一个 `GlyphEntry` 对象的哈希表缓存。该类继承自 `sktext::gpu::TextStrikeBase`，提供字形查找和创建功能，避免重复生成已渲染的字形数据。通过 `StrikeCache` 管理多个 `TextStrike` 实例，实现全局字形缓存复用。

## 架构位置

`TextStrike` 位于 Graphite 文本渲染的缓存管理层：

```
skgpu::graphite 文本渲染架构
    ├── sktext::gpu::StrikeCache (全局 strike 缓存管理器)
    │    └── TextStrike (单个字体 strike 的字形缓存)
    │         └── THashTable<GlyphEntry*> (字形哈希表)
    │              └── GlyphEntry (单个字形的缓存数据)
    └── 文本渲染管线使用 TextStrike 查找字形
```

它在文本绘制流程中负责字形级别的缓存查找和生命周期管理。

## 主要类与结构体

### TextStrike

```cpp
class TextStrike final : public sktext::gpu::TextStrikeBase
```

**核心成员变量：**
- `THashTable<GlyphEntry*, GlyphEntryKey, HashTraits> fCache` - 字形条目哈希表
- 继承自 `TextStrikeBase`：
  - `SkArenaAlloc fAlloc` - 内存分配器（用于分配 `GlyphEntry`）
  - `sk_sp<SkStrike> fStrike` - 关联的 Skia strike 对象
  - 内存使用量跟踪

**核心方法：**
- `static sk_sp<TextStrike> GetOrCreate()` - 获取或创建 strike 实例
- `GlyphEntry* getGlyph()` - 查找或创建字形条目

### HashTraits

```cpp
struct HashTraits
```

为 `THashTable` 提供键提取和哈希函数：
- `static const GlyphEntryKey& GetKey(const GlyphEntry* glyph)` - 从 `GlyphEntry` 提取键
- `static uint32_t Hash(GlyphEntryKey key)` - 计算键的哈希值

## 公共 API 函数

### Strike 获取或创建

```cpp
static sk_sp<TextStrike> GetOrCreate(
    sktext::gpu::StrikeCache* strikeCache,
    const SkStrikeSpec& strikeSpec
)
```

获取或创建指定 strike 规格的 `TextStrike` 实例。

**参数：**
- `strikeCache` - 全局 strike 缓存管理器
- `strikeSpec` - strike 规格（包含字体、大小、变换等信息）

**返回值：**
智能指针指向 `TextStrike` 实例（可能是已存在的或新创建的）。

**实现流程：**
1. 调用 `Find(strikeCache, strikeSpec.descriptor())` 查找已存在的 strike
2. 如果找到，转换为 `TextStrike*` 并返回
3. 如果未找到，创建新的 `TextStrike` 并调用 `Add()` 加入缓存

### 字形查找

```cpp
GlyphEntry* getGlyph(SkPackedGlyphID packedGlyphID, MaskFormat format)
```

查找或创建指定字形 ID 和遮罩格式的字形条目。

**参数：**
- `packedGlyphID` - 打包的字形 ID（包含子像素位置等信息）
- `format` - 遮罩格式（如 A8、ARGB、LCD 等）

**返回值：**
指向 `GlyphEntry` 的指针（永不为 nullptr）。

**实现流程：**
1. 使用 `GlyphEntryKey(packedGlyphID, format)` 构造查找键
2. 在 `fCache` 哈希表中查找
3. 如果找到，直接返回
4. 如果未找到：
   - 使用 `fAlloc.make<GlyphEntry>()` 分配新条目
   - 插入 `fCache` 哈希表
   - 更新内存使用量统计
   - 返回新创建的条目

## 内部实现细节

### 构造函数

```cpp
TextStrike::TextStrike(sktext::gpu::StrikeCache* strikeCache, const SkStrikeSpec& strikeSpec)
        : TextStrikeBase(strikeCache, strikeSpec)
```

通过调用基类构造函数初始化，基类负责创建关联的 `SkStrike` 对象和内存分配器。

### 哈希表实现

```cpp
skia_private::THashTable<GlyphEntry*, GlyphEntryKey, HashTraits> fCache
```

**键（Key）：** `GlyphEntryKey`，由 `SkPackedGlyphID` 和 `MaskFormat` 组成
**值（Value）：** `GlyphEntry*` 指针，指向分配器中的字形数据

哈希表使用自定义 `HashTraits` 提供键提取和哈希计算：
```cpp
const GlyphEntryKey& HashTraits::GetKey(const GlyphEntry* glyph) {
    return glyph->fGlyphEntryKey;
}

uint32_t HashTraits::Hash(GlyphEntryKey key) {
    return key.hash();
}
```

### 内存管理

- **分配器**：使用 `SkArenaAlloc`（来自基类）进行块分配，避免频繁的小对象分配
- **生命周期**：`GlyphEntry` 对象的生命周期与 `TextStrike` 绑定，strike 销毁时所有字形一起释放
- **内存跟踪**：通过 `addMemoryUsed()` 跟踪内存使用量，用于缓存淘汰策略

### 缓存查找优化

```cpp
GlyphEntry* glyph = fCache.findOrNull(localKey);
if (glyph == nullptr) {
    // 创建新条目的慢速路径
}
```

使用 `findOrNull()` 进行快速查找，命中缓存时避免任何分配操作。

## 依赖关系

**直接依赖：**
- `sktext::gpu::TextStrikeBase` - 基类，提供基础 strike 功能
- `sktext::gpu::StrikeCache` - Strike 缓存管理器
- `GlyphEntry` - 字形条目数据结构（定义在 `GlyphData.h`）
- `GlyphEntryKey` - 字形条目的键（定义在 `GlyphData.h`）
- `SkStrikeSpec` - Strike 规格描述
- `SkPackedGlyphID` - 打包的字形 ID
- `MaskFormat` - 遮罩格式枚举

**被依赖者：**
- Graphite 文本渲染器 - 使用 `TextStrike` 查找字形
- `StrikeCache` - 管理 `TextStrike` 实例的生命周期
- 文本绘制操作 - 通过 `getGlyph()` 获取字形数据

## 设计模式与设计决策

### 单例化 Strike（通过 StrikeCache）
每个 `SkStrikeSpec` 在全局 `StrikeCache` 中只有一个对应的 `TextStrike` 实例，避免重复缓存相同字形。

### 惰性创建（Lazy Creation）
字形条目仅在首次请求时创建，未使用的字形不占用内存。

### 工厂模式
`GetOrCreate()` 静态方法封装创建逻辑，客户端代码不直接构造 `TextStrike` 对象。

### 基于分配器的内存管理
使用 `SkArenaAlloc` 进行块分配，优点：
- 批量分配减少内存碎片
- 批量释放（strike 销毁时）非常高效
- 无需逐个释放字形对象

### 哈希表而非数组
选择哈希表而非数组是因为字形 ID 空间稀疏（Unicode 范围 + 子像素位置），哈希表提供 O(1) 查找且内存占用与实际使用字形数成正比。

### 键包含格式信息
`GlyphEntryKey` 同时包含 `SkPackedGlyphID` 和 `MaskFormat`，因为同一字形可能以不同格式渲染（如彩色字形 vs. 灰度遮罩）。

## 性能考量

1. **哈希表查找**
   O(1) 平均时间复杂度，命中缓存时无任何分配操作。

2. **内存局部性**
   `SkArenaAlloc` 顺序分配 `GlyphEntry` 对象，提高缓存命中率。

3. **避免锁竞争**
   `TextStrike` 本身不包含同步原语，由上层 `StrikeCache` 处理多线程访问（如需要）。

4. **内存跟踪**
   记录每个 strike 的内存使用量，支持 LRU 或基于大小的缓存淘汰策略。

5. **友元访问优化**
   声明 `StrikeCache` 为友元，允许缓存管理器直接访问内部状态，避免不必要的访问器开销。

6. **引用计数**
   使用 `sk_sp` 智能指针管理 `TextStrike` 生命周期，自动引用计数避免手动内存管理。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `src/text/gpu/StrikeCache.h` | Strike 缓存管理器基类 |
| `src/gpu/graphite/text/GlyphData.h` | GlyphEntry 和 GlyphEntryKey 定义 |
| `src/core/SkStrikeSpec.h` | Strike 规格描述 |
| `src/core/SkGlyph.h` | 字形基础数据结构 |
| `src/core/SkTHash.h` | THashTable 哈希表实现 |
| `src/gpu/MaskFormat.h` | 遮罩格式枚举定义 |
| `include/core/SkRefCnt.h` | 引用计数基类 |
