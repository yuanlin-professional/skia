# SkTextureCompressionType

> 源文件: `include/core/SkTextureCompressionType.h`

## 概述
SkTextureCompressionType 定义了 Skia 支持的纹理压缩格式枚举,用于在不同图形 API(OpenGL、Metal、Vulkan)之间提供统一的压缩纹理格式抽象。该枚举允许 Skia 在多个平台上以一致的方式处理压缩纹理,同时映射到各平台特定的压缩格式。

## 架构位置
该文件位于 Skia 核心(core)模块,是纹理管理和 GPU 资源抽象层的基础组件。它为上层 GPU 后端(Ganesh 和 Graphite)提供了平台无关的纹理压缩格式定义,使得纹理压缩功能可以跨平台一致使用。

## 主要枚举类型

### SkTextureCompressionType
定义支持的纹理压缩类型。

**枚举值**:
| 枚举值 | 值 | 说明 |
|--------|-----|------|
| kNone | 0 | 无压缩(未压缩纹理) |
| kETC2_RGB8_UNORM | 1 | ETC2 RGB8 未归一化格式 |
| kBC1_RGB8_UNORM | 2 | BC1 RGB8 未归一化格式(DXT1 RGB) |
| kBC1_RGBA8_UNORM | 3 | BC1 RGBA8 未归一化格式(DXT1 RGBA,带 1 位 alpha) |
| kLast | = kBC1_RGBA8_UNORM | 最后一个有效枚举值(用于迭代) |
| kETC1_RGB8 | = kETC2_RGB8_UNORM | ETC1 的别名(向后兼容) |

## 平台映射表

### 压缩格式对应关系
文件注释中提供了 Skia 枚举值与各图形 API 原生格式的映射:

| Skia 格式 | OpenGL 格式 | Metal 格式 | Vulkan 格式 |
|-----------|-------------|------------|-------------|
| kETC2_RGB8_UNORM | GL_COMPRESSED_ETC1_RGB8<br>GL_COMPRESSED_RGB8_ETC2 | MTLPixelFormatETC2_RGB8<br>(仅 iOS) | VK_FORMAT_ETC2_R8G8B8_UNORM_BLOCK |
| kBC1_RGB8_UNORM | GL_COMPRESSED_RGB_S3TC_DXT1_EXT | 不支持 | VK_FORMAT_BC1_RGB_UNORM_BLOCK |
| kBC1_RGBA8_UNORM | GL_COMPRESSED_RGBA_S3TC_DXT1_EXT | MTLPixelFormatBC1_RGBA<br>(仅 macOS) | VK_FORMAT_BC1_RGBA_UNORM_BLOCK |

## 设计决策

### ETC2/ETC1 兼容性
`kETC1_RGB8` 定义为 `kETC2_RGB8_UNORM` 的别名。这是因为 ETC2 在 RGB8 模式下向后兼容 ETC1 格式,允许旧代码无缝迁移到 ETC2,同时保持 API 一致性。

### 有限的格式支持
Skia 仅支持有限的几种压缩格式,主要考虑:
1. **广泛支持**: ETC2 在移动平台(iOS、Android)广泛支持
2. **桌面兼容**: BC1(DXT1)是 Windows 和桌面 OpenGL 的标准格式
3. **实现简单**: 支持少量格式降低了跨平台实现的复杂度

### 平台差异处理
不同平台对压缩格式的支持不同:
- **iOS**: 仅支持 ETC2,不支持 BC1
- **macOS**: 支持 BC1,不支持 ETC2
- **Android**: 通常支持 ETC2
- **Windows**: 通常支持 BC1

Skia 的后端代码需要根据运行时平台选择合适的压缩格式。

## 依赖关系

### 依赖的模块
该文件为独立定义,无外部依赖(仅标准 C++ enum class)。

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| src/gpu/ganesh/GrCaps.h | GPU 能力查询,检查支持的压缩格式 |
| src/gpu/ganesh/GrTexture.h | 纹理对象创建和管理 |
| src/image/SkImage_GpuBase.cpp | 从压缩数据创建 SkImage |
| include/gpu/GrBackendSurface.h | 后端表面的压缩格式描述 |
| src/gpu/graphite/ | Graphite 后端的纹理压缩支持 |

## 性能考量

### 内存节省
压缩纹理的主要优势是显著减少 GPU 内存占用:
- **ETC2_RGB8**: 压缩比 6:1 (相对于未压缩 RGB888)
- **BC1_RGB8**: 压缩比 6:1
- **BC1_RGBA8**: 压缩比 4:1 (带 1 位 alpha)

### 带宽优化
使用压缩纹理可减少从主内存到 GPU 的数据传输量,提高纹理采样性能,尤其在带宽受限的移动设备上效果显著。

### 解压成本
硬件支持的压缩格式在 GPU 上实时解压,几乎无性能损失。但在不支持的平台上可能需要软件解压,引入额外开销。

## 使用场景

### 移动应用
在内存和带宽受限的移动设备上,使用 ETC2 压缩纹理可以:
- 减少应用 APK/IPA 大小
- 降低运行时内存占用
- 提高纹理加载速度

### 桌面应用
在桌面平台,BC1(DXT)格式被广泛支持,特别是在游戏和高性能图形应用中。

### 跨平台策略
应用可以在资源打包时为不同平台准备不同格式的压缩纹理,运行时根据 `GrCaps::compressionSupported()` 选择最优格式。

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/GrBackendSurface.h | 使用此枚举描述后端纹理格式 |
| src/gpu/ganesh/GrCaps.h | 查询硬件支持的压缩格式 |
| include/core/SkImage.h | 从压缩数据创建 SkImage 的 API |
| src/codec/SkMasks.h | 像素格式掩码定义 |
| tools/gpu/BackendTextureImageFactory.h | 测试工具中的压缩纹理工厂 |
