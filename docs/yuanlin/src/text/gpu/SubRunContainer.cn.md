# SubRunContainer - SubRun 容器与子运行系统

> 源文件: `src/text/gpu/SubRunContainer.h`, `src/text/gpu/SubRunContainer.cpp`

## 概述

SubRunContainer 是 Skia GPU 文本渲染的核心组件，负责将 GlyphRunList 分解为不同类型的 SubRun（子运行），每种 SubRun 对应一种最优的 GPU 渲染策略。本模块定义了完整的 SubRun 类层次结构，包括：

- **DirectMaskSubRun** — 设备像素 1:1 对应的直接遮罩渲染（最常见）
- **TransformedMaskSubRun** — 需要变换的遮罩渲染（大色彩字形或非 1:1 映射）
- **SDFTSubRun** — 有符号距离场文本渲染（中等大小单色字形）
- **PathSubRun** — 路径渲染（大字形）
- **DrawableSubRun** — Drawable 渲染（特殊字形）

该文件是 Skia 中最大和最复杂的文本渲染文件之一（约 1900 行），涵盖了从字形分类、SubRun 创建到 GPU 渲染的完整流程。

## 架构位置

```
sktext::gpu 命名空间
  SubRun (基类)
    ├── PathSubRun
    ├── DrawableSubRun
    └── AtlasSubRun (Atlas 渲染基类)
          ├── DirectMaskSubRun
          ├── TransformedMaskSubRun
          └── SDFTSubRun

  SubRunList — SubRun 链表
  SubRunContainer — 容器，持有 SubRunList 和初始矩阵
```

- **创建者**: TextBlob::Make、SlugImpl::Make
- **渲染者**: GPU 后端（通过 AtlasDrawDelegate 回调）

## 主要类与结构体

### SubRun（基类）
所有 SubRun 的纯虚基类，使用链表 `fNext` 连接。

**纯虚方法**:
- `draw()` — 绘制
- `unflattenSize()` — 反序列化大小估算
- `canReuse()` — 是否可重用
- `subRunStreamTag()` — 序列化标签
- `doFlatten()` — 序列化

### AtlasSubRun
Atlas（图集）渲染的 SubRun 基类，持有 VertexFiller 和 GlyphVector。

**关键方法**:
- `glyphCount()` — 字形数量
- `maskFormat()` — 遮罩格式（A8、ARGB、A565）
- `deviceRectAndNeedsTransform()` — 设备矩形和是否需要变换
- `glyphParams()` — 渲染参数（isSDF、isLCD、isAA）
- `vertexFiller()` / `glyphVector()` — 访问内部组件

### SubRunList
使用 SubRunOwner（unique_ptr + Destroyer）的侵入式链表。

### SubRunContainer
**成员**:
- `fInitialPositionMatrix` — 创建时的位置矩阵
- `fSubRuns` — SubRun 链表

### RendererData
传递给 AtlasDrawDelegate 的渲染参数：isSDF、isLCD、maskFormat。

### PathOpSubmitter / DrawableOpSubmitter
内部辅助类，封装路径/Drawable 字形的延迟转换和渲染提交逻辑。

## 公共 API 函数

### SubRunContainer
```cpp
static SubRunContainerOwner MakeInAlloc(
    const GlyphRunList&, const SkMatrix&, const SkPaint&,
    SkStrikeDeviceInfo, StrikeForGPUCacheInterface*,
    SubRunAllocator*, SubRunCreationBehavior, const char* tag);

static SubRunContainerOwner MakeFromBufferInAlloc(
    SkReadBuffer&, const SkStrikeClient*, SubRunAllocator*);

static size_t EstimateAllocSize(const GlyphRunList&);
static int AllocSizeHintFromBuffer(SkReadBuffer&);

void draw(SkCanvas*, SkPoint, const SkPaint&, const SkRefCnt*, const AtlasDrawDelegate&) const;
bool canReuse(const SkPaint&, const SkMatrix&) const;
```

### SubRun
```cpp
static SubRunOwner MakeFromBuffer(SkReadBuffer&, SubRunAllocator*, const SkStrikeClient*);
void flatten(SkWriteBuffer&) const;
```

## 内部实现细节

### SubRun 分类决策（在 MakeInAlloc 中）
对每个 GlyphRun，根据字体大小和设备参数决定渲染策略：
1. **Direct**: 当 approximateDeviceTextSize 满足直接渲染条件时
2. **SDFT**: 大小在 SDFT 范围内的单色文本
3. **Path/Drawable**: 大字形或需要路径效果时
4. **Transformed**: 其他情况

