# GrMockBackendSurface

> 源文件
> - include/gpu/ganesh/mock/GrMockBackendSurface.h
> - src/gpu/ganesh/mock/GrMockBackendSurface.cpp

## 概述

`GrMockBackendSurface` 模块为 Ganesh 渲染引擎的 Mock 后端提供表面（Surface）对象的创建和操作接口。该模块实现了 Mock 后端的格式（Format）、纹理（Texture）和渲染目标（RenderTarget）的完整抽象，使测试代码能够在没有真实 GPU 的情况下模拟完整的图形管线操作。

该模块提供了三个命名空间的工厂函数和查询函数：`GrBackendFormats`、`GrBackendTextures` 和 `GrBackendRenderTargets`，用于创建和操作 Mock 后端的各种表面对象。

## 架构位置

该模块位于 Ganesh 后端表面抽象层的 Mock 实现：

```
Skia Graphics Library
└── GPU (Ganesh)
    ├── Backend Surface Abstraction
    │   ├── GrBackendFormat         ← 抽象接口
    │   ├── GrBackendTexture        ← 抽象接口
    │   └── GrBackendRenderTarget  ← 抽象接口
    └── Backend Implementations
        └── Mock Backend
            └── GrMockBackendSurface ← 当前模块（Mock 实现）
```

## 主要类与结构体

### GrMockBackendFormatData

Mock 后端格式数据类，封装格式的具体信息。

**继承关系**: `GrMockBackendFormatData` → `GrBackendFormatData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fColorType` | `GrColorType` | 颜色类型（如 RGBA_8888） |
| `fCompressionType` | `SkTextureCompressionType` | 压缩类型（如 ETC2） |
| `fIsStencilFormat` | `bool` | 是否为模板格式 |

**核心方法**
- `colorType()`: 返回颜色类型
- `compressionType()`: 返回压缩类型
- `isStencilFormat()`: 检查是否为模板格式
- `bytesPerBlock()`: 计算每块字节数
- `stencilBits()`: 返回模板位数（8 位或 0）
- `channelMask()`: 返回颜色通道掩码
- `validate()`: 验证格式的有效性（颜色类型、压缩类型、模板格式三者必须恰好有一个）

### GrMockBackendTextureData

Mock 后端纹理数据类，存储纹理的详细信息。

**继承关系**: `GrMockBackendTextureData` → `GrBackendTextureData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrMockTextureInfo` | Mock 纹理信息 |

**核心方法**
- `info()`: 获取纹理信息
- `isProtected()`: 检查是否为受保护纹理
- `isSameTexture()`: 比较是否为同一纹理（通过 ID 比较）
- `getBackendFormat()`: 获取后端格式对象

### GrMockBackendRenderTargetData

Mock 后端渲染目标数据类，存储渲染目标的详细信息。

**继承关系**: `GrMockBackendRenderTargetData` → `GrBackendRenderTargetData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrMockRenderTargetInfo` | Mock 渲染目标信息 |

**核心方法**
- `info()`: 获取渲染目标信息
- `isProtected()`: 检查是否为受保护渲染目标
- `getBackendFormat()`: 获取后端格式对象

## 公共 API 函数

### GrBackendFormats 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendFormat MakeMockColorType(GrColorType)` | 创建指定颜色类型的 Mock 格式 |
| `GrBackendFormat MakeMockCompressionType(SkTextureCompressionType)` | 创建指定压缩类型的 Mock 格式 |
| `GrBackendFormat MakeMockStencilFormat()` | 创建 Mock 模板格式 |
| `GrColorType AsMockColorType(const GrBackendFormat&)` | 从格式对象提取颜色类型 |
| `SkTextureCompressionType AsMockCompressionType(const GrBackendFormat&)` | 从格式对象提取压缩类型 |
| `bool IsMockStencilFormat(const GrBackendFormat&)` | 检查是否为模板格式 |

### GrBackendTextures 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendTexture MakeMock(int width, int height, skgpu::Mipmapped, const GrMockTextureInfo&, std::string_view label)` | 创建 Mock 纹理对象 |
| `GrMockTextureInfo GetMockTextureInfo(const GrBackendTexture&)` | 从纹理对象提取 Mock 信息 |

### GrBackendRenderTargets 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendRenderTarget MakeMock(int width, int height, int sampleCnt, int stencilBits, const GrMockRenderTargetInfo&)` | 创建 Mock 渲染目标对象 |
| `GrMockRenderTargetInfo GetMockRenderTargetInfo(const GrBackendRenderTarget&)` | 从渲染目标对象提取 Mock 信息 |

## 内部实现细节

### 格式验证机制

`GrMockBackendFormatData::validate()` 确保格式的互斥性：

```cpp
bool validate() const {
    int trueStates = 0;
    if (fCompressionType != SkTextureCompressionType::kNone) trueStates++;
    if (fColorType != GrColorType::kUnknown) trueStates++;
    if (fIsStencilFormat) trueStates++;
    return trueStates == 1;  // 恰好一个为真
}
```

这确保了每个格式对象只表示一种类型（颜色、压缩或模板）。

### 字节数计算

`bytesPerBlock()` 方法根据格式类型计算每块字节数：

