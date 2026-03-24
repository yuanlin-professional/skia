# SkRescaleAndReadPixels

> 源文件：src/image/SkRescaleAndReadPixels.h, src/image/SkRescaleAndReadPixels.cpp

## 概述

`SkRescaleAndReadPixels` 是 Skia 图像系统中用于高质量缩放和像素读取的同步实现函数。该函数为 `SkImage::asyncRescaleAndReadPixels()` 和 `SkSurface::asyncRescaleAndReadPixels()` 提供通用的后端实现。它能够在读取像素之前执行高质量的图像缩放操作，支持多种缩放模式（最近邻、线性、三次）和伽马校正，通过多步渐进式缩放算法确保输出质量。

该函数的核心设计思想是将大的缩放操作分解为多个小步骤，每步缩放不超过 2 倍（对数步进），从而避免直接大比例缩放可能导致的质量问题。

## 架构位置

`SkRescaleAndReadPixels` 在 Skia 图像处理流程中的位置：

- **功能层次**：位于图像和表面的辅助工具层
- **调用关系**：被 `SkImage` 和 `SkSurface` 的异步读取接口调用
- **依赖层**：依赖 `SkSurface`、`SkCanvas`、`SkPaint` 等核心绘图组件
- **应用场景**：缩略图生成、图像缩放、跨颜色空间转换

该函数不是类成员，而是独立的工具函数，提供通用的缩放和读取逻辑，可被多个图像类型复用。

## 主要类与结构体

### SkRescaleAndReadPixels 函数

```cpp
void SkRescaleAndReadPixels(SkBitmap src,
                            const SkImageInfo& resultInfo,
                            const SkIRect& srcRect,
                            SkImage::RescaleGamma,
                            SkImage::RescaleMode,
                            SkImage::ReadPixelsCallback,
                            SkImage::ReadPixelsContext)
```

这是唯一的公共函数，没有类结构。

**参数**：
- `src`：源位图
- `resultInfo`：目标图像信息（尺寸、颜色类型、颜色空间）
- `srcRect`：源矩形区域
- `rescaleGamma`：伽马处理模式（线性或保持原样）
- `rescaleMode`：缩放模式（最近邻/重复线性/重复三次）
- `callback`：完成时的回调函数
- `context`：回调上下文指针

### Result 类（内部类）

实现 `SkImage::AsyncReadResult` 接口的本地类，用于封装读取结果：

```cpp
class Result : public SkImage::AsyncReadResult {
    std::unique_ptr<const char[]> fData;
    size_t fRowBytes;
public:
    int count() const override { return 1; }
    const void* data(int i) const override { return fData.get(); }
    size_t rowBytes(int i) const override { return fRowBytes; }
};
```

虽然接口支持多平面数据，但此实现始终返回单平面结果。

## 公共 API 函数

### SkRescaleAndReadPixels

```cpp
void SkRescaleAndReadPixels(SkBitmap src,
                            const SkImageInfo& resultInfo,
                            const SkIRect& srcRect,
                            SkImage::RescaleGamma rescaleGamma,
                            SkImage::RescaleMode rescaleMode,
                            SkImage::ReadPixelsCallback callback,
                            SkImage::ReadPixelsContext context)
```

执行缩放和像素读取操作，结果通过回调函数返回。

**主要流程**：
1. 计算缩放步数（基于对数）
2. 处理伽马校正（如果需要）
3. 渐进式多步缩放
4. 读取最终像素
5. 调用回调函数返回结果或错误

**缩放模式**：
- `kNearest`：最近邻插值
- `kRepeatedLinear`：重复线性插值
- `kRepeatedCubic`：重复三次插值

**伽马模式**：
- `kLinear`：在线性颜色空间中缩放
- 默认：在源颜色空间中缩放

## 内部实现细节

### 缩放步数计算

使用对数方法计算所需的缩放步数：

```cpp
float sx = (float)resultInfo.width() / srcW;
float sy = (float)resultInfo.height() / srcH;

if (rescaleMode != SkImage::RescaleMode::kNearest) {
    stepsX = static_cast<int>((sx > 1.f) ? std::ceil(std::log2f(sx))
                                         : std::floor(std::log2f(sx)));
    stepsY = static_cast<int>((sy > 1.f) ? std::ceil(std::log2f(sy))
                                         : std::floor(std::log2f(sy)));
} else {
    stepsX = sx != 1.f;  // 最近邻模式只需一步
    stepsY = sy != 1.f;
}
```

**算法逻辑**：
- **上采样**（`sx > 1`）：向上取整，每步最多放大 2 倍
- **下采样**（`sx < 1`）：向下取整，每步最多缩小 2 倍
- **最近邻**：直接一步到位

例如，4 倍放大需要 2 步（2×2），8 倍缩小需要 3 步（0.5×0.5×0.5）。

### 伽马校正处理

在线性颜色空间中缩放可以提高质量：

