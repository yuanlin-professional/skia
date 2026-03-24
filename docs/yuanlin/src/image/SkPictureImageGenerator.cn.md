# SkPictureImageGenerator

> 源文件：src/image/SkPictureImageGenerator.h, src/image/SkPictureImageGenerator.cpp

## 概述

`SkPictureImageGenerator` 是从 `SkPicture` 图形命令序列生成像素数据的图像生成器实现。它继承自 `SkImageGenerator`，能够将矢量图形内容（`SkPicture`）按需栅格化为位图数据。该生成器支持自定义矩阵变换、绘制参数和表面属性，使得 Picture 可以像普通图像一样被使用，同时保持矢量内容的灵活性。

这个类是 Skia 图像系统中矢量到栅格转换的关键桥梁，让 `SkImage_Picture` 能够延迟栅格化，直到真正需要像素数据时才执行绘制操作。

## 架构位置

`SkPictureImageGenerator` 在 Skia 架构中的位置：

- **继承层次**：继承自 `SkImageGenerator` 抽象基类
- **所属模块**：`src/image/` 图像实现模块
- **服务对象**：主要为 `SkImage_Picture` 提供延迟栅格化能力
- **工厂函数**：通过 `SkImageGenerators::MakeFromPicture()` 创建
- **依赖关系**：依赖 `SkPicture`（矢量命令）和 `SkCanvas`（栅格化）

在图像生命周期中，该生成器充当 Picture 内容的"渲染器"，每次 `onGetPixels()` 调用都会重新绘制 Picture。

## 主要类与结构体

### SkPictureImageGenerator

从 Picture 生成像素的核心类。

**继承关系**：
```cpp
class SkPictureImageGenerator : public SkImageGenerator
```

**成员变量**：
- `fPicture`：`sk_sp<SkPicture>` - 保存的 Picture 命令序列
- `fMatrix`：`SkMatrix` - 应用到 Picture 的变换矩阵
- `fPaint`：`std::optional<SkPaint>` - 可选的绘制参数（如混合模式、透明度）
- `fProps`：`SkSurfaceProps` - 表面属性（如像素几何、抗锯齿设置）

**友元关系**：
```cpp
friend class SkImage_Picture;
```
允许 `SkImage_Picture` 访问私有成员。

### 工厂命名空间

`SkImageGenerators` 命名空间提供工厂函数：

```cpp
namespace SkImageGenerators {
    std::unique_ptr<SkImageGenerator> MakeFromPicture(
        const SkISize& size,
        sk_sp<SkPicture> picture,
        const SkMatrix* matrix,
        const SkPaint* paint,
        SkImages::BitDepth bitDepth,
        sk_sp<SkColorSpace> colorSpace,
        SkSurfaceProps props = {});
}
```

## 公共 API 函数

### SkImageGenerators::MakeFromPicture（两个重载）

**完整版本**：
```cpp
std::unique_ptr<SkImageGenerator> MakeFromPicture(
    const SkISize& size,
    sk_sp<SkPicture> picture,
    const SkMatrix* matrix,
    const SkPaint* paint,
    SkImages::BitDepth bitDepth,
    sk_sp<SkColorSpace> colorSpace,
    SkSurfaceProps props)
```

从 Picture 创建图像生成器。

**参数**：
- `size`：生成图像的尺寸
- `picture`：Picture 命令序列
- `matrix`：可选的变换矩阵（为 `nullptr` 时使用恒等矩阵）
- `paint`：可选的绘制参数（为 `nullptr` 时不应用额外绘制效果）
- `bitDepth`：位深度（`kU8` 或 `kF16`）
- `colorSpace`：目标颜色空间
- `props`：表面属性

**返回值**：成功返回生成器指针，失败返回 `nullptr`

**简化版本**（默认空 `SkSurfaceProps`）：
```cpp
std::unique_ptr<SkImageGenerator> MakeFromPicture(
    const SkISize& size,
    sk_sp<SkPicture> picture,
    const SkMatrix* matrix,
    const SkPaint* paint,
    SkImages::BitDepth bitDepth,
    sk_sp<SkColorSpace> colorSpace)
```

内部调用完整版本，传递空的 `SkSurfaceProps{}`。

### 构造函数

```cpp
SkPictureImageGenerator(const SkImageInfo& info,
                        sk_sp<SkPicture> picture,
                        const SkMatrix* matrix,
                        const SkPaint* paint,
                        const SkSurfaceProps& props)
```

内部构造函数，通过工厂函数间接调用。

**初始化逻辑**：
- 保存 Picture 智能指针
- 复制矩阵（如果提供）或初始化为恒等矩阵
- 复制 Paint（如果提供）或保持 `std::optional` 为空
- 保存表面属性

## 内部实现细节

### 像素生成流程

`onGetPixels()` 实现了核心的栅格化逻辑：

