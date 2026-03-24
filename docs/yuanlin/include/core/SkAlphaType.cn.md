# SkAlphaType

> 源文件: `include/core/SkAlphaType.h`

## 概述

SkAlphaType 是描述像素 Alpha 通道语义的枚举类型,定义了如何解释像素的透明度信息。它区分了不透明、预乘 Alpha 和非预乘 Alpha 三种核心状态,直接影响混合运算的正确性和性能,是 Skia 颜色处理系统的基础类型之一。

## 架构位置

SkAlphaType 位于 Skia 核心类型系统中,与 SkColorType 处于同一层级,共同描述像素的完整语义。它被 SkImageInfo、SkBitmap、SkPixmap 等类使用,是正确执行 Alpha 混合和颜色转换的前提条件。该类型影响从图像解码、颜色转换到最终混合渲染的整个流程。

## 枚举定义

### SkAlphaType

```cpp
enum SkAlphaType : int {
    kUnknown_SkAlphaType,    // 未初始化状态
    kOpaque_SkAlphaType,     // 像素不透明
    kPremul_SkAlphaType,     // 预乘 Alpha
    kUnpremul_SkAlphaType,   // 非预乘 Alpha
    kLastEnum_SkAlphaType = kUnpremul_SkAlphaType
};
```

**枚举值详解**:

| 枚举值 | 数值位置 | 含义 | Alpha 值约束 | RGB 存储方式 |
|--------|---------|------|-------------|-------------|
| kUnknown_SkAlphaType | 0 | 未初始化或无效 | N/A | N/A |
| kOpaque_SkAlphaType | 1 | 完全不透明 | Alpha = 1.0 (或最大值) | 独立存储 |
| kPremul_SkAlphaType | 2 | 预乘 Alpha | 任意 [0.0, 1.0] | RGB *= Alpha |
| kUnpremul_SkAlphaType | 3 | 非预乘 Alpha | 任意 [0.0, 1.0] | RGB 独立存储 |

## Alpha 类型详解

### kOpaque_SkAlphaType (不透明)

**语义**:
- 像素完全不透明,Alpha 通道无意义或被忽略
- 即使 SkColorType 包含 Alpha 通道,也假定为最大值(1.0 或 255)

**适用场景**:
- JPEG 图像(无透明度)
- RGB 格式(如 kRGB_888x_SkColorType)
- 已知不含透明像素的图像

**性能优势**:
- 混合运算可简化为直接覆盖
- 无需读取目标像素
- GPU 可使用快速路径

**风险**:
如果声明为 Opaque 但实际包含 Alpha < 1.0 的像素,渲染结果未定义。

### kPremul_SkAlphaType (预乘 Alpha)

**数学定义**:
存储的颜色 = 原始颜色 × Alpha
```
stored_R = original_R * Alpha
stored_G = original_G * Alpha
stored_B = original_B * Alpha
stored_A = Alpha
```

**混合公式**:
```
result = src + dst * (1 - src.A)
```

**优势**:
- **性能最优**: 混合公式最简单,减少运算
- **数值稳定**: 避免除法运算
- **硬件支持**: 大多数 GPU 默认使用预乘 Alpha

**劣势**:
- 精度损失: 低 Alpha 值时 RGB 信息丢失
- 不可逆: 无法完全恢复原始颜色

**最佳实践**:
- Skia 推荐的默认格式
- 适用于大多数渲染场景

### kUnpremul_SkAlphaType (非预乘 Alpha)

**数学定义**:
存储的颜色 = 原始颜色(RGB 与 Alpha 独立)
```
stored_R = original_R
stored_G = original_G
stored_B = original_B
stored_A = Alpha
```

**混合公式**:
```
result = src * src.A + dst * (1 - src.A)
```

**优势**:
- **无损编辑**: 保留原始 RGB 信息
- **颜色调整**: 可独立修改 Alpha 不影响 RGB
- **格式兼容**: 某些图像格式(如 PNG)原生使用

**劣势**:
- **性能开销**: 混合时需要额外乘法
- **除法风险**: 转换为预乘时需要除以 Alpha

**适用场景**:
- 图像编辑应用
- 需要保留原始颜色的场景
- 与外部系统交互(如 Web 标准)

### kUnknown_SkAlphaType

**用途**:
- 错误状态标记
- 未初始化的 SkImageInfo
- 不应用于实际像素数据

## 辅助函数

### SkAlphaTypeIsOpaque

```cpp
static inline bool SkAlphaTypeIsOpaque(SkAlphaType at) {
    return kOpaque_SkAlphaType == at;
}
```

**功能**: 快速检查 Alpha 类型是否为不透明

**使用场景**:
- 优化混合路径选择
- 验证图像格式一致性
- 跳过不必要的 Alpha 处理

**示例**:
```cpp
if (SkAlphaTypeIsOpaque(imageInfo.alphaType())) {
    // 使用快速覆盖路径,无需混合
    canvas->drawBitmap(bitmap, x, y);
} else {
    // 需要 Alpha 混合
    canvas->drawBitmap(bitmap, x, y, &paint);
}
```

## 内部实现细节

### Alpha 混合数学

**简单混合 (Simple Blending)**:
```
new_color = draw_color * alpha + destination_color * (1 - alpha)
```

