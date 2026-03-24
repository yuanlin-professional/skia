# SkTiledImageUtils

> 源文件：src/image/SkTiledImageUtils.cpp

## 概述

`SkTiledImageUtils.cpp` 实现了平铺图像绘制的工具函数。当绘制大型图像时，GPU 后端可能将其分割为多个瓦片（Tiles）以避免纹理尺寸限制。该文件提供了绘制接口和缓存键生成函数。

## 主要函数

### DrawImageRect

```cpp
void DrawImageRect(SkCanvas* canvas,
                   const SkImage* image,
                   const SkRect& src,
                   const SkRect& dst,
                   const SkSamplingOptions& sampling,
                   const SkPaint* paint,
                   SkCanvas::SrcRectConstraint constraint) {
    if (!image || !canvas) return;

    SkPaint p;
    if (paint) {
        p = *paint;
    }

    // 尝试平铺绘制
    if (!SkCanvasPriv::TopDevice(canvas)->drawAsTiledImageRect(
            canvas, image, &src, dst, sampling, p, constraint)) {
        // 回退到标准绘制
        canvas->drawImageRect(image, src, dst, sampling, paint, constraint);
    }
}
```

### GetImageKeyValues

```cpp
void GetImageKeyValues(const SkImage* image, uint32_t keyValues[kNumImageKeyValues]) {
    if (!image || !keyValues) {
        if (keyValues) {
            memset(keyValues, 0, kNumImageKeyValues * sizeof(uint32_t));
        }
        return;
    }

    const SkImage_Base* imageBase = as_IB(image);

    // 情况 1：栅格图像
    if (const SkBitmap* bm = imageBase->onPeekBitmap()) {
        keyValues[0] = bm->pixelRef()->getGenerationID();
        SkIRect subset = image->bounds();
        subset.offset(bm->pixelRefOrigin());

        keyValues[1] = 0;  // 与 Picture ID 区分
        keyValues[2] = subset.fLeft;
        keyValues[3] = subset.fTop;
        keyValues[4] = subset.fRight;
        keyValues[5] = subset.fBottom;
        return;
    }

    // 情况 2：Picture 图像
    if (imageBase->type() == SkImage_Base::Type::kLazyPicture) {
        const SkImage_Picture* pictureImage = static_cast<const SkImage_Picture*>(imageBase);
        if (pictureImage->getImageKeyValues(keyValues)) {
            return;
        }
    }

    // 情况 3：其他类型
    keyValues[0] = image->uniqueID();
    memset(&keyValues[1], 0, (kNumImageKeyValues-1) * sizeof(uint32_t));
}
```

## 缓存键结构

键值数组包含 6 个 `uint32_t`（`kNumImageKeyValues = 6`）：

**栅格图像**：
- `[0]`：PixelRef 生成 ID
- `[1]`：0（区分标记）
- `[2-5]`：子集边界（left, top, right, bottom）

**Picture 图像**：
- `[0]`：标志位（位深度、像素几何、表面属性）
- `[1]`：Picture 唯一 ID（非 0）
- `[2-3]`：宽度、高度
- `[4-5]`：平移变换（X, Y）

**其他图像**：
- `[0]`：图像唯一 ID
- `[1-5]`：0

## 使用场景

### 平铺绘制

大图像（如 8K 分辨率）可能超过 GPU 纹理限制（如 4096×4096），需要分割为多个瓦片。

### 缓存优化

通过缓存键快速查找已栅格化的瓦片，避免重复工作。

## 设计决策

### 决策 1：设备决定是否平铺

```cpp
if (!device->drawAsTiledImageRect(...)) {
    canvas->drawImageRect(...);  // 回退
}
```

- **原因**：只有 GPU 设备需要平铺
- **策略**：CPU 设备直接绘制

### 决策 2：键值数组固定大小

`kNumImageKeyValues = 6`

- **权衡**：足够表示常见图像类型，同时保持缓存键紧凑

### 决策 3：Picture 图像使用槽 [1] 区分

```cpp
keyValues[1] = pictureID;  // Picture
// vs
keyValues[1] = 0;  // 栅格图像
```

- **原因**：避免 Picture ID 与 PixelRef ID 冲突

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkTiledImageUtils.h` | 头文件 | 公共 API 声明 |
| `src/image/SkImage_Picture.h` | Picture 图像 | Picture 图像实现 |
| `src/core/SkDevice.h` | 设备 | 平铺绘制实现 |
| `include/core/SkCanvas.h` | Canvas | 绘制接口 |
