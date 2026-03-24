# SkOverdrawCanvas

> 源文件: include/core/SkOverdrawCanvas.h, src/core/SkOverdrawCanvas.cpp

## 概述

`SkOverdrawCanvas` 是 Skia 提供的一个特殊画布类，用于检测和可视化过度绘制（overdraw）问题。过度绘制是指同一像素被多次绘制的现象，这会导致不必要的性能开销。`SkOverdrawCanvas` 不绘制实际内容，而是每次有绘制操作触及某个像素时，就递增该像素的 alpha 通道值，从而将过度绘制情况转换为可视化的热力图。

该类继承自 `SkNWayCanvas`，通过包装另一个画布来工作，将所有绘制命令转换为简单的矩形或路径绘制，并使用特殊的 `SkPaint` 配置来累积绘制次数。

## 架构位置

`SkOverdrawCanvas` 位于 Skia 的调试和性能分析工具层：

- **所属模块**: `include/core/` - 公共 API，`src/core/` - 实现
- **层级定位**: 继承自 `SkNWayCanvas`（多路画布），属于调试工具
- **使用场景**: 性能分析、UI 优化、渲染调试
- **输出目标**: 通常输出到普通画布，以 alpha 值表示绘制次数

## 主要类与结构体

### SkOverdrawCanvas 类

**继承关系**:
```
SkCanvas
  └─ SkNWayCanvas
       └─ SkCanvasVirtualEnforcer<SkNWayCanvas>
            └─ SkOverdrawCanvas
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPaint` | `SkPaint` | 预配置的画笔，用于累积绘制次数 |
| `fList[0]` | `SkCanvas*` | 底层包装的目标画布（继承自 `SkNWayCanvas`） |

### TextDevice 辅助类

**继承关系**:
```
SkNoPixelsDevice
  └─ TextDevice (同时实现 skcpu::BitmapDevicePainter)
```

