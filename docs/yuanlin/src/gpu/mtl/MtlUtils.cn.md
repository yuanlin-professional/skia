# MtlUtils

> 源文件
> - src/gpu/mtl/MtlUtils.mm

## 概述

`MtlUtils.mm` 是 Skia Metal GPU 后端的格式工具函数实现文件，提供了 Metal 像素格式（`MTLPixelFormat`）的查询和转换功能。该文件包含一系列辅助函数，用于判断格式是否压缩、获取格式的通道信息、计算每块字节数、格式字符串转换等。

主要功能：
- 判断 Metal 格式是否为压缩格式
- 将格式枚举转换为可读字符串（用于调试和日志）
- 获取格式包含的颜色通道标志
- 计算格式的每块/每像素字节数
- 将 Metal 格式映射到 Skia 压缩类型

该文件为 Metal 后端的纹理管理、格式验证、内存分配等功能提供基础支持。

## 架构位置

```
skgpu::mtl (Metal 后端)
  ├── MtlUtils (格式工具 - 本文件)
  ├── MtlTexture (纹理实现)
  ├── MtlCaps (能力查询)
  └── MtlGpu (GPU 上下文)
```

## 主要函数

### MtlFormatIsCompressed

```cpp
bool MtlFormatIsCompressed(MTLPixelFormat mtlFormat)
```

**功能：** 判断给定的 Metal 像素格式是否为压缩格式。

**支持的压缩格式：**
- `MTLPixelFormatETC2_RGB8` - ETC2 压缩（所有平台）
- `MTLPixelFormatBC1_RGBA` - BC1/DXT1 压缩（仅 macOS）

### MtlFormatToString

```cpp
const char* MtlFormatToString(MTLPixelFormat mtlFormat)
```

**功能：** 将 Metal 格式枚举转换为可读字符串，用于调试输出。

**支持的格式：** 包含所有 Skia 使用的 Metal 格式，如 RGBA8Unorm、BGRA8Unorm、RGB10A2Unorm、RGBA16Float、ETC2_RGB8 等。

### MtlFormatChannels

```cpp
uint32_t MtlFormatChannels(MTLPixelFormat mtlFormat)
```

**功能：** 返回格式包含的颜色通道标志位。

**返回值：** `SkColorChannelFlags` 组合，如：
- `kRed_SkColorChannelFlag` - 仅红色通道
- `kRG_SkColorChannelFlags` - 红绿通道
- `kRGB_SkColorChannelFlags` - RGB 通道
- `kRGBA_SkColorChannelFlags` - RGBA 通道
- `kAlpha_SkColorChannelFlag` - 仅 Alpha 通道
- `0` - 无颜色通道（如 Stencil8）

### MtlFormatBytesPerBlock

```cpp
size_t MtlFormatBytesPerBlock(MTLPixelFormat mtlFormat)
```

**功能：** 返回格式的每块字节数。对于非压缩格式，等同于每像素字节数。

**示例：**
- `MTLPixelFormatR8Unorm` → 1 字节
- `MTLPixelFormatRGBA8Unorm` → 4 字节
- `MTLPixelFormatRGBA16Float` → 8 字节
- `MTLPixelFormatETC2_RGB8` → 8 字节（4x4 块压缩）

### MtlFormatToCompressionType

```cpp
SkTextureCompressionType MtlFormatToCompressionType(MTLPixelFormat mtlFormat)
```

**功能：** 将 Metal 压缩格式映射到 Skia 的压缩类型枚举。

**返回值：**
- `SkTextureCompressionType::kETC2_RGB8_UNORM` - ETC2 格式
- `SkTextureCompressionType::kBC1_RGBA8_UNORM` - BC1 格式（macOS）
- `SkTextureCompressionType::kNone` - 非压缩格式

## 依赖关系

### 依赖的头文件

| 头文件 | 用途 |
|--------|------|
| `src/gpu/mtl/MtlUtilsPriv.h` | 函数声明和 Metal 类型 |
| `src/core/SkImageInfoPriv.h` | `SkColorChannelFlags` 定义 |
| `include/core/SkTextureCompressionType.h` | 压缩类型枚举 |

### 被依赖关系

- **MtlCaps** - 查询格式通道和压缩类型
- **MtlTexture** - 计算纹理内存大小
- **MtlGpu** - 格式验证和转换
- **调试工具** - 格式字符串输出

## 设计决策

### 平台条件编译

使用 `#ifdef SK_BUILD_FOR_MAC` 区分 macOS 和 iOS：
- BC1 压缩仅在 macOS 上可用
- iOS 不支持 BC 系列压缩格式

### 注释说明

代码注释指出这些函数主要由 Ganesh 使用，在仅构建 Graphite 时链接器会自动移除未使用的符号。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/mtl/MtlUtilsPriv.h` | 头文件 | 函数声明 |
| `src/gpu/mtl/MtlCaps.h` | 使用者 | 能力查询和格式验证 |
| `src/gpu/mtl/MtlTexture.h` | 使用者 | 纹理创建和内存计算 |
| `src/gpu/mtl/MtlGpu.h` | 使用者 | GPU 上下文格式处理 |