### DirectMaskSubRun
- 设备像素 1:1 对应，无额外源空间到设备空间变换
- 目标矩形在设备空间
- `canReuse` 检查矩阵是否支持整数平移重用
- `glyphSrcPadding() = 0`

### TransformedMaskSubRun
- Atlas 中的字形需要变换到屏幕
- 目标矩形在源空间
- 有 1 像素的源边距（`glyphSrcPadding() = 1`）
- `canReuse` 仅检查初始矩阵的缩放是否 >= 1

### SDFTSubRun
- 使用有符号距离场渲染
- 固定使用 `MaskFormat::kA8`
- 额外存储 useLCDText、antiAliased、matrixRange
- `canReuse` 通过 matrixRange 检查矩阵是否在有效范围内
- `glyphSrcPadding() = SK_DistanceFieldInset`

### PathOpSubmitter
延迟将字形 ID 转换为 SkPath：
1. 初始创建时只存储 GlyphID（在 IDOrPath union 中）
2. 首次 submitDraws 时通过 `SkOnce` 线程安全地转换为 SkPath
3. 渲染时根据是否需要精确 CTM 选择两种路径：
   - 不需要: 在 canvas 上设置矩阵并直接绘制路径
   - 需要: 先变换路径到设备空间，再绘制

### DrawableOpSubmitter
类似 PathOpSubmitter，但将字形 ID 转换为 SkDrawable。注意：不能释放 Strike 引用，因为 Drawable 数据的生命周期依赖于 Strike。

### 多格式处理（add_multi_mask_format）
当一个 GlyphRun 中的字形有不同的遮罩格式时（如混合 A8 和 ARGB），将它们分组为不同格式的 SubRun。

### 序列化
使用 SubRunStreamTag 枚举标识各 SubRun 类型：
- kDirectMaskStreamTag
- kSDFTStreamTag
- kTransformMaskStreamTag
- kPathStreamTag
- kDrawableStreamTag

反序列化使用函数指针表根据标签分派到对应的 MakeFromBuffer。

## 依赖关系

- `GlyphVector` / `VertexFiller` — Atlas SubRun 的核心组件
- `SubRunAllocator` — 内存分配
- `GlyphRunList` — 输入数据
- `StrikeForGPU` — Strike 接口（IDOrPath、IDOrDrawable）
- `SubRunControl` — SubRun 类型决策策略
- `SDFMaskFilter` — SDF 文本的遮罩生成
- `SkDistanceFieldGen` — SDF 相关常量
- `SkRasterPipeline` — 无（纯 GPU 路径）

## 设计模式与设计决策

1. **策略模式**: SubRunControl 决定字形的渲染策略
2. **延迟转换**: PathOpSubmitter/DrawableOpSubmitter 延迟字形 ID 到渲染数据的转换
3. **线程安全**: SkOnce 确保路径/Drawable 转换仅执行一次
4. **链表而非数组**: SubRunList 使用侵入式链表，避免在 arena 中分配连续内存
5. **不可移动**: SubRunContainer 禁用移动操作（SubRun 可能引用 fInitialPositionMatrix）
6. **kStrikeCalculationsOnly**: 允许仅执行 Strike 计算而不创建 SubRun（用于预热缓存）

## 性能考量

- Direct SubRun 是最常见和最快的路径，仅需整数平移即可重用
- SDF SubRun 在一定缩放范围内可重用，减少重建频率
- Path SubRun 始终可重用（缩放无关）
- EstimateAllocSize 预估内存减少分配次数
- add_multi_mask_format 按格式分组减少 GPU draw call 切换
- PathOpSubmitter 的 needsExactCTM 检查避免了不必要的路径变换

## 相关文件

- `src/text/gpu/GlyphVector.h` — 字形向量
- `src/text/gpu/VertexFiller.h` — 顶点填充器
- `src/text/gpu/SubRunAllocator.h` — 内存分配器
- `src/text/gpu/SubRunControl.h` — SubRun 类型决策
- `src/text/gpu/TextBlob.h` — TextBlob（SubRunContainer 的所有者）
- `src/text/gpu/SlugImpl.h` — Slug（SubRunContainer 的所有者）
- `src/text/StrikeForGPU.h` — Strike 接口和 IDOrPath/IDOrDrawable
