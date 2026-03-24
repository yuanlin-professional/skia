# SkCanvasPriv

> 源文件: src/core/SkCanvasPriv.h, src/core/SkCanvasPriv.cpp

## 概述

`SkCanvasPriv` 是 Skia 内部使用的工具类,提供了对 `SkCanvas` 私有功能的访问接口。它主要包含三个核心功能模块:画布私有操作的静态辅助函数、Lattice(网格)序列化/反序列化支持、以及 `AutoLayerForImageFilter` 自动图层管理类,用于处理图像滤镜和蒙版滤镜的图层化渲染。

该类作为 Skia 内部 API,不对外公开,仅供 Skia 内部模块使用,提供了强大的画布操作能力和滤镜图层自动化管理。

## 架构位置

`SkCanvasPriv` 位于 Skia 核心层的私有接口区域:
- 被 `SkCanvas` 内部实现使用
- 为 Skia 内部模块提供画布高级功能访问
- 与滤镜系统(`SkImageFilter`, `SkMaskFilter`)紧密集成
- 支持序列化系统(通过 `SkReadBuffer`/`SkWriteBuffer`)
- 提供 Android 框架特定功能

## 主要类与结构体

### SkAutoCanvasMatrixPaint

RAII 风格的辅助类,自动管理画布的矩阵和绘制状态。

**继承关系:**
```
SkNoncopyable (通过 [[nodiscard]] 标记)
  └── SkAutoCanvasMatrixPaint
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fCanvas | SkCanvas* | 关联的画布指针 |
| fSaveCount | int | 保存的画布状态计数 |

### SkCanvasPriv

静态工具类,提供画布私有操作访问。

**主要功能分类:**
- Lattice 序列化/反序列化
- SaveBehind/DrawBehind 操作
- 设备访问
- 图像集计数计算
- SaveLayerRec 扩展功能
- 滤镜到颜色滤镜的转换

### AutoLayerForImageFilter

自动管理图像滤镜和蒙版滤镜所需图层的 RAII 类。

**继承关系:**
- 无继承关系(独立类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fPaint | SkPaint | 修改后用于绘制的画笔 |
| fCanvas | SkCanvas* | 关联的画布 |
| fTempLayersForFilters | int | 创建的临时图层数量 |
| fSaveCount | int | 调试用保存计数(仅 Debug 模式) |

## 公共 API 函数

### Lattice 序列化支持

```cpp
static bool ReadLattice(SkReadBuffer&, SkCanvas::Lattice*)
static void WriteLattice(SkWriteBuffer&, const SkCanvas::Lattice&)
static size_t WriteLattice(void* storage, const SkCanvas::Lattice&)
```
处理九宫格(Lattice)数据的序列化和反序列化。

### 特殊绘制操作

```cpp
static int SaveBehind(SkCanvas* canvas, const SkRect* subset)
static void DrawBehind(SkCanvas* canvas, const SkPaint& paint)
static void ResetClip(SkCanvas* canvas)
```
- `SaveBehind`: 保存指定区域后面的内容
- `DrawBehind`: 在保存的内容后面绘制
- `ResetClip`: 重置裁剪区域(非 Android 框架构建时用于测试)

### 设备访问

```cpp
static SkDevice* TopDevice(const SkCanvas* canvas)
```
获取画布顶层设备,用于底层操作。

### 图像集辅助

```cpp
static void GetDstClipAndMatrixCounts(const SkCanvas::ImageSetEntry set[], int count,
                                      int* totalDstClipCount, int* totalMatrixCount)