**预乘 Alpha 的优化**:
预乘格式下,draw_color 已包含 alpha 因子,混合简化为:
```
new_color = premul_src_color + dst_color * (1 - src_alpha)
```
节省了 3 次乘法(R, G, B 各一次)。

### 颜色转换

**预乘 → 非预乘**:
```cpp
if (alpha > 0) {
    R = premul_R / alpha;
    G = premul_G / alpha;
    B = premul_B / alpha;
} else {
    R = G = B = 0; // 或保持原值
}
```
风险: 除以零和精度损失

**非预乘 → 预乘**:
```cpp
premul_R = unpremul_R * alpha;
premul_G = unpremul_G * alpha;
premul_B = unpremul_B * alpha;
```
安全且无精度问题

## 依赖关系

### 依赖的模块

该头文件无外部依赖,是纯枚举定义。

### 被依赖的模块

SkAlphaType 被几乎所有图像处理模块使用:
- **SkImageInfo**: 描述图像的 Alpha 语义
- **SkBitmap/SkPixmap**: 像素缓冲区的 Alpha 解释
- **SkCodec**: 解码器根据格式设置 AlphaType
- **SkCanvas**: 绘制时处理 Alpha 混合
- **GPU 后端**: 选择混合模式和纹理格式

## 设计模式与设计决策

### 预乘 Alpha 作为默认选择

Skia 强烈推荐使用 kPremul_SkAlphaType:
- **历史原因**: 大多数图形系统采用预乘 Alpha
- **性能驱动**: GPU 硬件优化预乘格式
- **数学简洁**: Porter-Duff 合成公式更简单

### 类型安全设计

使用强类型枚举避免:
- 隐式整数转换
- 与其他枚举混淆
- 无效值传递

### 最小化枚举集

只定义真正必要的状态:
- Opaque: 特殊优化路径
- Premul: 标准高性能路径
- Unpremul: 兼容性和精确性需求

## 性能考量

### 混合性能对比

| Alpha 类型 | 混合复杂度 | GPU 支持 | 内存带宽 |
|-----------|----------|---------|---------|
| Opaque | 最低(直接覆盖) | 最优 | 最低 |
| Premul | 低(3 乘法 + 3 加法) | 优秀 | 中等 |
| Unpremul | 高(6 乘法 + 3 加法) | 需转换 | 中等 |

### 转换成本

**运行时转换开销**:
- Premul → Unpremul: 高(需要除法)
- Unpremul → Premul: 中(只需乘法)
- 任意 → Opaque: 低(设置 Alpha = 1.0)

**建议**: 在加载时转换为目标格式,避免运行时转换。

### GPU 优化

现代 GPU 硬件混合单元假定预乘 Alpha:
- 使用 Unpremul 需要额外的着色器指令
- Opaque 可禁用混合,直接写入

## 常见陷阱与最佳实践

### 陷阱 1: 错误的 Opaque 声明

```cpp
// 错误: PNG 可能包含透明像素
SkImageInfo info = SkImageInfo::Make(width, height,
    kRGBA_8888_SkColorType, kOpaque_SkAlphaType);
// 如果 PNG 实际有透明度,渲染结果不正确
```

### 陷阱 2: 预乘精度损失

```cpp
// Alpha 很小时,RGB 信息丢失
SkColor color = SkColorSetARGB(1, 255, 0, 0); // 几乎透明的红色
// 预乘后: R ≈ 1, 原始 255 信息丢失
```

### 最佳实践 1: 格式匹配

```cpp
SkImageInfo info;
if (codec->getInfo().alphaType() == kOpaque_SkAlphaType) {
    info = codec->getInfo(); // 保持 Opaque
} else {
    info = codec->getInfo().makeAlphaType(kPremul_SkAlphaType); // 转为预乘
}
```

### 最佳实践 2: 显式转换

```cpp
SkBitmap premulBitmap;
if (unpremulBitmap.readPixels(
    premulBitmap.info().makeAlphaType(kPremul_SkAlphaType),
    premulBitmap.getPixels(), premulBitmap.rowBytes(), 0, 0)) {
    // 成功转换为预乘格式
}
```

## 与其他图形系统的对比

| 系统 | 默认格式 | 术语 |
|------|---------|------|
| Skia | Premultiplied | kPremul_SkAlphaType |
| Core Graphics (macOS/iOS) | Premultiplied | kCGImageAlphaPremultipliedLast |
| Direct2D (Windows) | Premultiplied | D2D1_ALPHA_MODE_PREMULTIPLIED |
| HTML Canvas | Premultiplied | "premultiply" |
| OpenGL | Premultiplied | GL_ONE, GL_ONE_MINUS_SRC_ALPHA |

**结论**: 预乘 Alpha 是行业标准。

## 相关文件

| 文件 | 关系 |
|------|------|
| include/core/SkColorType.h | 配合描述像素格式 |
| include/core/SkImageInfo.h | 使用 AlphaType 描述图像 |
| include/core/SkColor.h | 颜色表示,涉及 Alpha 处理 |
| src/core/SkPixelRef.h | 像素数据的 Alpha 语义 |
| include/core/SkCanvas.h | 根据 AlphaType 执行混合 |
