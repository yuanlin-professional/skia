# GrMockTypes

> 源文件
> - include/gpu/ganesh/mock/GrMockTypes.h
> - src/gpu/ganesh/mock/GrMockTypes.cpp

## 概述

`GrMockTypes` 模块提供了 Mock GPU 后端的类型定义和配置选项，用于测试和开发目的。该模块定义了模拟纹理信息、渲染目标信息、表面信息以及 Mock 上下文的能力配置选项，使开发者能够在没有真实 GPU 的情况下测试 Skia 的图形渲染管线。

Mock 后端是 Ganesh GPU 架构中的一个轻量级测试后端，不执行实际的 GPU 操作，而是提供一个假的实现用于单元测试和功能验证。

## 架构位置

该模块位于 Ganesh 渲染引擎的 Mock 后端层：

```
Skia Graphics Library
└── GPU (Ganesh)
    └── Backend Implementations
        └── Mock Backend          ← 当前模块
            ├── GrMockTypes       ← 类型定义
            ├── GrMockGpu         ← GPU 实现
            └── GrMockCaps        ← 能力查询
```

Mock 后端与 Vulkan、Metal、OpenGL 等真实后端处于同一架构层次，但提供模拟实现。

## 主要类与结构体

### GrMockTextureInfo

纹理信息结构体，用于描述 Mock 纹理的属性。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorType` | `GrColorType` | 颜色类型（如 RGBA_8888） |
| `fCompressionType` | `SkTextureCompressionType` | 压缩类型（如 ETC2、BC1） |
| `fID` | `int` | 纹理的唯一标识符 |
| `fProtected` | `skgpu::Protected` | 是否为受保护的纹理 |

**构造函数与方法**
- `GrMockTextureInfo()`: 默认构造函数，创建未初始化的纹理信息
- `GrMockTextureInfo(colorType, compressionType, id, isProtected)`: 完整构造函数
- `getBackendFormat()`: 获取后端格式对象
- `compressionType()`: 获取压缩类型
- `colorType()`: 获取颜色类型（仅未压缩纹理）
- `id()`: 获取纹理 ID
- `isProtected()`: 检查是否为受保护纹理

### GrMockRenderTargetInfo

渲染目标信息结构体，描述 Mock 渲染目标的属性。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorType` | `GrColorType` | 颜色类型 |
| `fID` | `int` | 渲染目标的唯一标识符 |
| `fProtected` | `skgpu::Protected` | 是否为受保护的渲染目标 |

### GrMockSurfaceInfo

表面信息结构体，包含表面的通用属性。

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fSampleCount` | `uint32_t` | 多重采样数量 |
| `fLevelCount` | `uint32_t` | Mipmap 层级数量 |
| `fProtected` | `skgpu::Protected` | 是否为受保护表面 |
| `fColorType` | `GrColorType` | 颜色类型 |
| `fCompressionType` | `SkTextureCompressionType` | 压缩类型 |

### GrMockOptions

Mock 上下文配置选项结构体，用于配置 Mock GPU 的能力。

**继承关系**: 无继承关系，独立配置结构体

**关键成员变量**

| 类别 | 成员变量 | 类型 | 默认值 | 说明 |
|------|---------|------|--------|------|
| **能力选项** | `fMipmapSupport` | `bool` | `false` | 是否支持 Mipmap |
| | `fDrawInstancedSupport` | `bool` | `false` | 是否支持实例化绘制 |
| | `fHalfFloatVertexAttributeSupport` | `bool` | `false` | 是否支持半精度浮点顶点属性 |
| | `fMapBufferFlags` | `uint32_t` | `0` | 缓冲区映射标志 |
| | `fMaxTextureSize` | `int` | `2048` | 最大纹理尺寸 |
| | `fMaxRenderTargetSize` | `int` | `2048` | 最大渲染目标尺寸 |
| | `fMaxWindowRectangles` | `int` | `0` | 最大窗口矩形数量 |
| | `fMaxVertexAttributes` | `int` | `16` | 最大顶点属性数量 |
| **着色器能力** | `fIntegerSupport` | `bool` | `false` | 是否支持整数着色器 |
| | `fFlatInterpolationSupport` | `bool` | `false` | 是否支持平面插值 |
| | `fMaxVertexSamplers` | `int` | `0` | 最大顶点采样器数量 |
| | `fMaxFragmentSamplers` | `int` | `8` | 最大片段采样器数量 |
| | `fShaderDerivativeSupport` | `bool` | `true` | 是否支持着色器导数 |
| | `fDualSourceBlendingSupport` | `bool` | `false` | 是否支持双源混合 |
| **GPU 选项** | `fFailTextureAllocations` | `bool` | `false` | 是否模拟纹理分配失败 |
| **格式配置** | `fConfigOptions` | `ConfigOptions[kGrColorTypeCnt]` | - | 各颜色类型的配置 |
| | `fCompressedOptions` | `ConfigOptions[kSkTextureCompressionTypeCount]` | - | 各压缩类型的配置 |

**ConfigOptions 结构**
- `Renderability`: 可渲染性（`kNo` / `kNonMSAA` / `kMSAA`）
- `fTexturable`: 是否可作为纹理

**默认配置**
- `RGBA_8888` 和 `BGRA_8888`: 可纹理化和可渲染（非 MSAA）
- `Alpha_8`、`BGR_565`、`RGB_565`: 仅可纹理化
- `ETC2_RGB8_UNORM`、`BC1_RGB8_UNORM`、`BC1_RGBA8_UNORM`: 压缩纹理可用

## 公共 API 函数

### GrMockTextureInfo

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendFormat getBackendFormat() const` | 获取纹理的后端格式对象 |
| `SkTextureCompressionType compressionType() const` | 返回纹理的压缩类型 |
| `GrColorType colorType() const` | 返回颜色类型（仅未压缩纹理） |
| `int id() const` | 返回纹理的唯一标识符 |
| `skgpu::Protected getProtected() const` | 获取保护状态枚举值 |
| `bool isProtected() const` | 检查是否为受保护纹理 |
| `bool operator==(const GrMockTextureInfo&) const` | 比较两个纹理信息是否相等 |

