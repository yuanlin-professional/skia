# GrDataUtils

> 源文件
> - src/gpu/ganesh/GrDataUtils.h
> - src/gpu/ganesh/GrDataUtils.cpp

## 概述

`GrDataUtils` 是 Skia Ganesh 渲染引擎中的像素数据处理工具模块，提供了一系列用于像素格式转换、内存布局计算和图像清除的实用函数。该模块是GPU纹理上传和像素数据处理的核心支持库，处理各种颜色类型、颜色空间转换、预乘/非预乘alpha处理以及像素数据的swizzle操作。

该模块使用 `SkRasterPipeline` 进行高效的像素处理，支持多达30多种颜色类型之间的相互转换，并能处理复杂的颜色空间变换和alpha预乘状态转换。

## 架构位置

`GrDataUtils` 位于 Skia GPU 像素数据处理架构中：

```
Skia GPU Pixel Processing
├── Application Layer (应用层)
│   └── SkImage, SkBitmap
├── Pixel Data Layer (像素数据层)
│   ├── GrPixmap (GPU像素映射)
│   ├── GrCPixmap (常量GPU像素映射)
│   ├── GrImageInfo (图像信息)
│   └── GrDataUtils ← 当前模块
├── Pipeline Layer (管线层)
│   └── SkRasterPipeline (光栅化管线)
└── GPU Layer (GPU层)
    ├── GrTexture (纹理)
    └── GrGpu (GPU接口)
```

该模块在架构中的职责：
- 计算mipmap层级的内存布局
- 执行像素格式转换
- 处理颜色空间转换
- 清除图像内存
- 支持各种swizzle模式

## 主要类与结构体

### 核心函数

该模块以命名空间形式组织，不包含类定义，仅提供独立的实用函数。

### 内部枚举

#### LumMode
```cpp
enum class LumMode {
    kNone,      // 无亮度转换
    kToRGB,     // 亮度转RGB
    kToAlpha    // 亮度转Alpha
};
```
用于处理灰度图像到RGBA格式的转换。

## 公共 API 函数

### GrComputeTightCombinedBufferSize
```cpp
size_t GrComputeTightCombinedBufferSize(
    size_t bytesPerPixel,
    SkISize baseDimensions,
    skia_private::TArray<size_t>* individualMipOffsets,
    int mipLevelCount);
```
计算存储所有mipmap层级所需的紧凑缓冲区大小。

**参数说明：**
- `bytesPerPixel`: 每像素字节数
- `baseDimensions`: 基础层级尺寸
- `individualMipOffsets`: 输出参数，每个mip层级的偏移量
- `mipLevelCount`: mipmap层级数量

**对齐规则：**
- 最小对齐为4字节
- 对于3字节像素，使用12字节对齐
- 对于大于4字节的像素，使用自身大小对齐

**返回值：** 总缓冲区大小（字节）

### GrConvertPixels
```cpp
bool GrConvertPixels(const GrPixmap& dst, const GrCPixmap& src, bool flipY = false);
```
在不同像素格式之间转换数据，支持颜色空间转换和alpha预乘状态转换。

**参数说明：**
- `dst`: 目标像素映射
- `src`: 源像素映射
- `flipY`: 是否垂直翻转图像

**支持的转换：**
- 颜色类型转换（30+种颜色格式）
- 颜色空间转换
- 预乘↔非预乘alpha转换
- 像素格式swizzle
- sRGB编码/解码

**返回值：** 转换是否成功

### GrClearImage
```cpp
bool GrClearImage(const GrImageInfo& dstInfo,
                  void* dst,
                  size_t dstRB,
                  std::array<float, 4> color);
```
将图像清除为指定的常量颜色。

**参数说明：**
- `dstInfo`: 目标图像信息
- `dst`: 目标内存地址
- `dstRB`: 目标行字节数
- `color`: RGBA颜色值（浮点数，范围0-1）

**返回值：** 清除是否成功

