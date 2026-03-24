# ResourceTypes - Graphite GPU 资源类型定义

> 源文件: `src/gpu/graphite/ResourceTypes.h`

## 概述

`ResourceTypes.h` 是 Skia Graphite 渲染后端的核心类型定义文件，定义了 GPU 资源管理中使用的所有枚举类型和关键数据结构。这些类型涵盖了深度/模板标志、加载/存储操作、缓冲区类型、数据布局、纹理用途、采样器描述等方面，是整个 Graphite 资源系统的类型基础。

## 架构位置

`ResourceTypes.h` 位于 Graphite 资源管理子系统的底层，被几乎所有涉及 GPU 资源的组件引用：

```
Graphite 资源管理层
  ├── ResourceTypes.h (本文件 - 类型定义基础)
  ├── Buffer / Texture (具体资源类型)
  ├── ResourceProvider (资源创建与缓存)
  ├── CommandBuffer (命令录制，使用 LoadOp/StoreOp)
  ├── RenderPass (渲染通道，使用 DepthStencilFlags)
  └── Pipeline (管线，使用 SamplerDesc/Layout)
```

## 主要类与结构体

### `BindBufferInfo`

用于传递缓冲区绑定信息到 CommandBuffer 的结构体：

```cpp
struct BindBufferInfo {
    const Buffer* fBuffer = nullptr;  // 缓冲区指针
    uint32_t fOffset = 0;             // 偏移量
    uint32_t fSize = 0;               // 大小
};
```

- 支持 `explicit operator bool()` 转换，判断缓冲区是否有效
- 相等比较在 `fBuffer` 为空时仅比较指针，非空时还比较 offset 和 size

### `ImmutableSamplerInfo`

不可变采样器信息，用于 YCbCr 转换等场景：

```cpp
struct ImmutableSamplerInfo {
    uint32_t fNonFormatYcbcrConversionInfo = 0;  // YCbCr 转换信息
    uint64_t fFormat = 0;                         // 已知或外部格式
};
```

### `SamplerDesc`

采样器描述符，紧凑编码纹理采样参数：

- 将 TileMode（X/Y）、FilterMode、MipmapMode 和不可变采样器信息编码到单个 `uint32_t` 中
- 支持已知格式（2 个 uint32）和外部格式（3 个 uint32）的不同存储需求
- 提供 `asSpan()` 方法根据格式类型返回不同长度的数据视图

### `WorkgroupSize`（通过 ComputeTypes 引用）

此文件的类型被计算管线广泛使用。

## 公共 API 函数

### 采样数转换工具

| 函数 | 说明 |
|------|------|
| `SamplesToKey(SampleCount)` | 将采样数（1/2/4/8/16）转换为 3 位键值（0-4） |
| `KeyToSamples(uint32_t)` | 将键值转换回采样数 |

### 布局字符串转换

| 函数 | 说明 |
|------|------|
| `LayoutString(Layout)` | 将 Layout 枚举转换为人可读字符串 |

### SamplerDesc 方法

| 方法 | 返回类型 | 说明 |
|------|----------|------|
| `tileModeX()` / `tileModeY()` | `SkTileMode` | 获取 X/Y 方向平铺模式 |
| `filterMode()` | `SkFilterMode` | 获取过滤模式 |
| `mipmap()` | `SkMipmapMode` | 获取 Mipmap 模式 |
| `desc()` | `uint32_t` | 获取原始描述字段 |
| `format()` / `externalFormatMSBs()` | `uint32_t` | 获取格式信息 |
| `isImmutable()` | `bool` | 是否使用不可变采样器 |
| `usesExternalFormat()` | `bool` | 是否使用外部格式 |
| `samplingOptions()` | `SkSamplingOptions` | 获取硬件采样选项 |
| `immutableSamplerInfo()` | `ImmutableSamplerInfo` | 获取不可变采样器信息 |
| `asSpan()` | `SkSpan<const uint32_t>` | 以 Span 形式返回数据用于哈希/比较 |

## 内部实现细节

### 枚举类型详解

#### `DstReadStrategy` - 目标读取策略
定义混合操作时如何访问当前目标像素：
- `kNoneRequired` - 不需要读取目标
- `kTextureCopy` - 通过纹理拷贝
- `kTextureSample` - 直接纹理采样（待实现，b/238756862）
- `kReadFromInput` - 从输入读取
- `kFramebufferFetch` - 帧缓冲获取

#### `LoadOp` / `StoreOp` - 加载/存储操作
RenderPass 开始和结束时的操作：
- LoadOp: `kLoad`（加载）、`kClear`（清除）、`kDiscard`（丢弃）
- StoreOp: `kStore`（存储）、`kDiscard`（丢弃）

#### `BufferType` - 缓冲区类型
定义 GPU 缓冲区的用途，包括：
- 基础类型: 顶点、索引、传输（CPU->GPU / GPU->CPU）、Uniform、存储、查询
- GPU 专用类型: 间接分派、顶点存储、索引存储

