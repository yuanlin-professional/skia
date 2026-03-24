# DecodeUtils

> 源文件：tools/DecodeUtils.h, tools/DecodeUtils.cpp

## 概述

`DecodeUtils` 是 Skia 工具库中提供的图像解码辅助函数集合。该模块封装了常见的图像解码操作，简化了从编码数据或资源文件加载图像到 `SkBitmap` 或 `SkImage` 的过程。它提供了类型安全的接口来指定目标色彩类型，并与 `Resources` 模块集成，方便测试代码快速加载测试图像。这些函数广泛用于 Skia 的测试套件和示例程序中。

## 架构位置

`DecodeUtils` 在 Skia 架构中的位置：

- 位于 `tools/` 目录，属于测试和工具辅助函数
- 封装 `SkImageGenerator` 进行图像解码
- 与 `Resources` 模块集成，加载资源文件
- 提供便捷的内联函数简化常见操作
- 在 `ToolUtils` 命名空间中
- 主要服务于测试和示例代码

该模块是测试基础设施的一部分，让测试代码无需关心解码细节。

## 主要类与结构体

### ToolUtils 命名空间函数

**核心函数**：
```cpp
namespace ToolUtils {

bool DecodeDataToBitmap(sk_sp<SkData> data, SkBitmap* dst);

bool DecodeDataToBitmapWithColorType(sk_sp<SkData> data,
                                     SkBitmap* dst,
                                     SkColorType dstCT);

}  // namespace ToolUtils
```

**内联便捷函数**：
```cpp
inline bool GetResourceAsBitmap(const char* resource, SkBitmap* dst);

inline bool GetResourceAsBitmapWithColortype(const char* resource,
                                             SkBitmap* dst,
                                             SkColorType dstCT);

inline sk_sp<SkImage> GetResourceAsImage(const char* resource);
```

## 公共 API 函数

### 核心解码函数

**DecodeDataToBitmap()**
```cpp
bool DecodeDataToBitmap(sk_sp<SkData> data, SkBitmap* dst)
```
- **功能**：将编码数据解码为 Bitmap
- **参数**：
  - `data`: 编码的图像数据（如 PNG、JPEG）
  - `dst`: 输出的 Bitmap 对象
- **返回值**：成功返回 `true`，失败返回 `false`
- **特性**：
  - 使用图像的原始色彩类型
  - 移除色彩空间（`makeColorSpace(nullptr)`）
  - 自动分配像素内存

**DecodeDataToBitmapWithColorType()**
```cpp
bool DecodeDataToBitmapWithColorType(sk_sp<SkData> data,
                                     SkBitmap* dst,
                                     SkColorType dstCT)
```
- **功能**：将编码数据解码为指定色彩类型的 Bitmap
- **参数**：
  - `data`: 编码的图像数据
  - `dst`: 输出的 Bitmap 对象
  - `dstCT`: 目标色彩类型（如 `kRGBA_8888_SkColorType`）
- **返回值**：成功返回 `true`
- **用途**：测试特定色彩类型的渲染或处理

### 资源加载便捷函数

**GetResourceAsBitmap()**
```cpp
inline bool GetResourceAsBitmap(const char* resource, SkBitmap* dst)
```
- **功能**：从资源文件加载 Bitmap
- **参数**：
  - `resource`: 资源路径（如 "images/mandrill_128.png"）
  - `dst`: 输出的 Bitmap 对象
- **实现**：
```cpp
return DecodeDataToBitmap(GetResourceAsData(resource), dst);
```

**GetResourceAsBitmapWithColortype()**
```cpp
inline bool GetResourceAsBitmapWithColortype(const char* resource,
                                             SkBitmap* dst,
                                             SkColorType dstCT)
```
- **功能**：从资源文件加载指定色彩类型的 Bitmap
- **实现**：
```cpp
return DecodeDataToBitmapWithColorType(GetResourceAsData(resource), dst, dstCT);
```

**GetResourceAsImage()**
```cpp
inline sk_sp<SkImage> GetResourceAsImage(const char* resource)
```
- **功能**：从资源文件加载为 `SkImage`
- **返回值**：`SkImage` 智能指针，失败返回 `nullptr`
- **特性**：延迟解码（`DeferredFromEncodedData`）
- **实现**：
```cpp
return SkImages::DeferredFromEncodedData(GetResourceAsData(resource));
```

## 内部实现细节

### 解码流程

**DecodeDataToBitmap() 实现**：
```cpp
bool DecodeDataToBitmap(sk_sp<SkData> data, SkBitmap* dst) {
    // 1. 创建图像生成器
    std::unique_ptr<SkImageGenerator> gen(
        SkImageGenerators::MakeFromEncoded(std::move(data))
    );

    // 2. 分配像素内存
    return gen && dst->tryAllocPixels(gen->getInfo()) &&

    // 3. 解码像素数据（移除色彩空间）
           gen->getPixels(
               gen->getInfo().makeColorSpace(nullptr),
               dst->getPixels(),
               dst->rowBytes()
           );
}
```

**关键步骤**：
1. 使用 `SkImageGenerators::MakeFromEncoded()` 识别格式并创建生成器
2. 根据生成器的 `SkImageInfo` 分配 Bitmap 内存
3. 调用 `getPixels()` 解码到 Bitmap

