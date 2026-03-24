# AtlasTextOp

> 源文件
> - src/gpu/ganesh/ops/AtlasTextOp.h
> - src/gpu/ganesh/ops/AtlasTextOp.cpp

## 概述

`AtlasTextOp` 是 Skia Ganesh GPU 后端的文本渲染操作类，负责将文本字形通过图集（Atlas）纹理高效渲染到 GPU。该操作支持多种遮罩格式（灰度、LCD、彩色位图）和距离场文本（SDF）渲染，能够批量处理大量字形以优化性能。

该类的核心优势在于利用纹理图集技术将多个字形打包到共享纹理中，通过实例化绘制减少状态切换和绘制调用次数。支持透视变换、局部坐标、几何裁剪等高级特性，是 Skia 文本渲染管线的关键组件。

## 架构位置

`AtlasTextOp` 位于 Skia GPU 渲染管线的操作层：

```
Skia 文本渲染架构:
├── SkCanvas / SkTextBlob
├── 文本处理层
│   ├── SubRunContainer
│   └── AtlasSubRun
├── GPU 操作层
│   └── AtlasTextOp ← 本类位于此处
├── 几何处理器
│   ├── GrBitmapTextGeoProc (位图文本)
│   ├── GrDistanceFieldA8TextGeoProc (SDF 灰度)
│   └── GrDistanceFieldLCDTextGeoProc (SDF LCD)
└── 图集管理
    └── GrAtlasManager
```

## 主要类与结构体

### AtlasTextOp 类

继承自 `GrMeshDrawOp`，实现文本的批量网格绘制。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fProcessors` | `GrProcessorSet` | 片段处理器集合，处理颜色和效果 |
| `fNumGlyphs` | `int` | 所有几何体中的总字形数量 |
| `fDFGPFlags` | `uint32_t : 10` | 距离场几何处理器标志（10 位） |
| `fMaskType` | `uint32_t : 3` | 遮罩类型（3 位，最多 8 种类型） |
| `fUsesLocalCoords` | `uint32_t : 1` | 是否使用局部坐标 |
| `fNeedsGlyphTransform` | `uint32_t : 1` | 字形是否需要变换 |
| `fHasPerspective` | `uint32_t : 1` | 是否包含透视变换 |
| `fUseGammaCorrectDistanceTable` | `uint32_t : 1` | 是否使用伽马校正距离表 |
| `fColorSpaceXform` | `sk_sp<GrColorSpaceXform>` | 色彩空间转换（仅彩色 emoji） |
| `fLuminanceColor` | `SkColor` | 亮度颜色（SDF 渲染用） |
| `fHead/fTail` | `Geometry*` | 几何体链表头/尾指针 |

### MaskType 枚举

| 类型 | 说明 | 应用场景 |
|------|------|---------|
| `kGrayscaleCoverage` | 灰度覆盖率遮罩 | 标准抗锯齿文本 |
| `kLCDCoverage` | LCD 子像素遮罩 | LCD 文本渲染（A565 格式） |
| `kColorBitmap` | 彩色位图 | 彩色 emoji 和图像字形 |
| `kAliasedDistanceField` | 无抗锯齿距离场 | 别名 SDF 文本 |
| `kGrayscaleDistanceField` | 灰度距离场 | 抗锯齿 SDF 文本 |
| `kLCDDistanceField` | LCD 距离场 | LCD SDF 文本 |

### Geometry 结构体

存储单个文本子运行的渲染参数：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSubRun` | `const sktext::gpu::AtlasSubRun&` | 图集子运行对象引用 |
| `fSupportDataKeepAlive` | `sk_sp<SkRefCnt>` | 保持 TextBlob 或 Slug 存活 |
| `fDrawMatrix` | `SkMatrix` | 绘制变换矩阵 |
| `fDrawOrigin` | `SkPoint` | 绘制原点 |
| `fClipRect` | `SkIRect` | 几何裁剪矩形（仅 DirectMask 使用） |
| `fColor` | `SkPMColor4f` | 预乘 alpha 颜色 |
| `fNext` | `Geometry*` | 链表下一节点 |

### FlushInfo 结构体

刷新时的临时状态信息：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVertexBuffer` | `sk_sp<const GrBuffer>` | 顶点缓冲区 |
| `fIndexBuffer` | `sk_sp<const GrBuffer>` | 索引缓冲区 |
| `fGeometryProcessor` | `GrGeometryProcessor*` | 几何处理器 |
| `fPrimProcProxies` | `const GrSurfaceProxy**` | 图集纹理代理数组 |
| `fGlyphsToFlush` | `int` | 待刷新的字形数量 |
| `fVertexOffset` | `int` | 顶点缓冲区偏移 |
| `fNumDraws` | `int` | 绘制调用次数 |

## 公共 API 函数

### 工厂方法

```cpp
static std::tuple<const GrClip*, GrOp::Owner> Make(
    SurfaceDrawContext*, const sktext::gpu::AtlasSubRun*, const GrClip*,
    const SkMatrix& viewMatrix, SkPoint drawOrigin, const SkPaint&,
    sk_sp<SkRefCnt>&& subRunStorage)
