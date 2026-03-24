# src/text/gpu - GPU 文本渲染模块

## 概述

`src/text/gpu` 是 Skia 中负责 GPU 加速文本渲染的核心模块。该模块实现了从 `GlyphRunList`（由上层 `src/text` 模块提供）到 GPU 可执行绘制命令的完整转换流水线。它是 Skia GPU 文本渲染的关键基础设施，被 Ganesh 和 Graphite 两个 GPU 后端共同使用。

本模块的核心架构围绕 SubRun（子运行）概念展开。每一个 SubRun 代表一种特定的字形绘制策略：直接掩码绘制（DirectMask）、变换掩码绘制（TransformedMask）、签名距离场文本（SDFT）、路径绘制或可绘制对象绘制。`SubRunContainer` 负责分析输入的字形数据并选择最优策略，将字形分配到不同类型的 SubRun 中。

该模块的一个重要创新是 Slug 系统。Slug（`SlugImpl`）是对文本绘制操作的预处理快照，它将所有昂贵的字形处理和策略选择工作提前完成，并序列化为可高效重放的格式。这一机制在 Chromium 浏览器中被广泛使用，实现了渲染器进程（Renderer）和 GPU 进程之间的文本绘制数据高效传输。

内存管理是本模块的另一个设计亮点。`SubRunAllocator` 和底层的 `BagOfBytes` 提供了一套定制的竞技场分配器（Arena Allocator），将 SubRun 及其附属数据（字形向量、顶点位置等）集中到一块连续的内存区域中。这种设计不仅减少了内存碎片和分配开销，更关键的是保证了 Slug 序列化/反序列化时的内存布局一致性。

`TextBlobRedrawCoordinator` 实现了一套基于 LRU 策略的三层缓存系统，通过 TextBlob 唯一 ID、Key 匹配和 SubRun 可重用性判断来最大化缓存命中率，避免不必要的重复字形处理。

## 架构图

```
+------------------------------------------------------------------+
|                     GlyphRunList (来自 src/text)                   |
+------------------------------------------------------------------+
                              |
                              v
+------------------------------------------------------------------+
|              SubRunContainer::MakeInAlloc()                       |
|  分析每个字形，选择最佳绘制策略                                     |
|  [SubRunControl 控制 SDFT/Direct/Path 策略选择]                    |
+------------------------------------------------------------------+
          |              |              |              |
          v              v              v              v
  +-------------+ +-------------+ +-----------+ +------------+
  |DirectMask   | |Transformed  | |SDFT       | |Path/       |
  |SubRun       | |MaskSubRun   | |SubRun     | |Drawable    |
  |(1:1 像素)    | |(需要变换)    | |(距离场)    | |SubRun      |
  +-------------+ +-------------+ +-----------+ +------------+
          |              |              |              |
          v              v              v              v
  +------------------------------------------------------------------+
  |                   AtlasSubRun (公共基类)                          |
  |  VertexFiller: 生成顶点数据                                       |
  |  GlyphVector:  延迟查找图集位置                                    |
  +------------------------------------------------------------------+
                              |
              +---------------+----------------+
              v                                v
  +------------------------+    +----------------------------+
  | TextBlob (缓存实体)     |    | SlugImpl (序列化快照)       |
  | TextBlobRedrawCoord.   |    | Slug::MakeFromBuffer()     |
  | 三层缓存 + LRU          |    | 跨进程文本绘制              |
  +------------------------+    +----------------------------+
                              |
                              v
  +------------------------------------------------------------------+
  |               GPU 后端 (Ganesh / Graphite)                        |
  |  AtlasTextOp / AtlasDrawDelegate                                 |
  |  字形图集管理 + 顶点缓冲区生成                                     |
  +------------------------------------------------------------------+
```

## 目录结构

