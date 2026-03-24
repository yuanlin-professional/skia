# SkScalingCodec - 支持任意缩放的编解码器基类

> 源文件: `src/codec/SkScalingCodec.h`

## 概述

`SkScalingCodec.h` 定义了一个辅助基类 `SkScalingCodec`，用于支持任意缩放比例解码的图像编解码器。与仅支持特定缩放因子（如 1/2、1/4、1/8）的编解码器不同，继承自 `SkScalingCodec` 的编解码器可以解码为任意目标尺寸（在 1x1 到原始尺寸之间）。这是一个仅包含 45 行代码的简洁头文件。

## 架构位置

该文件位于 `src/codec/` 目录下，是 `SkCodec` 类层次结构中的一个中间基类。具体的图像格式编解码器（如 WebP 解码器）继承自 `SkScalingCodec` 而非直接继承 `SkCodec`，从而获得任意缩放能力。

## 主要类与结构体

### `SkScalingCodec`
继承自 `SkCodec` 的 protected 基类。

**构造函数**:
```cpp
SkScalingCodec(SkEncodedInfo&& info, XformFormat srcFormat,
               std::unique_ptr<SkStream> stream,
               SkEncodedOrigin origin = kTopLeft_SkEncodedOrigin)
```
将参数直接转发给 `SkCodec` 基类构造函数。

**覆写的虚函数**:
- `onGetScaledDimensions(float desiredScale)`: 根据期望缩放比例计算目标尺寸，最小为 1x1
- `onDimensionsSupported(const SkISize& requested)`: 验证请求的尺寸是否在 [1, 原始尺寸] 范围内

## 公共 API 函数

该类为 protected 基类，不直接提供公共 API。其功能通过 `SkCodec` 的公共接口暴露：
- `SkCodec::getScaledDimensions()` 会调用 `onGetScaledDimensions`
- `SkCodec::dimensionsSupported()` 会调用 `onDimensionsSupported`

## 内部实现细节

1. **最小尺寸保证**: `onGetScaledDimensions` 使用 `std::max(1, ...)` 确保结果尺寸至少为 1x1，因为 `SkCodec` 将零尺寸视为错误。这一保证对于极小的缩放因子（如 0.001）尤为重要。

2. **四舍五入**: 使用 `SkScalarRoundToInt` 对缩放结果进行四舍五入，而非截断。这提供了更精确的尺寸计算，例如 `0.5 * 101 = 50.5` 会被取整为 51 而非 50。

3. **独立维度验证**: `onDimensionsSupported` 对宽度和高度独立验证，允许非等比缩放。请求的尺寸必须满足 `1 <= w <= dim.width()` 且 `1 <= h <= dim.height()`，即只支持缩小不支持放大。

4. **默认方向**: 构造函数的 `origin` 参数默认为 `kTopLeft_SkEncodedOrigin`（无旋转），这是最常见的图像方向。子类可以传递从 EXIF 等元数据中读取的实际方向值。

5. **与固定缩放因子解码器的区别**: JPEG 解码器仅支持 1/1、1/2、1/4、1/8 等固定缩放因子（利用 DCT 系数截断），而 `SkScalingCodec` 的子类通过重采样支持任意中间尺寸。这意味着 WebP 等基于此类的解码器可以直接解码到精确的目标尺寸。

6. **构造函数参数传递**: 构造函数使用移动语义（`std::move`）传递 `SkEncodedInfo` 和 `SkStream`，避免不必要的拷贝。`XformFormat srcFormat` 指定了源像素的颜色变换格式。

## 依赖关系

- `include/codec/SkCodec.h`: 基类 `SkCodec`
- `include/codec/SkEncodedOrigin.h`: 图像方向枚举
- `include/core/SkScalar.h`: `SkScalarRoundToInt` 工具
- `include/core/SkSize.h`: `SkISize` 类型
- `include/core/SkStream.h`: 输入流
- `include/private/SkEncodedInfo.h`: 编码图像信息

## 设计模式与设计决策

1. **模板方法模式**: 通过覆写 `SkCodec` 的虚函数 `onGetScaledDimensions` 和 `onDimensionsSupported` 来定制缩放行为，基类 `SkCodec` 负责调用时机。

2. **最小实现原则**: 仅覆写缩放相关的两个方法，将像素解码（`onGetPixels`）、增量解码等功能留给具体格式子类实现。

3. **protected 继承接口**: 构造函数和方法均为 protected，强制通过继承使用，不能直接实例化 `SkScalingCodec`。

4. **头文件内联**: 所有方法定义在头文件中，无对应 .cpp 文件，体现了该类作为轻量级辅助基类的定位。

## 性能考量

- **内联实现**: 所有方法在头文件中内联实现，避免函数调用开销，编译器可以直接在调用点展开代码
- **简单算术**: 缩放计算仅涉及一次乘法和一次取整操作，没有分支预测问题
- **无额外状态**: `SkScalingCodec` 不引入任何额外的成员变量，不增加内存占用
- **编译时多态**: 通过虚函数表实现多态，在继承层次确定的情况下可被编译器去虚拟化优化

## 相关文件

- `include/codec/SkCodec.h`: 编解码器基类，定义了 `onGetScaledDimensions` 和 `onDimensionsSupported` 虚函数
- `include/private/SkEncodedInfo.h`: 编码图像信息，包含原始图像的尺寸和格式
- `include/codec/SkEncodedOrigin.h`: 图像方向枚举，影响解码后的显示方向
- `src/codec/SkWebpCodec.h`: WebP 解码器，可能继承此类以获得任意缩放支持
- `src/codec/SkWbmpCodec.h`: WBMP 解码器，可能继承此类
