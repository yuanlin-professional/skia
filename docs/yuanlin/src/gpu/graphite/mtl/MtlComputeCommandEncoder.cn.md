# MtlComputeCommandEncoder - Metal 计算命令编码器

> 源文件: `src/gpu/graphite/mtl/MtlComputeCommandEncoder.h`

## 概述

MtlComputeCommandEncoder 是 Skia Graphite Metal 后端中对 `MTLComputeCommandEncoder` 的 C++ 封装。它继承自 `Resource` 基类，包装了原生 Metal 计算命令编码器，并维护已绑定资源的状态跟踪以避免冗余的 GPU 状态切换。

计算命令编码器用于向 Metal 命令缓冲区录制 GPU 计算调度（dispatch）命令，支持设置计算管线状态、绑定缓冲区、纹理和采样器，以及调度线程组。

## 架构位置

```
Graphite Metal 后端
  -> MtlCommandBuffer (Metal 命令缓冲区)
    -> MtlComputeCommandEncoder (计算编码器)
      -> id<MTLComputeCommandEncoder> (原生 Metal 编码器)
```

MtlComputeCommandEncoder 由 MtlCommandBuffer 创建和管理，用于录制计算通道的 GPU 命令。

## 主要类与结构体

### `MtlComputeCommandEncoder`
- **基类**: `Resource`
- **职责**: 封装 Metal 计算命令编码器，提供状态跟踪和 Skia 风格的 API
- **生命周期**: 通过 `sk_sp` 管理，GPU 数据在 `freeGpuData()` 中释放

## 公共 API 函数

### 工厂方法
| 函数 | 说明 |
|------|------|
| `Make(SharedContext*, MTLCommandBuffer)` | 从 Metal 命令缓冲区创建计算编码器 |

### 调试方法
| 函数 | 说明 |
|------|------|
| `setLabel(NSString*)` | 设置编码器标签 |
| `pushDebugGroup(NSString*)` | 压入调试分组 |
| `popDebugGroup()` | 弹出调试分组 |
| `insertDebugSignpost(NSString*)` | 插入调试标记 |

### 管线状态
| 函数 | 说明 |
|------|------|
| `setComputePipelineState(id<MTLComputePipelineState>)` | 设置计算管线状态（带状态跟踪） |

### 资源绑定
| 函数 | 说明 |
|------|------|
| `setBuffer(buffer, offset, index)` | 绑定缓冲区到指定槽位（带冗余检查） |
| `setBufferOffset(offset, index)` | 仅更新缓冲区偏移（需 macOS 10.11+） |
| `setTexture(texture, index)` | 绑定纹理到指定槽位 |
| `setSamplerState(sampler, index)` | 绑定采样器到指定槽位 |
| `setThreadgroupMemoryLength(length, index)` | 设置线程组共享内存长度（需 16 字节对齐） |

### 调度
| 函数 | 说明 |
|------|------|
| `dispatchThreadgroups(globalSize, localSize)` | 直接调度计算线程组 |
| `dispatchThreadgroupsWithIndirectBuffer(buffer, offset, localSize)` | 使用间接缓冲区调度 |

### 编码控制
| 函数 | 说明 |
|------|------|
| `endEncoding()` | 结束编码 |
| `getResourceType()` | 返回 "Metal Compute Command Encoder" |

## 内部实现细节

### 状态跟踪与冗余消除
编码器维护以下状态缓存：
- `fCurrentComputePipelineState`: 当前管线状态对象
- `fBuffers[16]` + `fBufferOffsets[16]`: 已绑定的缓冲区和偏移
- `fTextures[16]`: 已绑定的纹理
- `fSamplers[16]`: 已绑定的采样器

每次绑定操作前都会检查是否与当前状态相同，避免向 Metal 发送冗余的状态切换命令。

### setBuffer 的优化路径
`setBuffer` 首先检查缓冲区是否已绑定在同一槽位：
1. 如果缓冲区相同（macOS 10.11+），仅调用 `setBufferOffset` 更新偏移
2. 如果缓冲区或偏移不同，调用完整的 `setBuffer:offset:atIndex:`

### @autoreleasepool 与 retain
`Make` 方法使用 `@autoreleasepool` 包裹编码器创建过程，并通过 `sk_ret_cfp` 显式添加 retain，确保 Skia 持有独立于 autorelease pool 的引用。

### 构造函数初始化
构造函数将所有缓冲区、纹理和采样器数组初始化为 `nil`，确保后续的状态比较不会因未初始化的值产生假阳性。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/Resource.h` | 资源基类 |
| `src/gpu/graphite/ComputeTypes.h` | WorkgroupSize 类型 |
| `include/core/SkRefCnt.h` | sk_sp 智能指针 |
| `include/ports/SkCFObject.h` | sk_cfp Core Foundation 对象包装 |
| `<Metal/Metal.h>` | Metal 框架 |

## 设计模式与设计决策

1. **状态跟踪模式**: 在 CPU 端缓存 GPU 状态，避免冗余的 Metal API 调用。这是 GPU 编程中常见的优化模式。

2. **资源管理**: 继承自 Resource 基类，通过 `freeGpuData()` 在资源不再需要时释放底层 Metal 对象。GPU 内存大小设为 0，因为编码器本身不占用 GPU 内存。

3. **常量限制**: `kMaxExpectedBuffers(16)` 和 `kMaxExpectedTextures(16)` 定义了预期的最大资源绑定数量，用于固定大小的数组缓存。

4. **API 版本兼容**: `setBufferOffset` 使用 `SK_API_AVAILABLE` 宏标记最低系统版本要求，`setBuffer` 中用 `@available` 运行时检查版本后选择优化路径。

## 性能考量

1. **冗余消除**: 状态跟踪避免了不必要的 Metal API 调用，这些调用虽然开销不大，但在高频调用场景中可以累积。
2. **固定大小数组**: 使用固定大小数组（而非动态容器）存储状态缓存，避免堆分配和提高缓存局部性。
3. **setBufferOffset 优化**: 当仅偏移变化时，`setBufferOffset` 比重新绑定整个缓冲区更轻量。

## 相关文件

- `src/gpu/graphite/mtl/MtlCommandBuffer.h` - 创建和管理计算编码器
- `src/gpu/graphite/mtl/MtlRenderCommandEncoder.h` - 渲染编码器（类似设计）
- `src/gpu/graphite/mtl/MtlBlitCommandEncoder.h` - Blit 编码器（类似设计）
- `src/gpu/graphite/Resource.h` - 资源基类
- `src/gpu/graphite/ComputeTypes.h` - WorkgroupSize 定义
