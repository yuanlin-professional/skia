# GrMtlBackendSurface

> 源文件
> - include/gpu/ganesh/mtl/GrMtlBackendSurface.h
> - src/gpu/ganesh/mtl/GrMtlBackendSurface.mm

## 概述

`GrMtlBackendSurface` 模块为 Ganesh 渲染引擎提供 Metal 后端表面（Surface）对象的创建和操作接口。该模块实现了 Metal 后端的格式（Format）、纹理（Texture）和渲染目标（RenderTarget）的完整封装，是 Skia 与 Metal 图形 API 交互的核心桥梁。

该模块提供了三个命名空间的工厂函数和查询函数：`GrBackendFormats`、`GrBackendTextures` 和 `GrBackendRenderTargets`，用于创建和操作 Metal 后端的各种表面对象。

## 架构位置

该模块位于 Ganesh 后端表面抽象层的 Metal 实现：

```
Skia Graphics Library
└── GPU (Ganesh)
    ├── Backend Surface Abstraction
    │   ├── GrBackendFormat         ← 抽象接口
    │   ├── GrBackendTexture        ← 抽象接口
    │   └── GrBackendRenderTarget  ← 抽象接口
    └── Backend Implementations
        └── Metal Backend
            ├── GrMtlBackendSurface  ← 当前模块（Metal 实现）
            ├── GrMtlGpu             ← GPU 实现
            └── GrMtlTexture         ← 纹理管理
```

## 主要类与结构体

### GrMtlBackendFormatData

Metal 后端格式数据类，封装 Metal 像素格式。

**继承关系**: `GrMtlBackendFormatData` → `GrBackendFormatData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFormat` | `MTLPixelFormat` | Metal 像素格式枚举值 |

**核心方法**

| 方法 | 功能描述 |
|------|---------|
| `asMtlFormat()` | 返回 Metal 像素格式枚举值 |
| `compressionType()` | 返回压缩类型 |
| `bytesPerBlock()` | 计算每块字节数 |
| `stencilBits()` | 返回模板位数 |
| `channelMask()` | 返回颜色通道掩码 |
| `desc()` | 返回颜色格式描述符 |

### GrMtlBackendTextureData

Metal 后端纹理数据类，存储 Metal 纹理信息。

**继承关系**: `GrMtlBackendTextureData` → `GrBackendTextureData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTexInfo` | `GrMtlTextureInfo` | Metal 纹理信息（包含 `id<MTLTexture>` 句柄） |

**核心方法**

| 方法 | 功能描述 |
|------|---------|
| `info()` | 获取 Metal 纹理信息 |
| `isProtected()` | 检查是否为受保护内存（Metal 不支持，返回 false） |
| `isSameTexture()` | 比较是否为同一纹理（通过 `GrMtlTextureInfo` 比较） |
| `getBackendFormat()` | 获取后端格式对象 |

### GrMtlBackendRenderTargetData

Metal 后端渲染目标数据类，存储渲染目标的 Metal 纹理信息。

**继承关系**: `GrMtlBackendRenderTargetData` → `GrBackendRenderTargetData`

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fTexInfo` | `GrMtlTextureInfo` | Metal 纹理信息 |

**核心方法**

与 `GrMtlBackendTextureData` 类似，提供纹理信息访问和格式查询功能。

## 公共 API 函数

### GrBackendFormats 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendFormat MakeMtl(GrMTLPixelFormat format)` | 创建指定 Metal 像素格式的 `GrBackendFormat` 对象 |
| `GrMTLPixelFormat AsMtlFormat(const GrBackendFormat&)` | 从格式对象提取 Metal 像素格式 |

### GrBackendTextures 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendTexture MakeMtl(int width, int height, skgpu::Mipmapped, const GrMtlTextureInfo& mtlInfo, std::string_view label = {})` | 创建 Metal 纹理对象 |
| `bool GetMtlTextureInfo(const GrBackendTexture&, GrMtlTextureInfo*)` | 从纹理对象提取 Metal 纹理信息 |

### GrBackendRenderTargets 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `GrBackendRenderTarget MakeMtl(int width, int height, const GrMtlTextureInfo& mtlInfo)` | 创建 Metal 渲染目标对象 |
| `bool GetMtlTextureInfo(const GrBackendRenderTarget&, GrMtlTextureInfo*)` | 从渲染目标提取 Metal 纹理信息 |

## 内部实现细节

### ARC 编译要求

文件使用 Objective-C++ 和 ARC（Automatic Reference Counting）：

```cpp
#if !__has_feature(objc_arc)
#error This file must be compiled with Arc. Use -fobjc-arc flag
#endif
```

### 压缩类型映射

`compressionType()` 方法映射 Metal 格式到 Skia 压缩类型：

```cpp
SkTextureCompressionType compressionType() const override {
    return GrMtlFormatToCompressionType(fFormat);
}
```

Metal 支持的压缩格式包括 PVRTC、ETC2、ASTC 等，取决于硬件平台。

### 格式描述符生成

`desc()` 方法生成颜色格式描述符：

```cpp
GrColorFormatDesc desc() const override {
    return GrMtlFormatDesc(fFormat);
}
```

描述符包含颜色空间、通道顺序、数据类型等信息。

### 纹理信息相等性判断

Metal 纹理通过 `GrMtlTextureInfo` 比较：

```cpp
bool equal(const GrBackendTextureData* that) const override {
    return this->isSameTexture(that);
}

bool isSameTexture(const GrBackendTextureData* that) const override {
    if (auto otherMtl = static_cast<const GrMtlBackendTextureData*>(that)) {
        return fTexInfo == otherMtl->fTexInfo;
    }
    return false;
}
```