```
src/text/gpu/
|-- BUILD.bazel                      # Bazel 构建配置
|-- DistanceFieldAdjustTable.h/.cpp  # 距离场文本调整查找表
|-- GlyphUtils.h                     # 字形工具函数
|-- GlyphVector.h/.cpp               # 字形向量（延迟后端数据绑定）
|-- SDFMaskFilter.h/.cpp             # SDF 掩码滤镜
|-- SkChromeRemoteGlyphCache.cpp     # Chromium 远程字形缓存
|-- Slug.cpp                         # Slug 基类实现
|-- SlugImpl.h/.cpp                  # Slug 具体实现
|-- StrikeCache.h/.cpp               # GPU 专用 Strike 缓存
|-- SubRunAllocator.h/.cpp           # SubRun 定制内存分配器
|-- SubRunContainer.h/.cpp           # SubRun 容器（策略选择核心）
|-- SubRunControl.h/.cpp             # SubRun 策略控制器
|-- TextBlob.h/.cpp                  # GPU TextBlob 缓存实体
|-- TextBlobRedrawCoordinator.h/.cpp # TextBlob 重绘协调器（三层缓存）
|-- VertexFiller.h/.cpp              # 顶点数据填充器
```

## 关键类与函数

### SubRunContainer（SubRun 容器）
```cpp
class SubRunContainer {
    static SubRunContainerOwner MakeInAlloc(
        const GlyphRunList& glyphRunList,
        const SkMatrix& positionMatrix,
        const SkPaint& runPaint,
        SkStrikeDeviceInfo strikeDeviceInfo,
        StrikeForGPUCacheInterface* strikeCache,
        SubRunAllocator* alloc,
        SubRunCreationBehavior creationBehavior,
        const char* tag);

    void draw(SkCanvas*, SkPoint drawOrigin, const SkPaint&,
              const SkRefCnt* subRunStorage, const AtlasDrawDelegate&) const;
};
```
SubRunContainer 是整个 GPU 文本渲染的入口。`MakeInAlloc()` 静态方法分析每个字形，根据大小、字体属性和变换矩阵，将字形分配到最佳类型的 SubRun 中。容器持有 `fInitialPositionMatrix` 用于后续的变换差异计算。

### SubRun 类型层次
```cpp
class SubRun {                    // 抽象基类
    virtual void draw(...) = 0;
    virtual bool canReuse(const SkPaint&, const SkMatrix&) = 0;
    void flatten(SkWriteBuffer&);
    static SubRunOwner MakeFromBuffer(SkReadBuffer&, ...);
};

class AtlasSubRun : public SubRun {  // 图集绘制基类
    VertexFiller fVertexFiller;       // 顶点数据生成
    GlyphVector fGlyphVector;         // 字形图集位置
    int glyphCount() const;
    skgpu::MaskFormat maskFormat() const;
};
```
SubRun 的三种图集绘制特化：
- **DirectMaskSubRun** - 字形与屏幕像素1:1对应，目标矩形在设备空间中，最高效的路径
- **TransformedMaskSubRun** - 字形需要在图集中变换后绘制，适用于大型彩色字形
- **SDFTSubRun** - 使用签名距离场的大号单色字形，在 Direct 和 Path 之间的尺寸范围

### GlyphVector（字形向量）
```cpp
class GlyphVector {
    SkStrikePromise fStrikePromise;
    SkSpan<GlyphBytes> fGlyphs;       // 初始为PackedGlyphID，后转为后端特定类型

    template <BackendData B>
    void initBackendData(StrikeCache* cache, MaskFormat maskFormat, auto&&... args);
};
```
GlyphVector 是连接平台无关字形数据和 GPU 后端特定数据的桥梁。它使用 C++20 概念（Concepts）约束后端数据类型 `BackendData` 和 `GlyphType`。初始状态下存储 `SkPackedGlyphID`，在 GPU 单线程环境中通过 `initBackendData()` 就地转换为后端特定的字形条目（包含图集位置信息）。

### VertexFiller（顶点填充器）
```cpp
class VertexFiller {
    skgpu::MaskFormat fMaskFormat;     // A8, A565, ARGB
    SkMatrix fCreationMatrix;          // 创建时的变换矩阵
    SkRect fCreationBounds;            // 创建时的边界
    SkSpan<const SkPoint> fLeftTop;    // 每个字形的左上角位置

    std::tuple<SkRect, SkMatrix> boundsAndDeviceMatrix(
        const SkMatrix& localToDevice, SkPoint drawOrigin) const;
    std::tuple<bool, SkRect> deviceRectAndCheckTransform(
        const SkMatrix& positionMatrix) const;
};
```
VertexFiller 负责将字形位置数据转换为 GPU 可用的顶点坐标。它的核心思想是计算"视图差异矩阵"（viewDifference），即当前绘制矩阵与创建时矩阵的差，通过这个差异矩阵将所有预计算的位置映射到新的设备坐标。

