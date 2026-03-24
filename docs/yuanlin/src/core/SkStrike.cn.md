# SkStrike

> 源文件
> - src/core/SkStrike.h
> - src/core/SkStrike.cpp

## 概述

`SkStrike` 是 Skia 字形渲染系统的核心缓存对象,存储特定字体配置下的字形数据(度量、图像、路径、Drawable)。它封装 `SkScalerContext` 进行字形生成,并使用 Arena 分配器高效管理内存。SkStrike 作为字形查找的热点对象,通过哈希表和向量结合的方式提供快速访问,同时支持序列化/反序列化用于远程字形传输(如 GPU 进程)。

主要功能:
- 字形度量、图像、路径、Drawable 的缓存和生成
- 通过 SkGlyphDigest 快速字形查找
- 支持批量字形准备操作
- 内存使用跟踪和报告
- 序列化支持(远程渲染)

## 架构位置

`SkStrike` 在文本渲染管线中的位置:
- **上层**: 被 `SkStrikeCache` 管理,被 `SkStrikeSpec` 创建
- **下层**: 使用 `SkScalerContext` 生成字形数据
- **横向**: 实现 `StrikeForGPU` 接口供 GPU 渲染使用
- **作用**: 作为字形数据的一级缓存,避免重复光栅化

## 主要类与结构体

### SkStrike

**继承关系**:
```
SkStrike : public sktext::StrikeForGPU
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFontMetrics` | `const SkFontMetrics` | 字体度量(不可变) |
| `fRoundingSpec` | `const SkGlyphPositionRoundingSpec` | 位置舍入规格 |
| `fStrikeSpec` | `const SkStrikeSpec` | Strike 创建规格 |
| `fStrikeCache` | `SkStrikeCache* const` | 所属缓存管理器 |
| `fStrikeLock` | `mutable SkMutex` | Strike 内部锁 |
| `fDigestForPackedGlyphID` | `THashTable<SkGlyphDigest, ...>` | 字形快速查找表 |
| `fGlyphForIndex` | `std::vector<SkGlyph*>` | 按索引访问字形 |
| `fScalerContext` | `std::unique_ptr<SkScalerContext>` | 字形生成器 |
| `fAlloc` | `SkArenaAlloc` | Arena 内存分配器 |
| `fMemoryUsed` | `size_t` | 当前内存使用量 |
| `fMemoryIncrease` | `size_t` | 当前操作的内存增量 |

### SkStrikePinner

生命周期扩展接口,允许外部控制 Strike 的删除时机。

**关键方法**:

| 方法 | 说明 |
|------|------|
| `virtual bool canDelete()` | 返回是否可以删除 Strike |
| `virtual void assertValid()` | 调试验证 |

## 公共 API 函数

### 生命周期

```cpp
SkStrike(SkStrikeCache* strikeCache,
         const SkStrikeSpec& strikeSpec,
         std::unique_ptr<SkScalerContext> scaler,
         const SkFontMetrics* metrics,
         std::unique_ptr<SkStrikePinner> pinner);
```

### StrikeForGPU 接口实现

```cpp
// 锁操作
void lock() override;
void unlock() override;

// 字形准备
SkGlyphDigest digestFor(skglyph::ActionType, SkPackedGlyphID) override;
bool prepareForImage(SkGlyph* glyph) override;
bool prepareForPath(SkGlyph*) override;
bool prepareForDrawable(SkGlyph*) override;
```

### 批量操作

```cpp
// 批量获取度量
SkSpan<const SkGlyph*> metrics(
    SkSpan<const SkGlyphID> glyphIDs, const SkGlyph* results[]);

// 批量准备路径
SkSpan<const SkGlyph*> preparePaths(
    SkSpan<const SkGlyphID> glyphIDs, const SkGlyph* results[]);

// 批量准备图像
SkSpan<const SkGlyph*> prepareImages(
    SkSpan<const SkPackedGlyphID> glyphIDs, const SkGlyph* results[]);

// 批量准备 Drawables
SkSpan<const SkGlyph*> prepareDrawables(
    SkSpan<const SkGlyphID> glyphIDs, const SkGlyph* results[]);
```