#### `Layout` - 数据布局
主机可共享缓冲区的数据布局要求：
- `kStd140` / `kStd140_F16` - OpenGL std140 布局（含 F16 变体）
- `kStd430` / `kStd430_F16` - OpenGL std430 布局（含 F16 变体）
- `kMetal` - Metal 特定布局

#### `AccessPattern` - 访问模式
指示资源的预期访问模式以优化内存类型选择：
- `kGpuOnly` - 仅 GPU 访问，优先使用私有内存
- `kHostVisible` - 需要 CPU 可见
- `kGpuOnlyCopySrc` - GPU 专用但支持拷贝源（调试用）

#### `TextureUsage` - 纹理用途（位掩码）
```
kRender   = 0x01  // 渲染附件
kMSRTSS   = 0x02  // MSAA 渲染到单采样
kSample   = 0x04  // 着色器采样
kCopySrc  = 0x08  // 拷贝源
kCopyDst  = 0x10  // 拷贝目标
kStorage  = 0x20  // 计算管线读写
kHostCopy = 0x40  // 主机直接写入
```

#### 其他枚举
- `ClearBuffer` - 是否清零缓冲区
- `Discardable` - 渲染后内容是否可丢弃
- `Ownership` - 资源所有权（自有/包装）
- `Shareable` - 资源是否可多用户共享（kNo/kScratch/kYes）
- `Tiling` - 纹理内存排列（Optimal/Linear）

### SamplerDesc 位编码

SamplerDesc 使用位域将多个采样参数紧凑编码到单个 `uint32_t` 中：

```
位字段布局:
[TileModeX] [TileModeY] [FilterMode] [MipmapMode] [ImmutableSamplerInfo...]
 2 bits       2 bits      1 bit        2 bits        剩余位
```

注意立方体（Cubic）采样在着色器中处理，实际纹理采样使用最近邻模式。

### 唯一对象表示保证

`SamplerDesc` 的三个 `uint32_t` 成员按特定顺序排列，确保 `has_unique_object_representation` 为真，从而可以使用 `SkGoodHash` 直接哈希。外部格式的 `uint64_t` 被拆分为两个 `uint32_t` 存储以维持此保证。

## 依赖关系

- **include/core/SkSamplingOptions.h**: 采样选项类型
- **include/core/SkSpan.h**: Span 视图类型
- **include/core/SkTileMode.h**: 平铺模式枚举
- **include/gpu/graphite/GraphiteTypes.h**: Graphite 公共类型（DepthStencilFlags, SampleCount）
- **include/private/base/SkTo.h**: 类型转换工具
- **src/base/SkEnumBitMask.h**: 枚举位掩码操作宏
- **src/base/SkMathPriv.h**: SkNextLog2 等数学工具

## 设计模式与设计决策

### 位掩码枚举模式

`DepthStencilFlags`、`SampleCount`、`TextureUsage` 使用 `SK_MAKE_BITMASK_OPS` 宏启用位运算操作符。值得注意的是，`DepthStencilFlags` 和 `SampleCount` 在公共头文件（GraphiteTypes.h）中作为普通枚举类出现，仅在内部头文件中启用位掩码操作，实现了公共 API 的简洁性。

### 紧凑键值编码

`SamplesToKey()` 将 5 种有效采样数映射到 3 位键值空间，最小化管线状态键的存储需求。`SamplerDesc` 将多个采样参数编码到单个 `uint32_t`，减少哈希和比较的开销。

### 类型安全枚举

所有枚举均使用 `enum class`，避免隐式转换。布尔语义的枚举（如 `ClearBuffer`、`Discardable`）显式指定基础类型为 `bool`，提供类型安全的同时保持语义清晰。

## 性能考量

- `SamplerDesc` 设计为紧凑的 12 字节结构（3 个 `uint32_t`），适合作为哈希表键
- 所有转换函数均为 `constexpr`，在编译时求值
- `asSpan()` 根据是否使用不可变采样器/外部格式返回 1-3 个 `uint32_t` 的视图，避免传递不必要数据
- `BindBufferInfo` 的相等比较对空缓冲区进行短路优化
- 枚举使用最小基础类型（`uint8_t`）减少结构体填充

## 相关文件

- `include/gpu/graphite/GraphiteTypes.h` - 公共 Graphite 类型（DepthStencilFlags, SampleCount 定义）
- `src/gpu/graphite/DrawTypes.h` - 绘制相关类型
- `src/gpu/graphite/Caps.h` - GPU 能力查询（使用这些类型）
- `src/gpu/graphite/Buffer.h` - Buffer 类定义
- `src/gpu/graphite/TextureProxy.h` - 纹理代理（使用 TextureUsage）
- `include/core/SkSamplingOptions.h` - 公共采样选项类型
- `include/core/SkTileMode.h` - 平铺模式枚举
