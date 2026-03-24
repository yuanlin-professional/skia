# TextureFormat

> 源文件: src/gpu/graphite/TextureFormat.h, src/gpu/graphite/TextureFormat.cpp

## 概述

`TextureFormat` 是 Skia Graphite 渲染架构中定义 GPU 纹理格式的核心枚举类型。该枚举封装了 Graphite 所有后端（Metal、Vulkan、Dawn）支持的颜色、深度和模板纹理格式的统一表示。`TextureFormat` 提供了跨后端的格式抽象，并配套了一系列辅助函数用于格式查询、转换以及与 `SkColorType` 的映射。

该模块负责纹理格式的命名规范、属性查询（如字节大小、通道掩码、压缩类型）、以及 CPU 和 GPU 数据表示之间的转换逻辑。它是 Graphite 纹理系统的基础组件，被纹理创建、数据上传、渲染目标配置等所有涉及纹理格式的操作使用。

## 架构位置

`TextureFormat` 在 Graphite 架构中的位置：

```
Graphite 纹理系统：
  ├── SkColorType（CPU 侧颜色表示）
  │   └── TextureFormat（GPU 侧格式表示）★
  │       ├── 格式属性查询
  │       ├── 压缩类型映射
  │       ├── 颜色类型兼容性
  │       └── Swizzle 计算
  ├── TextureInfo（后端无关的纹理描述）
  ├── Caps（后端能力查询，格式支持检测）
  └── 后端实现：
      ├── Metal: MTLPixelFormat
      ├── Vulkan: VkFormat
      └── Dawn: wgpu::TextureFormat
```

## 主要类与结构体

### TextureFormat 枚举

```cpp
enum class TextureFormat : uint8_t {
    kUnsupported,
    // 1 通道
    kR8, kR16, kR16F, kR32F, kA8,
    // 2 通道
    kRG8, kRG16, kRG16F, kRG32F,
    // 3 通道
    kRGB8, kBGR8, kB5_G6_R5, kR5_G6_B5, kRGB16, kRGB16F, kRGB32F,
    kRGB8_sRGB, kBGR10_XR,
    // 4 通道
    kRGBA8, kRGBA16, kRGBA16F, kRGBA32F, kRGB10_A2, kRGBA10x6,
    kRGBA8_sRGB, kBGRA8, kBGR10_A2, kBGRA8_sRGB, kABGR4, kARGB4, kBGRA10x6_XR,
    // 压缩格式
    kRGB8_ETC2, kRGB8_ETC2_sRGB, kRGB8_BC1, kRGBA8_BC1, kRGBA8_BC1_sRGB,
    // 多平面格式
    kYUV8_P2_420, kYUV8_P3_420, kYUV10x6_P2_420,
    kExternal,
    // 深度/模板格式
    kS8, kD16, kD32F, kD24_S8, kD32F_S8,
    kLast = kD32F_S8
};
```

### FormatXferOp 枚举

```cpp
enum class FormatXferOp : uint8_t {
    kIdentity  = 0x0, // 无需额外转换
    kSwapRB    = 0x1, // 交换 RB 通道
    kDropAlpha = 0x2, // 丢弃/填充 alpha 通道
    kDisabled  = 0x4, // 禁用数据传输
};
SK_MAKE_BITMASK_OPS(FormatXferOp)
```

### 命名规范

**通道顺序**: 小端序（内存中的字节顺序）
**位深度表示**:
- `n`: n 位无符号归一化整数 [0,1]
- `nF`: n 位浮点数
- `_`: 分隔不同位深度的组件

**行为标签**:
- `_sRGB`: 硬件 sRGB 解码/编码
- `_XR`: 扩展范围格式
- `_ETC2` / `_BC1`: 压缩算法

**示例**:
- `kR8`: 8 位单通道红色，归一化到 [0,1]
- `kRGBA16F`: 4 通道，每通道 16 位浮点数
- `kRGB10_A2`: RGB 各 10 位，Alpha 2 位，打包为 32 位
- `kD24_S8`: 24 位深度 + 8 位模板

