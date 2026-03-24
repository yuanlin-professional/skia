# MtlTextureInfo - Metal 纹理信息

> 源文件: `src/gpu/graphite/mtl/MtlTextureInfo.mm`

## 概述

MtlTextureInfo.mm 实现了 Skia Graphite Metal 后端的纹理信息类 `MtlTextureInfo` 的核心方法以及 `TextureInfos` 命名空间中的工厂函数。MtlTextureInfo 封装了 Metal 纹理的关键属性，包括像素格式、使用方式、存储模式、采样数和 mipmap 级别等。

该文件提供了从原生 Metal 纹理对象（`id<MTLTexture>`）提取信息、格式转换、兼容性检查和字符串序列化等功能。

## 架构位置

```
Graphite 纹理信息抽象层
  -> TextureInfo (跨后端纹理信息接口)
    -> MtlTextureInfo (Metal 实现)
      -> MTLPixelFormat, MTLTextureUsage, MTLStorageMode 等
```

MtlTextureInfo 是 Graphite 跨后端纹理信息系统的 Metal 特定实现。

## 主要类与结构体

### `MtlTextureInfo`
- **职责**: 存储和查询 Metal 纹理的属性
- **成员**（从源码推断）:
  - `fSampleCount`: 采样数
  - `fMipmapped`: 是否有 mipmap
  - `fFormat`: MTLPixelFormat 像素格式
  - `fUsage`: MTLTextureUsage 使用标志
  - `fStorageMode`: MTLStorageMode 存储模式
  - `fFramebufferOnly`: 是否为帧缓冲专用

## 公共 API 函数

| 函数 | 命名空间 | 说明 |
|------|----------|------|
| `MtlTextureInfo(CFTypeRef)` | - | 从 Metal 纹理对象构造 |
| `viewFormat()` | - | 返回跨后端的 TextureFormat 枚举 |
| `toBackendString()` | - | 序列化为人可读的字符串 |
| `isCompatible(TextureInfo, bool)` | - | 检查与另一个 TextureInfo 的兼容性 |
| `MakeMetal(CFTypeRef)` | `TextureInfos` | 从 Metal 纹理创建 TextureInfo |
| `MakeMetal(MtlTextureInfo)` | `TextureInfos` | 从 MtlTextureInfo 创建 TextureInfo |
| `GetMtlTextureInfo(TextureInfo, MtlTextureInfo*)` | `TextureInfos` | 提取 Metal 纹理信息 |

## 内部实现细节

### 从纹理对象构造
构造函数从 `id<MTLTexture>` 读取所有属性：
- `sampleCount` 转换为 Skia 的 `SampleCount` 枚举
- `mipmapLevelCount > 1` 判断是否有 mipmap
- 直接读取 `pixelFormat`、`usage`、`storageMode`、`framebufferOnly`

### 兼容性检查
`isCompatible` 方法检查两个纹理信息是否兼容：
- 像素格式必须匹配
- 存储模式必须匹配
- `framebufferOnly` 标志必须匹配
- 使用方式（usage）：若 `requireExact` 为 false，允许传入的 usage 是当前 usage 的超集

### 格式转换
`viewFormat()` 通过 `MTLPixelFormatToTextureFormat` 将 Metal 的 `MTLPixelFormat` 转换为 Skia 的跨后端 `TextureFormat` 枚举。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/TextureInfoPriv.h` | TextureInfo 的私有构造和访问接口 |
| `include/gpu/graphite/mtl/MtlGraphiteTypes.h` | MtlTextureInfo 类型声明 |
| `src/gpu/graphite/mtl/MtlGraphiteUtils.h` | Metal 工具函数 |
| `src/gpu/mtl/MtlUtilsPriv.h` | MTLPixelFormat 转换等工具 |
| `<Metal/Metal.h>` | Metal 框架 |

## 设计模式与设计决策

1. **命名空间工厂模式**: `TextureInfos` 命名空间提供工厂函数，使公共 API 与实现细节分离。
2. **兼容性的宽松模式**: `isCompatible` 支持 `requireExact` 参数，允许在非精确模式下接受 usage 超集，适用于资源复用场景。
3. **类型擦除**: 通过 `TextureInfoPriv::Make` 将 MtlTextureInfo 封装进跨后端的 TextureInfo。

## 性能考量

1. **构造开销**: 从 `id<MTLTexture>` 构造需要多次 Objective-C 消息发送来读取属性，但这通常只在纹理创建时执行一次。
2. **兼容性检查**: `isCompatible` 使用简单的值比较和位操作，开销极低。

## 相关文件

- `include/gpu/graphite/mtl/MtlGraphiteTypes.h` - MtlTextureInfo 的声明
- `src/gpu/graphite/TextureInfoPriv.h` - TextureInfo 私有接口
- `src/gpu/graphite/mtl/MtlBackendTexture.mm` - 使用 MtlTextureInfo 创建 BackendTexture
- `src/gpu/mtl/MtlUtilsPriv.h` - Metal 格式转换工具
