# text - GPU 文本渲染系统

## 概述

`src/gpu/graphite/text/` 目录实现了 Skia Graphite 后端的 GPU 文本渲染子系统。该子系统负责管理字形（glyph）的光栅化、图集（atlas）打包、缓存策略以及将字形数据传输到 GPU 的完整流程。文本渲染是图形库中最复杂的功能之一，因为它需要在高效的纹理图集管理、字形缓存策略和多种遮罩格式之间取得平衡。

文本渲染系统的核心组件是 `TextAtlasManager`，它管理三种不同遮罩格式（MaskFormat）的 `DrawAtlas` 实例：A8（Alpha 8 位灰度遮罩）、A565（RGB 565 LCD 子像素渲染）和 ARGB（完整 32 位彩色遮罩）。这三个图集的尺寸并非独立配置，而是通过 `AtlasConfig` 类基于 ARGB 图集的尺寸推导：A8 图集通常是 ARGB 图集尺寸的 2 倍（因为 A8 是最常用的遮罩格式，需要更大的空间），而 565 图集与 ARGB 共享相同尺寸。所有图集尺寸受限于 GPU 最大纹理尺寸和客户端指定的最大字节数。

`TextStrike` 类是 Graphite 特有的字形缓存实现，它继承自 `sktext::gpu::TextStrikeBase`，为特定字体配置（SkStrikeSpec）维护一个 `GlyphEntry` 的哈希表缓存。每个 `GlyphEntry` 包含字形的打包 ID（`SkPackedGlyphID`）、遮罩格式和在图集中的位置信息（`DrawAtlas::AtlasLocator`）。`TextStrike` 使用全局的 `StrikeCache` 进行管理，通过 `GetOrCreate` 模式确保同一字体配置只有一个 strike 实例。

`GlyphData` 类是存储在 SubRun 上的关键数据结构，它维护从 SubRun 的打包字形 ID 到图集位置的映射。其 `regenerateAtlas()` 方法实现了图集更新的核心逻辑：检查当前图集代是否与缓存一致，如果不一致则重新上传字形数据并更新 atlas locator。该方法使用 `BulkUsePlotUpdater` 进行批量更新以提高性能，避免逐个字形地更新 plot 使用标记。

系统还处理了平台特定的兼容性问题。例如，在 Intel macOS 上使用 Metal 时不支持 RGB 565 纹理格式，`TextAtlasManager::resolveMaskFormat()` 会自动将 565 格式降级为 ARGB 格式，配合 `get_packed_glyph_image()` 中的格式转换逻辑完成透明的数据迁移。

## 架构图

```
                    +-------------------+
                    |   SkCanvas/       |
                    |   SkPaint 文本绘制 |
                    +--------+----------+
                             |
                             v
                    +-------------------+
                    |   SubRun 系统     |  <-- 文本绘制的批处理单元
                    |  (sktext::gpu)    |
                    +--------+----------+
                             |
              +--------------+--------------+
              |                             |
              v                             v
     +----------------+            +----------------+
     |   GlyphData    |            |  GlyphVector   |
     | - fTextStrike  |            | (sktext::gpu)  |
     | - fAtlasGen    |            +----------------+
     | - fBulkUpdater |
     +-------+--------+
              |
    +---------+---------+
    |                   |
    v                   v
+----------+    +--------------+
|TextStrike|    |TextAtlasManager|
| - fCache |    | - fAtlases[3] |
| (GlyphEntry)  | - fAtlasConfig|
+----------+    +------+-------+
                       |
            +----------+----------+
            |          |          |
            v          v          v
        +------+   +------+   +------+
        | A8   |   | A565 |   | ARGB |
        |Atlas |   |Atlas |   |Atlas |
        +------+   +------+   +------+
            |
            v
     +---------------+
     |   DrawAtlas   |  <-- 纹理图集核心
     | - 多页纹理     |
     | - Plot 管理    |
     | - LRU 驱逐    |
     +-------+-------+
              |
              v
     +---------------+
     | TextureProxy  |  <-- GPU 纹理代理
     +---------------+

  遮罩格式 (MaskFormat):
  +-------+--------+------+
  | A8    | 8bit   | 灰度 |  <-- SDF / 直接遮罩
  | A565  | 16bit  | LCD  |  <-- LCD 子像素
  | ARGB  | 32bit  | 彩色 |  <-- 彩色表情符号
  +-------+--------+------+
```