```
创建 `AtlasTextOp` 实例。返回优化后的裁剪对象和操作所有权。处理几何裁剪、颜色计算、SDF 参数配置等。

### 内存管理

```cpp
void* operator new(size_t s)
void operator delete(void* b) noexcept
static void ClearCache()
```
使用线程局部缓存优化内存分配，避免频繁的堆分配开销。

### GrMeshDrawOp 接口实现

```cpp
const char* name() const override
```
返回操作名称 "AtlasTextOp"。

```cpp
void visitProxies(const GrVisitProxyFunc&) const override
```
访问片段处理器使用的纹理代理（图集代理在准备阶段动态添加）。

```cpp
FixedFunctionFlags fixedFunctionFlags() const override
```
返回固定功能标志（文本渲染不使用特殊固定功能）。

```cpp
GrProcessorSet::Analysis finalize(const GrCaps&, const GrAppliedClip*,
                                  GrClampType) override
```
最终化处理器分析，确定覆盖率类型、颜色常量化、局部坐标使用等。

## 内部实现细节

### 线程局部内存缓存

使用 `thread_local` 变量 `gCache` 缓存单个 `AtlasTextOp` 的内存：
- **优势**：避免小对象频繁分配/释放的开销
- **限制**：每线程只缓存一个实例
- **清理**：通过 `ClearCache()` 显式释放

### 几何裁剪优化

`calculate_clip` 函数判断裁剪方法：
1. **kClippedOut**：完全裁剪，跳过操作
2. **kUnclipped**：无需裁剪
3. **kGeometryClipped**：使用 CPU 端几何裁剪（矩形且像素对齐）
4. **kGPUClipped**：使用 GPU 裁剪

几何裁剪避免了 GPU 裁剪开销，适用于轴对齐矩形裁剪区域。

### 距离场参数计算

`calculate_sdf_parameters` 根据上下文计算 SDF 标志：
- **相似变换标志**：`kSimilarity_DistanceFieldEffectFlag`
- **缩放平移标志**：`kScaleOnly_DistanceFieldEffectFlag`
- **伽马校正标志**：`kGammaCorrect_DistanceFieldEffectFlag`
- **别名标志**：`kAliased_DistanceFieldEffectFlag`
- **透视标志**：`kPerspective_DistanceFieldEffectFlag`
- **LCD 相关标志**：`kUseLCD_DistanceFieldEffectFlag`、`kBGR_DistanceFieldEffectFlag`、`kPortrait_DistanceFieldEffectFlag`

### 顶点数据生成

`fillVertexData` 方法：
1. 应用绘制原点到变换矩阵
2. 调用 `GlyphData::fillVertexData` 填充顶点
3. 每个字形生成 4 个顶点（矩形四边形）
4. 顶点包含位置、纹理坐标、颜色等属性

### 图集再生机制

`onPrepareDraws` 中的图集管理：
1. 获取当前图集视图（可能包含多个纹理页）
2. 遍历所有几何体和字形
3. 调用 `glyphData.regenerateAtlas` 确保字形在图集中
4. 如果图集满或顶点缓冲区满，创建部分绘制
5. 动态添加新的图集纹理页到几何处理器

### 批量绘制流程

```
onPrepareDraws:
├── 计算局部坐标矩阵
├── 获取图集管理器和视图
├── 创建几何处理器（Bitmap 或 SDF）
├── 分配顶点/索引缓冲区
├── 遍历所有几何体
│   ├── 初始化后端数据（GlyphData）
│   ├── 再生图集（确保字形已上传）
│   ├── 填充顶点数据
│   └── 缓冲区满或图集满时创建绘制
└── 通过 FlushInfo 管理状态

onExecute:
├── 创建管线
└── 执行所有绘制和上传
```

### 操作合并条件

`onCombineIfPossible` 检查以下条件：
- 所有标志位必须匹配（`fDFGPFlags`、`fMaskType` 等）
- 片段处理器集合相同
- 如果使用局部坐标，绘制矩阵必须相同
- SDF 文本的亮度颜色必须匹配
- 彩色位图的颜色必须相同

满足条件时合并几何体链表，累加字形数量。

### 动态图集页管理

图集可能在准备过程中增长（添加新页）：
- 检测 `gp->numTextureSamplers() != numActiveViews`
- 调用 `addNewViews` 更新几何处理器的纹理采样器
- 为现有绘制增加新代理的引用计数

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrMeshDrawOp` | 继承 | 网格绘制操作基类 |
| `AtlasSubRun` | 核心依赖 | 图集子运行，提供字形数据 |
| `GrAtlasManager` | 强依赖 | 管理字形图集纹理 |
| `GrBitmapTextGeoProc` | 强依赖 | 位图文本几何处理器 |
| `GrDistanceFieldGeoProc` | 强依赖 | 距离场文本几何处理器 |
| `GlyphData` | 强依赖 | 字形后端数据管理 |
| `GrProcessorSet` | 强依赖 | 片段处理器集合 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `SurfaceDrawContext` | 创建 | 通过 `Make` 工厂方法创建操作 |
| `SubRunContainer` | 使用 | 文本子运行容器调用此操作渲染文本 |
| `SkTextBlob` | 间接使用 | 通过文本 blob 渲染管线使用 |