1. **压缩格式**: 使用 `SkCompressedDataSize` 计算压缩块大小
2. **模板格式**: 固定返回 4 字节
3. **颜色格式**: 使用 `GrColorTypeBytesPerPixel` 计算像素字节数

### 纹理相等性判断

提供两种级别的相等性判断：

- `equal()`: 完整比较所有字段（包括颜色类型、压缩类型、ID、保护状态）
- `isSameTexture()`: 仅比较纹理 ID，用于判断是否引用同一纹理资源

### 类型安全的向下转型

使用辅助函数 `get_and_cast_data()` 确保类型安全：

```cpp
static const GrMockBackendFormatData* get_and_cast_data(const GrBackendFormat& format) {
    auto data = GrBackendSurfacePriv::GetBackendData(format);
    SkASSERT(!data || data->type() == GrBackendApi::kMock);
    return static_cast<const GrMockBackendFormatData*>(data);
}
```

### 调试信息生成

`toString()` 方法在调试模式下生成可读的格式描述：

```cpp
std::string toString() const override {
#if defined(SK_DEBUG) || defined(GPU_TEST_UTILS)
    std::string str = GrColorTypeToStr(fColorType);
    str += "-";
    str += skgpu::CompressionTypeToStr(fCompressionType);
    if (fIsStencilFormat) {
        str += "-stencil";
    }
    return str;
#else
    return "";
#endif
}
```

### 采样数标准化

在创建渲染目标时，确保采样数至少为 1：

```cpp
return GrBackendSurfacePriv::MakeGrBackendRenderTarget(
    width, height,
    std::max(1, sampleCnt),  // 标准化采样数
    stencilBits,
    // ...
);
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrBackendSurfacePriv` | 访问后端表面的私有构造函数 |
| `GrMockTypes` | 使用 Mock 类型信息结构体 |
| `SkCompressedDataUtils` | 计算压缩纹理的数据大小 |
| `GrUtil` | 使用 Ganesh 工具函数 |
| `GrColorTypeBytesPerPixel` | 计算颜色类型字节数 |
| `GrColorTypeChannelFlags` | 获取颜色通道掩码 |
| `GrGetColorTypeDesc` | 获取颜色类型描述符 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| 测试代码 | 使用 Mock 表面进行单元测试 |
| `GrMockGpu` | 使用 Mock 表面创建 GPU 资源 |
| `GrContext` 测试 | 创建 Mock 上下文时使用 |
| 表面工厂 | 作为表面创建的后端实现 |

## 设计模式与设计决策

### 1. 工厂模式

通过命名空间函数提供统一的工厂接口：
- `GrBackendFormats::MakeMock*()` 创建格式对象
- `GrBackendTextures::MakeMock()` 创建纹理对象
- `GrBackendRenderTargets::MakeMock()` 创建渲染目标对象

### 2. 策略模式

通过继承 `GrBackendFormatData`、`GrBackendTextureData` 等基类，实现 Mock 后端的特定策略，允许多态访问。

### 3. 类型状态模式

`GrMockBackendFormatData` 使用三个布尔状态（颜色类型、压缩类型、模板格式）的互斥组合表示不同类型的格式。

### 4. 数据驱动设计

所有 Mock 对象都是数据驱动的，不包含复杂逻辑，便于测试和验证。

### 5. 命名空间隔离

使用命名空间而非类静态方法，避免头文件依赖，提高编译速度。

### 6. 任意数据容器（Any 模式）

使用 `AnyFormatData`、`AnyTextureData` 等类型擦除容器，允许存储不同后端的数据而无需虚函数开销。

### 7. RAII 和值语义

所有对象都使用值语义，依赖自动内存管理，避免手动资源管理。

## 性能考量

### 1. 内联数据存储

Mock 对象直接存储数据（如 `fInfo`），避免额外的间接访问和缓存未命中。

### 2. 编译期类型检查

使用 `#if defined(SK_DEBUG)` 限制调试代码，确保发布版本没有类型检查开销。

### 3. 零虚函数调用（在 Release 模式）

虽然继承自基类，但编译器可以在已知类型的情况下进行去虚化优化。

### 4. 快速 ID 比较

纹理相等性通过整数 ID 比较实现（`isSameTexture`），是 O(1) 操作。

### 5. 延迟字符串生成

`toString()` 仅在调试模式下生成字符串，避免生产代码的字符串分配开销。

### 6. 固定大小结构

所有数据类使用固定大小的成员变量，便于内存布局优化和缓存对齐。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/mock/GrMockTypes.h` | Mock 类型信息定义 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端表面抽象接口 |
| `src/gpu/ganesh/GrBackendSurfacePriv.h` | 后端表面私有构造函数 |
| `include/core/SkTextureCompressionType.h` | 纹理压缩类型定义 |
| `src/core/SkCompressedDataUtils.h` | 压缩数据计算工具 |
| `src/gpu/ganesh/GrUtil.h` | Ganesh 通用工具函数 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | Ganesh 私有类型定义 |
| `src/gpu/ganesh/mock/GrMockGpu.h` | Mock GPU 实现 |
| `src/gpu/GpuTypesPriv.h` | GPU 通用私有类型 |