## 目录结构

```
src/gpu/graphite/text/
|-- BUILD.bazel                  # Bazel 构建配置
|-- TextAtlasManager.h           # 文本图集管理器头文件
|-- TextAtlasManager.cpp         # 文本图集管理器实现（核心，15KB+）
|-- GlyphData.h                  # 字形数据存储与图集协调
|-- GlyphData.cpp                # 字形数据实现
|-- TextStrike.h                 # Graphite 特有的 strike 缓存
|-- TextStrike.cpp               # TextStrike 实现
```

## 关键类与函数

### TextAtlasManager
管理文本渲染使用的所有 DrawAtlas 实例的生命周期。

```cpp
class TextAtlasManager : public DrawAtlas::GenerationCounter {
public:
    TextAtlasManager(Recorder*);
    ~TextAtlasManager();

    // 获取指定遮罩格式的纹理代理数组
    const sk_sp<TextureProxy>* getProxies(MaskFormat format, unsigned int* numActiveProxies);

    // 检查指定字形是否已在图集中
    bool hasGlyph(MaskFormat, const GlyphEntry&);

    // 将字形添加到图集
    DrawAtlas::ErrorCode addGlyphToAtlas(const SkGlyph&, GlyphEntry*, int srcPadding);

    // 批量更新 plot 使用标记
    void addGlyphToBulkAndSetUseToken(DrawAtlas::BulkUsePlotUpdater*, MaskFormat,
                                       const GlyphEntry&, Token);

    // 记录上传命令到 DrawContext
    bool recordUploads(DrawContext* dc);

    // 释放 GPU 资源
    void freeGpuResources();

    // 压缩图集（释放未使用的页面）
    void compact();

    // 查询图集代（用于缓存失效判断）
    uint64_t atlasGeneration(MaskFormat format) const;

private:
    MaskFormat resolveMaskFormat(MaskFormat format) const;
    bool initAtlas(MaskFormat);

    Recorder* fRecorder;
    DrawAtlas::AllowMultitexturing fAllowMultitexturing;
    std::unique_ptr<DrawAtlas> fAtlases[kMaskFormatCount];  // kMaskFormatCount == 3
    bool fSupportBilerpAtlas;
    AtlasConfig fAtlasConfig;
};
```

### TextAtlasManager::AtlasConfig
基于 GPU 能力和客户端配置计算图集和 plot 的尺寸。

```cpp
class AtlasConfig {
public:
    // maxTextureSize: GPU 最大纹理尺寸; maxBytes: 单个图集的最大字节数
    AtlasConfig(int maxTextureSize, size_t maxBytes);

    SkISize atlasDimensions(MaskFormat type) const;  // 图集总尺寸
    SkISize plotDimensions(MaskFormat type) const;    // 单个 plot 尺寸
private:
    static constexpr int kMaxAtlasDim = 2048;
    SkISize fARGBDimensions;
    int fMaxTextureSize;
};
```

### TextStrike
Graphite 特有的字形缓存，每个 strike 对应一个特定的字体配置。

```cpp
class TextStrike final : public sktext::gpu::TextStrikeBase {
public:
    TextStrike(sktext::gpu::StrikeCache* strikeCache, const SkStrikeSpec& strikeSpec);

    // 查找或创建 TextStrike
    static sk_sp<TextStrike> GetOrCreate(sktext::gpu::StrikeCache* strikeCache,
                                         const SkStrikeSpec& strikeSpec);

    // 获取或创建字形条目
    GlyphEntry* getGlyph(SkPackedGlyphID packedGlyphID, MaskFormat format);

private:
    skia_private::THashTable<GlyphEntry*, GlyphEntryKey, HashTraits> fCache;
};
```

### GlyphData
存储在 SubRun 上的字形数据管理器，协调字形与图集之间的关系。

