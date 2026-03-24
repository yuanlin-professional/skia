# SkMatrixConvolutionImageFilter - 矩阵卷积图像滤镜

> 源文件:
> - `src/effects/imagefilters/SkMatrixConvolutionImageFilter.h`
> - `src/effects/imagefilters/SkMatrixConvolutionImageFilter.cpp`

## 概述

`SkMatrixConvolutionImageFilter` 实现了矩阵卷积图像滤镜，用于对图像应用卷积核(kernel)操作。该滤镜是 SVG `feConvolveMatrix` 滤镜原语的底层实现，允许用户指定任意大小的卷积核对图像进行卷积运算，从而实现模糊、锐化、边缘检测等各种图像处理效果。

卷积运算采用朴素算法（非频域 DFT 变换），因此卷积核的大小受限制以确保合理的运算时间。最大支持的核大小为 256 个元素，其中小于 28 个元素的核通过 uniform 数组传递，而更大的核则编码为 A8 纹理图像。

## 架构位置

该文件位于 Skia 的图像效果子系统中：

```
include/effects/SkImageFilters.h    // 公共工厂方法 (MatrixConvolution)
  |
  v
src/effects/imagefilters/
  SkMatrixConvolutionImageFilter.h   // 命名空间常量定义
  SkMatrixConvolutionImageFilter.cpp // 内部类实现
  |
  v
src/core/SkImageFilter_Base.h       // 基类
src/core/SkKnownRuntimeEffects.h    // 关联 SkSL runtime effect
```

矩阵卷积滤镜通过 `SkImageFilters::MatrixConvolution()` 工厂函数创建，内部与 `SkCropImageFilter` 配合实现平铺模式。

## 主要类与结构体

### 命名空间 `MatrixConvolutionImageFilter`

定义核大小相关的常量：

| 常量 | 值 | 说明 |
|------|-----|------|
| `kLargeKernelSize` | 256 | 核元素数量的最大值 |
| `kSmallKernelSize` | 64 | 小核纹理尺寸阈值 |
| `kMaxUniformKernelSize` | 28 | uniform 数组可容纳的最大核大小（必须为4的倍数） |

### 匿名命名空间中的 `SkMatrixConvolutionImageFilter` 类

继承自 `SkImageFilter_Base`，为 `final` 类。

**主要成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fKernel` | `TArray<float>` | 原始卷积核数据，用于序列化 |
| `fKernelSize` | `LayerSpace<SkISize>` | 核的宽高（图层坐标系） |
| `fKernelOffset` | `LayerSpace<IVector>` | 核的偏移（图层坐标系） |
| `fGain` | `float` | 增益因子 |
| `fBias` | `float` | 偏置值（假定在 0-255 范围） |
| `fConvolveAlpha` | `bool` | 是否对 alpha 通道也做卷积 |
| `fKernelBitmap` | `SkBitmap` | 大核数据编码为 A8 位图 |
| `fInnerGain` / `fInnerBias` | `float` | 从 unorm8 重建原始系数的参数 |

## 公共 API 函数

### `SkImageFilters::MatrixConvolution()`

```cpp
static sk_sp<SkImageFilter> MatrixConvolution(
    const SkISize& kernelSize,
    const SkScalar kernel[],
    SkScalar gain,
    SkScalar bias,
    const SkIPoint& kernelOffset,
    SkTileMode tileMode,
    bool convolveAlpha,
    sk_sp<SkImageFilter> input,
    const CropRect& cropRect);
