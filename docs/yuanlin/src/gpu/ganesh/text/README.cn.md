# text - GPU 文本渲染模块

## 概述

`src/gpu/ganesh/text` 目录是 Skia 图形库 Ganesh GPU 后端中负责文本渲染的核心模块。该模块实现了从字形光栅化到 GPU 纹理图集（Atlas）管理再到最终顶点数据填充的完整文本渲染管线。文本渲染是 2D 图形中最复杂的子系统之一，因为它需要同时兼顾渲染质量、内存效率和高性能。

该模块的核心架构围绕纹理图集（Texture Atlas）展开。`GrAtlasManager` 管理多个 `GrDrawOpAtlas` 实例，每种掩码格式（MaskFormat）对应一个图集。字形图像被光栅化后上传到这些图集纹理中，渲染时着色器从图集中采样字形数据并合成到屏幕上。图集使用分页和紧凑化（compaction）机制来高效利用 GPU 纹理内存。

`TextStrike` 类是 Ganesh 特有的字形缓存条目，为每个字体 Strike（特定字体大小、变换和渲染参数的组合）维护一个哈希表，将 `SkPackedGlyphID` 映射到包含图集位置信息的 `GlyphEntry`。`GlyphData` 类则负责协调 SubRun（文本子运行）级别的字形数据管理，包括图集重生成、顶点步长计算和顶点数据填充。

该模块支持三种掩码格式：`MaskFormat::kA8`（灰度抗锯齿和 SDF 文本）、`MaskFormat::kA565`（LCD 亚像素文本）和 `MaskFormat::kARGB`（彩色 Emoji 和全彩字形）。当平台不支持 565 格式时（例如 macOS 上的 Metal 后端），系统会自动将 565 格式降级为 ARGB 格式，并在数据上传时进行格式转换。

模块中的所有高级功能（如向图集添加字形）仅在 flush 时通过 `GrOpFlushState` 可用，这种设计确保了图集操作与 GPU 命令流的正确同步。图集的生成代（generation）机制允许系统检测图集内容是否已改变，避免不必要的纹理坐标重新计算。

## 架构图

```
+---------------------------------------------------------------+
|                     应用层 (SkCanvas::drawText)                 |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|              sktext::gpu (通用文本 GPU 基础设施)                 |
|  StrikeCache / GlyphVector / VertexFiller / StrikeCache        |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|              skgpu::ganesh::text (本模块)                       |
+---------------------------------------------------------------+
        |                     |                      |
        v                     v                      v
+----------------+  +------------------+  +------------------+
| TextStrike     |  | GlyphData        |  | GrAtlasManager   |
| (字形缓存条目)  |  | (SubRun 字形管理) |  | (图集生命周期)    |
|                |  |                  |  |                  |
| - GetOrCreate  |  | - makeGlyphFrom  |  | - addGlyphTo     |
| - getGlyph     |  |   ID             |  |   Atlas          |
| - fCache:      |  | - regenerateAtlas|  | - getViews       |
|   THashTable   |  | - fillVertexData |  | - freeAll         |
+----------------+  +------------------+  +------------------+
        |                     |                      |
        v                     v                      v
+---------------------------------------------------------------+
|              GrDrawOpAtlas (图集纹理管理)                       |
|  - 分页管理 (Plot)                                             |
|  - 纹理上传 (GrDeferredUploadTarget)                           |
|  - 生成代追踪 (atlasGeneration)                                |
|  - 多纹理支持 (AllowMultitexturing)                            |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|              GrSurfaceProxy / GrTexture (GPU 纹理)             |
+---------------------------------------------------------------+

掩码格式映射:
+------------------+-------------------+------------------------+
| MaskFormat::kA8  | MaskFormat::kA565 | MaskFormat::kARGB      |
| (灰度/SDF 文本)  | (LCD 亚像素文本)   | (彩色 Emoji/全彩字形)   |
+------------------+-------------------+------------------------+
```

## 文件分类索引

### 1. 字形数据 — Glyph Data

| 文件 | 说明 |
|------|------|
| GlyphData.h / GlyphData.cpp | 字形数据管理与顶点填充实现 |

### 2. 文本图集管理 — Atlas Manager

| 文件 | 说明 |
|------|------|
| GrAtlasManager.h / GrAtlasManager.cpp | 文本图集管理器（字形纹理图集的创建与缓存） |

### 3. 文本缓存 — Text Strike Cache

| 文件 | 说明 |
|------|------|
| TextStrike.h / TextStrike.cpp | 文本 Strike 缓存条目（字形到图集位置的映射） |

## 关键类与函数

### GrAtlasManager
图集管理器，继承自 `GrOnFlushCallbackObject` 和 `GrAtlasGenerationCounter`。管理三个 `GrDrawOpAtlas` 实例（对应三种 `MaskFormat`）的完整生命周期。