**用途**: 处理文本绘制的特殊逻辑，将字形位置转换为矩形绘制。

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fOverdrawCanvas` | `SkCanvas*` | 指向 `SkOverdrawCanvas` 的指针 |
| `fPainter` | `skcpu::GlyphRunListPainter` | 字形绘制器 |

## 公共 API 函数

### 构造函数

```cpp
explicit SkOverdrawCanvas(SkCanvas* canvas)
```

**功能**: 创建包装指定画布的过度绘制分析画布。

**参数**:
- `canvas`: 目标画布，不转移所有权

**初始化逻辑**:
1. 设置内部画笔为累积模式：
   - 抗锯齿关闭（精确像素计数）
   - 混合模式为 `SkBlendMode::kPlus`（累加）
   - 颜色滤镜设置为递增 alpha 值

```cpp
static constexpr float kIncrementAlpha[] = {
    0.0f, 0.0f, 0.0f, 0.0f, 0.0f,
    0.0f, 0.0f, 0.0f, 0.0f, 0.0f,
    0.0f, 0.0f, 0.0f, 0.0f, 0.0f,
    0.0f, 0.0f, 0.0f, 0.0f, 1.0f/255,
};
fPaint.setColorFilter(SkColorFilters::Matrix(kIncrementAlpha));
```

每次绘制为 alpha 增加 `1/255`。

### 重写的绘制方法

以下方法将原始绘制转换为简单的几何绘制：

| 方法 | 转换策略 |
|------|---------|
| `onDrawPaint()` | 忽略清除操作，其他绘制整个画布 |
| `onDrawRect()` | 直接绘制矩形 |
| `onDrawOval()` | 直接绘制椭圆 |
| `onDrawRRect()` | 直接绘制圆角矩形 |
| `onDrawPath()` | 直接绘制路径（忽略原始画笔） |
| `onDrawImage2()` | 转换为图像位置的矩形 |
| `onDrawImageRect2()` | 转换为目标矩形 |
| `onDrawImageLattice2()` | 转换为多个矩形（九宫格拆分） |
| `onDrawTextBlob()` | 转换为字形边界框矩形 |
| `onDrawGlyphRunList()` | 使用 `TextDevice` 处理 |
| `onDrawVerticesObject()` | 直接绘制顶点对象 |
| `onDrawAtlas2()` | 直接绘制图集 |
| `onDrawShadowRec()` | 转换为阴影边界矩形 |
| `onDrawEdgeAAQuad()` | 绘制四边形或矩形 |
| `onDrawEdgeAAImageSet2()` | 绘制多个图像的边界 |

### 特殊处理方法

```cpp
void onDrawPaint(const SkPaint& paint)
```

**特殊逻辑**: 检测清除操作并忽略：

```cpp
if (0 == paint.getColor() && !paint.getColorFilter() && !paint.getShader()) {
    // 这是清除操作，忽略
} else {
    fList[0]->onDrawPaint(this->overdrawPaint(paint));
}
```

**理由**: 清除操作不应计入过度绘制。

```cpp
void onDrawGlyphRunList(const sktext::GlyphRunList& glyphRunList, const SkPaint& paint)
```

**特殊逻辑**: 使用 `TextDevice` 将字形转换为矩形：

```cpp
void TextDevice::paintMasks(SkZip<const SkGlyph*, SkPoint> accepted, const SkPaint& paint) const {
    for (auto [glyph, pos] : accepted) {
        SkMask mask = glyph->mask(pos);
        fOverdrawCanvas->save();
        fOverdrawCanvas->resetMatrix();  // 重置矩阵避免双重应用
        fOverdrawCanvas->drawRect(SkRect::Make(mask.fBounds), SkPaint());
        fOverdrawCanvas->restore();
    }
}
```

**注意**: 矩阵需要重置，因为字形位置已经包含了变换。

## 内部实现细节

### 1. 累积机制

使用颜色矩阵滤镜实现 alpha 累积：

```cpp
// 5x4 颜色矩阵（RGBA + offset）
// 只有最后一个元素（alpha offset）为 1/255
static constexpr float kIncrementAlpha[] = {
    0, 0, 0, 0, 0,   // R' = 0
    0, 0, 0, 0, 0,   // G' = 0
    0, 0, 0, 0, 0,   // B' = 0
    0, 0, 0, 0, 1/255, // A' = 1/255
};
```

配合 `SkBlendMode::kPlus` 混合模式，每次绘制使 alpha 增加固定值。

### 2. 画笔转换

```cpp
inline SkPaint SkOverdrawCanvas::overdrawPaint(const SkPaint& paint) {
    SkPaint newPaint = fPaint;
    newPaint.setStyle(paint.getStyle());           // 保留样式（填充/描边）
    newPaint.setStrokeWidth(paint.getStrokeWidth()); // 保留描边宽度
    return newPaint;
}
```

**保留属性**: 样式、描边宽度
**丢弃属性**: 颜色、着色器、滤镜等

### 3. 图像绘制简化

所有图像绘制都转换为矩形：

```cpp
void SkOverdrawCanvas::onDrawImage2(const SkImage* image, SkScalar x, SkScalar y,
                                    const SkSamplingOptions&, const SkPaint*) {
    fList[0]->onDrawRect(SkRect::MakeXYWH(x, y, image->width(), image->height()), fPaint);
}
```

**理由**: 过度绘制检测只关心覆盖区域，不关心实际内容。

### 4. 九宫格图像处理

```cpp
void SkOverdrawCanvas::onDrawImageLattice2(...) {
    // ...
    if (SkLatticeIter::Valid(...)) {
        SkLatticeIter iter(latticePlusBounds, dst);
        SkRect ignored, iterDst;
        while (iter.next(&ignored, &iterDst)) {
            fList[0]->onDrawRect(iterDst, fPaint);  // 逐个绘制子矩形
        }
    } else {
        fList[0]->onDrawRect(dst, fPaint);  // 无效时绘制整个目标
    }
}
```

将九宫格拆分为多个独立矩形，精确计算过度绘制。

### 5. 阴影处理

```cpp
void SkOverdrawCanvas::onDrawShadowRec(const SkPath& path, const SkDrawShadowRec& rec) {
    SkRect bounds;
    SkDrawShadowMetrics::GetLocalBounds(path, rec, this->getTotalMatrix(), &bounds);
    fList[0]->onDrawRect(bounds, fPaint);
}
```

使用阴影的边界矩形而非精确形状，快速估算。

### 6. 边缘抗锯齿图像集

```cpp
void SkOverdrawCanvas::onDrawEdgeAAImageSet2(...) {
    int clipIndex = 0;
    for (int i = 0; i < count; ++i) {
        if (set[i].fMatrixIndex >= 0) {
            fList[0]->save();
            fList[0]->concat(preViewMatrices[set[i].fMatrixIndex]);
        }
        if (set[i].fHasClip) {
            fList[0]->onDrawPath(SkPath::Polygon({dstClips + clipIndex, 4}, true), fPaint);
            clipIndex += 4;
        } else {
            fList[0]->onDrawRect(set[i].fDstRect, fPaint);
        }
        if (set[i].fMatrixIndex >= 0) {
            fList[0]->restore();
        }
    }
}
```

处理批量图像绘制，支持裁剪和矩阵变换。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkNWayCanvas.h` | 基类，提供多路画布功能 |
| `SkBlendMode.h` | 使用 `kPlus` 混合模式 |
| `SkColorFilter.h` | 颜色矩阵滤镜实现累积 |
| `SkPaint.h` | 配置绘制属性 |
| `SkDevice.h` | 设备层接口 |
| `SkGlyphRunPainter.h` | 字形绘制 |
| `SkLatticeIter.h` | 九宫格迭代器 |
| `SkDrawShadowInfo.h` | 阴影计算 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| 调试工具 | 性能分析工具使用 |
| UI 框架 | 检测界面过度绘制 |
| 测试框架 | 验证渲染优化效果 |

