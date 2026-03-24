# SkSpecialImage

> 源文件
> - src/core/SkSpecialImage.h
> - src/core/SkSpecialImage.cpp

## 概述

`SkSpecialImage` 是 Skia 内部专用的受限图像抽象类,用于图像滤镜等内部操作。它是对 `SkImage` 的简化和限定,只能由光栅或 GPU 纹理支持,并且允许后备存储大于标称边界。该类的主要目的是在图像效果处理管道中提供一个统一、轻量的图像表示,同时支持子集视图和高效的着色器创建。

## 架构位置

`SkSpecialImage` 位于 Skia 核心渲染模块中,是图像效果处理系统的基础组件:

- **图像抽象层**: 在 `SkImage` 和具体实现之间提供中间抽象
- **效果系统**: 为图像滤镜(image filter)提供统一的图像表示
- **GPU/光栅统一接口**: 同时支持 Ganesh 和 Graphite 后端

## 主要类与结构体

### SkSpecialImage (抽象基类)

**继承关系**:
```
SkRefCnt
  └── SkSpecialImage
        ├── SkSpecialImage_Raster (内部实现)
        └── (GPU backed implementations)
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSubset` | `const SkIRect` | 相对于后备存储的子集矩形 |
| `fUniqueID` | `const uint32_t` | 图像唯一标识符 |
| `fColorInfo` | `const SkColorInfo` | 颜色空间和像素格式信息 |
| `fProps` | `const SkSurfaceProps` | 表面属性(像素几何等) |

### SkSpecialImage_Raster (具体实现)

**继承关系**: `SkSpecialImage` → `SkSpecialImage_Raster`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fBitmap` | `SkBitmap` | 底层位图数据 |

## 公共 API 函数

### 属性访问

```cpp
// 获取尺寸信息
int width() const;                          // 返回子集宽度
int height() const;                         // 返回子集高度
SkISize dimensions() const;                 // 返回尺寸
const SkIRect& subset() const;              // 返回子集矩形

// 获取后备存储信息
virtual SkISize backingStoreDimensions() const = 0;
virtual size_t getSize() const = 0;
bool isExactFit() const;                    // 子集是否与后备存储完全匹配
```

### 绘制与着色器

```cpp
// 绘制到画布
void draw(SkCanvas* canvas, SkScalar x, SkScalar y,
          const SkSamplingOptions& sampling,
          const SkPaint* paint, bool strict = true) const;

// 转换为图像
virtual sk_sp<SkImage> asImage() const = 0;

// 创建着色器
virtual sk_sp<SkShader> asShader(SkTileMode, const SkSamplingOptions&,
                                 const SkMatrix& lm, bool strict=true) const;
```

### 子集操作

```cpp
// 创建子集
sk_sp<SkSpecialImage> makeSubset(const SkIRect& subset) const;

