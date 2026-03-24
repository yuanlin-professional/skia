# SkEncodedInfo

> 源文件: `include/private/SkEncodedInfo.h`

## 概述

`SkEncodedInfo` 是 Skia 图像编解码系统中的核心元数据结构体，负责描述编码图像的像素格式、颜色空间、透明度类型、色彩深度等关键信息。它为图像解码器提供统一的接口，用于表示各种图像格式(PNG、JPEG、WEBP、GIF 等)的编码特征，并为后续的解码过程提供必要的格式转换建议。

## 架构位置

该结构体位于 Skia 的私有头文件目录 `include/private/` 中，属于图像编解码子系统的核心层。它在解码器(Codec)层和图像信息(ImageInfo)层之间起桥梁作用，将底层编码格式的原始信息转换为 Skia 内部使用的标准化描述。

## 主要枚举类型

### Alpha

定义图像的透明度类型：

| 枚举值 | 说明 |
|--------|------|
| `kOpaque_Alpha` | 完全不透明，无 Alpha 通道 |
| `kUnpremul_Alpha` | 未预乘的 Alpha 通道 |
| `kBinary_Alpha` | 二值透明度，每个像素要么完全透明要么完全不透明 |

### Color

定义图像的颜色格式，支持多种编码标准：

| 枚举值 | 支持格式 | 说明 |
|--------|----------|------|
| `kGray_Color` | PNG, WBMP | 灰度图像 |
| `kGrayAlpha_Color` | PNG | 灰度+透明度 |
| `kXAlpha_Color` | PNG | 特殊的 Alpha 格式，忽略灰度分量 |
| `k565_Color` | PNG | RGB565 格式(5-6-5 位分配) |
| `kPalette_Color` | PNG, GIF, BMP | 调色板索引色 |
| `kRGB_Color` | PNG, RAW | 标准 RGB 格式 |
| `kRGBA_Color` | PNG, RAW | RGB + Alpha |
| `kBGR_Color` | BMP | BGR 字节序 |
| `kBGRX_Color` | BMP | BGR + 未使用的 X 通道 |
| `kBGRA_Color` | BMP | BGR + Alpha |
| `kYUV_Color` | JPEG, WEBP | YUV 颜色空间 |
| `kYUVA_Color` | WEBP | YUV + Alpha |
| `kInvertedCMYK_Color` | JPEG | 反转 CMYK(Photoshop 标准) |
| `kYCCK_Color` | JPEG | YCCK 颜色空间 |