- `GrAtlasManager(GrProxyProvider*, size_t maxTextureBytes, AllowMultitexturing, bool supportBilerpAtlas)` - 构造函数，通过 `GrDrawOpAtlasConfig` 根据最大纹理尺寸和字节数自动配置图集和 plot 尺寸
- `getViews(MaskFormat, unsigned int*)` - 获取指定格式图集的 `GrSurfaceProxyView` 数组和活跃页面数
- `addGlyphToAtlas(const SkGlyph&, GlyphEntry*, int srcPadding, GrResourceProvider*, GrDeferredUploadTarget*)` - 将字形图像添加到图集，处理不同掩码格式的像素数据转换
- `addGlyphToBulkAndSetUseToken(GrBulkUsePlotUpdater*, MaskFormat, const GlyphEntry&, skgpu::Token)` - 批量更新 plot 使用令牌，防止图集驱逐正在使用的字形
- `hasGlyph(MaskFormat, const GlyphEntry&)` - 检查字形是否仍在图集中
- `addToAtlas(GrResourceProvider*, GrDeferredUploadTarget*, MaskFormat, int w, int h, const void*, GrAtlasLocator*)` - 底层图集添加接口
- `preFlush()` - flush 前回调，实例化所有活跃图集的纹理代理
- `postFlush()` - flush 后回调，对图集执行紧凑化
- `resolveMaskFormat()` - 在 565 格式不可用时将其降级为 ARGB

### GlyphData
存储在 SubRun 上的字形数据管理类，位于 `skgpu::ganesh` 命名空间。协调从打包字形 ID 到图集位置的映射更新。

- `GlyphData(sk_sp<TextStrike>)` - 构造函数，绑定到特定的 TextStrike
- `makeGlyphFromID(SkPackedGlyphID, MaskFormat)` - 从 ID 创建 Glyph 包装器
- `regenerateAtlas(int begin, int end, GlyphVector&, MaskFormat, int srcPadding, GrMeshDrawTarget*)` - 重生成图集条目，返回 `{success, glyphs_placed_in_atlas}`。检测图集世代变化并使用 `GrBulkUsePlotUpdater` 批量更新
- `vertexStride(MaskFormat, const SkMatrix&)` - 计算顶点步长，根据掩码格式和是否有透视变换返回 `Mask2DVertex/Mask3DVertex/ARGB2DVertex/ARGB3DVertex` 的大小
- `fillVertexData(const VertexFiller&, SkSpan<const Glyph>, ...)` - 填充顶点缓冲区数据，支持直接绘制（无变换/有裁剪）和变换绘制（2D/3D）两种路径
- `FindStrike()` - 静态工厂方法，委托给 `TextStrike::GetOrCreate()`

### GlyphEntry / GlyphEntryKey
Ganesh 特有的字形类型，包含图集位置信息。

- `GlyphEntryKey` - 由 `SkPackedGlyphID` 和 `MaskFormat` 组成的复合键，用于在 `TextStrike` 哈希表中查找
- `GlyphEntry` - 包含 `GlyphEntryKey` 和 `GrAtlasLocator`，后者存储字形在图集中的 UV 坐标和 plot 位置
- `Glyph` - 适配器类，包装 `GlyphEntry*`，提供 `packedID()` 和 `entry()` 访问接口，满足 `GlyphVector` 的类型要求

### TextStrike
Ganesh 特有的文本 Strike 缓存条目，继承自 `sktext::gpu::TextStrikeBase`。

- `TextStrike(StrikeCache*, const SkStrikeSpec&)` - 构造函数，注册到全局 StrikeCache
- `GetOrCreate(StrikeCache*, const SkStrikeSpec&)` - 静态工厂方法，查找已有 Strike 或创建新实例
- `getGlyph(SkPackedGlyphID, MaskFormat)` - 在内部哈希表中查找或创建 GlyphEntry，使用 Arena 分配器
- `HashTraits` - 哈希表特征类，提供 `GetKey()` 和 `Hash()` 函数

### 顶点数据结构（定义在 GlyphData.cpp 中）

```cpp
struct Mask2DVertex { SkPoint devicePos; GrColor color; AtlasPt atlasPos; };
struct ARGB2DVertex { SkPoint devicePos; AtlasPt atlasPos; };  // 无颜色
struct Mask3DVertex { SkPoint3 devicePos; GrColor color; AtlasPt atlasPos; };
struct ARGB3DVertex { SkPoint3 devicePos; AtlasPt atlasPos; }; // 无颜色
```

## 依赖关系

### 上游依赖（本模块依赖的模块）
- `src/text/gpu/` - 通用文本 GPU 基础设施（`StrikeCache`、`GlyphVector`、`VertexFiller`、`GlyphUtils`）
- `src/gpu/ganesh/` - Ganesh 核心（`GrDrawOpAtlas`、`GrOnFlushResourceProvider`、`GrMeshDrawTarget`、`GrProxyProvider`、`GrCaps`）
- `src/gpu/ganesh/GrAtlasTypes.h` - 图集相关类型（`GrAtlasLocator`、`GrBulkUsePlotUpdater`、`GrAtlasGenerationCounter`）
- `src/core/` - 核心字形系统（`SkGlyph`、`SkStrikeSpec`、`SkStrike`、`SkDistanceFieldGen`）
- `src/gpu/MaskFormat.h` - 掩码格式定义（`MaskFormat::kA8`、`kA565`、`kARGB`）

