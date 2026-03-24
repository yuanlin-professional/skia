# SkGlyph

> 源文件
> - src/core/SkGlyph.h
> - src/core/SkGlyph.cpp

## 概述

`SkGlyph` 是 Skia 字形渲染系统的核心数据结构,用于表示单个字形的完整信息,包括度量信息、位图数据、路径数据和可绘制对象。它封装了字形的所有渲染相关属性,如边界框、前进量、遮罩格式以及实际的渲染内容。该类提供了高效的字形数据管理和序列化机制,支持多种字形表示形式(位图、路径、矢量图形)的按需加载。

`SkPackedGlyphID` 是一个紧凑的字形标识符,将 glyph ID 和子像素位置信息打包到单个 32 位整数中,实现高效的字形缓存和查找。`SkGlyphDigest` 是字形的轻量级摘要信息,用于 GPU 绘制决策,无需访问完整的字形数据。

## 架构位置

`SkGlyph` 位于 Skia 文本渲染管线的核心层,连接字体缩放器(scaler context)和文本绘制器之间:

- **上游依赖**: `SkScalerContext` 负责从字体文件生成字形度量和图像数据
- **下游使用**: `SkStrike`(字形缓存)、文本绘制管线使用 `SkGlyph` 进行渲染
- **协作模块**: 与 `SkMask`、`SkPath`、`SkDrawable` 等渲染抽象协作
- **存储管理**: 使用 `SkArenaAlloc` 进行高效的内存分配

## 主要类与结构体

### SkPackedGlyphID

字形标识符,打包 glyph ID 和子像素位置信息。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fID | uint32_t | 打包的 ID(16位 glyph ID + 4位子像素位置) |

### SkGlyphPositionRoundingSpec

子像素位置舍入规范。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| halfAxisSampleFreq | SkVector | 半轴采样频率 |
| ignorePositionMask | SkIPoint | 位置忽略掩码 |
| ignorePositionFieldMask | SkIPoint | 位置字段忽略掩码 |

### SkGlyphRect

使用 SIMD 优化的矩形类,用于快速并集和交集计算。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fRect | skvx::Vec&lt;4, SkScalar&gt; | SIMD 向量存储(-left, -top, right, bottom) |

### SkGlyphDigest

字形摘要信息,用于 GPU 绘制决策。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPackedID | uint64_t:20 | 打包的字形 ID |
| fIndex | uint64_t:20 | 字形索引 |
| fIsEmpty | uint64_t:1 | 是否为空字形 |
| fFormat | uint64_t:3 | 遮罩格式 |
| fActions | uint64_t:12 | 各种动作类型的状态 |
| fLeft, fTop | int16_t | 字形原点偏移 |
| fWidth, fHeight | uint16_t | 字形尺寸 |

### SkGlyph

**继承关系**: 无直接继承,但有友元类 `SkScalerContext`

| 关键成员变量 | 类型 | 说明 |
|-------------|------|------|
| fID | SkPackedGlyphID | 字形标识符 |
| fWidth, fHeight | uint16_t | 字形遮罩尺寸 |
| fTop, fLeft | int16_t | 字形原点到遮罩左上角的偏移 |
| fImage | void* | 图像数据指针 |
| fPathData | PathData* | 路径数据 |
| fDrawableData | DrawableData* | 可绘制对象数据 |
| fAdvanceX, fAdvanceY | float | 前进量 |
| fMaskFormat | SkMask::Format | 遮罩格式(BW/A8/LCD/ARGB32/SDF) |
| fScalerContextBits | uint16_t | 缩放器上下文特定标志位 |

### SkPictureBackedGlyphDrawable

**继承关系**: 继承自 `SkDrawable`

| 关键成员变量 | 类型 | 说明 |
|-------------|------|------|
| fPicture | sk_sp&lt;SkPicture&gt; | 封装的 Picture 对象 |

## 公共 API 函数

### SkPackedGlyphID

```cpp
// 构造函数
constexpr SkPackedGlyphID(SkGlyphID glyphID)
constexpr SkPackedGlyphID(SkGlyphID glyphID, SkFixed x, SkFixed y)
SkPackedGlyphID(SkGlyphID glyphID, SkPoint pt, SkIPoint mask)

// 访问方法
SkGlyphID glyphID() const
uint32_t value() const
SkFixed getSubXFixed() const
SkFixed getSubYFixed() const
uint32_t hash() const
```