### 序列化

```cpp
// 反序列化合并
bool mergeFromBuffer(SkReadBuffer& buffer);

// 序列化输出
static void FlattenGlyphsByType(
    SkWriteBuffer& buffer,
    SkSpan<SkGlyph> images,
    SkSpan<SkGlyph> paths,
    SkSpan<SkGlyph> drawables);
```

### 遗留接口(已弃用)

```cpp
// 合并字形和图像(用于远程渲染)
SkGlyph* mergeGlyphAndImage(SkPackedGlyphID toID, const SkGlyph& fromGlyph);

// 合并路径
const SkPath* mergePath(SkGlyph* glyph, const SkPath* path,
                        bool hairline, bool modified);

// 合并 Drawable
const SkDrawable* mergeDrawable(SkGlyph* glyph, sk_sp<SkDrawable> drawable);
```

### 其他

```cpp
// 查找线条相交
void findIntercepts(const SkScalar bounds[2], SkScalar scale, SkScalar xPos,
                    SkGlyph*, SkScalar* array, int* count);

// 获取字体度量
const SkFontMetrics& getFontMetrics() const;

// 调试输出
void dump() const;
void dumpMemoryStatistics(SkTraceMemoryDump* dump) const;
```

## 内部实现细节

### 字形查找与生成流程

1. **快速查找**: 通过 `fDigestForPackedGlyphID` 哈希表查找 `SkGlyphDigest`
2. **未命中处理**:
   - 调用 `fScalerContext->makeGlyph` 生成基础度量
   - 在 `fAlloc` 中分配 `SkGlyph` 对象
   - 添加到 `fGlyphForIndex` 向量
   - 插入哈希表
3. **数据准备**: 根据 ActionType 按需生成图像/路径/Drawable
4. **内存跟踪**: 累积 `fMemoryIncrease`,在 unlock 时更新缓存

### 两级索引结构

**哈希表** (`fDigestForPackedGlyphID`):
- 键: `SkPackedGlyphID`(包含 GlyphID 和子像素位置)
- 值: `SkGlyphDigest`(包含索引和状态)
- 用途: O(1) 查找

**向量** (`fGlyphForIndex`):
- 索引: 字形在 Strike 中的序号
- 值: `SkGlyph*` 指针
- 用途: 从 Digest 快速获取 Glyph 对象

### SkGlyphDigest 状态机

每个 Digest 包含字形的准备状态:
```cpp
enum class GlyphAction {
    kUnset,      // 未准备
    kAccept,     // 已准备
    kReject,     // 不支持该操作
};
```

ActionType 包括:
- `kDirectMask`: 直接遮罩(小字形)
- `kPath`: 路径渲染(大字形)
- `kDrawable`: 复杂字形(彩色、SVG等)

### Arena 分配策略

```cpp
inline static constexpr size_t kMinGlyphCount = 8;
inline static constexpr size_t kMinGlyphImageSize = 16 * 8;
inline static constexpr size_t kMinAllocAmount =
    kMinGlyphImageSize * kMinGlyphCount;

SkArenaAlloc fAlloc{kMinAllocAmount};
```

- **连续分配**: 字形数据在 Arena 中连续存储
- **无碎片**: Arena 一次性释放,无碎片问题
- **缓存友好**: 相关数据紧密排列

### 锁与内存管理

**Monitor RAII 类**:
```cpp
class Monitor {
    Monitor(SkStrike* strike) { strike->lock(); }
    ~Monitor() { strike->unlock(); }
};
```

**内存更新机制**:
1. `lock()` 时重置 `fMemoryIncrease = 0`
2. 操作期间累积内存增量
3. `unlock()` 时调用 `updateMemoryUsage` 更新缓存统计
4. 使用缓存锁保护 `fTotalMemoryUsed` 更新