## 主要成员变量

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fWidth` | `int` | 图像宽度(像素) |
| `fHeight` | `int` | 图像高度(像素) |
| `fColor` | `Color` | 颜色格式枚举 |
| `fAlpha` | `Alpha` | 透明度类型枚举 |
| `fBitsPerComponent` | `uint8_t` | 每个颜色分量的位数 |
| `fColorDepth` | `uint8_t` | RGB 通道的实际色彩深度 |
| `fColorProfile` | `std::unique_ptr<const SkCodecs::ColorProfile>` | 嵌入的 ICC 色彩配置文件 |
| `fHdrMetadata` | `skhdr::Metadata` | HDR 元数据信息 |

## 公共 API 函数

### 静态工厂方法

#### `Make(int width, int height, Color color, Alpha alpha, int bitsPerComponent)`
- **功能**: 创建基础的 `SkEncodedInfo` 对象
- **参数**:
  - `width`, `height`: 图像尺寸
  - `color`: 颜色格式
  - `alpha`: 透明度类型
  - `bitsPerComponent`: 每分量位数(通常为 8 或 16)
- **返回值**: 按值返回构造的对象

#### `Make(..., std::unique_ptr<SkCodecs::ColorProfile> profile)`
- **功能**: 创建带色彩配置文件的对象
- **参数**: 额外接受 ICC 色彩配置文件指针
- **返回值**: 包含色彩配置的完整对象

#### `Make(..., int colorDepth)`
- **功能**: 创建指定色彩深度的对象
- **说明**: 用于支持非标准位深度的图像格式

#### `Make(..., const skhdr::Metadata& hdrMetadata)`
- **功能**: 创建包含 HDR 元数据的对象
- **说明**: 支持 HDR 图像的动态范围和色调映射信息

### 访问器方法

#### `makeImageInfo() const`
- **功能**: 生成推荐的 `SkImageInfo` 对象
- **说明**: 根据编码信息推断最优的解码目标格式
- **返回值**: 建议使用的 `SkImageInfo`

#### `bitsPerPixel() const`
- **功能**: 计算每像素总位数
- **实现**: 根据颜色格式和每分量位数计算
  - 灰度: `fBitsPerComponent`
  - 灰度+Alpha: `2 * fBitsPerComponent`
  - RGB: `3 * fBitsPerComponent`
  - RGBA/CMYK: `4 * fBitsPerComponent`
- **返回值**: `uint8_t` 类型的位数

#### `profile() const`
- **功能**: 获取底层的 `skcms_ICCProfile` 指针
- **说明**: 用于与 skcms 颜色管理库交互
- **返回值**: 指向 ICC 配置文件的常量指针，可能为 `nullptr`

#### `profileData() const`
- **功能**: 序列化色彩配置文件数据
- **返回值**: 包含配置文件原始字节的 `SkData` 智能指针

#### `getColorDepth() const`
- **功能**: 获取 R/G/B 通道的色彩深度
- **返回值**: 实际使用的位深度(可能与 `bitsPerComponent` 不同)

#### `getHdrMetadata() const`
- **功能**: 获取 HDR 元数据
- **说明**: 即使 SDR 图像也可能包含 HDR 元数据用于逆向色调映射
- **返回值**: `skhdr::Metadata` 的常量引用

### 特殊成员函数

#### `SkEncodedInfo(const SkEncodedInfo&) = delete`
- **说明**: 禁止拷贝构造，防止意外复制大型对象

#### `SkEncodedInfo(SkEncodedInfo&& orig)`
- **说明**: 支持移动构造，允许高效的所有权转移

#### `copy() const`
- **功能**: 显式深拷贝方法
- **说明**: 需要拷贝时必须显式调用，避免隐式复制

## 内部实现细节

### 颜色格式验证

`VerifyColor` 静态方法在构造时验证格式组合的合法性：

1. **灰度图必须不透明**: `kGray_Color` 要求 `kOpaque_Alpha`
2. **灰度+Alpha 必须有透明度**: `kGrayAlpha_Color` 要求非 `kOpaque_Alpha`
3. **调色板不支持 16 位**: `kPalette_Color` 禁止 `bitsPerComponent == 16`
4. **RGB 系列要求至少 8 位**: `kRGB_Color`, `kBGR_Color` 等要求 `bitsPerComponent >= 8`
5. **YUV/CMYK 必须 8 位**: 这些格式固定使用 8 位分量
6. **特殊格式约束**: `kXAlpha_Color` 必须是未预乘且 8 位

### 像素位数计算

`bitsPerPixel()` 方法通过 switch-case 为每种颜色格式计算准确的位数：
- 调色板格式返回索引位数(而非展开后的 RGB 位数)
- BGRX 格式计算 4 个分量(即使 X 未使用)
- 所有 CMYK 和 YCCK 格式按 4 分量计算

### 移动语义

类型支持移动构造和移动赋值，避免拷贝 `std::unique_ptr<ColorProfile>` 指针，确保色彩配置文件的唯一所有权。

## 依赖关系

### 依赖的模块

| 依赖 | 用途 |
|------|------|
| `SkImageInfo` | 目标解码格式的表示 |
| `SkColorSpace` | 色彩空间管理 |
| `SkCodecs::ColorProfile` | ICC 配置文件封装 |
| `skcms` | 颜色管理库，处理 ICC 配置文件 |
| `SkHdrMetadata` | HDR 图像元数据结构 |
| `SkData` | 配置文件数据的存储 |

### 被依赖的模块

`SkEncodedInfo` 被以下解码器使用：
- PNG 解码器: 解析 PNG 块头信息
- JPEG 解码器: 处理 JPEG 颜色空间(YUV/CMYK)
- WEBP 解码器: 处理 WEBP 的 VP8/VP8L 格式
- GIF 解码器: 处理调色板和透明度
- BMP 解码器: 处理各种 BMP 变体(RGB/BGR/压缩)
- RAW 解码器: 处理相机原始格式

## 设计模式与设计决策

### 值语义设计

尽管包含 `std::unique_ptr`，但提供显式的 `copy()` 方法而非隐式拷贝构造：
- **优点**: 避免意外的深拷贝开销，使所有权转移意图明确
- **适用场景**: 解码器构造对象后通常直接移动给调用者

### 枚举驱动的多态

使用 `Color` 和 `Alpha` 枚举而非继承层次：
- **优点**: 轻量级，无虚函数开销，适合频繁创建
- **缺点**: 添加新格式需要修改枚举和 switch 语句

### CMYK 特殊处理

JPEG CMYK 格式被标记为 `kInvertedCMYK_Color`：
- **原因**: Photoshop 在 JPEG 中写入反转的 CMYK(零表示 100% 墨水覆盖)
- **兼容性**: 虽然可能破坏其他应用，但 Web 上的 CMYK JPEG 遵循此约定

### HDR 元数据集成

即使 SDR 图像也支持 HDR 元数据：
- **目的**: 存储逆向色调映射信息，用于在 HDR 显示器上正确显示
- **标准**: 支持 SMPTE ST 2086 和 CTA-861.3 标准

## 性能考量

### 移动优化

构造函数和赋值运算符支持移动语义，避免拷贝 `unique_ptr` 和 `ColorProfile` 对象。解码器通常通过 `std::move` 返回对象。

### 内联访问器

简单的 getter 方法(如 `width()`, `height()`)声明为内联，编译器可将其优化为直接内存访问。

### 缓存 bitsPerPixel

虽然 `bitsPerPixel()` 是计算方法，但逻辑简单，编译器可内联并消除 switch 分支。对于性能关键路径，调用者可缓存结果。

### 色彩配置文件惰性解析

`ColorProfile` 使用 `unique_ptr` 存储，仅在需要时解析和分配。对于不使用色彩管理的解码路径，避免了解析开销。

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkImageInfo.h` | 目标格式定义，`makeImageInfo()` 返回此类型 |
| `include/core/SkColorSpace.h` | 色彩空间的高层抽象 |
| `include/private/SkHdrMetadata.h` | HDR 元数据结构定义 |
| `modules/skcms/skcms.h` | 底层色彩管理库接口 |
| `src/codec/SkPngCodec.cpp` | PNG 解码器实现，构造 `SkEncodedInfo` |
| `src/codec/SkJpegCodec.cpp` | JPEG 解码器，处理 YUV/CMYK 格式 |
| `src/codec/SkWebpCodec.cpp` | WEBP 解码器实现 |