```cpp
if (rescaleGamma == SkSurface::RescaleGamma::kLinear && bmp.info().colorSpace() &&
    !bmp.info().colorSpace()->gammaIsLinear()) {
    auto cs = bmp.info().colorSpace()->makeLinearGamma();
    // 提升到 F16 以保持精度
    auto ii = SkImageInfo::Make(srcW, srcH, kRGBA_F16_SkColorType, bmp.info().alphaType(),
                                std::move(cs));
    auto linearSurf = SkSurfaces::Raster(ii);
    linearSurf->getCanvas()->drawImage(bmp.asImage().get(), -srcX, -srcY, sampling, &paint);
    tempSurf = std::move(linearSurf);
    srcImage = tempSurf->makeImageSnapshot();
    // ...
}
```

**步骤**：
1. 创建线性伽马颜色空间
2. 提升到 `RGBA_F16` 保持精度
3. 绘制图像进行颜色空间转换
4. 后续缩放在线性空间中进行

### 采样选项映射

将缩放模式转换为采样选项：

```cpp
auto rescaling_to_sampling = [](SkImage::RescaleMode rescaleMode) {
    SkSamplingOptions sampling;
    if (rescaleMode == SkImage::RescaleMode::kRepeatedLinear) {
        sampling = SkSamplingOptions(SkFilterMode::kLinear);
    } else if (rescaleMode == SkImage::RescaleMode::kRepeatedCubic) {
        sampling = SkSamplingOptions({1.0f/3, 1.0f/3});  // Mitchell-Netravali B=C=1/3
    }
    return sampling;
};
```

三次插值使用 Mitchell-Netravali 滤波器参数 `B=C=1/3`，这是常用的高质量插值设置。

### 渐进式缩放循环

核心的多步缩放实现：

```cpp
while (stepsX || stepsY) {
    int nextW = resultInfo.width();
    int nextH = resultInfo.height();

    // 计算下一步的尺寸
    if (stepsX < 0) {
        nextW = resultInfo.width() << (-stepsX - 1);  // 下采样
        stepsX++;
    } else if (stepsX != 0) {
        if (stepsX > 1) {
            nextW = srcW * 2;  // 上采样
        }
        --stepsX;
    }
    // 对 Y 方向做相同处理

    auto ii = srcImage->imageInfo().makeWH(nextW, nextH);
    if (!stepsX && !stepsY) {
        ii = resultInfo;  // 最后一步使用目标格式
    }

    auto next = SkSurfaces::Raster(ii);
    next->getCanvas()->drawImageRect(
        srcImage.get(), SkRect::Make(SkIRect::MakeXYWH(srcX, srcY, srcW, srcH)),
        SkRect::MakeIWH(nextW, nextH), sampling, &paint, constraint);

    tempSurf = std::move(next);
    srcImage = tempSurf->makeImageSnapshot();
    // 更新源尺寸和位置
    srcX = srcY = 0;
    srcW = nextW;
    srcH = nextH;
}
```

**算法特点**：
- 每次迭代处理一个缩放步骤
- 下采样从后往前计算（先缩到中间尺寸）
- 上采样逐步放大 2 倍
- 最后一步直接转换到目标格式

### 像素读取和结果返回

```cpp
size_t rowBytes = resultInfo.minRowBytes();
std::unique_ptr<char[]> data(new char[resultInfo.height() * rowBytes]);
SkPixmap pm(resultInfo, data.get(), rowBytes);

if (srcImage->readPixels(nullptr, pm, srcX, srcY)) {
    callback(context, std::make_unique<Result>(std::move(data), rowBytes));
} else {
    callback(context, nullptr);
}
```

成功时创建 `Result` 对象包装数据，失败时传递 `nullptr`。

### 绘制优化

使用 `SkBlendMode::kSrc` 避免不必要的混合：

```cpp
SkPaint paint;
paint.setBlendMode(SkBlendMode::kSrc);
```

使用 `SkCanvas::SrcRectConstraint` 控制边界处理：
- 初始绘制使用 `kStrict_SrcRectConstraint` 确保严格裁剪
- 后续步骤使用 `kFast_SrcRectConstraint` 提高性能

### 下采样限制

```cpp
if (stepsX < 0 || stepsY < 0) {
    // 不触发 MIP 生成，当前无法为下采样绘制触发三次插值
    if (rescaleMode != SkImage::RescaleMode::kNearest) {
        rescaleMode = SkImage::RescaleMode::kRepeatedLinear;
    }
}
```

下采样时降级到线性插值，因为当前实现不支持三次下采样。

## 依赖关系

### 核心依赖

| 依赖项 | 用途 |
|--------|------|
| `SkBitmap` | 源位图数据结构 |
| `SkSurface` | 创建中间渲染表面 |
| `SkCanvas` | 执行图像绘制和缩放 |
| `SkPaint` | 控制绘制属性 |
| `SkSamplingOptions` | 配置插值算法 |

### 次要依赖