### GrMockRenderTargetInfo

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendFormat getBackendFormat() const` | 获取渲染目标的后端格式对象 |
| `GrColorType colorType() const` | 返回颜色类型 |
| `skgpu::Protected getProtected() const` | 获取保护状态枚举值 |
| `bool isProtected() const` | 检查是否为受保护渲染目标 |
| `bool operator==(const GrMockRenderTargetInfo&) const` | 比较两个渲染目标信息是否相等 |

### 辅助函数

| 函数签名 | 功能描述 |
|---------|---------|
| `GrMockSurfaceInfo GrMockTextureSpecToSurfaceInfo(const GrMockTextureSpec&, uint32_t sampleCount, uint32_t levelCount, GrProtected)` | 将纹理规格转换为表面信息 |

## 内部实现细节

### 类型验证机制

在 `GrMockTextureInfo` 的构造函数中，实施了严格的类型验证：

```cpp
if (fCompressionType != SkTextureCompressionType::kNone) {
    SkASSERT(colorType == GrColorType::kUnknown);
}
```

这确保了压缩纹理不能同时指定颜色类型，维护了类型系统的一致性。

### 格式转换流程

`getBackendFormat()` 方法根据纹理属性创建相应的后端格式：

1. **未压缩纹理**: 使用 `GrBackendFormats::MakeMockColorType(fColorType)`
2. **压缩纹理**: 使用 `GrBackendFormats::MakeMockCompressionType(fCompressionType)`

### 默认配置初始化

`GrMockOptions` 构造函数默认启用常见的颜色格式：
- 将 `RGBA_8888` 和 `BGRA_8888` 配置为可渲染和可纹理化
- 启用三种常见的压缩格式支持
- 设置合理的资源限制（2048x2048 纹理尺寸）

### 表面信息转换

`GrMockTextureSpecToSurfaceInfo` 函数整合多个参数：
- 从 `GrMockTextureSpec` 提取颜色类型和压缩类型
- 添加采样数、层级数和保护状态
- 返回统一的 `GrMockSurfaceInfo` 结构

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `SkTextureCompressionType` | 定义纹理压缩类型枚举 |
| `GrTypesPriv` | 提供 Ganesh 私有类型定义 |
| `GrColorType` | 定义颜色类型枚举 |
| `skgpu::Protected` | 定义内存保护枚举 |
| `GrBackendFormat` | 后端格式抽象接口 |
| `GrBackendSurface` | 后端表面类型定义 |
| `GrMockBackendSurface` | Mock 后端表面工厂函数 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrMockGpu` | 使用 `GrMockOptions` 配置 GPU 能力 |
| `GrMockCaps` | 根据 `GrMockOptions` 创建能力对象 |
| `GrBackendSurface` | 使用 Mock 类型信息创建后端表面 |
| 测试代码 | 使用 Mock 类型进行单元测试 |

## 设计模式与设计决策

### 1. 配置对象模式

`GrMockOptions` 作为配置对象，在创建 Mock 上下文时传入，避免了构造函数参数爆炸问题。

### 2. 类型安全设计

通过枚举类型和断言确保：
- 压缩纹理和颜色类型互斥
- 所有 ID 非零（`SkASSERT(fID)`）
- 类型查询前验证状态

### 3. POD 结构设计

所有信息结构体都是 Plain Old Data 类型，便于：
- 快速复制和传递
- 在 C/C++ 边界安全使用
- 减少内存分配开销

### 4. 测试友好设计

Mock 后端的设计目标是测试，因此：
- 提供失败模拟选项（`fFailTextureAllocations`）
- 所有能力都可配置
- 不依赖真实 GPU 驱动

### 5. 格式配置数组

使用数组存储所有可能的格式配置（`fConfigOptions` 和 `fCompressedOptions`），提供 O(1) 查询性能。

## 性能考量

### 1. 零开销抽象

Mock 类型使用简单的整数 ID 和枚举值，没有虚函数调用和动态分配，确保测试代码性能不受影响。

### 2. 内联函数

所有 getter 方法都在头文件中实现，编译器可以完全内联这些调用。

### 3. 默认配置优化

构造函数中的默认配置初始化仅执行一次，后续可以重用相同的配置对象。

### 4. 编译期常量

`kSkTextureCompressionTypeCount` 等常量在编译期确定，避免运行时计算。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/mock/GrMockBackendSurface.h` | Mock 后端表面创建函数 |
| `src/gpu/ganesh/mock/GrMockTypesPriv.h` | Mock 类型的私有辅助定义 |
| `src/gpu/ganesh/mock/GrMockGpu.h/.cpp` | Mock GPU 实现 |
| `src/gpu/ganesh/mock/GrMockCaps.h/.cpp` | Mock 能力查询实现 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端表面抽象接口 |
| `include/core/SkTextureCompressionType.h` | 纹理压缩类型定义 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | Ganesh 私有类型定义 |