### SkGlyph

```cpp
// 工厂方法
static std::optional<SkGlyph> MakeFromBuffer(SkReadBuffer&)

// 度量访问
SkVector advanceVector() const
int width() const, int height() const
int left() const, int top() const
SkIRect iRect() const
SkRect rect() const
bool isEmpty() const

// 图像管理
bool setImage(SkArenaAlloc* alloc, SkScalerContext* scalerContext)
bool setImage(SkArenaAlloc* alloc, const void* image)
bool setImageHasBeenCalled() const
const void* image() const
size_t imageSize() const
SkMask mask() const
SkMask mask(SkPoint position) const

// 路径管理
bool setPath(SkArenaAlloc* alloc, SkScalerContext* scalerContext)
bool setPath(SkArenaAlloc* alloc, const SkPath* path, bool hairline, bool modified)
bool setPathHasBeenCalled() const
const SkPath* path() const
bool pathIsHairline() const
bool pathIsModified() const

// 可绘制对象管理
bool setDrawable(SkArenaAlloc* alloc, SkScalerContext* scalerContext)
bool setDrawable(SkArenaAlloc* alloc, sk_sp<SkDrawable> drawable)
SkDrawable* drawable() const

// 序列化
void flattenMetrics(SkWriteBuffer&) const
void flattenImage(SkWriteBuffer&) const
void flattenPath(SkWriteBuffer&) const
void flattenDrawable(SkWriteBuffer&) const
size_t addImageFromBuffer(SkReadBuffer&, SkArenaAlloc*)
size_t addPathFromBuffer(SkReadBuffer&, SkArenaAlloc*)
size_t addDrawableFromBuffer(SkReadBuffer&, SkArenaAlloc*)
```

### SkGlyphDigest

```cpp
// 构造与查询
SkGlyphDigest(size_t index, const SkGlyph& glyph)
int index() const
bool isEmpty() const
bool isColor() const
SkMask::Format maskFormat() const

// 动作管理
skglyph::GlyphAction actionFor(skglyph::ActionType actionType) const
void setActionFor(skglyph::ActionType, SkGlyph*, sktext::StrikeForGPU*)

// 尺寸检查
bool fitsInAtlasDirect() const
bool fitsInAtlasInterpolated() const
uint16_t maxDimension() const
SkGlyphRect bounds() const
```

## 内部实现细节

### 子像素定位编码

`SkPackedGlyphID` 使用位域技术将字形 ID 和子像素位置打包到 32 位:
- 位 0-1: X 轴子像素位置 (2位)
- 位 2-17: Glyph ID (16位)
- 位 18-19: Y 轴子像素位置 (2位)

子像素位置提供 4 级精度(2位),通过 `kSubpixelRound = 1/(2^3)` 常量舍入。

### 延迟加载机制

字形数据采用按需加载策略:
1. 初始创建时仅包含 `SkPackedGlyphID`
2. 度量信息由 `SkScalerContext::getMetrics()` 填充
3. 图像/路径/可绘制对象通过 `setImage/setPath/setDrawable` 按需生成
4. 使用标志位(`setImageHasBeenCalled()`)避免重复请求

### 内存管理

- **Arena 分配**: 所有可变大小数据(图像、路径)通过 `SkArenaAlloc` 分配,支持批量释放
- **对齐要求**: 图像数据按格式对齐(ARGB32→4字节, A8→1字节)
- **尺寸限制**: `kMaxGlyphWidth = 8192` 防止过大的字形消耗内存

### 路径间隙计算

`calculate_path_gap()` 函数为下划线/删除线计算字形路径与水平线的交集:
- 使用 Bézier 曲线求交算法(`SkBezierQuad::IntersectWithHorizontalLine`)
- 处理直线、二次和三次曲线
- 返回左右边界用于文本装饰绘制

### SkGlyphDigest 动作状态机

使用 12 位字段存储 6 种动作类型的状态(每个 2 位):
- `kDirectMask`: 直接遮罩绘制
- `kDirectMaskCPU`: CPU 端直接遮罩
- `kMask`: 需要插值的遮罩
- `kSDFT`: 有向距离场文本
- `kPath`: 路径绘制
- `kDrawable`: 可绘制对象