| 依赖项 | 用途 |
|--------|------|
| `SkImageInfo` | 图像格式描述 |
| `SkColorSpace` | 颜色空间转换 |
| `SkPixmap` | 像素数据访问 |
| `SkImage` | 图像接口和枚举 |

### 反向依赖

| 依赖方 | 调用方式 |
|--------|----------|
| `SkImage_Base` | 实现 `asyncRescaleAndReadPixels()` |
| `SkSurface_Base` | 实现 `asyncRescaleAndReadPixels()` |

## 设计模式与设计决策

### 回调模式（Callback Pattern）

使用回调函数返回结果，保持接口的异步兼容性：

```cpp
SkImage::ReadPixelsCallback callback,
SkImage::ReadPixelsContext context
```

虽然实现是同步的，但接口设计允许将来实现真正的异步版本。

### 渐进式优化策略

**决策 1：对数步进而非直接缩放**
- **原因**：大比例直接缩放质量差，尤其是下采样时容易产生锯齿
- **权衡**：增加了计算量，但显著提高了输出质量

**决策 2：最后一步融合格式转换**
```cpp
if (!stepsX && !stepsY) {
    ii = resultInfo;  // 在最后一步转换颜色类型
}
```
- **原因**：避免额外的格式转换步骤
- **权衡**：无明显缺点，纯粹的性能优化

**决策 3：伽马校正使用 F16 精度**
```cpp
auto ii = SkImageInfo::Make(srcW, srcH, kRGBA_F16_SkColorType, ...);
```
- **原因**：线性空间计算需要更高精度避免精度损失
- **权衡**：内存占用翻倍，但保证了质量

**决策 4：下采样降级到线性插值**
- **原因**：当前绘制管线不支持三次下采样
- **权衡**：略微降低质量，但保持实现简单

### 模板方法的变体

虽然不是经典的模板方法模式，但算法结构类似：
1. 预处理（伽马校正）
2. 迭代缩放（核心算法）
3. 后处理（像素读取）

每个阶段都有明确的职责分工。

### 同步实现异步接口

函数名包含 "async" 但实现是同步的，这是一种接口前瞻性设计：
- 当前版本同步执行
- API 设计为回调形式，便于将来实现真正的异步（如 GPU 加速）

## 性能考量

### 缩放质量与性能权衡

**对数步进的优势**：
- 避免直接大比例缩放的质量损失
- 每步缩放倍数不超过 2，保持良好的滤波效果

**性能开销**：
- 多步缩放意味着多次表面创建和绘制
- 例如 8 倍缩放需要 3 步，比直接缩放慢 3 倍

### 内存使用

**中间表面分配**：
```cpp
auto next = SkSurfaces::Raster(ii);
```
每步都创建新表面，但旧表面会立即释放（`std::move`）。

**最终数据分配**：
```cpp
std::unique_ptr<char[]> data(new char[resultInfo.height() * rowBytes]);
```
结果数据移交给 `Result` 对象，由调用方控制生命周期。

### 伽马校正开销

线性伽马处理需要：
1. 额外的颜色空间转换绘制
2. F16 格式的内存开销（每像素 8 字节）
3. 后续所有缩放步骤在 F16 上操作

适用于质量优先的场景，性能敏感场景可跳过。

### 采样模式性能

性能排序（从快到慢）：
1. **kNearest**：最快，质量最差
2. **kRepeatedLinear**：中等，质量较好
3. **kRepeatedCubic**：最慢，质量最佳

三次插值需要更多的纹理采样和计算。

### 优化建议

1. **小缩放比例**：接近 1:1 的缩放可以使用最近邻模式
2. **跳过伽马校正**：非显示用途（如数据分析）可以跳过
3. **预分配缓冲**：对于批量操作，可以复用分配的缓冲区（需修改 API）

### 瓶颈分析

主要时间消耗：
1. **像素绘制**：`drawImageRect()` 调用占主要时间
2. **表面创建**：每步的 `SkSurfaces::Raster()` 分配
3. **格式转换**：伽马校正和最终颜色类型转换

对于大图像，像素绘制是绝对瓶颈；对于小图像，表面分配开销相对更明显。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkImage.h` | API 定义 | 定义回调类型和枚举 |
| `include/core/SkSurface.h` | API 定义 | 定义缩放和读取接口 |
| `src/image/SkImage_Base.h` | 调用方 | 图像基类使用此函数 |
| `src/image/SkSurface_Base.h` | 调用方 | 表面基类使用此函数 |
| `include/core/SkCanvas.h` | 核心依赖 | 绘制和缩放操作 |
| `include/core/SkBitmap.h` | 数据结构 | 源位图表示 |
| `include/core/SkColorSpace.h` | 颜色管理 | 伽马校正和颜色空间转换 |
| `include/core/SkSamplingOptions.h` | 采样控制 | 插值算法配置 |
| `include/core/SkPixmap.h` | 像素访问 | 最终像素数据读取 |