### 色彩类型转换

**DecodeDataToBitmapWithColorType() 实现**：
```cpp
bool DecodeDataToBitmapWithColorType(sk_sp<SkData> data, SkBitmap* dst, SkColorType dstCT) {
    std::unique_ptr<SkImageGenerator> gen(
        SkImageGenerators::MakeFromEncoded(std::move(data))
    );

    // 修改目标色彩类型
    return gen && dst->tryAllocPixels(gen->getInfo().makeColorType(dstCT)) &&
           gen->getPixels(
               gen->getInfo().makeColorSpace(nullptr).makeColorType(dstCT),
               dst->getPixels(),
               dst->rowBytes()
           );
}
```

**色彩转换**：
- 使用 `makeColorType()` 修改目标色彩类型
- `SkImageGenerator` 自动执行必要的像素格式转换

### 色彩空间处理

**移除色彩空间**：
```cpp
gen->getInfo().makeColorSpace(nullptr)
```
- 测试代码通常不需要色彩空间转换
- 移除色彩空间简化测试，确保像素值一致性

### 资源加载集成

**GetResourceAsData()**：
- 来自 `tools/Resources.h`
- 从资源目录加载文件为 `SkData`
- 支持相对路径（如 `"images/color_wheel.png"`）

**资源路径**：
- 默认资源目录：`resources/`
- 可通过命令行标志覆盖：`--resourcePath`

## 依赖关系

**Skia 核心依赖**：
- `include/core/SkBitmap.h` - 位图类
- `include/core/SkImage.h` - 图像类
- `include/core/SkData.h` - 数据容器
- `include/core/SkImageGenerator.h` - 图像生成器接口
- `include/core/SkImageInfo.h` - 图像信息
- `include/core/SkColorType.h` - 色彩类型枚举
- `include/core/SkColorSpace.h` - 色彩空间

**图像生成器**：
- `src/image/SkImageGeneratorPriv.h` - 图像生成器工厂
- `SkImageGenerators::MakeFromEncoded()` - 自动识别格式

**资源模块**：
- `tools/Resources.h` - 资源文件加载
- `GetResourceAsData()` - 加载资源为数据

## 设计模式与设计决策

### 外观模式
封装复杂的图像生成器 API，提供简单的一步解码函数。

### 便捷函数模式
内联函数组合基础函数，减少重复代码。

### 失败返回 bool
使用布尔返回值表示成功/失败，避免异常处理。

### 关键设计决策

**1. 移除色彩空间**
测试代码通常比较像素值，色彩空间会引入不确定性。

**2. 分离色彩类型转换**
提供两个函数而非可选参数，使接口更清晰。

**3. 内联便捷函数**
资源加载函数定义在头文件，允许编译器内联优化。

**4. 智能指针参数**
使用 `sk_sp<SkData>` 管理数据生命周期。

**5. 延迟解码选项**
`GetResourceAsImage()` 使用延迟解码，节省内存。

**6. 命名空间隔离**
使用 `ToolUtils` 命名空间避免全局命名污染。

## 性能考量

### 解码性能

**SkImageGenerator**：
- 自动选择最优解码器（如 libpng、libjpeg）
- 硬件加速（如果可用）

**延迟解码 vs 立即解码**：
- `GetResourceAsImage()`：延迟解码，首次使用时才解码
- `GetResourceAsBitmap()`：立即解码到内存

### 内存使用

**Bitmap**：
- 立即分配完整的像素缓冲区
- 内存占用：`width × height × bytesPerPixel`

**Image**：
- 可能保留编码数据，按需解码
- 适合不立即访问像素的场景

### 色彩转换开销

**色彩类型转换**：
- `SkImageGenerator` 内部执行像素格式转换
- 例如：RGBA → BGRA、8888 → 565

**优化建议**：
- 尽量使用原始色彩类型（避免转换）
- 对于重复使用的图像，缓存解码结果

### 使用场景

**适合**：
- 测试代码加载测试图像
- 示例程序加载资源
- 原型开发快速加载图像

**不适合**：
- 生产环境的图像加载（缺少错误处理和日志）
- 需要精细控制解码参数的场景
- 性能关键路径（应使用直接 API）

## 相关文件

**资源管理**：
- `tools/Resources.h` - 资源文件加载函数
- `tools/Resources.cpp` - 资源路径解析

**图像生成器**：
- `include/core/SkImageGenerator.h` - 生成器接口
- `src/image/SkImageGeneratorPriv.h` - 内部工厂函数
- `src/codec/` - 各种图像格式解码器

**使用示例**：
- `tests/` - 大量测试用例使用这些函数
- `gm/` - GM（Gold Master）测试使用资源加载
- `tools/viewer/` - Viewer 工具加载示例图像

**编解码器**：
- `include/codec/SkCodec.h` - 编解码器接口
- `src/codec/SkPngCodec.h` - PNG 解码器
- `src/codec/SkJpegCodec.h` - JPEG 解码器

**构建配置**：
- `BUILD.gn` - 工具库编译配置
- 测试目标依赖 `tools` 模块
