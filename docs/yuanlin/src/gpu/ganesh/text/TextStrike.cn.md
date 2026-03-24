# TextStrike

> 源文件
> - `src/gpu/ganesh/text/TextStrike.h`
> - `src/gpu/ganesh/text/TextStrike.cpp`

## 概述

`TextStrike` 是 Ganesh 文本渲染系统中的特定字体 Strike 缓存条目,继承自 `sktext::gpu::TextStrikeBase`。它管理特定字体规格(font strike)的 `GlyphEntry` 对象缓存,每个 `GlyphEntry` 将 `SkPackedGlyphID` 和 `MaskFormat` 映射到文本图集系统中的位置。该类通过哈希表提供高效的字形查找和创建,是字形从 CPU Strike 到 GPU 图集的关键桥梁。

## 架构位置

`TextStrike` 位于 Skia GPU 文本渲染管线的字形缓存层:

```
Skia 文本渲染架构
├── 字体管理层
│   ├── SkStrikeSpec (字体规格描述)
│   └── SkStrike (CPU 字形缓存)
├── GPU 字形缓存层
│   ├── StrikeCache (Strike 缓存管理器)
│   ├── TextStrikeBase (基类,跨平台)
│   └── TextStrike (Ganesh 特定实现) ← 当前类
├── 字形数据层
│   ├── GlyphEntry (字形条目)
│   ├── GlyphEntryKey (字形键)
│   └── GlyphData (字形数据管理器)
└── 图集管理层
    └── GrAtlasManager (图集管理器)
```

该类是 Ganesh 后端特定的字形缓存实现,为上层提供类型安全的字形访问。

## 主要类与结构体

### 继承关系

| 类名 | 关系 | 说明 |
|------|------|------|
| `sktext::gpu::TextStrikeBase` | 父类 | 跨平台 GPU Strike 基类 |
| `TextStrike` | 当前类 | Ganesh 特定 Strike 实现 |

### 内部嵌套类型

| 类型 | 说明 |
|------|------|
| `HashTraits` | 哈希表特征类,定义键提取和哈希函数 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCache` | `skia_private::THashTable<GlyphEntry*, GlyphEntryKey, HashTraits>` | 字形条目哈希表 |
| `fAlloc` | `SkArenaAlloc` (继承自基类) | 字形条目内存分配器 |
| `fStrikeSpec` | `SkStrikeSpec` (继承自基类) | 关联的字体规格 |

## 公共 API 函数

### 构造函数

```cpp
TextStrike(sktext::gpu::StrikeCache* strikeCache, const SkStrikeSpec& strikeSpec);
```
创建新的 TextStrike 实例,关联到 StrikeCache 和特定字体规格。

### 静态工厂函数

```cpp
static sk_sp<TextStrike> GetOrCreate(sktext::gpu::StrikeCache* strikeCache,
                                      const SkStrikeSpec& strikeSpec);
```
从 StrikeCache 获取已存在的 TextStrike,或创建新实例。

**实现逻辑:**
```cpp
auto existingStrike = Find(strikeCache, strikeSpec.descriptor());
if (existingStrike) {
    return sk_ref_sp(static_cast<TextStrike*>(existingStrike.get()));
}
auto newStrike = sk_make_sp<TextStrike>(strikeCache, strikeSpec);
Add(strikeCache, newStrike);
return newStrike;
```

### 字形访问

```cpp
GlyphEntry* getGlyph(SkPackedGlyphID packedGlyphID, MaskFormat format);
```
获取或创建 GlyphEntry。如果缓存中不存在,则使用 Arena 分配器创建新条目并添加到哈希表。

**实现细节:**
```cpp
GlyphEntryKey localKey(packedGlyphID, format);
GlyphEntry* glyph = fCache.findOrNull(localKey);
if (glyph == nullptr) {
    glyph = fAlloc.make<GlyphEntry>(packedGlyphID, format);
    fCache.set(glyph);
    this->addMemoryUsed(sizeof(GlyphEntry));  // 跟踪内存使用
}
return glyph;
```

## 内部实现细节

### HashTraits 实现

```cpp
struct HashTraits {
    static const GlyphEntryKey& GetKey(const GlyphEntry* glyph) {
        return glyph->fGlyphEntryKey;
    }

    static uint32_t Hash(GlyphEntryKey key) {
        return key.hash();  // 委托给 GlyphEntryKey::hash()
    }
};
```

**设计要点:**
- 哈希表存储 `GlyphEntry*` 指针,避免值拷贝
- 键提取函数从条目中提取 `GlyphEntryKey`
- 哈希函数使用 `SkPackedGlyphID` 的内置哈希

### 内存管理策略

**Arena 分配器**:
```cpp
glyph = fAlloc.make<GlyphEntry>(packedGlyphID, format);
```
- 使用 `SkArenaAlloc` 批量分配,避免单个 `new`/`delete` 开销
- 字形条目生命周期绑定到 Strike,统一释放
- 内存紧凑排列,提升缓存命中率

**内存跟踪**:
```cpp
this->addMemoryUsed(sizeof(GlyphEntry));
```
跟踪总内存使用,支持缓存驱逐策略。

### 键的复合性

`GlyphEntryKey` 由两部分组成:
```cpp
struct GlyphEntryKey {
    const SkPackedGlyphID fPackedID;  // 字形 ID
    MaskFormat fFormat;                // 掩码格式(A8/A565/ARGB)
};
```

**为何需要 MaskFormat:**
同一字形在不同渲染模式下需要不同图集条目:
- A8 格式: 普通抗锯齿文本
- A565 格式: LCD 子像素渲染
- ARGB 格式: 彩色 emoji 或位图字体

### 查找流程

```
getGlyph(packedGlyphID, format)
    ↓
