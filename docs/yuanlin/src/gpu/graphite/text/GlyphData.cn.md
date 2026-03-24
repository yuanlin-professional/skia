# GlyphData -- 字形数据管理

> 源文件:
> - `src/gpu/graphite/text/GlyphData.h`
> - `src/gpu/graphite/text/GlyphData.cpp`

## 概述

GlyphData 模块定义了 Graphite 特有的字形数据结构和图集协调逻辑。它包含字形条目键 (`GlyphEntryKey`)、字形条目 (`GlyphEntry`)、字形适配器 (`Glyph`) 和字形数据管理器 (`GlyphData`)。该模块桥接了 Graphite 的 SubRun 系统与 TextAtlasManager,负责将字形从打击缓存映射到图集位置,并填充绘制实例数据。

## 架构位置

```
SubRun (文本子运行)
  -> GlyphData  <-- 本模块
       -> TextStrike (打击缓存)
       -> TextAtlasManager (图集管理)
       -> DrawWriter (实例数据输出)
```

## 主要类与结构体

### GlyphEntryKey

```cpp
struct GlyphEntryKey {
    const SkPackedGlyphID fPackedID;
    MaskFormat fFormat;
};
```
唯一标识一个字形（字形 ID + 遮罩格式），支持相等比较和哈希。

### GlyphEntry

```cpp
struct GlyphEntry {
    const GlyphEntryKey fGlyphEntryKey;
    DrawAtlas::AtlasLocator fAtlasLocator;  // 图集位置（动态更新）
};
```
存储字形在图集中的位置信息,`fAtlasLocator` 在图集重新生成时更新。

### Glyph

```cpp
class Glyph final {
    GlyphEntry* fEntry;
public:
    explicit Glyph(GlyphEntry* entry);
    SkPackedGlyphID packedID() const;
    GlyphEntry& entry() const;
};
```
适配器类,使 `GlyphEntry*` 符合 `GlyphVector` 的 `GlyphType` 约束。禁止拷贝,仅支持移动。

### GlyphData

```cpp
class GlyphData final {
    sk_sp<TextStrike> fTextStrike;
    uint64_t fAtlasGeneration;
    DrawAtlas::BulkUsePlotUpdater fBulkUseUpdater;
};
```

## 公共 API 函数

### FindStrike
```cpp
static sk_sp<TextStrike> FindStrike(sktext::gpu::StrikeCache*, const SkStrikeSpec&);
```
从缓存中查找或创建 TextStrike。

### makeGlyphFromID
```cpp
Glyph makeGlyphFromID(SkPackedGlyphID, MaskFormat);
```
通过 TextStrike 获取或创建字形条目。

### regenerateAtlas
```cpp
std::tuple<bool, int> regenerateAtlas(int begin, int end,
    sktext::gpu::GlyphVector& glyphVector, MaskFormat, int srcPadding, Recorder*);
```
为指定范围的字形重新生成图集条目。返回 `{success, glyphs_placed_in_atlas}`。

### fillInstanceData
```cpp
void fillInstanceData(const VertexFiller&, SkSpan<const Glyph>, DrawWriter*,
    int offset, int count, unsigned short flags, uint32_t ssboIndex, SkScalar depth) const;
```
填充绘制实例数据到 DrawWriter。

## 内部实现细节

### 图集重新生成逻辑

`regenerateAtlas` 的核心流程:

1. **代检查**: 比较当前 `fAtlasGeneration` 与图集的最新代号
2. **需要更新时**:
   - 重置 `fBulkUseUpdater`
   - 通过 `SkBulkGlyphMetricsAndImages` 批量获取字形度量和图像
   - 遍历字形,检查是否已在图集中 (`hasGlyph`)
   - 不在则通过 `addGlyphToAtlas` 添加
   - 使用 `addGlyphToBulkAndSetUseToken` 批量更新令牌
   - 全部成功后更新 `fAtlasGeneration`
3. **已是最新时**: 仅通过 `setUseTokenBulk` 批量更新使用令牌

### 实例数据格式

```cpp
struct AtlasPt { uint16_t u, v; };
```

每个字形实例写入:
- `AtlasPt{width, height}` -- UV 尺寸
- `AtlasPt{al & 0x1fff, at}` -- UV 偏移（低 13 位 + 全量顶部）
- `leftTop` -- 屏幕位置
- `uint16_t(al >> 13)` -- 纹理页索引（高位编码）
- `flags` -- 字形标志
- `1.0f` -- 打击到源缩放
- `depth` -- 深度值
- `ssboIndex` -- SSBO 索引

纹理页索引通过 UV 左边界的高位编码，利用了图集坐标不会使用全部 16 位的特性。

## 依赖关系

- `TextStrike` -- 字形条目存储
- `TextAtlasManager` -- 图集管理
- `DrawAtlas` -- 图集分配器
- `DrawWriter` -- 实例数据写入
- `GlyphVector` -- 字形向量（跨后端抽象）
- `VertexFiller` -- 顶点位置计算

## 设计模式与设计决策

1. **延迟图集更新**: 通过代号比较实现惰性更新,仅在图集变化时重新生成。
2. **批量令牌更新**: `BulkUsePlotUpdater` 收集所有需要更新的绘图区域,一次性刷新,减少逐字形的令牌更新开销。
3. **适配器模式**: `Glyph` 类适配 `GlyphEntry*` 到 `GlyphVector` 期望的接口。
4. **紧凑实例数据**: UV 坐标使用 16 位,纹理索引通过高位编码,最大化数据密度。

## 性能考量

- 批量度量和图像获取（`SkBulkGlyphMetricsAndImages`）减少锁竞争和缓存查找。
- 代号快速路径:图集未变时仅更新令牌,跳过所有字形处理。
- `DrawWriter::Instances` 使用 `reserve(count)` 预分配,避免绘制过程中的内存重分配。
- 16 位 UV 坐标减少了每实例的内存带宽需求。

## 相关文件

- `src/gpu/graphite/text/TextStrike.h` -- 打击缓存
- `src/gpu/graphite/text/TextAtlasManager.h` -- 图集管理
- `src/gpu/graphite/DrawAtlas.h` -- 图集核心
- `src/gpu/graphite/DrawWriter.h` -- 绘制数据写入
- `src/text/gpu/GlyphVector.h` -- 字形向量
- `src/text/gpu/VertexFiller.h` -- 顶点填充
