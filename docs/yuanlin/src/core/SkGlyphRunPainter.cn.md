# SkGlyphRunPainter

> 源文件
> - src/core/SkGlyphRunPainter.h
> - src/core/SkGlyphRunPainter.cpp

## 概述

`skcpu::GlyphRunListPainter` 是 Skia CPU 文本渲染管线的核心绘制器,负责将字形运行列表(glyph run list)绘制到位图设备上。它实现了多层回退策略,根据字形大小、变换矩阵和渲染质量要求,自动选择最优的渲染路径:路径绘制、直接遮罩绘制或缩放位图绘制。该类处理子像素定位、LCD 文本支持、透视变换下的字形渲染等复杂场景。

## 架构位置

`GlyphRunListPainter` 位于 Skia 文本渲染栈的中间层:

- **上游**: 接收来自 `sktext::GlyphRunList` 的字形运行数据
- **下游**: 调用 `BitmapDevicePainter` 进行实际位图操作
- **协作模块**:
  - `SkStrike`: 字形缓存查询
  - `SkStrikeSpec`: 字形缓存规格生成
  - `SkScalerContext`: 字形数据生成
- **应用场景**: CPU 位图设备的文本绘制(如 PDF、位图 Canvas)

## 主要类与结构体

### GlyphRunListPainter

**继承关系**: 无继承

| 关键成员变量 | 类型 | 说明 |
|-------------|------|------|
| fDeviceProps | const SkSurfaceProps | 实际设备的表面属性 |
| fBitmapFallbackProps | const SkSurfaceProps | 位图回退时的属性(禁用 LCD) |
| fColorType | const SkColorType | 设备颜色类型 |
| fScalerContextFlags | const SkScalerContextFlags | 缩放器上下文标志(gamma 校正等) |

## 公共 API 函数

```cpp
// 构造函数
GlyphRunListPainter(const SkSurfaceProps& props,
                   SkColorType colorType,
                   SkColorSpace* cs)

// 核心绘制方法
void drawForBitmapDevice(
    SkCanvas* canvas,
    const BitmapDevicePainter* bitmapDevice,
    const sktext::GlyphRunList& glyphRunList,
    const SkPaint& paint,
    const SkMatrix& drawMatrix)
```

## 内部实现细节

### 三级渲染回退策略

`drawForBitmapDevice()` 实现了智能的渲染路径选择:

#### 1. 路径绘制阶段

条件判断: `SkStrikeSpec::ShouldDrawAsPath(paint, font, matrix)`

适用场景:
- 大字号文本
- 存在透视变换
- 应用了路径效果或遮罩滤镜

实现细节:
```cpp
// 创建路径专用的 strike
auto [strikeSpec, strikeToSourceScale] =
    SkStrikeSpec::MakePath(runFont, paint, props, fScalerContextFlags);
```

两种路径绘制模式:
- **简单模式**: 直接变换和绘制路径(无 shader/效果)
- **精确 CTM 模式**: 需要完整变换矩阵时,先转换路径再绘制

可绘制对象处理:
- 复杂字形(如 OpenType SVG)返回 `SkDrawable`
- 使用 `saveLayer` 应用 paint 效果后绘制

#### 2. 直接遮罩绘制阶段

条件判断: `!matrix.hasPerspective()`(无透视变换)

核心函数: `prepare_for_direct_mask_drawing()`

实现步骤:
1. 计算带舍入的位置矩阵: `positionMatrixWithRounding = ctm + halfSampleFreq`
2. 将源空间位置映射到设备空间并舍入
3. 使用 `kDirectMaskCPU` 动作类型查询字形摘要
4. 接受的字形直接通过 `bitmapDevice->paintMasks()` 绘制

优点: 最高效的渲染路径,直接操作位图像素。

#### 3. 缩放位图绘制阶段

适用场景: 透视变换或字形需要缩放

实现流程:

**尺度计算**:
```cpp
// 计算四边形每条边的缩放因子
SkPoint corners[4];
positionMatrix.mapRectToQuad(corners, glyphRect);
// 取最大边长比例作为缩放因子
maxScale = max(每条边的缩放比)
```

**限制最大缩放**:
```cpp
if (maxScale * fontSize > 256) {
    maxScale = 256.0f / fontSize;
}
```

**渲染步骤**:
1. 创建缩放后的 strike: `SkStrikeSpec::MakeMask(..., SkMatrix::Scale(maxScale, maxScale))`
2. 从缓存获取放大的字形位图
3. 使用逆缩放因子将位图绘制到正确位置:
```cpp
SkMatrix translate = SkMatrix::Translate(pos);
translate.preScale(1.0f/maxScale, 1.0f/maxScale);
bitmapDevice->drawBitmap(bm, translate, nullptr, SkFilterMode::kLinear, paint, nullptr);
```

### LCD 文本支持

LCD 文本(子像素抗锯齿)仅在特定条件下启用:

```cpp
auto& props = (kN32_SkColorType == fColorType && paint.isSrcOver())
              ? fDeviceProps
              : fBitmapFallbackProps;  // 禁用 LCD
```

限制条件:
- 设备必须是 N32 颜色类型(RGBA/BGRA)
- 混合模式必须是 `SrcOver`
- 否则降级为 A8 格式

