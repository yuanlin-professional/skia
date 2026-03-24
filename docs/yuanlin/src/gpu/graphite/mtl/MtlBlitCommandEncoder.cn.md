# MtlBlitCommandEncoder - Metal Blit 命令编码器

> 源文件: `src/gpu/graphite/mtl/MtlBlitCommandEncoder.h`

## 概述

MtlBlitCommandEncoder 是 Skia Graphite Metal 后端中对 `MTLBlitCommandEncoder` 的 C++ 封装。它继承自 `Resource` 基类，提供了在 GPU 上执行数据传输（Blit）操作的接口，包括纹理与缓冲区之间的拷贝、纹理到纹理的拷贝、缓冲区到缓冲区的拷贝以及缓冲区填充等操作。

Blit 编码器是 Metal 命令模型中三种编码器之一（另外两种是渲染编码器和计算编码器），专门用于非计算、非渲染的数据传输操作。

## 架构位置

```
Graphite Metal 后端
  -> MtlCommandBuffer (Metal 命令缓冲区)
    -> MtlBlitCommandEncoder (Blit 编码器)
      -> id<MTLBlitCommandEncoder> (原生 Metal 编码器)
```

MtlBlitCommandEncoder 由 MtlCommandBuffer 创建，用于执行纹理上传、下载、拷贝等数据传输操作。

## 主要类与结构体

### `MtlBlitCommandEncoder`
- **基类**: `Resource`
- **职责**: 封装 Metal Blit 命令编码器，提供纹理和缓冲区之间的数据传输操作
- **设计特点**: 与 MtlComputeCommandEncoder 不同，Blit 编码器不需要状态跟踪，因为每次操作都是独立的

## 公共 API 函数

### 工厂方法
| 函数 | 说明 |
|------|------|
| `Make(SharedContext*, MTLCommandBuffer)` | 从 Metal 命令缓冲区创建 Blit 编码器 |

### 调试方法
| 函数 | 说明 |
|------|------|
| `pushDebugGroup(NSString*)` | 压入调试分组 |
| `popDebugGroup()` | 弹出调试分组 |

### 数据传输操作
| 函数 | 说明 |
|------|------|
| `fillBuffer(buffer, offset, bytes, value)` | 用指定值填充缓冲区 |
| `copyFromTexture(texture, srcRect, buffer, offset, rowBytes)` | 从纹理拷贝到缓冲区 |
| `copyFromBuffer(buffer, offset, rowBytes, texture, dstRect, level)` | 从缓冲区拷贝到纹理 |
| `copyTextureToTexture(src, srcRect, dst, dstPoint, mipLevel)` | 纹理到纹理拷贝 |
| `copyBufferToBuffer(src, srcOffset, dst, dstOffset, size)` | 缓冲区到缓冲区拷贝 |

### 平台特定
| 函数 | 说明 |
|------|------|
| `synchronizeResource(buffer)` | 同步 managed 存储模式的缓冲区（仅 macOS） |

### 编码控制
| 函数 | 说明 |
|------|------|
| `endEncoding()` | 结束编码 |
| `getResourceType()` | 返回 "Metal Blit Command Encoder" |

## 内部实现细节

### @autoreleasepool 管理
`Make` 方法使用 `@autoreleasepool` 包裹编码器创建过程。通过 `sk_ret_cfp` 显式 retain 编码器对象，确保 autorelease pool 释放后编码器仍然有效。

### copyFromTexture 参数映射
将 Skia 的 `SkIRect` 转换为 Metal 的 `MTLOrigin` 和 `MTLSize`，同时设置 `sourceSlice: 0` 和 `sourceLevel: 0` 表示从纹理的第一层和第一个 mip 级别拷贝。`destinationBytesPerImage` 计算为 `bufferRowBytes * srcRect.height()`。

### copyFromBuffer 参数映射
类似地将缓冲区布局参数（偏移、行字节数）和纹理区域参数转换为 Metal API 的调用形式。支持指定目标 mip 级别。

### 平台条件编译
`synchronizeResource` 方法使用 `#ifdef SK_BUILD_FOR_MAC` 条件编译，因为此 API 仅在 macOS 上可用。在 iOS 上，由于使用 shared 存储模式，不需要显式同步。

### Resource 构造
构造函数传入 `gpuMemorySize=0`，因为编码器本身不占用 GPU 内存。`Ownership::kOwned` 表示 Skia 拥有此资源的所有权。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/Resource.h` | 资源基类 |
| `include/core/SkRect.h` | SkIRect 矩形区域参数 |
| `include/core/SkRefCnt.h` | sk_sp 智能指针 |
| `include/ports/SkCFObject.h` | sk_cfp Core Foundation 对象包装 |
| `<Metal/Metal.h>` | Metal 框架 |

## 设计模式与设计决策

1. **薄封装层**: 与 MtlComputeCommandEncoder 的状态跟踪不同，Blit 编码器是 Metal API 的薄封装，因为 Blit 操作是无状态的独立命令。

2. **Skia 类型适配**: 将 Skia 的 `SkIRect`、`SkIPoint` 等类型转换为 Metal 的 `MTLOrigin`、`MTLSize`，使调用方无需了解 Metal 类型系统。

3. **平台抽象**: 通过条件编译处理 macOS 和 iOS 的 API 差异（如 `synchronizeResource`）。

## 性能考量

1. **无状态跟踪**: Blit 操作每次都是独立的，不存在状态冗余问题，因此无需像渲染/计算编码器那样维护状态缓存。
2. **批量传输**: 单个 Blit 编码器可以录制多个传输操作，在 `endEncoding` 前它们会被批量提交。
3. **行字节对齐**: 调用者负责确保 `bufferRowBytes` 满足 Metal 的对齐要求。

## 相关文件

- `src/gpu/graphite/mtl/MtlCommandBuffer.h` - 创建和管理 Blit 编码器
- `src/gpu/graphite/mtl/MtlComputeCommandEncoder.h` - 计算编码器（类似设计）
- `src/gpu/graphite/mtl/MtlRenderCommandEncoder.h` - 渲染编码器（类似设计）
- `src/gpu/graphite/Resource.h` - 资源基类