### SlugImpl（Slug 实现）
```cpp
class SlugImpl final : public Slug {
    SubRunAllocator fAlloc;              // 内联分配器
    SubRunContainerOwner fSubRuns;       // SubRun 容器
    const SkRect fSourceBounds;          // 源边界
    const SkPoint fOrigin;               // 绘制原点

    static sk_sp<SlugImpl> Make(const SkMatrix&, const GlyphRunList&,
                                const SkPaint&, SkStrikeDeviceInfo,
                                StrikeForGPUCacheInterface*);
    static sk_sp<Slug> MakeFromBuffer(SkReadBuffer&, const SkStrikeClient*);
};
```
Slug 是文本绘制的可序列化快照。在 Chromium 架构中，渲染器进程创建 Slug 并序列化，GPU 进程反序列化后直接重放绘制。SlugImpl 使用 placement new 和内联分配器将所有数据集中在一块连续内存中。

### TextBlob（GPU TextBlob）
```cpp
class TextBlob final : public SkRefCnt {
    struct Key {
        uint32_t fUniqueID;
        SkColor fCanonicalColor;         // 亮度桶规范色
        SkMatrix fPositionMatrix;        // 位置矩阵
        SkMaskFilterBase::BlurRec fBlurRec;
        // ... 更多用于缓存匹配的字段
    };
    SubRunAllocator fAlloc;
    SubRunContainerOwner fSubRuns;
};
```
TextBlob 是 GPU 文本缓存的核心实体。Key 结构包含影响文本渲染结果的所有因素，包括颜色亮度分桶（用于伽马校正）、矩阵、模糊参数等。

### TextBlobRedrawCoordinator（重绘协调器）
```cpp
class TextBlobRedrawCoordinator {
    // 三层缓存查找
    void drawGlyphRunList(SkCanvas*, const SkMatrix&, const GlyphRunList&,
                          const SkPaint&, SkStrikeDeviceInfo, const AtlasDrawDelegate&);
    // 消息总线清理
    void purgeStaleBlobs();
};
```
三层缓存策略：
1. 第一层：通过 `SkTextBlob::uniqueID()` 快速查找
2. 第二层：通过 `TextBlob::Key` 进行精确匹配
3. 第三层：通过 `SubRun::canReuse()` 检查是否可复用

### SubRunControl（SubRun 策略控制）
```cpp
class SubRunControl {
    bool isSDFT(SkScalar approximateDeviceTextSize, ...) const;
    bool isDirect(SkScalar approximateDeviceTextSize, ...) const;
    std::tuple<SkFont, SkScalar, SDFTMatrixRange> getSDFFont(...) const;
};
```
SubRunControl 控制字形的绘制策略选择。它定义了 SDFT（签名距离场文本）的尺寸范围 `[fMinDistanceFieldFontSize, fMaxDistanceFieldFontSize]`，在该范围内使用 SDF 渲染；低于该范围使用直接掩码；高于该范围使用路径。

### StrikeCache（GPU Strike 缓存）
```cpp
class StrikeCache {
    StrikeHash fCache;                    // 哈希表存储
    size_t fCacheSizeLimit;               // 2MB 默认限制
    int32_t fCacheCountLimit;             // 2048 默认条目限制
    size_t internalPurge(size_t minBytesNeeded);  // LRU 清理
};
```
GPU 专用的 Strike 缓存，使用双向链表实现 LRU 淘汰策略，通过哈希表提供 O(1) 查找性能。

### SubRunAllocator / BagOfBytes
```cpp
class BagOfBytes {
    // 斐波那契递增的内存块分配策略
    char* allocateBytes(int size, int alignment);
};
class SubRunAllocator {
    template <typename T, typename... Args> T* makePOD(Args&&... args);
    template <typename T, typename... Args>
    std::unique_ptr<T, Destroyer> makeUnique(Args&&... args);
};
```
定制的竞技场分配器，区分 POD 类型（无析构需求）和非 POD 类型（需要析构跟踪）。使用斐波那契数列递增块大小以平衡内存利用率和分配次数。

## 依赖关系