## 公共 API 函数

### 格式属性查询

```cpp
const char* TextureFormatName(TextureFormat);
```
返回格式的字符串名称（如 "RGBA8"）。

```cpp
int TextureFormatBytesPerBlock(TextureFormat);
```
返回每个像素或压缩块的字节大小。对于压缩格式，返回压缩块大小（如 BC1 为 8 字节）。

```cpp
uint32_t TextureFormatChannelMask(TextureFormat);
```
返回通道掩码（`SkColorChannelFlag` 的位或组合），指示格式包含哪些通道。

```cpp
bool TextureFormatIsDepthOrStencil(TextureFormat);
bool TextureFormatHasDepth(TextureFormat);
bool TextureFormatHasStencil(TextureFormat);
```
查询格式是否为深度/模板格式。

```cpp
bool TextureFormatIsMultiplanar(TextureFormat);
```
查询格式是否为多平面格式（如 YUV）。

```cpp
bool TextureFormatAutoClamps(TextureFormat);
```
查询写入颜色附件时是否自动钳制到 [0,1]。浮点格式和扩展范围格式不自动钳制。

```cpp
bool TextureFormatIsFloatingPoint(TextureFormat);
```
查询格式是否为浮点格式。

### 压缩格式支持

```cpp
SkTextureCompressionType TextureFormatCompressionType(TextureFormat);
```
返回压缩格式类型，非压缩格式返回 `kNone`。

```cpp
TextureFormat CompressionTypeToTextureFormat(SkTextureCompressionType);
```
从 Skia 压缩类型转换为 `TextureFormat`。

### SkColorType 与 TextureFormat 转换

```cpp
SkSpan<const TextureFormat> PreferredTextureFormats(SkColorType);
```
返回给定 `SkColorType` 的首选纹理格式列表，按兼容性从高到低排序：
1. 精确匹配（无需 swizzle 或 CPU 操作）
2. 无损且无语义差异（需要 CPU 操作如交换 RB，但无需 swizzle）
3. 无损但有语义差异（需要 swizzle，可能需要 CPU 操作）
4. 有损或数据不匹配（最后的选择）

```cpp
std::pair<SkColorType, SkEnumBitMask<FormatXferOp>>
TextureFormatColorTypeInfo(TextureFormat);
```
返回给定格式的最佳匹配 `SkColorType` 和所需的额外数据操作。

```cpp
bool AreColorTypeAndFormatCompatible(SkColorType, TextureFormat);
```
查询颜色类型和格式是否兼容。

### Swizzle 计算

```cpp
Swizzle ReadSwizzleForColorType(SkColorType, TextureFormat);
```
返回从纹理采样或读回时使用的 swizzle。

**处理的语义**:
- 灰度映射到 `rrra`
- 红色通道 vs alpha 通道映射
- 强制不透明（RGB1）

```cpp
std::optional<Swizzle> WriteSwizzleForColorType(SkColorType, TextureFormat);
```
返回写入 surface 时使用的 swizzle。返回 `nullopt` 表示颜色类型无法渲染到该格式。

**限制**:
- 不支持灰度计算（超出 swizzle 能力）
- 不支持强制不透明（无法保证目标 alpha 值）

## 内部实现细节

### 格式字节大小计算

**未压缩格式**:
```cpp
case TF::kRGBA8:  return 4;  // 4 字节/像素
case TF::kRGBA16F: return 8;  // 8 字节/像素
case TF::kRGB32F: return 12;  // 12 字节/像素
```

**压缩格式**:
```cpp
case TF::kRGB8_ETC2:
case TF::kRGBA8_BC1:
    return 8;  // 8 字节/块（4x4 像素）
```

**多平面格式**（估算）:
```cpp
case TF::kYUV8_P2_420: return 3;  // 过估算，实际计算需要特殊查询
```