### 序列化格式

**输出格式**:
```
[image_count][image_1][image_2]...[image_n]
[path_count][path_1][path_2]...[path_n]
[drawable_count][drawable_1][drawable_2]...[drawable_n]
```

每个字形包含:
- 度量数据(metrics)
- 类型特定数据(image/path/drawable)

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkScalerContext` | 生成字形数据 |
| `SkGlyph` | 字形数据结构 |
| `SkArenaAlloc` | 内存分配 |
| `SkTHash` | 哈希表 |
| `SkMutex` | 线程同步 |
| `SkReadBuffer` / `SkWriteBuffer` | 序列化 |
| `SkPath` / `SkDrawable` | 字形表示 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `SkStrikeCache` | 管理 Strike 生命周期 |
| `SkStrikeSpec` | 创建 Strike |
| GPU 文本渲染 | 通过 `StrikeForGPU` 接口 |
| 远程渲染 | 序列化字形数据 |

## 设计模式与设计决策

### 设计模式

1. **享元模式**: 共享相同配置的字形数据
2. **代理模式**: 包装 `SkScalerContext`,延迟生成字形
3. **对象池**: Arena 分配器管理字形对象池
4. **RAII**: Monitor 类管理锁生命周期
5. **策略模式**: 不同 ActionType 对应不同准备策略

### 设计决策

1. **两级索引**:
   - 哈希表提供快速查找
   - 向量提供密集索引
   - 权衡: 额外内存 vs 访问速度

2. **Arena 分配**:
   - 批量释放,避免逐个析构
   - 缓存友好,减少内存碎片
   - 字形生命周期与 Strike 绑定

3. **延迟生成**:
   - 只在需要时生成图像/路径
   - SkGlyphDigest 记录准备状态
   - 避免不必要的计算

4. **不可变核心**:
   - `fFontMetrics`, `fStrikeSpec` 等声明为 const
   - 线程安全,无竞态条件
   - 简化并发推理

5. **序列化设计**:
   - 按类型分组(images/paths/drawables)
   - 先写数量,再写数据
   - 支持流式处理,无需预先知道总大小

6. **内存跟踪延迟更新**:
   - 避免在锁内多次更新缓存统计
   - 批量更新减少缓存锁争用

## 性能考量

1. **快速路径优化**:
   - SkGlyphDigest 内联判断避免虚函数
   - 小字形数据直接存储在 SkGlyph 中

2. **批量操作**:
   - `preparePaths` 等方法减少锁获取次数
   - 一次性准备多个字形

3. **内存局部性**:
   - Arena 连续分配
   - 相关字形数据紧密存储
   - 提高 CPU 缓存命中率

4. **哈希冲突最小化**:
   - `SkPackedGlyphID` 包含 GlyphID 和子像素位置
   - `SkDescriptor::getChecksum()` 作为良好哈希函数

5. **引用计数优化**:
   - Strike 通过 `sk_sp` 管理
   - 原子操作实现线程安全引用计数

6. **最小 Arena 分配**:
   ```cpp
   kMinAllocAmount = 16 * 8 * 8 = 1024 bytes
   ```
   - 避免小对象频繁分配
   - 预留典型字形数据大小

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkStrikeCache.h` | Strike 缓存管理器 |
| `src/core/SkStrikeSpec.h` | Strike 创建规格 |
| `src/core/SkGlyph.h` | 字形数据结构 |
| `src/core/SkScalerContext.h` | 字形生成器 |
| `src/base/SkArenaAlloc.h` | Arena 分配器 |
| `src/core/SkTHash.h` | 哈希表 |
| `src/text/StrikeForGPU.h` | GPU Strike 接口 |
| `src/core/SkReadBuffer.h` / `SkWriteBuffer.h` | 序列化 |