```
计算图像集所需的裁剪和矩阵数组大小。

### SaveLayerRec 扩展

```cpp
static SkCanvas::SaveLayerRec ScaledBackdropLayer(...)
static SkScalar GetBackdropScaleFactor(const SkCanvas::SaveLayerRec& rec)
static void SetBackdropScaleFactor(SkCanvas::SaveLayerRec* rec, SkScalar scale)
```
创建和操作带有缩放背景的图层记录。

### 滤镜优化

```cpp
static bool ImageToColorFilter(SkPaint* paint)
```
尝试将图像滤镜转换为等价的颜色滤镜,避免额外图层。

## 内部实现细节

### AutoLayerForImageFilter 工作原理

构造函数根据画笔内容创建 0-2 个图层:

1. **图像滤镜图层** (如果存在且无法转为颜色滤镜):
   - 窃取 blender 和 image filter
   - 原始画笔使用 `kSrcOver` 混合模式绘制到图层
   - 恢复时应用滤镜和混合

2. **蒙版滤镜图层** (如果存在且不跳过):
   - 窃取所有着色效果(shader, color filter)
   - 原始画笔使用白色纯色绘制(将覆盖率编码到 alpha 通道)
   - 保留几何效果(path effect, stroke)
   - 恢复时将蒙版滤镜转为图像滤镜应用

**图层创建顺序**:
```
图像滤镜图层(外层) → 蒙版滤镜图层(内层) → 原始绘制
```

### 滤镜到颜色滤镜优化

`ImageToColorFilter` 实现关键优化:

```cpp
bool SkCanvasPriv::ImageToColorFilter(SkPaint* paint) {
    if (paint->getMaskFilter()) return false;  // 不能与蒙版滤镜共存

    SkColorFilter* imgCFPtr;
    if (!paint->getImageFilter()->asAColorFilter(&imgCFPtr)) return false;

    // 组合颜色滤镜
    sk_sp<SkColorFilter> imgCF(imgCFPtr);
    if (SkColorFilter* paintCF = paint->getColorFilter()) {
        imgCF = imgCF->makeComposed(sk_ref_sp(paintCF));
    }

    paint->setColorFilter(std::move(imgCF));
    paint->setImageFilter(nullptr);
    return true;
}
```

条件限制:
- 图像滤镜必须可表达为颜色滤镜
- 不能同时有蒙版滤镜(避免顺序问题)
- 与透明背景的 src-over 混合是无操作

### Lattice 内存布局

```cpp
size_t WriteLattice(void* buffer, const SkCanvas::Lattice& lattice) {
    int flagCount = lattice.fRectTypes ? (lattice.fXCount + 1) * (lattice.fYCount + 1) : 0;

    const size_t size = (1 + lattice.fXCount + 1 + lattice.fYCount + 1) * sizeof(int32_t) +
                        SkAlign4(flagCount * sizeof(RectType)) +
                        SkAlign4(flagCount * sizeof(SkColor)) +
                        sizeof(SkIRect);
    // ...
}
```

内存结构:
1. fXCount (int32_t)
2. fXDivs 数组 (int32_t[fXCount])
3. fYCount (int32_t)
4. fYDivs 数组 (int32_t[fYCount])
5. flagCount (int32_t)
6. fRectTypes 数组 (对齐到 4 字节)
7. fColors 数组
8. fBounds (SkIRect)

### 蒙版滤镜图层细节

```cpp
void AutoLayerForImageFilter::addMaskFilterLayer(const SkRect* drawBounds) {
    auto [maskFilterAsImageFilter, appliesShading] =
        as_MFB(fPaint.getMaskFilter())->asImageFilter(fCanvas->getTotalMatrix(), fPaint);

    if (!maskFilterAsImageFilter) return;  // 传统蒙版滤镜,由设备处理

    SkPaint restorePaint;
    if (!appliesShading) {
        // 普通蒙版滤镜:恢复画笔包含原始着色
        restorePaint.setColor4f(fPaint.getColor4f());
        restorePaint.setShader(fPaint.refShader());
        restorePaint.setColorFilter(fPaint.refColorFilter());
        restorePaint.setDither(fPaint.isDither());
    }
    restorePaint.setBlender(fPaint.refBlender());
    restorePaint.setImageFilter(maskFilterAsImageFilter);

    // 工作画笔只保留覆盖率信息
    fPaint.setColor4f(SkColors::kWhite);
    fPaint.setShader(nullptr);
    // ...
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| include/core/SkCanvas.h | 画布接口 |
| include/core/SkImageFilter.h | 图像滤镜 |
| include/core/SkMaskFilter.h | 蒙版滤镜 |
| src/core/SkMaskFilterBase.h | 蒙版滤镜内部接口 |
| src/core/SkReadBuffer.h | 反序列化 |
| src/core/SkWriteBuffer.h | 序列化 |
| include/core/SkColorFilter.h | 颜色滤镜 |
| include/core/SkShader.h | 着色器 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| SkCanvas 实现 | 使用 AutoLayerForImageFilter 和辅助函数 |
| SkPicture | 使用 Lattice 序列化 |
| 测试代码 | 使用 ResetClip 和 TopDevice |
| Android 框架 | 使用 SaveBehind/DrawBehind |

## 设计模式与设计决策

### RAII 模式

`SkAutoCanvasMatrixPaint` 和 `AutoLayerForImageFilter` 使用 RAII:
- 构造时设置状态/创建图层
- 析构时自动恢复/删除图层
- 使用 `[[nodiscard]]` 防止临时对象
- 支持移动语义,禁止拷贝

### 策略模式

滤镜处理使用不同策略:
1. 优化策略:转换为颜色滤镜,无需图层
2. 图层策略:创建临时图层应用滤镜
3. 设备策略:传统蒙版滤镜由设备直接处理

### 访问者模式变体

```cpp
static void DrawBehind(SkCanvas* canvas, const SkPaint& paint) {
    canvas->drawClippedToSaveBehind(paint);
}
```

静态函数作为友元访问私有方法,避免破坏封装。

### 组合滤镜模式

```cpp
imgCF = imgCF->makeComposed(sk_ref_sp(paintCF));
```

使用滤镜组合而非多次绘制:
- 减少图层数量
- 提高性能
- 保持颜色精度

## 性能考量

### 滤镜图层优化

避免不必要的图层:
- 检测可转换为颜色滤镜的图像滤镜
- 单次绘制代替多次图层绘制
- 减少内存分配和带宽使用

### 最小边界计算

```cpp
const SkRect* contentBounds = nullptr;
if (drawBounds && fPaint.canComputeFastBounds()) {
    contentBounds = &fPaint.computeFastBounds(*drawBounds, &storage);
}
```

计算最小可能的图层边界:
- 减少图层尺寸
- 降低内存占用
- 加速滤镜处理

### Lattice 对齐优化

```cpp
SkAlign4(flagCount * sizeof(SkCanvas::Lattice::RectType))
```

4 字节对齐访问:
- 利用硬件对齐访问优势
- 避免未对齐访问惩罚
- 简化指针算术

### 延迟蒙版滤镜转换

只在需要时将蒙版滤镜转换为图像滤镜:
- 传统蒙版滤镜可能有硬件加速
- 避免不必要的图层创建
- 支持向后兼容

### 图层复用

```cpp
fCanvas->fSaveCount += 1;
fCanvas->internalSaveLayer(...);
```

直接操作内部保存计数:
- 避免额外的 save/restore 开销
- 精确控制图层生命周期

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| include/core/SkCanvas.h | 主要接口 | 画布公共 API |
| src/core/SkCanvas.cpp | 实现 | 使用 SkCanvasPriv 的辅助功能 |
| include/core/SkImageFilter.h | 滤镜接口 | 图像滤镜 API |
| src/core/SkMaskFilterBase.h | 蒙版基类 | 蒙版滤镜内部接口 |
| src/core/SkDevice.h | 设备抽象 | 设备层操作 |
| include/core/SkPaint.h | 绘制属性 | 画笔配置 |
| src/core/SkReadBuffer.h | 序列化 | 数据读取 |
| src/core/SkWriteBuffer.h | 序列化 | 数据写入 |