// 扩展子集(用于滤镜边缘像素)
sk_sp<SkSpecialImage> makePixelOutset() const;
```

## 内部实现细节

### 坐标系统

`SkSpecialImage` 使用两套坐标系:
1. **内容坐标**: 相对于子集左上角(0, 0)
2. **后备存储坐标**: 相对于实际后备存储的绝对坐标

```cpp
// 子集创建时的坐标转换
sk_sp<SkSpecialImage> makeSubset(const SkIRect& subset) const {
    SkIRect absolute = subset.makeOffset(this->subset().topLeft());
    return this->onMakeBackingStoreSubset(absolute);
}
```

### 着色器创建策略

着色器创建根据 `strict` 参数有两种模式:

1. **严格模式** (strict=true): 使用 `SkImageShader::MakeSubset` 强制遵守子集边界
2. **快速模式** (strict=false): 假设相邻像素有效,允许硬件采样超出子集

```cpp
sk_sp<SkShader> asShader(..., bool strict) const {
    SkMatrix subsetOrigin = SkMatrix::Translate(-this->subset().topLeft());
    subsetOrigin.postConcat(lm);

    if (strict) {
        return SkImageShader::MakeSubset(this->asImage(), subset, ...);
    } else {
        return this->asImage()->makeShader(..., subsetOrigin);
    }
}
```

### 光栅实现优化

`SkSpecialImage_Raster` 通过 `SkBitmap::extractSubset` 避免不必要的数据复制:

```cpp
sk_sp<SkSpecialImage> onMakeBackingStoreSubset(const SkIRect& subset) const override {
    // 不需要提取子集,onGetROPixels 会处理
    return SkSpecialImages::MakeFromRaster(subset, fBitmap, this->props());
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkImage` | 图像接口和实现 |
| `SkBitmap` | 光栅位图表示 |
| `SkImageShader` | 着色器创建 |
| `SkCanvas` | 绘制目标 |
| `SkColorInfo` | 颜色空间管理 |
| `SkSurfaceProps` | 表面属性配置 |

### 被依赖的模块

| 模块 | 说明 |
|------|------|
| 图像滤镜系统 | `SkImageFilter` 使用 `SkSpecialImage` 传递中间结果 |
| GPU 后端 | Ganesh/Graphite 实现 GPU 版本的 `SkSpecialImage` |
| 着色效果 | `SkShader` 系统通过 `asShader()` 集成 |

## 设计模式与设计决策

### 1. 抽象工厂模式

通过命名空间函数提供多种创建方式:

```cpp
namespace SkSpecialImages {
    sk_sp<SkSpecialImage> MakeFromRaster(const SkIRect& subset, ...);
    sk_sp<SkSpecialImage> CopyFromRaster(const SkIRect& subset, ...);
    bool AsBitmap(const SkSpecialImage* img, SkBitmap* result);
}
```

### 2. 策略模式

不同后端(光栅/GPU)通过虚函数实现不同策略:
- `asImage()`: 光栅用 `SkBitmap::asImage()`, GPU 用纹理包装
- `backingStoreDimensions()`: 返回实际存储尺寸
- `onMakeBackingStoreSubset()`: 创建子集视图

### 3. 设计权衡

**为什么限制功能?**
- 不支持 generators: 确保同步访问,避免延迟加载复杂性
- 不支持 tiling/mipmaps: 简化内部效果管道
- 允许超出标称边界: 支持 GPU 纹理 POT 对齐等需求

**为什么需要两套坐标?**
- 子集坐标系: 用户友好的逻辑坐标
- 后备存储坐标: 对应实际内存布局,避免数据复制

## 性能考量

### 1. 零拷贝设计

```cpp
sk_sp<SkSpecialImage> MakeFromRaster(const SkIRect& subset, const SkBitmap& bm, ...) {
    // 直接使用 SkBitmap,不复制像素数据
    return sk_make_sp<SkSpecialImage_Raster>(subset, bm, props);
}
```

### 2. 子集视图优化

子集操作不复制数据,仅调整指针和边界:

```cpp
bool getROPixels(SkBitmap* bm) const {
    // SkBitmap::extractSubset 只调整指针,不复制数据
    return fBitmap.extractSubset(bm, this->subset());
}
```

### 3. 着色器快速路径

当子集等于后备存储时,自动降级为非严格模式,启用硬件平铺:

```cpp
if (strict && this->isExactFit()) {
    // 降级为硬件采样,避免软件边界检查
}
```

### 4. 内存占用

- 光栅实现: 仅存储 `SkBitmap` 引用(8字节)
- 基类开销: 24字节(subset + uniqueID + props)
- 总计: ~32字节 + 共享像素数据

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/core/SkSpecialImage.h` | 公共接口定义 |
| `src/core/SkSpecialImage.cpp` | 核心实现和光栅版本 |
| `src/image/SkImage_Base.h` | `SkImage` 基础接口 |
| `src/shaders/SkImageShader.h` | 图像着色器创建 |
| `src/core/SkImageFilter*.cpp` | 图像滤镜实现(主要使用者) |
| `src/gpu/ganesh/GrSpecialImage.*` | Ganesh GPU 实现 |
| `src/gpu/graphite/SkSpecialImage_Graphite.*` | Graphite GPU 实现 |