### 子像素定位

使用 `SkGlyphPositionRoundingSpec` 处理子像素对齐:
- `halfAxisSampleFreq`: 舍入偏移量(全像素为 0.5,子像素为 0.125)
- `ignorePositionFieldMask`: 控制哪个轴启用子像素定位

位置计算:
```cpp
SkMatrix positionMatrixWithRounding = creationMatrix;
positionMatrixWithRounding.postTranslate(halfSampleFreq.x(), halfSampleFreq.y());
SkPoint mappedPos = positionMatrixWithRounding.mapPoint(pos);
// 舍入到子像素网格
SkPoint roundedPos{SkScalarFloorToScalar(mappedPos.x()),
                   SkScalarFloorToScalar(mappedPos.y())};
```

### Scaler Context 标志计算

```cpp
SkScalerContextFlags compute_scaler_context_flags(const SkColorSpace* cs) {
    if (cs && cs->gammaIsLinear()) {
        return SkScalerContextFlags::kBoostContrast;
    } else {
        return SkScalerContextFlags::kFakeGammaAndBoostContrast;
    }
}
```

- **线性颜色空间**: 禁用 gamma 校正,仅启用对比度增强
- **非线性颜色空间**: 启用假 gamma 校正和对比度增强

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| sktext::GlyphRunList | 输入的字形运行数据 |
| BitmapDevicePainter | 位图设备抽象接口 |
| SkStrike | 字形缓存查询 |
| SkStrikeSpec | 生成字形缓存规格 |
| SkGlyph | 字形数据结构 |
| SkGlyphDigest | 字形摘要和动作决策 |
| SkScalerContext | 字形数据生成 |
| SkPath | 路径绘制 |
| SkDrawable | 复杂字形绘制 |
| SkMask | 遮罩数据结构 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| SkBitmapDevice | 使用 GlyphRunListPainter 进行文本绘制 |
| SkDraw | CPU 绘制管线集成 |
| PDF/XPS 后端 | 位图设备文本渲染 |

## 设计模式与设计决策

### 策略模式

三级回退策略实现了渲染路径的自动选择:
1. **路径策略**: 最高质量,适合大字号和特殊效果
2. **直接遮罩策略**: 最高性能,适合常规文本
3. **缩放位图策略**: 处理透视变换等复杂场景

### 工厂模式

使用 `SkStrikeSpec` 工厂创建不同类型的 strike:
- `SkStrikeSpec::MakePath()`: 路径渲染 strike
- `SkStrikeSpec::MakeMask()`: 遮罩渲染 strike

### 责任链模式

字形处理流程中,每个阶段处理自己能接受的字形,拒绝的字形传递到下一阶段:
```cpp
auto [accepted, rejected] = prepare_for_path_drawing(...);
source = rejected;  // 传递到下一阶段
// 继续处理 rejected...
```

### 设计决策: 最大缩放限制

为什么限制 `maxScale * fontSize <= 256`:
- 防止创建过大的字形位图
- 平衡内存使用和渲染质量
- 超出此限制时降级到路径渲染

### 设计决策: LCD 文本限制

为什么 LCD 仅在 N32 + SrcOver 下启用:
- LCD 抗锯齿需要 RGB 子像素信息
- 非 SrcOver 混合模式会破坏子像素精度
- 确保文本渲染正确性优先于性能

## 性能考量

### 缓存友好的批量处理

使用 `STArray<64, ...>` 预分配缓冲区:
```cpp
STArray<64, const SkGlyph*> acceptedPackedGlyphIDs;
STArray<64, SkPoint> acceptedPositions;
```

- 64 个字形的栈上预分配避免堆内存分配
- 适应大多数文本绘制场景

### Strike 锁定优化

在字形查询期间短暂锁定 strike:
```cpp
strike->lock();
for (auto [glyphID, pos] : source) {
    // 查询字形摘要...
}
strike->unlock();
```

减少锁竞争,提高多线程性能。

### 尺度计算优化

仅对拒绝的字形计算缩放因子:
- 路径和直接遮罩阶段已处理大部分字形
- 缩放位图作为最后回退,减少计算开销

### 线性插值滤镜

缩放位图绘制使用 `SkFilterMode::kLinear`:
- 提供合理的质量
- 比双三次插值快
- 平衡性能和视觉质量

### 无限位置跳过

```cpp
if (!SkIsFinite(pos.x(), pos.y())) {
    continue;
}
```

过滤无效位置,防止崩溃和无限循环。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| src/text/GlyphRun.h | 输入 | 字形运行数据结构 |
| src/core/SkDraw.h | 集成 | CPU 绘制管线 |
| src/core/SkBitmapDevice.cpp | 使用者 | 位图设备 |
| src/core/SkStrike.h | 依赖 | 字形缓存 |
| src/core/SkStrikeSpec.h | 依赖 | Strike 规格生成 |
| src/core/SkGlyph.h | 依赖 | 字形数据结构 |
| src/core/SkScalerContext.h | 依赖 | 字形生成器 |
| include/core/SkCanvas.h | 接口 | 画布 API |
| include/core/SkPaint.h | 接口 | 绘制属性 |