```

工厂函数，创建矩阵卷积图像滤镜。

**参数验证：**
- `kernelSize` 宽高均需 >= 1
- 核面积不得超过 `kLargeKernelSize`（256）
- `kernel` 不可为 nullptr
- `kernelOffset` 必须在核范围内

**平铺模式处理：**
- 若提供了 `cropRect` 且 `tileMode != kDecal`，则先用 `SkImageFilters::Crop` 包裹输入
- 输出总是以 kDecal 模式裁剪

### `SkRegisterMatrixConvolutionImageFilterFlattenable()`

注册序列化/反序列化支持，同时注册旧名称 `SkMatrixConvolutionImageFilterImpl` 以兼容旧 SKP 文件。

## 内部实现细节

### 核大小量化策略

`quantize_by_kernel_size()` 函数将核大小映射到三个级别：

1. **Uniform 路径**（< 28 元素）：通过 `half4` uniform 数组传递，使用 `kMatrixConvUniforms` runtime effect
2. **小纹理路径**（28-64 元素）：编码为 A8 纹理，使用 `kMatrixConvTexSm` runtime effect
3. **大纹理路径**（65-256 元素）：编码为 A8 纹理，使用 `kMatrixConvTexLg` runtime effect

### 核数据编码为位图

`create_kernel_bitmap()` 将大核数据编码为 A8 格式的一维位图：

1. 遍历核数据找到最小值 `min` 和最大值 `max`
2. 计算 `innerGain = max - min`，`innerBias = min`
3. 每个系数归一化为 `uint8`: `round(255 * (kernel[i] - min) / innerGain)`
4. 着色器中通过 `(a + innerBias) * innerGain` 重建原始系数

### 着色器创建

`createShader()` 根据核大小选择对应的 SkRuntimeEffect，设置以下 child/uniform：

- `child`：输入着色器
- `kernel`（纹理路径）：核数据纹理 + `innerGainAndBias`
- `kernel`（uniform 路径）：28 元素 float 数组
- `size`、`offset`：核尺寸与偏移
- `gainAndBias`：增益和偏置（偏置除以 255 以匹配 [0,1] 颜色范围）
- `convolveAlpha`：是否卷积 alpha

### 边界计算

- `boundsSampledByKernel()`：给定输出区域，计算需要采样的输入区域（向外扩展）
- `boundsAffectedByKernel()`：给定输入区域，计算可能受影响的输出区域（向内收缩）

### `onAffectsTransparentBlack()`

始终返回 `true`。这是因为卷积核在设备空间中应用，而 `computeFastBounds()` API 不提供变换信息，因此无法精确计算快速边界。

## 依赖关系

### 内部依赖

- `SkImageFilter_Base`：图像滤镜基类
- `SkImageFilterTypes.h`：`skif::Context`、`skif::FilterResult` 等类型
- `SkKnownRuntimeEffects.h`：预编译的 SkSL runtime effect
- `SkRuntimeEffect` / `SkRuntimeShaderBuilder`：运行时着色器构建
- `SkSafeMath`：安全的数学运算
- `SkPicturePriv`：SKP 版本常量

### 外部依赖

- `SkImageFilters::Crop`：用于实现平铺模式
- `SkBitmap` / `SkImage`：核数据存储与纹理化

## 设计模式与设计决策

1. **工厂模式**：通过 `SkImageFilters::MatrixConvolution()` 静态工厂创建，隐藏内部类名
2. **策略模式**：根据核大小选择 uniform 或纹理路径，自动降级
3. **装饰器模式**：平铺模式通过包裹 `Crop` 滤镜实现，而非在卷积滤镜内部处理
4. **序列化兼容**：保留旧名称注册以兼容历史 SKP 文件；新版本中平铺信息由外部 Crop 滤镜处理
5. **精度与通用性权衡**：大核数据使用 A8（unorm8）存储，牺牲精度换取通用 GPU 兼容性

## 性能考量

1. **朴素卷积**：未使用 DFT/FFT，时间复杂度为 O(核面积 * 像素数)，大核性能下降显著
2. **核大小限制**：限制为 256 元素，SkSL 在 >= 2048 时会报错
3. **三级量化**：uniform（最快，< 28）→ 小纹理（64）→ 大纹理（256），减少不必要的纹理读取
4. **Uniform 打包**：uniform 数组以 `half4` 打包，避免 std140 布局中的 16 字节对齐浪费
5. **位图缓存**：`fKernelBitmap` 在构造时一次性创建，通过 `ctx.backend()->getCachedBitmap()` 缓存纹理
6. **`ShaderFlags::kSampledRepeatedly`**：标记输入着色器被重复采样，提示后端优化

## 相关文件

- `include/effects/SkImageFilters.h` - 公共 API 声明
- `src/core/SkImageFilter_Base.h` - 图像滤镜基类
- `src/core/SkKnownRuntimeEffects.h` - 预注册的 SkSL runtime effect 键
- `src/core/SkImageFilterTypes.h` - `skif` 命名空间下的类型定义
- `src/core/SkPicturePriv.h` - SKP 版本常量
- `src/effects/imagefilters/SkCropImageFilter.cpp` - 裁剪/平铺滤镜（配合使用）