## 设计模式与设计决策

### 1. 装饰器模式

`SkOverdrawCanvas` 包装现有画布，拦截绘制命令并转换为过度绘制检测逻辑。

**优势**:
- 不修改原有绘图代码
- 可插拔的分析工具
- 支持与任何画布配合使用

### 2. 策略模式

不同绘制方法使用不同的转换策略：
- 几何图形 → 直接绘制
- 图像 → 转换为矩形
- 文本 → 转换为字形边界框

### 3. 模板方法模式

继承自 `SkCanvasVirtualEnforcer<SkNWayCanvas>`，使用 CRTP 强制实现虚函数。

### 4. 委托模式

文本绘制委托给 `TextDevice`，字形绘制委托给 `GlyphRunListPainter`。

### 5. 简化抽象

**设计决策**: 所有复杂绘制（图像、文本、阴影）都简化为矩形或路径。

**理由**:
- 过度绘制检测只关心覆盖区域
- 简化提高性能
- 避免处理复杂的像素级混合

### 6. 精度权衡

**设计决策**: alpha 增量为 `1/255`。

**含义**:
- 最多可检测 255 层过度绘制
- 每层对应一个 alpha 值
- 超过 255 层会饱和（alpha = 1.0）

## 性能考量

### 1. 关闭抗锯齿

```cpp
fPaint.setAntiAlias(false);
```

**理由**:
- 抗锯齿会导致边缘像素部分累积
- 精确像素计数需要硬边缘
- 提高绘制速度

### 2. 几何简化

将复杂绘制转换为简单矩形：
- 图像 → 矩形
- 文本 → 字形边界框
- 阴影 → 边界矩形

**优势**:
- 避免像素级渲染
- 减少 GPU 负载
- 快速估算覆盖区域

### 3. 避免不必要的计算

忽略清除操作：

```cpp
if (0 == paint.getColor() && !paint.getColorFilter() && !paint.getShader()) {
    // 忽略
}
```

### 4. 批量处理

图像集使用循环批量处理，避免递归调用开销。

### 5. 矩阵管理

文本绘制时重置矩阵避免双重应用：

```cpp
fOverdrawCanvas->save();
fOverdrawCanvas->resetMatrix();
// ... 绘制 ...
fOverdrawCanvas->restore();
```

**注意**: 这是注释中提到的 bug 修复（skbug.com/40044818）。

### 6. 内存开销

`SkOverdrawCanvas` 只增加一个 `SkPaint` 成员，额外开销约 80 字节。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/utils/SkNWayCanvas.h` | 基类，多路画布实现 |
| `include/core/SkCanvas.h` | 画布基类 |
| `include/core/SkPaint.h` | 画笔配置 |
| `include/core/SkColorFilter.h` | 颜色滤镜（矩阵滤镜） |
| `include/core/SkBlendMode.h` | 混合模式定义 |
| `src/core/SkDevice.h` | 设备层接口 |
| `src/core/SkGlyphRunPainter.h` | 字形绘制器 |
| `src/core/SkLatticeIter.h` | 九宫格迭代器 |
| `src/core/SkDrawShadowInfo.h` | 阴影计算辅助 |
| `include/core/SkImage.h` | 图像对象 |
| `include/core/SkTextBlob.h` | 文本对象 |
| `include/core/SkPath.h` | 路径对象 |
