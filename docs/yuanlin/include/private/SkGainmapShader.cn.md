# SkGainmapShader

> 源文件: `include/private/SkGainmapShader.h`

## 概述

SkGainmapShader 是一个用于创建 Gainmap 着色器的工厂类。Gainmap 着色器能够根据显示器的 HDR 动态范围,将基础图像和 Gainmap 图像动态混合,实现从 SDR 到 HDR 的平滑过渡。该类是 Skia HDR 图像渲染的核心组件,遵循 Adobe Gainmap 技术规范。

## 架构位置

SkGainmapShader 位于 Skia 着色器系统的高级抽象层,专门处理 HDR Gainmap 渲染。它将基础图像、Gainmap 图像和渲染参数组合成一个 SkShader 对象,可以在 SkCanvas 绘制时使用。该类与图像解码器、颜色空间管理和 GPU 渲染管线紧密集成。

## 主要类与结构体

### SkGainmapShader

这是一个纯静态工厂类,提供创建 Gainmap 着色器的方法。

**设计特点**:
- 所有方法都是静态的,无需创建实例
- 使用工厂模式创建 SkShader 对象
- 支持自定义目标颜色空间

## 公共 API 函数

### `static sk_sp<SkShader> Make(...)`

创建 Gainmap 着色器的主要方法,有两个重载版本。

#### 版本 1: 不指定目标颜色空间

```cpp
static sk_sp<SkShader> Make(
    const sk_sp<const SkImage>& baseImage,
    const SkRect& baseRect,
    const SkSamplingOptions& baseSamplingOptions,
    const sk_sp<const SkImage>& gainmapImage,
    const SkRect& gainmapRect,
    const SkSamplingOptions& gainmapSamplingOptions,
    const SkGainmapInfo& gainmapInfo,
    const SkRect& dstRect,
    float dstHdrRatio
);
```

**参数说明**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| baseImage | const sk_sp<const SkImage>& | 基础图像(SDR 或 HDR) |
| baseRect | const SkRect& | 基础图像的采样矩形 |
| baseSamplingOptions | const SkSamplingOptions& | 基础图像的采样选项(滤波方式) |
| gainmapImage | const sk_sp<const SkImage>& | Gainmap 图像 |
| gainmapRect | const SkRect& | Gainmap 图像的采样矩形 |
| gainmapSamplingOptions | const SkSamplingOptions& | Gainmap 图像的采样选项 |
| gainmapInfo | const SkGainmapInfo& | Gainmap 渲染参数 |
| dstRect | const SkRect& | 目标绘制矩形 |
| dstHdrRatio | float | 目标显示器的 HDR 与 SDR 亮度比 |

**返回值**:
- 成功返回 SkShader 智能指针
- 失败返回 nullptr

#### 版本 2: 指定目标颜色空间

```cpp
static sk_sp<SkShader> Make(
    const sk_sp<const SkImage>& baseImage,
    const SkRect& baseRect,
    const SkSamplingOptions& baseSamplingOptions,
    const sk_sp<const SkImage>& gainmapImage,
    const SkRect& gainmapRect,
    const SkSamplingOptions& gainmapSamplingOptions,
    const SkGainmapInfo& gainmapInfo,
    const SkRect& dstRect,
    float dstHdrRatio,
    sk_sp<SkColorSpace> dstColorSpace
);
```

**额外参数**:

| 参数名 | 类型 | 说明 |
|--------|------|------|
| dstColorSpace | sk_sp<SkColorSpace> | 目标颜色空间,用于混合计算 |

**说明**: 如果未指定 dstColorSpace,默认使用基础图像的颜色空间。

## Gainmap 渲染数学

Gainmap 着色器实现的核心算法如 SkGainmapInfo 中所述:

### 权重计算

首先计算 Gainmap 应用的权重:
```
W = clamp((log(H) - log(fDisplayRatioSdr)) /
          (log(fDisplayRatioHdr) - log(fDisplayRatioSdr)), 0, 1)
```
其中 H 是 dstHdrRatio(目标显示器的 HDR/SDR 比)。

