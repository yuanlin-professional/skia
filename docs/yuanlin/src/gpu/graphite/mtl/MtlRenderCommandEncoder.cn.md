# MtlRenderCommandEncoder - Metal 渲染命令编码器

> 源文件: `src/gpu/graphite/mtl/MtlRenderCommandEncoder.h`

## 概述

MtlRenderCommandEncoder 是 Skia Graphite Metal 后端中对 `MTLRenderCommandEncoder` 的 C++ 封装。它继承自 `Resource` 基类，包装了原生 Metal 渲染命令编码器，并维护丰富的状态跟踪以避免冗余的 GPU 状态切换调用。

渲染命令编码器是 Metal 命令模型中用于录制渲染通道（Render Pass）命令的核心对象。它支持设置渲染管线状态、绑定顶点/片段缓冲区和纹理、配置深度模板状态、设置视口/裁剪区域以及发出绘制命令（包括直接绘制、实例绘制和索引绘制）。

## 架构位置

```
Graphite Metal 后端
  -> MtlCommandBuffer (Metal 命令缓冲区)
    -> MtlRenderCommandEncoder (渲染编码器)
      -> id<MTLRenderCommandEncoder> (原生 Metal 编码器)
        -> 渲染管线状态 / 深度模板 / 绘制命令
```

MtlRenderCommandEncoder 由 MtlCommandBuffer 在开始渲染通道时创建，用于录制该通道的所有渲染命令。

## 主要类与结构体

### `MtlRenderCommandEncoder`
- **基类**: `Resource`
- **职责**: 封装 Metal 渲染命令编码器，提供状态跟踪和 Skia 风格的渲染 API
- **状态缓存**: 渲染管线状态、深度模板状态、模板参考值、纹理、采样器、裁剪矩形、三角形填充模式

## 公共 API 函数

### 工厂方法
| 函数 | 说明 |
|------|------|
| `Make(SharedContext*, MTLCommandBuffer, MTLRenderPassDescriptor*)` | 创建渲染编码器 |

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
| `setRenderPipelineState(id<MTLRenderPipelineState>)` | 设置渲染管线状态（带跟踪） |
| `setTriangleFillMode(MTLTriangleFillMode)` | 设置三角形填充模式（带跟踪） |
| `setFrontFacingWinding(MTLWinding)` | 设置正面朝向 |

### 视口和裁剪
| 函数 | 说明 |
|------|------|
| `setViewport(const MTLViewport&)` | 设置视口 |
| `setScissorRect(const MTLScissorRect&)` | 设置裁剪矩形（带跟踪） |

### 资源绑定
| 函数 | 说明 |
|------|------|
| `setVertexBuffer(buffer, offset, index)` | 绑定顶点缓冲区 |
| `setFragmentBuffer(buffer, offset, index)` | 绑定片段缓冲区 |
| `setVertexBytes(bytes, length, index)` | 直接设置顶点字节数据 |
| `setFragmentBytes(bytes, length, index)` | 直接设置片段字节数据 |
| `setFragmentTexture(texture, index)` | 绑定片段纹理（带跟踪） |
| `setFragmentSamplerState(sampler, index)` | 绑定片段采样器（带跟踪） |

### 混合和深度模板
| 函数 | 说明 |
|------|------|
| `setBlendColor(float[4])` | 设置混合常量颜色 |
| `setStencilReferenceValue(uint32_t)` | 设置模板参考值（带跟踪） |
| `setDepthStencilState(id<MTLDepthStencilState>)` | 设置深度模板状态（带跟踪） |

### 绘制命令
| 函数 | 说明 |
|------|------|
| `drawPrimitives(type, start, count)` | 直接绘制 |
| `drawPrimitives(type, start, count, instances, base)` | 实例化绘制 |
| `drawPrimitives(type, indirectBuffer, offset)` | 间接绘制 |
| `drawIndexedPrimitives(type, count, indexType, buffer, offset)` | 索引绘制 |
| `drawIndexedPrimitives(type, count, indexType, buffer, offset, instances, baseV, baseI)` | 索引实例化绘制 |
| `drawIndexedPrimitives(type, indexType, buffer, offset, indirect, indirectOffset)` | 索引间接绘制 |

### 编码控制
| 函数 | 说明 |
|------|------|
| `endEncoding()` | 结束编码 |

## 内部实现细节