```cpp
class GlyphData final {
public:
    GlyphData(sk_sp<TextStrike>);

    Glyph makeGlyphFromID(SkPackedGlyphID, MaskFormat);

    // 重新生成图集条目，返回 {success, glyphs_placed_in_atlas}
    std::tuple<bool, int> regenerateAtlas(int begin, int end,
                                          sktext::gpu::GlyphVector& glyphVector,
                                          MaskFormat maskFormat, int srcPadding,
                                          Recorder* recorder);

    // 填充 GPU 实例数据
    void fillInstanceData(const sktext::gpu::VertexFiller&, SkSpan<const Glyph> glyphs,
                          DrawWriter* dw, int offset, int count, unsigned short flags,
                          uint32_t ssboIndex, SkScalar depth) const;
private:
    sk_sp<TextStrike> fTextStrike;
    uint64_t fAtlasGeneration;
    DrawAtlas::BulkUsePlotUpdater fBulkUseUpdater;
};
```

### GlyphEntry 与 GlyphEntryKey
字形在图集中的条目表示。

```cpp
struct GlyphEntryKey {
    const SkPackedGlyphID fPackedID;
    MaskFormat fFormat;
    uint32_t hash() const;
};

struct GlyphEntry {
    const GlyphEntryKey fGlyphEntryKey;
    DrawAtlas::AtlasLocator fAtlasLocator;  // 图集中的位置信息
};
```

### Glyph
适配器类，将 `GlyphEntry*` 包装为符合 `GlyphVector` 要求的类型。

```cpp
class Glyph final {
public:
    explicit Glyph(GlyphEntry* entry);
    SkPackedGlyphID packedID() const;
    GlyphEntry& entry() const;
};
```

### 关键内部函数

- `get_packed_glyph_image()` - 从 SkGlyph 中提取并转换字形图像数据到目标遮罩格式
- `expand_bits()` - 将 BW 格式位图展开为 A8 或 A565 格式
- `TextAtlasManager::resolveMaskFormat()` - 在不支持 565 的平台上自动降级为 ARGB

## 依赖关系

### 上游依赖（本目录依赖的模块）

| 模块 | 说明 |
|------|------|
| `src/gpu/graphite/DrawAtlas.h` | 通用纹理图集实现（plot 管理、LRU 驱逐、多页） |
| `src/gpu/graphite/AtlasProvider.h` | 图集提供者，管理各种类型的图集 |
| `src/gpu/graphite/DrawWriter.h` | GPU 绘制写入器，写入实例数据 |
| `src/gpu/graphite/RecorderPriv.h` | Recorder 内部接口 |
| `src/gpu/graphite/TextureProxy.h` | 纹理代理 |
| `src/gpu/graphite/Caps.h` | GPU 能力查询 |
| `src/gpu/MaskFormat.h` | 遮罩格式枚举定义 |
| `src/core/SkGlyph.h` | 字形数据结构 |
| `src/core/SkStrikeSpec.h` | 字体 strike 规格 |
| `src/core/SkDistanceFieldGen.h` | SDF 字体生成 |
| `src/text/gpu/StrikeCache.h` | 跨后端共享的 strike 缓存基础设施 |
| `src/text/gpu/GlyphVector.h` | 字形向量，SubRun 使用的字形集合 |
| `src/text/gpu/VertexFiller.h` | 顶点填充器，生成字形顶点数据 |

### 下游依赖（依赖本目录的模块）

| 模块 | 说明 |
|------|------|
| `src/text/gpu/SubRun*.h` | SubRun 实现，使用 GlyphData 进行图集管理 |
| `src/gpu/graphite/Device.h` | Graphite 设备，绘制文本时调用本模块 |
| `src/gpu/graphite/AtlasProvider.h` | 通过 AtlasProvider 持有 TextAtlasManager |

## 设计模式分析

### 1. 享元模式（Flyweight Pattern）
文本渲染系统广泛使用享元模式来共享字形数据。相同字体配置下的所有字形共享同一个 `TextStrike` 实例（通过 `GetOrCreate` 保证唯一性）。字形图像数据存储在共享的 `DrawAtlas` 纹理中，各处使用通过 `AtlasLocator` 引用共享纹理中的特定区域。