## 内部实现细节

### Mipmap缓冲区大小计算

```cpp
size_t GrComputeTightCombinedBufferSize(...) {
    individualMipOffsets->push_back(0);

    size_t combinedBufferSize = baseDimensions.width() * bytesPerPixel * baseDimensions.height();
    SkISize levelDimensions = baseDimensions;

    int desiredAlignment = (bytesPerPixel == 3) ? 12 : (bytesPerPixel > 4 ? bytesPerPixel : 4);

    for (int currentMipLevel = 1; currentMipLevel < mipLevelCount; ++currentMipLevel) {
        levelDimensions = {std::max(1, levelDimensions.width() /2),
                           std::max(1, levelDimensions.height()/2)};

        size_t trimmedSize = levelDimensions.area() * bytesPerPixel;
        const size_t alignmentDiff = combinedBufferSize % desiredAlignment;
        if (alignmentDiff != 0) {
            combinedBufferSize += desiredAlignment - alignmentDiff;
        }

        individualMipOffsets->push_back(combinedBufferSize);
        combinedBufferSize += trimmedSize;
    }

    return combinedBufferSize;
}
```

**关键点：**
- 每个mip层级尺寸减半（最小为1）
- 每个层级起始地址按对齐规则对齐
- 满足Vulkan等API的对齐要求

### 像素格式加载映射

`get_load_and_src_swizzle` 函数将40多种 `GrColorType` 映射到 `SkRasterPipelineOp`：

| GrColorType | Pipeline Op | Swizzle | 说明 |
|-------------|-------------|---------|------|
| `kAlpha_8` | `load_a8` | `rgba` | 8位alpha通道 |
| `kRGBA_8888` | `load_8888` | `rgba` | 标准RGBA |
| `kBGRA_8888` | `load_8888` | `bgra` | BGRA格式 |
| `kRGB_565` | `load_565` | `bgr1` | 16位RGB |
| `kRGBA_F16` | `load_f16` | `rgba` | 半精度浮点 |
| `kRGBA_F32` | `load_f32` | `rgba` | 全精度浮点 |
| `kGray_8` | `load_a8` | `aaa1` | 灰度图 |

### 像素格式存储映射

`get_dst_swizzle_and_store` 函数处理存储操作和亮度转换：

```cpp
case GrColorType::kGray_8:
    *lumMode = LumMode::kToAlpha;
    *store = SkRasterPipelineOp::store_a8;
    break;
case GrColorType::kGrayAlpha_88:
    *lumMode = LumMode::kToRGB;
    swizzle = skgpu::Swizzle("ragb");
    *store = SkRasterPipelineOp::store_rg88;
    break;
```

### RGB_888 特殊处理

由于 `SkRasterPipeline` 不直接支持24位RGB，采用两阶段转换：

**读取时：**
```cpp
if (src.colorType() == GrColorType::kRGB_888) {
    // 转换为RGB_888x (32位)
    GrPixmap temp = GrPixmap::Allocate(src.info().makeColorType(GrColorType::kRGB_888x));
    for (int y = 0; y < src.height(); ++y) {
        for (int x = 0; x < src.width(); ++x) {
            memcpy(t, s, 3);
            t[3] = 0xFF;  // 补充alpha通道
        }
    }
    return GrConvertPixels(dst, temp, flipY);
}
```

**写入时：**
```cpp
if (dst.colorType() == GrColorType::kRGB_888) {
    GrPixmap temp = GrPixmap::Allocate(dst.info().makeColorType(GrColorType::kRGB_888x));
    if (!GrConvertPixels(temp, src, flipY)) return false;
    // 打包为24位
    for (int y = 0; y < dst.height(); ++y) {
        for (int x = 0; x < dst.width(); ++x) {
            memcpy(d, t, 3);  // 只拷贝RGB，忽略alpha
        }
    }
    return true;
}
```

### 像素转换管线构建