### 状态跟踪缓存
编码器维护以下状态以避免冗余的 Metal API 调用：
- `fCurrentRenderPipelineState`: 当前渲染管线状态对象
- `fCurrentDepthStencilState`: 当前深度模板状态
- `fCurrentStencilReferenceValue`: 当前模板参考值（默认 0）
- `fCurrentTexture[16]`: 已绑定的片段纹理
- `fCurrentSampler[16]`: 已绑定的片段采样器
- `fCurrentScissorRect`: 当前裁剪矩形
- `fCurrentTriangleFillMode`: 当前三角形填充模式（初始化为无效值 -1）

### 裁剪矩形比较
`setScissorRect` 逐字段比较 `MTLScissorRect` 的 x、y、width、height，因为 `MTLScissorRect` 是 C 结构体，不支持直接相等比较。

### 三角形填充模式初始化
`fCurrentTriangleFillMode` 初始化为 `(MTLTriangleFillMode)-1`，这是一个无效的枚举值，确保第一次调用 `setTriangleFillMode` 时一定会执行 Metal API 调用。

### 缓冲区绑定不跟踪
与 MtlComputeCommandEncoder 不同，渲染编码器的 `setVertexBuffer` 和 `setFragmentBuffer` 不进行状态跟踪，每次调用都直接转发到 Metal API。这可能是因为渲染编码器的缓冲区绑定模式更复杂（顶点和片段分别绑定，偏移频繁变化）。

### 资源槽位限制
- `kMaxExpectedBuffers = 6`: 渲染编码器期望的最大缓冲区绑定数
- `kMaxExpectedTextures = 16`: 最大纹理/采样器绑定数

缓冲区限制（6）远小于计算编码器（16），反映了渲染管线的典型资源使用模式。

### API 版本注解
多个方法使用 `SK_API_AVAILABLE` 标记最低版本要求：
- `setVertexBytes` / `setFragmentBytes`: macOS 10.11+, iOS 8.3+
- 实例化绘制 / 间接绘制: macOS 10.11+, iOS 9.0+

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/Resource.h` | 资源基类 |
| `include/core/SkRefCnt.h` | sk_sp 智能指针 |
| `include/ports/SkCFObject.h` | sk_cfp Core Foundation 对象包装 |
| `<Metal/Metal.h>` | Metal 框架 |

## 设计模式与设计决策

1. **选择性状态跟踪**: 仅对频繁切换且比较成本低的状态进行跟踪（管线状态、纹理、采样器、深度模板），不跟踪缓冲区绑定（因为偏移频繁变化使跟踪收益不大）。

2. **无效初始值**: 使用无效的初始值（如 `nil`、`(MTLTriangleFillMode)-1`、`{0,0,0,0}` 裁剪矩形）确保第一次状态设置一定会执行 Metal API 调用。

3. **完整的绘制 API 覆盖**: 封装了 Metal 的所有绘制方法变体（直接、索引、实例化、间接），使上层代码可以选择最适合的绘制方式。

4. **@autoreleasepool 管理**: Make 方法使用自动释放池和显式 retain 管理 Objective-C 对象的生命周期。

## 性能考量

1. **管线状态切换**: 渲染管线状态切换是 GPU 最昂贵的操作之一，状态跟踪在此处的收益最大。

2. **纹理和采样器绑定**: 跟踪 16 个纹理和采样器的绑定状态，避免在同一纹理反复绑定时的冗余调用。

3. **裁剪矩形比较**: 逐字段比较 4 个整数的开销极低，但可以避免不必要的裁剪矩形更新（GPU 端状态更新）。

4. **setVertexBytes / setFragmentBytes**: 这些方法适用于少量临时数据（如 push constants），避免了创建缓冲区的开销，但有数据大小限制（通常 4KB）。

5. **对象大小**: 状态缓存数组（纹理 16 个 + 采样器 16 个 + 其他状态）使编码器对象本身较大，但每次渲染通道通常只有一个编码器实例。

## 相关文件

- `src/gpu/graphite/mtl/MtlCommandBuffer.h` - 创建和管理渲染编码器
- `src/gpu/graphite/mtl/MtlComputeCommandEncoder.h` - 计算编码器（类似设计）
- `src/gpu/graphite/mtl/MtlBlitCommandEncoder.h` - Blit 编码器（类似设计）
- `src/gpu/graphite/Resource.h` - 资源基类
- `src/gpu/graphite/RenderPassDesc.h` - 渲染通道描述符
