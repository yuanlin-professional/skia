# GlyphUtils

> 源文件: `src/text/gpu/GlyphUtils.h`

## 概述

`GlyphUtils.h` 提供了一个简洁的工具函数,用于在 GPU 文本渲染管线中将 SkMask 的掩码格式转换为 GPU 后端使用的 `skgpu::MaskFormat`。该函数在多个 GPU 后端间共享,是字形处理流程中格式适配的关键桥梁。

## 架构位置

```
SkGlyph (核心层)
  └─ SkMask::Format           CPU 端掩码格式
        │
        ▼
  FormatFromSkGlyph()         格式转换 (本文件)
        │
        ▼
  skgpu::MaskFormat            GPU 端掩码格式
        │
        ▼
  GrAtlasManager / graphite   GPU 纹理图集管理
```

该文件位于 `src/text/gpu` 目录中,属于 GPU 文本渲染的共享工具层,被 Ganesh 和 Graphite 两个 GPU 后端共同使用。

## 主要类与结构体

本文件不包含类或结构体,仅包含一个内联工具函数,位于 `sktext::gpu` 命名空间中。

## 公共 API 函数

### `FormatFromSkGlyph(SkMask::Format format) -> skgpu::MaskFormat`
将 CPU 端的 `SkMask::Format` 枚举值转换为 GPU 端的 `skgpu::MaskFormat` 枚举值。

转换映射关系:
| SkMask::Format | skgpu::MaskFormat | 说明 |
|---|---|---|
| `kBW_Format` | `kA8` | 位图格式存储在 8 位缓存中 |
| `kSDF_Format` | `kA8` | SDF(有符号距离场)格式存储在 8 位缓存中 |
| `kA8_Format` | `kA8` | 8 位 alpha 格式直接映射 |
| `k3D_Format` | `kA8` | 忽略乘法和加法平面,仅使用掩码平面 |
| `kLCD16_Format` | `kA565` | LCD 子像素抗锯齿映射为 565 格式 |
| `kARGB32_Format` | `kARGB` | 全彩色字形(如 emoji)映射为 ARGB 格式 |

若输入不匹配任何已知格式,函数触发 `SkUNREACHABLE`。

## 内部实现细节

- 函数声明为 `inline`,避免多重定义问题,允许在头文件中直接定义
- 使用 `switch` 语句进行映射,利用 fall-through 特性将 `kBW_Format` 和 `kSDF_Format` 统一处理
- `k3D_Format` 是一种包含三个平面(掩码、乘法、加法)的特殊格式,此处仅提取掩码平面信息
- `SkUNREACHABLE` 宏确保所有枚举值都被处理,在调试构建中触发断言失败

## 依赖关系

- `src/core/SkMask.h` - 提供 `SkMask::Format` 枚举定义
- `src/gpu/MaskFormat.h` - 提供 `skgpu::MaskFormat` 枚举定义

## 设计模式与设计决策

### 格式降级策略
多种掩码格式被映射到 `kA8`,体现了 GPU 端存储的简化策略:
- BW(位图)和 SDF 虽然语义不同,但在 GPU 纹理图集中都以 8 位单通道存储
- 3D 格式的乘法和加法平面在 GPU 路径中不使用,简化了处理流程

### 跨后端共享
将此函数放在 `src/text/gpu` 而非特定后端目录中,确保 Ganesh 和 Graphite 使用一致的格式映射逻辑。

## 性能考量

- 内联函数消除了函数调用开销
- switch 语句通常被编译器优化为跳转表,实现 O(1) 的转换效率
- 该函数在字形处理的热路径上被频繁调用,内联对性能有积极影响

## 相关文件

- `src/core/SkMask.h` - SkMask 格式定义
- `src/gpu/MaskFormat.h` - GPU 掩码格式定义
- `src/text/gpu/TextBlobRedrawCoordinator.h` - 使用该函数的文本块管理器
- `src/gpu/ganesh/text/GrAtlasManager.h` - Ganesh 纹理图集管理
- `src/gpu/graphite/text/TextAtlasManager.h` - Graphite 纹理图集管理