```cpp
bool GrConvertPixels(const GrPixmap& dst, const GrCPixmap& src, bool flipY) {
    // 快速路径：相同格式且无转换
    if (src.colorType() == dst.colorType() && !alphaOrCSConversion) {
        if (flipY) {
            // 逐行翻转拷贝
        } else {
            SkRectMemcpy(dst.addr(), dst.rowBytes(), src.addr(), src.rowBytes(), ...);
        }
        return true;
    }

    // 构建转换管线
    SkRasterPipeline_<256> pipeline;
    pipeline.append(load, &srcCtx);

    if (hasConversion) {
        loadSwizzle.apply(&pipeline);
        if (srcIsSRGB) {
            pipeline.appendTransferFunction(*skcms_sRGB_TransferFunction());
        }
        if (alphaOrCSConversion) {
            steps->apply(&pipeline);  // 颜色空间和alpha转换
        }
        switch (lumMode) {
            case LumMode::kToRGB:
                pipeline.append(SkRasterPipelineOp::bt709_luminance_or_luma_to_rgb);
                break;
            case LumMode::kToAlpha:
                pipeline.append(SkRasterPipelineOp::bt709_luminance_or_luma_to_alpha);
                break;
        }
        if (dstIsSRGB) {
            pipeline.appendTransferFunction(*skcms_sRGB_Inverse_TransferFunction());
        }
        storeSwizzle.apply(&pipeline);
    } else {
        loadStoreSwizzle.apply(&pipeline);
    }

    pipeline.append(store, &dstCtx);
    auto pipelineFn = pipeline.compile();

    for (int i = 0; i < cnt; ++i) {
        pipelineFn(0, 0, src.width(), height);
        // 更新指针（翻转时）
    }

    return true;
}
```

**管线阶段：**
1. **Load**: 从源格式加载像素
2. **Load Swizzle**: 重排源通道
3. **sRGB Decode**: 解码sRGB（如需要）
4. **Color Space**: 颜色空间转换
5. **Alpha Conversion**: 预乘/非预乘转换
6. **Luminance**: 亮度转换（如需要）
7. **sRGB Encode**: 编码sRGB（如需要）
8. **Store Swizzle**: 重排目标通道
9. **Store**: 存储到目标格式

### 图像清除实现