## 设计模式与设计决策

### 1. 工厂方法模式

使用 `Make` 静态工厂方法而非公共构造函数：
- 封装复杂的创建逻辑（裁剪计算、颜色转换、参数配置）
- 返回优化后的裁剪对象和操作所有权
- 允许返回 `nullptr` 表示跳过渲染

### 2. 线程局部缓存优化

设计决策：使用 `thread_local` 缓存单个实例
- **权衡**：只缓存一个实例 vs 缓存池的复杂性
- **理由**：文本操作通常连续创建，单实例缓存命中率高
- **效果**：显著减少文本密集场景的内存分配开销

### 3. 位域优化

使用位域存储标志以节省内存：
- `fDFGPFlags : 10`：距离场标志
- `fMaskType : 3`：遮罩类型（最多 8 种）
- 5 个单比特标志

总计 18 位，打包到 3 字节而非 7 个独立字节。

### 4. 链表管理几何体

使用侵入式链表而非容器：
- **优点**：无额外内存分配，缓存友好
- **管理**：通过 `fHead/fTail` 指针高效追加
- **生命周期**：在操作析构时手动释放

### 5. 延迟图集代理添加

图集代理在 `onPrepareDraws` 时才添加到 `sampledProxyArray`：
- **原因**：创建时图集纹理尚未确定
- **实现**：在准备阶段遍历视图手动添加
- **动态性**：支持图集在准备期间增长

### 6. 两种几何处理器路径

根据 `usesDistanceFields()` 选择处理器：
- **SDF 路径**：`setupDfProcessor`，支持 LCD 和灰度
- **Bitmap 路径**：`GrBitmapTextGeoProc`，使用纹理过滤

SDF 提供更好的缩放质量，Bitmap 性能更优。

### 7. 几何裁剪与 GPU 裁剪的权衡

优先使用几何裁剪（`kGeometryClipped`）：
- **条件**：矩形裁剪且像素对齐
- **优势**：避免 GPU 裁剪开销，减少片段处理
- **实现**：在顶点数据填充时应用裁剪矩形

## 性能考量

### 1. 线程局部缓存

每线程缓存单个 `AtlasTextOp` 实例，避免 95%+ 的堆分配。

### 2. 批量合并

通过 `onCombineIfPossible` 合并兼容操作：
- 减少绘制调用次数
- 共享几何处理器和管线设置
- 累积字形到更大的批次

### 3. 顶点缓冲区分块

限制单次顶点分配不超过 `kMaxVertexBytes`（默认缓冲区大小）：
- 避免巨大的连续内存分配
- 在大文本量时自动分批绘制

### 4. 图集再生优化

只再生需要的字形范围（`subRunCursor` 到 `regenEnd`）：
- 避免重新上传已在图集中的字形
- 分批处理减少单次上传量

### 5. 索引缓冲区复用

使用 `refNonAAQuadIndexBuffer` 共享索引缓冲区：
- 所有字形使用相同的四边形索引模式（0,1,2,2,1,3）
- 通过 `setIndexedPatterned` 实现模式化索引

### 6. 局部坐标计算优化

只在 `fUsesLocalCoords` 为 `true` 时计算逆矩阵：
- 处理器分析确定是否需要局部坐标
- 避免不必要的矩阵逆运算

### 7. 颜色常量化

处理器分析可能将颜色常量化：
- 在 CPU 端计算最终颜色
- 减少片段着色器计算量

### 8. 距离场亮度调整表

使用预计算的亮度调整表（`DistanceFieldAdjustTable`）：
- 根据背景亮度和伽马校正查表
- 避免片段着色器中的复杂计算

### 9. LCD 子像素优化

LCD 渲染使用 RGB 三通道独立调整：
- 每个颜色通道独立的距离调整
- 充分利用 LCD 子像素结构

### 10. 动态纹理页管理

支持图集在准备期间增长：
- 自动检测新增的纹理页
- 动态更新几何处理器的采样器绑定
- 为已录制的绘制增加引用计数

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrMeshDrawOp.h` | 基类 | 网格绘制操作基类 |
| `src/text/gpu/SubRunContainer.h` | 协作 | 文本子运行容器 |
| `src/gpu/ganesh/text/GrAtlasManager.h` | 依赖 | 字形图集管理器 |
| `src/gpu/ganesh/effects/GrBitmapTextGeoProc.h` | 依赖 | 位图文本几何处理器 |
| `src/gpu/ganesh/effects/GrDistanceFieldGeoProc.h` | 依赖 | 距离场几何处理器 |
| `src/gpu/ganesh/text/GlyphData.h` | 依赖 | 字形后端数据 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 创建和管理文本操作 |
| `src/text/gpu/DistanceFieldAdjustTable.h` | 依赖 | 距离场亮度调整表 |
| `src/gpu/ganesh/GrProcessorSet.h` | 依赖 | 片段处理器集合管理 |
