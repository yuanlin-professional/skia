# RenderPassDesc (渲染通道描述)

> 源文件：[src/gpu/graphite/RenderPassDesc.h](../../../../src/gpu/graphite/RenderPassDesc.h)、[src/gpu/graphite/RenderPassDesc.cpp](../../../../src/gpu/graphite/RenderPassDesc.cpp)

## 概述

`RenderPassDesc` 是描述一个完整渲染通道（render pass）配置的核心结构体。它包含颜色附件、颜色解析附件、深度/模板附件的格式与操作描述，以及写入 swizzle、采样数、清除值和目标读取策略等信息。`RenderPassDesc` 是生成管线缓存键（pipeline key）的关键输入之一，直接影响管线编译和渲染通道创建。

`AttachmentDesc` 是附件的子描述，紧凑地封装了纹理格式、加载/存储操作和采样数，仅占用 4 字节内存。

## 架构位置

`RenderPassDesc` 位于渲染管线配置与渲染通道创建之间：

- **上游**：`DrawContext::flush()` 和 `DrawPass::Make()` 根据目标纹理信息和绘制需求构建 `RenderPassDesc`。
- **下游**：
  - `Caps::makeGraphicsPipelineKey()` 使用 `RenderPassDesc` 生成管线缓存键。
  - `CommandBuffer` 使用 `RenderPassDesc` 配置实际的 GPU 渲染通道。
  - `SerializationUtils` 使用 `RenderPassDesc` 进行管线序列化。

## 主要类与结构体

### `AttachmentDesc`
描述单个附件的紧凑结构体（4 字节）：
- `fFormat` (TextureFormat)：纹理格式，`kUnsupported` 表示附件未使用。
- `fLoadOp` (LoadOp)：加载操作（`kLoad`、`kClear`、`kDiscard`）。
- `fStoreOp` (StoreOp)：存储操作（`kStore`、`kDiscard`）。
- `fSampleCount` (SampleCount)：采样数。
- `operator==`：特殊处理两个均为 `kUnsupported` 的附件视为相等。
- `isCompatible(TextureInfo)`：检查附件描述是否与纹理信息兼容（格式和采样数匹配）。
- `toString()`：返回可读字符串表示。

### `RenderPassDesc`
完整的渲染通道描述：
- `fColorAttachment`：颜色附件描述。
- `fColorResolveAttachment`：颜色解析附件描述（MSAA 解析时使用）。
- `fDepthStencilAttachment`：深度/模板附件描述。
- `fWriteSwizzle` (Swizzle)：写入通道重排（在着色器中应用）。
- `fSampleCount`：渲染通道的整体采样数。
- `fDstReadStrategy`：目标读取策略。
- `fClearColor / fClearDepth / fClearStencil`：清除值。

## 公共 API 函数

### `RenderPassDesc::Make`
```cpp
static RenderPassDesc Make(const Caps*, const TextureInfo& targetInfo,
                           LoadOp, StoreOp, DepthStencilFlags, clearColor,
                           bool requiresMSAA, Swizzle writeSwizzle, DstReadStrategy);
```
工厂方法，根据目标纹理信息和渲染需求构建完整的渲染通道描述。处理三种 MSAA 场景：
1. **直接多采样**：目标已是多采样纹理，直接使用。
2. **MSAA 渲染到单采样（MSRTSS）**：利用硬件扩展，无需额外 MSAA 附件。
3. **显式 MSAA 附件 + 解析**：创建多采样颜色附件和单采样解析附件。

### `toString()` / `toPipelineLabel()`
- `toString()`：完整的调试字符串，包含所有字段。
- `toPipelineLabel()`：仅包含影响管线编译的固定状态，用于管线标签。区分三种 MSAA 模式的标签格式：`xN`（直接采样）、`xN->1`（MSRTSS 或显式解析）。

### `AttachmentDesc::isCompatible`
检查附件描述与实际纹理信息的兼容性（格式和采样数匹配）。

## 内部实现细节

### MSAA 配置策略
`RenderPassDesc::Make` 中的 MSAA 处理逻辑：
- 如果 `requiresMSAA` 为 true，从 `Caps` 获取兼容的 MSAA 采样数。
- 如果目标是单采样且不支持 MSRTSS，则：
  - 颜色附件设为多采样，加载操作为 `kDiscard`（除非原始 loadOp 为 `kClear`），存储操作为 `kDiscard`（MSAA 数据不保留）。
  - 解析附件设为单采样，继承原始的加载/存储操作。
- 深度/模板附件在需要 MSAA 时，强制使用 `DepthStencil` 组合格式（减少管线变体）。

### 深度/模板清除策略
深度清除值固定为 1.0f（GPU 历史 OpenGL 默认值，深度测试使用 less-than 比较）。模板清除值固定为 0。这些值在渲染通道开始时一次性清除。

### 管线标签生成
`toPipelineLabel()` 仅包含影响管线编译的状态，有意省略加载/存储操作等运行时配置（除非涉及 MSAA 从解析附件加载的情况）。格式为 `RP((colorFmt+dsFmt sampleStr).swizzle[loadStr])`。

## 依赖关系

### 上游依赖
- `Caps`：能力查询（MSAA 支持、深度/模板格式选择）。
- `TextureInfo`：目标纹理信息。
- `TextureFormat`：纹理格式枚举和工具函数。
- `ResourceTypes.h`：`LoadOp`、`StoreOp`、`SampleCount`、`DepthStencilFlags`、`DstReadStrategy` 等枚举。
- `Swizzle`：通道重排。

### 下游使用者
- `DrawPass::Make()`：创建绘制通道时构建 RenderPassDesc。
- `Caps::makeGraphicsPipelineKey()`：管线键生成。
- `CommandBuffer`：渲染通道执行。
- `SerializationUtils`：管线序列化。

## 设计模式与设计决策

1. **紧凑附件描述**：`AttachmentDesc` 仅 4 字节，通过枚举的位宽紧凑编码，支持高效比较和序列化。

2. **工厂方法封装复杂性**：`Make()` 方法封装了 MSAA 配置的复杂分支逻辑，调用方只需提供高层需求（是否需要 MSAA）而非具体的附件配置。

3. **深度/模板格式统一化**：在需要 MSAA 时，强制使用组合深度+模板格式，减少管线变体数量。

4. **管线标签与完整描述分离**：`toPipelineLabel()` 仅包含影响编译的状态，避免清除值等运行时差异导致管线重复编译。

## 性能考量

- `AttachmentDesc` 的 4 字节大小使得 `RenderPassDesc` 的比较操作非常高效。
- MSAA 配置在 `Make()` 时一次性确定，后续使用无需重复计算。
- 深度/模板格式统一化减少了管线变体数量，提高管线缓存命中率。

## 相关文件

- `src/gpu/graphite/Caps.h/.cpp`：能力查询和格式选择。
- `src/gpu/graphite/DrawPass.h/.cpp`：绘制通道，使用 RenderPassDesc。
- `src/gpu/graphite/CommandBuffer.h/.cpp`：命令缓冲区，执行渲染通道。
- `src/gpu/graphite/SerializationUtils.h/.cpp`：管线序列化。
- `src/gpu/graphite/ResourceTypes.h`：资源类型枚举。
- `src/gpu/graphite/TextureFormat.h`：纹理格式定义。