```cpp
bool GrClearImage(const GrImageInfo& dstInfo, void* dst, size_t dstRB, std::array<float, 4> color) {
    // RGB_888特殊处理
    if (dstInfo.colorType() == GrColorType::kRGB_888) {
        uint32_t rgba = SkColor4f{color[0], color[1], color[2], color[3]}.toBytes_RGBA();
        for (int y = 0; y < dstInfo.height(); ++y) {
            for (int x = 0; x < dstInfo.width(); ++x, d += 3) {
                memcpy(d, &rgba, 3);
            }
        }
        return true;
    }

    // 通用管线
    SkRasterPipeline_<256> pipeline;
    pipeline.appendConstantColor(&alloc, color.data());
    // 添加亮度和sRGB转换
    // 添加swizzle
    pipeline.append(store, &dstCtx);
    pipeline.run(0, 0, dstInfo.width(), dstInfo.height());

    return true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `GrPixmap` / `GrCPixmap` | 像素映射封装 |
| `GrImageInfo` | 图像信息 |
| `SkRasterPipeline` | 像素处理管线 |
| `SkColorSpaceXformSteps` | 颜色空间转换 |
| `skgpu::Swizzle` | 通道重排 |
| `SkRectMemcpy` | 内存拷贝 |
| `skcms` | 颜色管理系统 |
| `GrColorType` | 颜色类型枚举 |

### 被依赖的模块

| 模块 | 使用方式 |
|-----|---------|
| `GrGpu` | 纹理上传前的像素转换 |
| `GrSurfaceContext` | 读写像素数据 |
| `GrTextureProxy` | 纹理数据准备 |
| `GrMippedBitmap` | Mipmap生成 |
| 图像编解码器 | 格式转换 |

## 设计模式与设计决策

### 管线模式（Pipeline Pattern）

使用 `SkRasterPipeline` 构建像素处理管线：
```cpp
pipeline.append(load, &srcCtx);
pipeline.append(transform);
pipeline.append(store, &dstCtx);
auto fn = pipeline.compile();
fn(0, 0, width, height);
```

**优点：**
- 灵活组合处理阶段
- 高效的JIT编译
- SIMD优化

### 策略模式（Strategy Pattern）

通过swizzle和load/store操作映射支持多种颜色格式，无需为每种组合编写代码。

### 模板方法模式（Template Method）

`GrConvertPixels` 提供转换框架，具体的load/store操作作为参数：
```cpp
auto loadSwizzle = get_load_and_src_swizzle(src.colorType(), &load, ...);
auto storeSwizzle = get_dst_swizzle_and_store(dst.colorType(), &store, ...);
```

### 快速路径优化

对常见情况提供快速路径：
```cpp
if (src.colorType() == dst.colorType() && !alphaOrCSConversion) {
    SkRectMemcpy(...);  // 直接内存拷贝
    return true;
}
```

### 特殊格式处理

对不支持的格式（如RGB_888）进行预处理和后处理，保持接口一致性。

### 设计决策

1. **使用SkRasterPipeline**：提供统一的像素处理抽象，支持SIMD加速
2. **分离swizzle和转换**：提高代码复用性
3. **支持就地翻转**：通过逐行处理支持垂直翻转
4. **对齐要求显式化**：明确列出Vulkan等API的对齐要求
5. **sRGB优化**：避免不必要的sRGB编解码

## 性能考量

### SIMD加速

`SkRasterPipeline` 使用SIMD指令集加速像素处理：
- SSE/AVX（x86）
- NEON（ARM）
- 自动向量化

### 快速路径

对于相同格式无转换的情况，直接使用 `memcpy`：
```cpp
SkRectMemcpy(dst.addr(), dst.rowBytes(), src.addr(), src.rowBytes(), tightRB, src.height());
```

### 管线编译缓存

`SkRasterPipeline::compile()` 生成的函数可以重复使用：
```cpp
auto pipelineFn = pipeline.compile();
for (int i = 0; i < cnt; ++i) {
    pipelineFn(0, 0, src.width(), height);
}
```

### 对齐优化

Mipmap布局遵循GPU对齐要求，减少传输开销。

### sRGB优化

```cpp
if (srcIsSRGB && dstIsSRGB && !hasConversion) {
    // 如果源和目标都是sRGB且无其他转换，跳过编解码
    srcIsSRGB = dstIsSRGB = false;
}
```

### 避免不必要的swizzle

当load和store的swizzle可以组合时，跳过中间变换：
```cpp
if (!alphaOrCSConversion) {
    loadStoreSwizzle = skgpu::Swizzle::Concat(loadSwizzle, storeSwizzle);
}
```

### 追踪事件

使用 `TRACE_EVENT0` 进行性能分析：
```cpp
TRACE_EVENT0("skia.gpu", TRACE_FUNC);
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrPixmap.h` | 使用 | GPU像素映射 |
| `src/gpu/ganesh/GrImageInfo.h` | 使用 | 图像信息 |
| `src/core/SkRasterPipeline.h` | 依赖 | 像素处理管线 |
| `src/core/SkColorSpaceXformSteps.h` | 依赖 | 颜色空间转换 |
| `src/gpu/Swizzle.h` | 依赖 | 通道重排 |
| `src/base/SkRectMemcpy.h` | 依赖 | 内存拷贝 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | GPU类型定义 |
| `src/gpu/ganesh/GrGpu.h` | 被使用 | GPU接口 |
| `src/gpu/ganesh/GrSurfaceContext.h` | 被使用 | 表面上下文 |
| `src/gpu/ganesh/image/GrMippedBitmap.h` | 被使用 | Mipmap位图 |