### 下游依赖（依赖本模块的模块）
- SubRun 实现类使用 `GlyphData` 管理字形图集数据
- `GrOpFlushState` 通过 `atlasManager()` 暴露 `GrAtlasManager`
- Ganesh 文本绘制操作使用 `TextStrike` 缓存字形条目

## 设计模式分析

### 享元模式（Flyweight Pattern）
`TextStrike` 和 `GlyphEntry` 构成了典型的享元模式。每个字形条目（GlyphEntry）是共享的轻量级对象，通过 `SkPackedGlyphID` 和 `MaskFormat` 组成的键在 `TextStrike` 哈希表中唯一标识。多个 SubRun 可以共享同一个 `TextStrike`，避免重复缓存。

### 观察者模式（Observer Pattern）
`GrAtlasManager` 实现了 `GrOnFlushCallbackObject` 接口，作为观察者注册到 flush 系统中。`preFlush()` 和 `postFlush()` 回调确保图集在正确的时机进行实例化和紧凑化。

### 世代计数模式（Generation Counting）
图集使用单调递增的世代编号（`atlasGeneration`）来追踪内容变化。`GlyphData` 通过比较 `fAtlasGeneration` 与当前图集世代来判断是否需要重新计算纹理坐标。如果世代匹配，仅更新使用令牌即可；如果不匹配，则需要重新生成图集条目。

### 批量更新模式（Bulk Update Pattern）
`GrBulkUsePlotUpdater` 收集一批需要更新使用令牌的 plot，在最后通过 `setUseTokenBulk()` 一次性更新，减少逐个更新的开销。

### 模板方法与策略组合
`fillVertexData()` 方法内部使用了模板化的 `fillDirectNoClipping()`、`fillDirectClipped()`、`fill2D()` 和 `fill3D()` 函数，根据掩码格式和变换类型选择不同的顶点填充策略，编译期消除分支开销。

## 数据流

```
1. 字形光栅化请求
   SubRun 通过 GlyphData::regenerateAtlas() 请求字形数据
       |
       v
2. Strike 缓存查找
   TextStrike::GetOrCreate() 在 StrikeCache 中查找或创建 Strike
   TextStrike::getGlyph() 在内部哈希表中查找或创建 GlyphEntry
       |
       v
3. 图集检查与更新
   GrAtlasManager::hasGlyph() 检查字形是否仍在图集中
       |
       +--- 已存在 --> addGlyphToBulkAndSetUseToken() 更新令牌
       |
       +--- 不存在 --> addGlyphToAtlas() 执行以下步骤:
             |
             v
4. 字形图像处理
   SkBulkGlyphMetricsAndImages 获取字形像素数据
   get_packed_glyph_image() 处理格式转换:
   - 相同格式: 直接复制（处理 BW 位展开为 A8/A565）
   - A565 --> ARGB: 逐像素 565 到 8888 颜色转换
   添加 padding（直接掩码 0/1 像素，变换掩码 1 像素，SDF 内置）
       |
       v
5. 图集空间分配
   GrDrawOpAtlas::addToAtlas() 在图集 plot 中分配空间
   返回 GrAtlasLocator（包含 UV 坐标和 plot 定位器）
   glyph->fAtlasLocator.insetSrc(srcPadding) 调整源区域
       |
       v
6. 顶点数据填充
   GlyphData::fillVertexData() 根据绘制模式选择路径:
   - 直接绘制无裁剪: fillDirectNoClipping() (99% 常见情况)
   - 直接绘制有裁剪: fillDirectClipped()
   - 2D 变换: fill2D()
   - 3D 透视: fill3D()
   每个字形生成 4 个顶点（一个四边形）
       |
       v
7. GPU 渲染
   着色器从图集纹理采样字形数据并混合到帧缓冲区
```

## 相关文档与参考

- `src/text/gpu/` - 通用文本 GPU 基础设施目录
- `src/gpu/ganesh/GrDrawOpAtlas.h` - 绘制操作图集实现，包含 plot 管理和纹理分页
- `src/gpu/ganesh/GrAtlasTypes.h` - 图集定位器和批量更新器类型
- `src/gpu/MaskFormat.h` - 掩码格式定义和工具函数
- `src/core/SkGlyph.h` - 字形元数据和图像数据
- `src/core/SkStrikeSpec.h` - Strike 规格，定义字形光栅化参数
- `src/core/SkDistanceFieldGen.h` - SDF（Signed Distance Field）文本生成，`SK_DistanceFieldInset` 常量定义
- Slug 文本渲染系统 - Skia 的高层文本渲染抽象，使用本模块进行图集管理