每个动作有 4 种状态: `kUnset`, `kAccept`, `kReject`, `kDrop`

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkScalerContext | 生成字形度量和图像数据 |
| SkMask | 字形遮罩表示 |
| SkPath | 矢量字形路径 |
| SkDrawable | 复杂字形的可绘制表示 |
| SkArenaAlloc | 内存分配器 |
| SkReadBuffer/SkWriteBuffer | 序列化支持 |
| SkChecksum | ID 哈希计算 |
| skvx | SIMD 向量运算 |
| SkBezierCurves | 曲线求交 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkStrike | 使用 SkGlyph 作为缓存条目 |
| SkGlyphRunPainter | 使用 SkGlyph 进行文本绘制 |
| StrikeForGPU | GPU 文本渲染使用 SkGlyphDigest |
| SubRunContainer | 使用字形度量进行文本布局 |
| SkRemoteGlyphCache | 跨进程字形缓存传输 |

## 设计模式与设计决策

### 按需加载模式

字形数据分阶段加载:
- **阶段 1**: 度量信息(边界、前进量)
- **阶段 2**: 渲染数据(图像/路径/可绘制对象之一)

优点: 减少内存占用,支持不同渲染路径的选择。

### 多态表示

单个字形可以有三种表示:
1. **位图(fImage)**: 栅格化遮罩,适合小字号
2. **路径(fPathData)**: 矢量表示,适合大字号或变换
3. **可绘制对象(fDrawableData)**: 复杂字形(如 OpenType SVG、COLRv1)

设计决策: 路径和可绘制对象不能同时存在,通过 nullable 指针管理生命周期。

### 位域压缩

`SkGlyphDigest` 使用 C++ 位域将多个字段压缩到最少字节:
- 总大小 64位 + 4×16位 = 128位
- 避免在远程缓存中传输完整 `SkGlyph`
- 50% 负载因子哈希表优化查找性能(Speedometer3 基准测试验证)

### Intercepts 缓存

字形的文本装饰交集计算结果缓存在链表中:
```cpp
struct Intercept {
    Intercept* fNext;
    SkScalar fBounds[2];    // 装饰线的上下边界
    SkScalar fInterval[2];  // 字形路径与装饰线的交集区间
};
```

避免重复计算相同装饰线位置的交集。

### 不可变性保证

关键决策:
- 字形数据一旦设置即不可变(通过 `setXxxHasBeenCalled()` 检查)
- 图像/路径/可绘制对象只能设置一次
- 防止缓存一致性问题

## 性能考量

### 子像素定位

2 位子像素精度提供 4 个对齐位置,平衡内存使用和渲染质量:
- LCD 文本通常需要子像素定位
- `ignorePositionMask` 允许在不支持子像素时禁用

### 尺寸限制

- **Atlas 最大尺寸**: 256×256 像素(`kSkSideTooBigForAtlas`)
- **插值 padding**: 插值字形需额外 2 像素边距
- 超大字形自动降级到路径渲染

### SIMD 优化

`SkGlyphRect` 使用 `skvx::Vec<4, SkScalar>` 存储矩形:
- 向量化并集/交集运算(`skvx::max/min`)
- 存储为 `(-left, -top, right, bottom)` 便于 SIMD 操作

### 哈希表负载因子

`SkGlyphDigest` 哈希表使用 50% 负载因子(而非传统 75%):
- 减少哈希冲突
- 在 Speedometer3 Editor-TipTap 基准测试中显著提升性能
- 平衡内存使用和查找速度

### Arena 分配器

使用 `SkArenaAlloc` 管理字形数据:
- 批量分配减少碎片
- 按 strike 生命周期批量释放
- 避免逐字形 malloc/free 开销

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/core/SkScalerContext.h | 生产者 | 生成字形度量和数据 |
| src/core/SkStrike.h | 容器 | 字形缓存管理 |
| src/core/SkGlyphRunPainter.cpp | 消费者 | 使用字形进行绘制 |
| src/text/StrikeForGPU.h | 消费者 | GPU 文本渲染 |
| src/core/SkMask.h | 数据结构 | 字形遮罩表示 |
| include/core/SkPath.h | 数据结构 | 矢量字形路径 |
| include/core/SkDrawable.h | 数据结构 | 可绘制字形 |
| src/base/SkArenaAlloc.h | 工具 | 内存分配器 |
| src/base/SkBezierCurves.h | 工具 | 曲线求交算法 |