```cpp
bool SkPictureImageGenerator::onGetPixels(const SkImageInfo& info,
                                          void* pixels,
                                          size_t rowBytes,
                                          const Options& opts) {
    // 1. 创建直接映射到目标缓冲区的 Canvas
    std::unique_ptr<SkCanvas> canvas = SkCanvas::MakeRasterDirect(info, pixels, rowBytes, &fProps);
    if (!canvas) {
        return false;
    }

    // 2. 清空画布（透明黑色）
    canvas->clear(0);

    // 3. 绘制 Picture，应用变换矩阵和可选的 Paint
    canvas->drawPicture(fPicture, &fMatrix, SkOptAddressOrNull(fPaint));

    return true;
}
```

**关键步骤**：

1. **零拷贝栅格化**：使用 `MakeRasterDirect()` 直接在调用方提供的缓冲区上绘制，避免额外的内存分配和拷贝

2. **清空画布**：确保背景为透明（颜色值 0），避免 Picture 部分区域未绘制导致的脏像素

3. **应用变换**：通过矩阵参数缩放、旋转或平移 Picture 内容

4. **可选 Paint**：通过 `SkOptAddressOrNull(fPaint)` 智能处理 `std::optional<SkPaint>`：
   - 如果 `fPaint` 有值，返回指针
   - 如果为空，返回 `nullptr`

### 参数验证

工厂函数进行了严格的参数验证：

```cpp
if (!picture || !colorSpace || size.isEmpty()) {
    return nullptr;
}
```

拒绝以下情况：
- 空 Picture 指针
- 空颜色空间（必须明确指定）
- 空尺寸（宽度或高度为 0）

### 颜色类型选择

根据位深度选择颜色类型：

```cpp
SkColorType colorType = kN32_SkColorType;  // 默认 8 位
if (SkImages::BitDepth::kF16 == bitDepth) {
    colorType = kRGBA_F16_SkColorType;     // 高精度 16 位浮点
}
```

- **kN32_SkColorType**：平台相关的 32 位颜色（通常是 RGBA 或 BGRA）
- **kRGBA_F16_SkColorType**：每通道 16 位浮点，用于 HDR 或高精度场景

### Alpha 类型固定

```cpp
SkImageInfo info = SkImageInfo::Make(size, colorType, kPremul_SkAlphaType, ...);
```

始终使用 `kPremul_SkAlphaType`（预乘 Alpha），这是 Skia 绘制管线的标准格式。

### 表面属性应用

`fProps` 传递给 Canvas 创建：

```cpp
std::unique_ptr<SkCanvas> canvas = SkCanvas::MakeRasterDirect(info, pixels, rowBytes, &fProps);
```

表面属性控制：
- **像素几何**（`SkPixelGeometry`）：影响子像素文本渲染
- **使用设备独立字体**：影响字体渲染行为

### 矩阵处理

构造函数中的矩阵初始化：

```cpp
if (matrix) {
    fMatrix = *matrix;
} else {
    fMatrix.reset();  // 恒等矩阵
}
```

恒等矩阵意味着 Picture 按原始坐标绘制。

### Paint 处理

使用 `std::optional` 处理可选参数：

```cpp
if (paint) {
    fPaint = *paint;  // 复制构造
}
// 否则 fPaint 保持为空
```

绘制时通过辅助函数获取指针：

```cpp
canvas->drawPicture(fPicture, &fMatrix, SkOptAddressOrNull(fPaint));
```

`SkOptAddressOrNull()` 是处理 `std::optional` 的 Skia 工具函数。

## 依赖关系

### 核心依赖

| 依赖项 | 用途 |
|--------|------|
| `SkImageGenerator` | 基类，定义像素生成接口 |
| `SkPicture` | 矢量图形命令序列 |
| `SkCanvas` | 栅格化引擎 |
| `SkMatrix` | 几何变换 |
| `SkPaint` | 绘制参数 |

### 次要依赖

| 依赖项 | 用途 |
|--------|------|
| `SkImageInfo` | 图像格式描述 |
| `SkColorSpace` | 颜色空间管理 |
| `SkSurfaceProps` | 表面渲染属性 |
| `SkImageGeneratorPriv.h` | 内部辅助函数（如 `SkOptAddressOrNull`） |

### 反向依赖

| 依赖方 | 用途 |
|--------|------|
| `SkImage_Picture` | 使用该生成器实现延迟栅格化 |
| 图像工厂函数 | 通过 `SkImages::DeferredFromPicture()` 间接使用 |

## 设计模式与设计决策

### 策略模式（Strategy Pattern）

`SkPictureImageGenerator` 是 `SkImageGenerator` 的具体策略实现：

- **抽象策略**：`SkImageGenerator`
- **具体策略**：`SkPictureImageGenerator`（Picture 栅格化）、其他生成器（如编码图像解码器）
- **上下文**：`SkImage_Lazy` 使用生成器获取像素