### Gainmap 值转换

将采样的 Gainmap 值 G 转换为对数空间的增益 L:
```
L = mix(log(fGainmapRatioMin), log(fGainmapRatioMax), pow(G, fGainmapGamma))
```

### 像素混合

根据基础图像类型应用增益:
- **SDR 基础图像**:
  ```
  D = (B + fEpsilonSdr) * exp(L * W) - fEpsilonHdr
  ```
- **HDR 基础图像**:
  ```
  D = (B + fEpsilonHdr) * exp(L * (W - 1)) - fEpsilonSdr
  ```

其中:
- B: 基础图像的像素值(线性颜色空间)
- D: 输出像素值
- W: 权重参数
- L: 对数空间的增益

## 内部实现细节

### 着色器管线

SkGainmapShader 创建的着色器通常编译为以下 GPU 着色器管线:

1. **基础图像采样**:
   - 根据 baseRect 到 dstRect 的变换计算纹理坐标
   - 使用 baseSamplingOptions 采样 baseImage

2. **Gainmap 采样**:
   - 根据 gainmapRect 到 dstRect 的变换计算纹理坐标
   - 使用 gainmapSamplingOptions 采样 gainmapImage

3. **颜色空间转换**:
   - 将基础图像转换到线性空间
   - 应用 fGainmapMathColorSpace 转换(如果指定)

4. **Gainmap 应用**:
   - 计算权重 W
   - 转换 Gainmap 值为增益 L
   - 混合基础图像和增益

5. **输出转换**:
   - 转换到目标颜色空间
   - 应用输出传输函数

### 矩形映射

三个矩形(baseRect, gainmapRect, dstRect)的关系:
- **baseRect**: 基础图像中的源区域(像素坐标)
- **gainmapRect**: Gainmap 图像中的源区域(像素坐标)
- **dstRect**: 着色器输出的目标区域(着色器坐标)

着色器会创建两个独立的坐标变换:
- baseRect → dstRect: 用于采样基础图像
- gainmapRect → dstRect: 用于采样 Gainmap 图像

这允许基础图像和 Gainmap 有不同的分辨率和裁剪区域。

### 采样选项

SkSamplingOptions 控制图像采样的质量:
- **SkFilterMode::kNearest**: 最近邻插值,最快但质量低
- **SkFilterMode::kLinear**: 双线性插值,平衡质量和性能
- **SkCubicResampler**: 双三次插值,最高质量但较慢
- **MipMap**: 支持 MipMap 采样,用于缩小时的抗锯齿

通常:
- baseImage 使用高质量采样(双线性或双三次)
- gainmapImage 可以使用较低质量采样(因为通常分辨率较低)

### 颜色空间处理

Gainmap 数学必须在线性光照空间进行:
1. 基础图像从其颜色空间转换到线性空间
2. 应用 Gainmap 增益(在 fGainmapMathColorSpace 中进行)
3. 转换到目标颜色空间(dstColorSpace)

如果 fGainmapMathColorSpace 未指定,使用基础图像的色彩原色。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `include/core/SkRefCnt.h` | 智能指针 sk_sp |
| `include/core/SkShader.h` | 着色器基类 |
| `include/core/SkImage.h` | 图像数据 |
| `include/core/SkColorSpace.h` | 颜色空间管理 |
| `include/private/SkGainmapInfo.h` | Gainmap 参数 |
| `include/core/SkRect.h` | 矩形定义 |
| `include/core/SkSamplingOptions.h` | 采样选项 |
| `include/private/base/SkAPI.h` | API 导出宏 |

### 被依赖的模块

- **SkImage**: 图像类在加载 HDR JPEG 时使用 SkGainmapShader
- **SkCanvas**: 绘制 HDR 图像时使用此着色器
- **图像查看器**: 显示 HDR 照片的应用
- **GPU 后端**: Ganesh 和 Graphite 实现着色器编译

## 设计模式与设计决策

### 工厂模式

使用静态工厂方法而非构造函数:
- **封装复杂性**: 隐藏着色器创建的实现细节
- **返回基类**: 返回 SkShader,用户无需知道具体类型
- **错误处理**: 可以返回 nullptr 表示失败