### 上游依赖
- `src/text/GlyphRun.h` - GlyphRun/GlyphRunList 输入数据
- `src/text/StrikeForGPU.h` - SkStrikePromise、StrikeForGPU 接口
- `src/core/SkGlyph.h` - 字形数据结构
- `src/core/SkStrikeSpec.h` - Strike 规格说明
- `src/gpu/MaskFormat.h` - 掩码格式枚举（A8/A565/ARGB）
- `include/core/SkMatrix.h` - 矩阵变换
- `include/private/chromium/Slug.h` - Slug 公共接口

### 下游消费者
- `src/gpu/ganesh/text/` - Ganesh 文本渲染操作
- `src/gpu/graphite/text/` - Graphite 文本渲染操作
- Chromium 的 `cc/paint/` 层 - 通过 Slug 接口

## 设计模式分析

### 策略模式（Strategy Pattern）
SubRun 的类型层次是典型的策略模式。`SubRunContainer::MakeInAlloc()` 充当策略选择器，根据字形大小、字体属性和变换矩阵为每个字形选择最优的 SubRun 类型。每种 SubRun 类型封装了不同的顶点生成和绘制逻辑。

### 享元模式（Flyweight Pattern）
`GlyphVector` 通过共享 Strike 缓存和延迟后端数据绑定实现了享元模式。多个 SubRun 可以共享相同的 Strike，而字形的图集位置数据直接就地覆盖原有的 PackedGlyphID。

### 竞技场分配模式（Arena Allocation）
`SubRunAllocator` 和 `BagOfBytes` 实现了竞技场分配模式，将生命周期相同的对象集中管理。这种模式在 Slug 的序列化/反序列化过程中尤为重要，因为所有数据可以作为一个整体进行传输。

### 观察者模式（Observer Pattern）
`TextBlobRedrawCoordinator` 通过 `SkMessageBus<PurgeBlobMessage>` 实现了跨线程的缓存失效通知，当 `SkTextBlob` 被销毁时，通过消息总线通知缓存系统清理相关数据。

### 概念约束模式（Concepts-Based Polymorphism）
`GlyphVector` 使用 C++20 概念（`BackendData` 和 `GlyphType`）替代传统的虚函数继承，在编译时约束后端类型的接口要求，避免了虚函数调用的运行时开销。

## 数据流

```
1. 输入处理
   GlyphRunList --> SubRunContainer::MakeInAlloc()
        |
2. 策略分类 (由 SubRunControl 控制)
   对每个字形计算设备空间近似大小
        |
   +----+----------+----------+----------+
   |    |          |          |          |
   v    v          v          v          v
   小字形  中等字形   大字形    超大字形   彩色字形
   Direct  SDFT     Path     Path      Transformed
   Mask    SubRun   SubRun   SubRun    Mask SubRun
        |
3. SubRun 构建
   为每种类型的 SubRun 创建:
   - VertexFiller (位置 + 掩码格式 + 创建矩阵)
   - GlyphVector (SkStrikePromise + PackedGlyphID[])
        |
4. 封装
   +---> TextBlob: 带缓存 Key 的 SubRunContainer
   |     (用于 drawTextBlob 的热路径)
   |
   +---> SlugImpl: 可序列化的 SubRunContainer
         (用于 Chromium 跨进程传输)
        |
5. 绘制执行
   SubRun::draw() --> AtlasDrawDelegate
   - GlyphVector::initBackendData() 将 PackedGlyphID 转为图集条目
   - VertexFiller 生成设备空间顶点坐标
   - GPU 后端执行 AtlasTextOp 或等效操作
```

## 相关文档与参考

- `src/text/README.md` - 上层文本渲染核心模块
- `src/gpu/ganesh/text/` - Ganesh GPU 后端文本操作
- `src/gpu/graphite/text/` - Graphite GPU 后端文本操作
- `include/private/chromium/Slug.h` - Slug 的公共 API 定义
- `src/core/SkStrikeSpec.h` - Strike 规格说明
- `src/gpu/MaskFormat.h` - GPU 掩码格式定义
- 签名距离场文本渲染技术: Valve 的 "Improved Alpha-Tested Magnification for Vector Textures and Special Effects" (SIGGRAPH 2007)
- Skia GPU 文本渲染设计文档（内部文档）