### 通道掩码实现

```cpp
uint32_t TextureFormatChannelMask(TextureFormat format) {
    switch (format) {
        case TF::kA8:    return kAlpha_SkColorChannelFlag;
        case TF::kR8:    return kRed_SkColorChannelFlag;
        case TF::kRG8:   return kRG_SkColorChannelFlags;
        case TF::kRGB8:  return kRGB_SkColorChannelFlags;
        case TF::kRGBA8: return kRGBA_SkColorChannelFlags;
        // ...
    }
}
```

### 读取 Swizzle 计算

```cpp
Swizzle ReadSwizzleForColorType(SkColorType ct, TextureFormat format) {
    if (SkColorTypeIsAlphaOnly(ct)) {
        if (formatChannels == kAlpha_SkColorChannelFlag) {
            return Swizzle::RGBA();  // 硬件自动处理
        } else if (formatChannels & kAlpha_SkColorChannelFlag) {
            return Swizzle("000a");  // 从 alpha 通道读取
        } else {
            return Swizzle("000r");  // 从红色通道读取
        }
    } else {
        Swizzle swizzle = (colorChannels & kGray_SkColorChannelFlag)
                          ? Swizzle::RRRA()  // 灰度映射
                          : Swizzle::RGBA(); // 正常 RGBA
        if (!(colorChannels & kAlpha_SkColorChannelFlag) &&
             (formatChannels & kAlpha_SkColorChannelFlag)) {
            swizzle = Swizzle::Concat(swizzle, Swizzle::RGB1());  // 强制不透明
        }
        return swizzle;
    }
}
```

### 写入 Swizzle 计算

```cpp
std::optional<Swizzle> WriteSwizzleForColorType(SkColorType ct, TextureFormat format) {
    // 深度/模板、压缩、外部、多平面格式不可渲染
    if (format == TextureFormat::kExternal ||
        TextureFormatIsDepthOrStencil(format) ||
        TextureFormatIsMultiplanar(format) ||
        TextureFormatCompressionType(format) != SkTextureCompressionType::kNone) {
        return std::nullopt;
    }

    if (SkColorTypeIsAlphaOnly(ct)) {
        if (formatChannels == kAlpha_SkColorChannelFlag) {
            return Swizzle::RGBA();
        } else if (formatChannels & kAlpha_SkColorChannelFlag) {
            return Swizzle("000a");  // 写入 alpha 通道
        } else {
            return Swizzle("a000");  // 写入红色通道
        }
    } else {
        if (((colorChannels & formatChannels) != formatChannels) ||
            (colorChannels & kGray_SkColorChannelFlag)) {
            return std::nullopt;  // 不兼容
        }
        return Swizzle::RGBA();
    }
}
```

### 颜色类型和格式的映射表

```cpp
SkSpan<const TextureFormat> PreferredTextureFormats(SkColorType ct) {
    switch (ct) {
        case kAlpha_8_SkColorType:
            return {TF::kR8};  // Alpha 映射到红色通道
        case kRGBA_8888_SkColorType:
            return {TF::kRGBA8, TF::kBGRA8};  // 优先 RGBA，备选 BGRA
        case kBGRA_8888_SkColorType:
            return {TF::kBGRA8, TF::kRGBA8};  // 优先 BGRA，备选 RGBA
        case kRGBA_F16_SkColorType:
            return {TF::kRGBA16F};
        // ...
    }
}
```

### 特殊格式处理

**ARGB_4444 特殊情况**:
```cpp
// kARGB_4444_SkColorType 实际上是 ABGR 顺序
if (ct == kARGB_4444_SkColorType && format == TextureFormat::kARGB4) {
    return Swizzle::BGRA();  // 需要交换 RB
}
```

**RGB_565 特殊情况**:
```cpp
// kRGB_565_SkColorType 实际上是 B5G6R5 顺序
CASE(kRGB_565_SkColorType, TF::kB5_G6_R5, TF::kR5_G6_B5)
```