### 2. 缓存模式（Cache Pattern）
`TextStrike` 内部维护了一个 `THashTable` 作为字形缓存。`GlyphData` 通过 `fAtlasGeneration` 追踪图集的代号变化，只有在图集内容发生变化（如字形被驱逐）时才重新上传数据，避免了不必要的重复工作。

### 3. 延迟初始化（Lazy Initialization）
`TextAtlasManager::initAtlas()` 采用延迟初始化策略 -- 每种遮罩格式的图集只在首次需要时才被创建。`fAtlases` 数组初始为空指针，调用 `getProxies()` 时才通过 `initAtlas()` 创建对应的 `DrawAtlas`。

### 4. 适配器模式（Adapter Pattern）
`Glyph` 类是一个适配器，将 Graphite 特有的 `GlyphEntry*` 包装为符合 `sktext::gpu::GlyphVector` 模板要求的类型接口。这使得共享的文本渲染代码能够与 Graphite 特有的数据结构无缝协作。

### 5. 批量更新模式（Bulk Update Pattern）
`DrawAtlas::BulkUsePlotUpdater` 实现了批量更新优化。在 `regenerateAtlas()` 中，系统不是逐个字形更新 plot 使用标记，而是收集所有需要更新的 plot，然后通过 `setUseTokenBulk()` 一次性更新，减少了重复的锁获取和状态检查。

## 数据流

```
1. 文本绘制请求:
   SkCanvas.drawText() -> SubRun 构建
     |
     v
2. 字形发现与缓存查找:
   GlyphData.makeGlyphFromID(packedID, format)
     |-- TextStrike.getGlyph()
     |     |-- fCache.findOrNull(key)  <-- 缓存命中
     |     |-- 或: fAlloc.make<GlyphEntry>()  <-- 缓存未命中，创建新条目
     |
     v
3. 图集重新生成 (每帧):
   GlyphData.regenerateAtlas(begin, end, glyphVector, maskFormat, srcPadding, recorder)
     |-- 检查 fAtlasGeneration 是否过期
     |-- 如果过期:
     |     |-- for each glyph:
     |     |     |-- atlasManager.hasGlyph() ?
     |     |     |-- 如果不在图集:
     |     |     |     |-- SkBulkGlyphMetricsAndImages.glyph() <-- 光栅化字形
     |     |     |     |-- get_packed_glyph_image() <-- 格式转换
     |     |     |     |-- atlasManager.addGlyphToAtlas() <-- 打包到图集
     |     |     |-- addGlyphToBulkAndSetUseToken() <-- 标记使用
     |     |-- 更新 fAtlasGeneration
     |-- 如果未过期:
     |     |-- setUseTokenBulk() <-- 批量更新使用标记
     |
     v
4. 实例数据填充:
   GlyphData.fillInstanceData(vf, glyphs, drawWriter, ...)
     |-- for each glyph:
     |     |-- 获取 UV 坐标: fAtlasLocator.getUVs()
     |     |-- 写入实例: {size, uv, position, atlasIndex, flags, scale, depth, ssbo}
     |
     v
5. GPU 上传与渲染:
   TextAtlasManager.recordUploads(drawContext)
     |-- for each atlas:
     |     |-- DrawAtlas.recordUploads() <-- 将新/更新的 plot 上传到 GPU
     |
     v
   渲染通道执行，GPU 采样图集纹理绘制字形
```

## 相关文档与参考

- `src/gpu/graphite/DrawAtlas.h` - 通用 DrawAtlas 实现
- `src/gpu/graphite/AtlasProvider.h` - 图集提供者
- `src/gpu/MaskFormat.h` - 遮罩格式定义
- `src/text/gpu/StrikeCache.h` - 共享的 strike 缓存
- `src/text/gpu/GlyphVector.h` - 字形向量
- `src/text/gpu/VertexFiller.h` - 顶点填充器
- `src/text/gpu/SubRunAllocator.h` - SubRun 分配器
- `src/core/SkGlyph.h` - 字形基础数据结构
- `src/core/SkStrikeSpec.h` - Strike 规格
- `src/core/SkDistanceFieldGen.h` - 有符号距离场生成
- `src/core/SkMask.h` - 遮罩格式底层定义