创建临时 GlyphEntryKey(packedGlyphID, format)
    ↓
fCache.findOrNull(key) → 哈希查找
    ↓
命中 → 返回已有 GlyphEntry*
    ↓
未命中 → fAlloc.make<GlyphEntry>() → fCache.set() → 跟踪内存
    ↓
返回新 GlyphEntry*
```

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `sktext::gpu::TextStrikeBase` | 继承 | 提供基础 Strike 功能和生命周期管理 |
| `sktext::gpu::StrikeCache` | 强依赖 | Strike 缓存管理器,查找和注册 Strike |
| `GlyphEntry` | 强依赖 | 存储的数据类型 |
| `GlyphEntryKey` | 强依赖 | 哈希表键类型 |
| `SkStrikeSpec` | 强依赖 | 字体规格描述符 |
| `skia_private::THashTable` | 容器 | 高性能哈希表实现 |
| `SkArenaAlloc` | 工具 | Arena 内存分配器(继承自基类) |

### 被依赖的模块

| 模块 | 使用场景 |
|------|---------|
| `GlyphData` | 通过 `FindStrike` 获取 TextStrike |
| `StrikeCache` | 管理 TextStrike 的生命周期 |
| 文本渲染管线 | 通过 GlyphData 间接访问 TextStrike |

## 设计模式与设计决策

### 工厂方法模式

`GetOrCreate` 静态方法封装查找和创建逻辑:
```cpp
static sk_sp<TextStrike> GetOrCreate(StrikeCache*, const SkStrikeSpec&);
```
- 统一的创建接口,确保 Strike 正确注册到 StrikeCache
- 返回智能指针,自动管理生命周期
- 避免重复创建相同规格的 Strike

### 延迟创建

字形条目仅在首次访问时创建:
```cpp
if (glyph == nullptr) {
    glyph = fAlloc.make<GlyphEntry>(packedGlyphID, format);
}
```
- 避免预分配所有可能字形
- 按需创建,减少内存占用

### 类型安全封装

Ganesh 特定的 `TextStrike` 类型封装:
```cpp
return sk_ref_sp(static_cast<TextStrike*>(existingStrike.get()));
```
- 基类 `TextStrikeBase` 提供通用接口
- 派生类提供类型安全的 Ganesh 特定 API(`getGlyph` 返回 `GlyphEntry*`)

### 内存池化

使用 Arena 分配器池化小对象分配:
- 避免频繁的堆分配/释放
- 提升内存局部性
- 统一释放,无需单独析构

### 友元访问控制

```cpp
friend class sktext::gpu::StrikeCache;
```
限制 StrikeCache 访问内部成员,确保 Strike 生命周期由 StrikeCache 管理。

## 性能考量

### 哈希表优化

**高效哈希函数**:
```cpp
uint32_t Hash(GlyphEntryKey key) {
    return key.hash();  // 使用 SkPackedGlyphID 的内置哈希
}
```
`SkPackedGlyphID` 已包含预计算的哈希值,避免重复计算。

**键比较优化**:
```cpp
bool operator==(const GlyphEntryKey& that) const {
    return fPackedID == that.fPackedID && fFormat == that.fFormat;
}
```
先比较整数 ID(快速路径),再比较枚举格式。

### Arena 分配器性能

1. **批量分配**: 减少系统调用,降低分配开销
2. **无碎片**: 线性分配,无内存碎片
3. **快速释放**: 整体释放,无需遍历析构
4. **缓存友好**: 连续内存布局,提升缓存命中率

### 内存占用

每个 `GlyphEntry` 仅占用约 24 字节:
```cpp
struct GlyphEntry {
    GlyphEntryKey fGlyphEntryKey;  // 8 字节(4 ID + 4 format 对齐)
    GrAtlasLocator fAtlasLocator;  // 16 字节
};
```

### 查找性能

- **平均情况**: O(1) 哈希查找
- **未命中创建**: O(1) Arena 分配 + O(1) 哈希插入
- **无锁操作**: 单线程访问(StrikeCache 保证)

### 内存跟踪开销

```cpp
this->addMemoryUsed(sizeof(GlyphEntry));
```
简单的整数累加,开销可忽略,支持缓存驱逐决策。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/text/gpu/StrikeCache.h` | 协作 | Strike 缓存管理器基类 |
| `src/gpu/ganesh/text/GlyphData.h` | 使用者 | 定义 GlyphEntry/GlyphEntryKey |
| `src/core/SkStrikeSpec.h` | 依赖 | 字体规格描述 |
| `src/core/SkGlyph.h` | 类型 | SkPackedGlyphID 定义 |
| `src/core/SkTHash.h` | 容器 | 哈希表实现 |
| `src/gpu/MaskFormat.h` | 类型 | MaskFormat 枚举 |
| `include/private/base/SkArenaAlloc.h` | 工具 | Arena 分配器 |