`GrMtlTextureInfo` 内部比较 `MTLTexture` 对象指针。

### 采样数标准化

在创建渲染目标时，确保采样数至少为 1：

```cpp
return GrBackendSurfacePriv::MakeGrBackendRenderTarget(
    width, height,
    std::max(1, GrMtlTextureInfoSampleCount(mtlInfo)),  // 标准化采样数
    /*stencilBits=*/0,
    GrBackendApi::kMetal,
    /*framebufferOnly=*/false,  // TODO: 从 mtlInfo.fTexture->framebufferOnly 设置
    GrMtlBackendRenderTargetData(mtlInfo));
```

### 格式无效值处理

当格式无效时，返回 0（`MTLPixelFormatInvalid`）：

```cpp
GrMTLPixelFormat AsMtlFormat(const GrBackendFormat& format) {
    if (format.isValid() && format.backend() == GrBackendApi::kMetal) {
        const GrMtlBackendFormatData* data = get_and_cast_data(format);
        SkASSERT(data);
        return data->asMtlFormat();
    }
    // MTLPixelFormatInvalid == 0
    return GrMTLPixelFormat(0);
}
```

### 调试字符串生成

`toString()` 方法在调试模式下生成可读的格式描述：

```cpp
std::string toString() const override {
#if defined(SK_DEBUG) || GPU_TEST_UTILS
    return skgpu::MtlFormatToString(fFormat);
#else
    return "";
#endif
}
```

### 像素格式提取

从 `GrMtlTextureInfo` 提取像素格式：

```cpp
GrBackendFormat getBackendFormat() const override {
    return GrBackendFormats::MakeMtl(GrGetMTLPixelFormatFromMtlTextureInfo(fTexInfo));
}
```

`GrGetMTLPixelFormatFromMtlTextureInfo` 从 `MTLTexture` 对象查询像素格式。

### 类型安全的转换

使用辅助函数 `get_and_cast_data()` 确保类型安全：

```cpp
static const GrMtlBackendFormatData* get_and_cast_data(const GrBackendFormat& format) {
    auto data = GrBackendSurfacePriv::GetBackendData(format);
    SkASSERT(!data || data->type() == GrBackendApi::kMetal);
    return static_cast<const GrMtlBackendFormatData*>(data);
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrBackendSurfacePriv` | 访问后端表面的私有构造函数 |
| `GrMtlTypes` | 使用 `GrMtlTextureInfo` 等 Metal 类型 |
| `GrMtlCppUtil` | Metal C++ 工具函数 |
| `GrMtlUtil` | Metal 格式转换和验证 |
| `MtlUtilsPriv` | Metal 私有工具函数 |
| `GrTypes` | 提供 Ganesh 基础类型 |
| `SkAssert` | 提供断言宏 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrMtlGpu` | 创建和管理 Metal 表面资源 |
| `GrContext` | 创建 Metal 上下文时使用 |
| `GrSurface` | 封装 Metal 表面 |
| `SkSurface` | 创建 Metal 支持的 Skia 表面 |
| 互操作代码 | 与外部 Metal 资源交互 |

## 设计模式与设计决策

### 1. 适配器模式

将 Metal 的 `MTLTexture`、`MTLPixelFormat` 等概念适配为 Skia 的 `GrBackendTexture`、`GrBackendFormat` 接口。

### 2. 工厂模式

通过命名空间函数提供清晰的创建接口，支持不同的初始化参数组合。

### 3. 策略模式

通过继承 `GrBackendFormatData` 等基类，实现 Metal 特定的格式和纹理管理策略。

### 4. 值语义

所有 Metal 对象通过 `GrMtlTextureInfo` 传递，该结构体包含 ARC 管理的 Metal 对象引用。

### 5. 命名空间隔离

使用命名空间而非类静态方法，减少头文件依赖。

### 6. 保护内存标志

Metal 不支持受保护内存，`isProtected()` 总是返回 `false`。

### 7. 未来扩展预留

渲染目标创建代码包含 TODO 注释，预留了 `framebufferOnly` 属性的支持。

## 性能考量

### 1. ARC 引用计数

Metal 对象使用 ARC 管理引用计数，编译器自动优化引用计数操作。

### 2. 固定大小结构

`GrMtlTextureInfo` 使用固定大小的结构体，便于缓存对齐和快速复制。

### 3. 内联函数

访问器函数（如 `asMtlFormat()`、`info()`）可以被编译器内联。

### 4. 条件调试代码

使用 `#if defined(SK_DEBUG)` 限制调试代码，确保发布版本无额外开销。

### 5. 智能指针优化

使用 `sk_sp` 的原子引用计数，支持多线程安全的资源共享。

### 6. 格式查询缓存

Metal 像素格式从 `MTLTexture` 查询一次后缓存在 `GrMtlTextureInfo` 中。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/mtl/GrMtlTypes.h` | Metal 类型定义 |
| `include/gpu/ganesh/GrBackendSurface.h` | 后端表面抽象接口 |
| `src/gpu/ganesh/GrBackendSurfacePriv.h` | 后端表面私有构造函数 |
| `src/gpu/ganesh/mtl/GrMtlCppUtil.h` | Metal C++ 工具函数 |
| `src/gpu/ganesh/mtl/GrMtlUtil.h` | Metal 格式和验证工具 |
| `src/gpu/mtl/MtlUtilsPriv.h` | Metal 私有工具函数 |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 基础类型 |
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | Metal GPU 实现 |
| `src/gpu/ganesh/mtl/GrMtlTexture.h` | Metal 纹理管理 |