### 不可变对象

创建的 SkShader 是不可变的:
- **线程安全**: 可以在多线程中安全共享
- **缓存友好**: 不可变对象易于缓存
- **避免副作用**: 着色器的行为完全由创建时的参数决定

### 矩形参数化

使用三个独立的矩形参数:
- **灵活性**: 支持裁剪、缩放、不同分辨率
- **效率**: 避免不必要的中间图像创建
- **通用性**: 适用于各种使用场景

### 颜色空间显式化

提供 dstColorSpace 参数:
- **精确控制**: 用户可以指定期望的输出颜色空间
- **默认合理**: 默认使用基础图像的颜色空间
- **支持 HDR 工作流**: 可以输出到宽色域或 PQ/HLG 空间

## 性能考量

### GPU 加速

Gainmap 着色器在 GPU 上执行:
- **并行计算**: 所有像素并行处理
- **单次通过**: 整个计算在一个着色器中完成,无需中间纹理
- **硬件采样**: 利用 GPU 的纹理采样单元

### 采样优化

- **Gainmap 分辨率**: Gainmap 通常是基础图像的 1/2 或 1/4 分辨率,节省带宽
- **MipMap**: 对于缩小的图像,使用 MipMap 可以显著提高性能和质量
- **采样器缓存**: GPU 会缓存纹理采样器状态

### 颜色空间转换

- **查找表(LUT)**: 某些颜色空间转换可以使用 3D LUT 加速
- **硬件支持**: 现代 GPU 支持部分颜色空间转换的硬件加速
- **合并计算**: 多个转换会被合并到单个着色器中

### 典型性能

在现代 GPU 上:
- 1080p HDR 图像渲染: ~1-2ms
- 4K HDR 图像渲染: ~4-8ms
- 瓶颈通常是纹理带宽,而非计算

## 使用示例

### 基本使用

```cpp
// 加载 HDR JPEG,获取基础图像和 Gainmap
sk_sp<SkImage> baseImage = ...;
sk_sp<SkImage> gainmapImage = ...;
SkGainmapInfo gainmapInfo = ...;

// 获取显示器 HDR 能力
float displayHdrRatio = getDisplayHdrRatio();  // 例如 4.0

// 创建 Gainmap 着色器
sk_sp<SkShader> shader = SkGainmapShader::Make(
    baseImage,
    SkRect::MakeWH(baseImage->width(), baseImage->height()),
    SkSamplingOptions(SkFilterMode::kLinear),
    gainmapImage,
    SkRect::MakeWH(gainmapImage->width(), gainmapImage->height()),
    SkSamplingOptions(SkFilterMode::kLinear),
    gainmapInfo,
    SkRect::MakeWH(dstWidth, dstHeight),
    displayHdrRatio
);

// 使用着色器绘制
SkPaint paint;
paint.setShader(shader);
canvas->drawRect(SkRect::MakeWH(dstWidth, dstHeight), paint);
```

### 高级使用:指定输出颜色空间

```cpp
// 输出到 Display P3 颜色空间
sk_sp<SkColorSpace> dstColorSpace = SkColorSpace::MakeRGB(
    SkNamedTransferFn::kSRGB,
    SkNamedGamut::kDisplayP3
);

sk_sp<SkShader> shader = SkGainmapShader::Make(
    baseImage, baseRect, baseSampling,
    gainmapImage, gainmapRect, gainmapSampling,
    gainmapInfo, dstRect, displayHdrRatio,
    dstColorSpace
);
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `src/shaders/SkGainmapShader.cpp` | 实现文件 |
| `include/private/SkGainmapInfo.h` | Gainmap 参数定义 |
| `include/core/SkShader.h` | 着色器基类 |
| `src/gpu/ganesh/GrFragmentProcessor.cpp` | GPU 着色器编译 |
| `include/private/SkJpegMetadataDecoder.h` | 解码 Gainmap 图像 |
| `tests/GainmapShaderTest.cpp` | 单元测试 |