### 桥接模式（Bridge Pattern）

将图像抽象（`SkImage`）与像素生成实现（`SkPictureImageGenerator`）分离：

- **抽象层**：`SkImage` 提供统一接口
- **实现层**：`SkPictureImageGenerator` 处理 Picture 特定逻辑

### 设计决策

**决策 1：每次重新绘制而非缓存**
- **原因**：Picture 可能包含动态内容或参数化绘制
- **权衡**：每次调用都重新绘制，性能较低但保证正确性
- **优化途径**：调用方可通过 `SkBitmapCache` 缓存结果

**决策 2：使用 `MakeRasterDirect()` 零拷贝**
- **原因**：避免分配临时缓冲区和像素拷贝
- **优点**：内存效率高，性能好
- **要求**：调用方必须提供正确对齐的缓冲区

**决策 3：必须提供颜色空间**
- **原因**：Picture 是矢量内容，没有"固有"颜色空间
- **权衡**：增加了 API 复杂性，但避免了颜色空间歧义

**决策 4：固定使用预乘 Alpha**
- **原因**：Skia 绘制管线标准格式
- **权衡**：不支持非预乘格式，但简化了实现

**决策 5：`std::optional<SkPaint>` 而非指针**
- **原因**：明确所有权，避免悬空指针
- **优点**：内存安全，值语义
- **缺点**：复制 Paint 对象（但 Paint 本身较小）

**决策 6：友元访问 `SkImage_Picture`**
```cpp
friend class SkImage_Picture;
```
- **原因**：`SkImage_Picture` 需要访问内部成员进行特定优化
- **权衡**：打破封装性，但简化了两个紧密耦合类之间的交互

## 性能考量

### 栅格化开销

**每次调用都重新绘制**：
```cpp
canvas->drawPicture(fPicture, &fMatrix, SkOptAddressOrNull(fPaint));
```

对于复杂的 Picture，这可能是昂贵的操作。性能取决于：
- Picture 的命令数量
- 绘制的图形复杂度（路径、文本、图像）
- 目标尺寸（更大的尺寸需要更多像素填充）

### 内存效率

**零拷贝设计**：
- 直接在目标缓冲区绘制，无中间缓冲区
- Picture 本身通过智能指针共享，不重复占用内存

**缓存建议**：
生成器本身不缓存，依赖调用方：
```cpp
// SkImage_Lazy 会通过 SkBitmapCache 缓存结果
SkBitmap bm;
if (this->getROPixels(ctx, &bm, SkImage::kAllow_CachingHint)) {
    // 缓存命中或新生成后已缓存
}
```

### 矩阵变换成本

`fMatrix` 应用在 Picture 绘制时：
- 简单变换（平移、缩放）：开销小
- 复杂变换（旋转、透视）：增加计算量
- 所有 Picture 内的路径和坐标都会经过变换

### 表面属性影响

`fProps` 影响文本渲染质量：
- **子像素抗锯齿**：更高质量但计算更慢
- **设备无关字体**：可能触发不同的字体缓存路径

### 优化建议

1. **缓存生成器结果**：对于静态 Picture，缓存第一次生成的位图
2. **预缩放 Picture**：如果目标尺寸已知，创建生成器时指定合适的尺寸和矩阵
3. **避免频繁像素访问**：尽量复用 `SkImage` 对象而非重复调用 `getPixels()`
4. **考虑 GPU 加速**：对于动态或大尺寸 Picture，GPU 渲染可能更快（但当前实现是 CPU 栅格化）

### 性能测量

关键瓶颈：
- **Picture 绘制**：占绝大部分时间
- **Canvas 创建**：轻量级操作，开销可忽略
- **清空画布**：线性时间，对大尺寸图像有影响

对于 1000×1000 的图像，`canvas->clear(0)` 需要清空 4MB 数据（RGBA32）。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `include/core/SkImageGenerator.h` | 基类 | 图像生成器抽象接口 |
| `src/image/SkImage_Picture.h` | 主要使用方 | 基于 Picture 的图像实现 |
| `include/core/SkPicture.h` | 核心依赖 | 矢量图形命令序列 |
| `include/core/SkCanvas.h` | 栅格化引擎 | 执行 Picture 绘制 |
| `include/core/SkMatrix.h` | 几何变换 | 变换矩阵支持 |
| `include/core/SkPaint.h` | 绘制参数 | 控制绘制效果 |
| `include/core/SkSurfaceProps.h` | 表面属性 | 控制渲染行为 |
| `src/image/SkImageGeneratorPriv.h` | 内部工具 | 辅助函数如 `SkOptAddressOrNull` |
| `src/image/SkImage_Base.h` | 图像基类 | 图像实现框架 |
| `src/core/SkBitmapCache.h` | 缓存系统 | 缓存生成的像素数据 |