## 依赖关系

### 内部依赖

| 依赖 | 用途 |
|------|------|
| `SkColorType` | CPU 侧颜色表示 |
| `SkTextureCompressionType` | Skia 的压缩类型枚举 |
| `Swizzle` | 通道重排逻辑 |
| `SkColorChannelFlag` | 通道掩码标志 |

### 外部依赖

| 依赖 | 用途 |
|------|------|
| Skia Core | 颜色类型定义 |
| `SkImageInfoPriv` | 颜色类型属性查询 |

### 被依赖情况

| 依赖者 | 用途 |
|--------|------|
| `TextureInfo` | 描述纹理格式 |
| `Caps` | 查询后端格式支持 |
| `TextureProxy` | 纹理创建 |
| `TextureUtils` | 数据上传和读回 |
| `Swizzle` | 通道重排计算 |

## 设计模式与设计决策

### 枚举类设计

使用 `enum class` 而非普通枚举：
- 类型安全，防止隐式转换
- 避免命名空间污染
- 使用 `uint8_t` 存储，节省内存

### 查询表模式

所有格式属性通过 switch 语句实现，编译器可以生成高效的跳转表。

### 转换策略分离

CPU 和 GPU 数据转换分为两层：
1. **硬件层**（Swizzle）: GPU 自动处理的通道重排
2. **软件层**（FormatXferOp）: CPU 需要执行的数据操作

### 兼容性优先级

格式列表按兼容性排序：
1. 精确匹配（最高效）
2. 无损转换（需要 CPU 操作）
3. 语义转换（需要 Swizzle）
4. 有损匹配（最后选择）

### 关键设计决策

1. **统一格式枚举**: 跨后端的统一格式表示，后端负责映射
2. **命名规范**: 小端序命名，位深度后缀，行为标签
3. **通道掩码**: 使用位掩码表示通道，高效查询
4. **Swizzle 最小化**: 只处理 alpha/red 映射和强制不透明，硬件处理 RGB/BGR
5. **禁用标志**: 某些格式（如压缩、多平面）禁用 CPU 数据传输

## 性能考量

### 内存占用

- 枚举值使用 `uint8_t`（1 字节）
- 通道掩码使用 `uint32_t`（4 字节）
- 格式名称字符串是静态常量（无运行时分配）

### 查询性能

- **switch 语句**: 编译器生成跳转表，O(1) 查询
- **静态数组**: `PreferredTextureFormats()` 返回静态数组的 span，无分配

### 转换开销

- **Swizzle**: GPU 硬件支持，零开销（在采样时自动应用）
- **FormatXferOp**: CPU 端操作，仅在数据传输时执行

### 缓存友好性

- 格式属性查询是纯函数，无副作用
- 静态数组和 switch 语句对 CPU 缓存友好

## 相关文件

| 文件路径 | 作用 |
|----------|------|
| `include/gpu/graphite/TextureInfo.h` | 纹理信息描述符 |
| `src/gpu/graphite/Caps.h` | 后端能力查询和格式支持 |
| `src/gpu/graphite/Texture.h` | 纹理资源基类 |
| `src/gpu/graphite/TextureUtils.h` | 纹理数据传输辅助函数 |
| `src/gpu/Swizzle.h` | 通道重排逻辑 |
| `include/core/SkColorType.h` | Skia 颜色类型定义 |
| `include/core/SkTextureCompressionType.h` | 压缩类型枚举 |
| `src/core/SkImageInfoPriv.h` | 颜色类型属性查询 |
| `src/gpu/graphite/mtl/MtlCaps.cpp` | Metal 格式映射 |
| `src/gpu/graphite/vk/VulkanCaps.cpp` | Vulkan 格式映射 |
| `src/gpu/graphite/dawn/DawnCaps.cpp` | Dawn 格式映射 |
