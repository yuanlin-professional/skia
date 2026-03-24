# GrBackendSurfacePriv — 后端表面私有接口

> 源文件: `src/gpu/ganesh/GrBackendSurfacePriv.h`

## 概述

`GrBackendSurfacePriv` 提供了一组私有辅助接口，用于在 Ganesh GPU 后端内部创建和访问 `GrBackendFormat`、`GrBackendTexture` 和 `GrBackendRenderTarget` 对象的底层数据。该头文件同时定义了三个抽象基类——`GrBackendFormatData`、`GrBackendTextureData` 和 `GrBackendRenderTargetData`——它们作为各平台特定后端数据的多态接口，使得不同 GPU API（如 Vulkan、Metal、OpenGL）能够以统一方式存储和操作后端表面信息。

## 架构位置

该文件位于 Ganesh GPU 渲染管线的核心层：

```
Skia 公共 API (include/gpu/ganesh/GrBackendSurface.h)
    └── GrBackendSurfacePriv (本文件 - 私有工厂和访问器)
        ├── GrBackendFormatData (抽象基类)
        ├── GrBackendTextureData (抽象基类)
        └── GrBackendRenderTargetData (抽象基类)
            ├── Vulkan 实现
            ├── Metal 实现
            ├── GL 实现
            └── Mock 实现
```

`GrBackendSurfacePriv` 是 `GrBackendFormat`、`GrBackendTexture` 和 `GrBackendRenderTarget` 的 friend 类，可以直接访问它们的私有构造函数和成员。

## 主要类与结构体

### GrBackendFormatData

抽象基类，定义后端格式数据的多态接口：

| 方法 | 描述 |
|------|------|
| `compressionType()` | 返回纹理压缩类型 (`SkTextureCompressionType`) |
| `bytesPerBlock()` | 返回每个像素块的字节数 |
| `stencilBits()` | 返回模板缓冲区位数 |
| `equal()` | 比较两个格式数据是否相等 |
| `channelMask()` | (私有) 返回颜色通道掩码 |
| `desc()` | (私有) 返回颜色格式描述 |
| `toString()` | (私有) 返回格式的字符串表示 |
| `copyTo()` | (私有) 将数据复制到 `AnyFormatData` 内联存储中 |
| `makeTexture2D()` | (私有, 仅 Vulkan) 将纹理设置为 2D 类型 |

### GrBackendTextureData

抽象基类，定义后端纹理数据的多态接口：

| 方法 | 描述 |
|------|------|
| `isProtected()` | 检查纹理是否受保护 |
| `equal()` | 比较两个纹理数据是否相等 |
| `isSameTexture()` | 检查是否指向同一纹理资源 |
| `getBackendFormat()` | 获取后端格式信息 |
| `copyTo()` | 将数据复制到 `AnyTextureData` 内联存储 |
| `getMutableState()` | (仅 Vulkan) 获取可变纹理状态 |
| `setMutableState()` | (仅 Vulkan) 设置可变纹理状态 |

### GrBackendRenderTargetData

抽象基类，定义后端渲染目标数据的多态接口：

| 方法 | 描述 |
|------|------|
| `getBackendFormat()` | 获取后端格式信息 |
| `isProtected()` | 检查渲染目标是否受保护 |
| `equal()` | 比较两个渲染目标数据是否相等 |
| `copyTo()` | 将数据复制到 `AnyRenderTargetData` 内联存储 |
| `getMutableState()` | (仅 Vulkan) 获取可变纹理状态 |
| `setMutableState()` | (仅 Vulkan) 设置可变纹理状态 |

### GrBackendSurfacePriv

静态工具类（`final`），提供模板工厂方法和访问器：

| 方法 | 描述 |
|------|------|
| `MakeGrBackendFormat<FormatData>()` | 根据模板参数构造 `GrBackendFormat` |
| `MakeGrBackendTexture<TextureData>()` | 根据模板参数构造 `GrBackendTexture` |
| `MakeGrBackendRenderTarget<RenderTargetData>()` | 根据模板参数构造 `GrBackendRenderTarget` |
| `GetBackendData(const GrBackendFormat&)` | 获取格式的只读后端数据指针 |
| `GetBackendData(const GrBackendTexture&)` | 获取纹理的只读后端数据指针 |
| `GetBackendData(GrBackendTexture*)` | 获取纹理的可写后端数据指针 |
| `GetBackendData(const GrBackendRenderTarget&)` | 获取渲染目标的只读后端数据指针 |
| `GetBackendData(GrBackendRenderTarget*)` | 获取渲染目标的可写后端数据指针 |

## 公共 API 函数

此文件为内部私有头文件，不属于 Skia 公共 API。所有函数均为 Skia 内部使用。

- **`GrBackendSurfacePriv::MakeGrBackendFormat()`**: 接受 `GrTextureType`、`GrBackendApi` 和具体格式数据，调用 `GrBackendFormat` 的私有构造函数。
- **`GrBackendSurfacePriv::MakeGrBackendTexture()`**: 接受宽度、高度、标签、mipmap 状态等参数，调用 `GrBackendTexture` 的私有构造函数。
- **`GrBackendSurfacePriv::MakeGrBackendRenderTarget()`**: 接受宽度、高度、采样数、模板位数等参数，调用 `GrBackendRenderTarget` 的私有构造函数。
- **`GrBackendSurfacePriv::GetBackendData()`**: 重载函数族，提供对各类后端数据的访问，包含 const 和非 const 版本。

## 内部实现细节

1. **类型擦除与多态**: 三个抽象基类通过虚函数实现类型擦除，使公共类 `GrBackendFormat` 等无需了解具体后端类型。每个具体后端（GL、Vulkan、Metal、Mock）实现这些纯虚函数。

2. **内联存储 (AnyFormatData/AnyTextureData/AnyRenderTargetData)**: 使用 `copyTo()` 方法将数据复制到固定大小的内联缓冲区中，避免堆分配。这些类型别名如 `GrBackendFormat::AnyFormatData` 在 `GrBackendSurface.h` 中通过 `skgpu::ScratchKey` 或类似机制定义。

3. **Vulkan 特殊处理**: `makeTexture2D()`、`getMutableState()` 和 `setMutableState()` 提供了默认空实现，只有 Vulkan 后端会覆盖这些方法。这体现了 Vulkan 纹理状态管理的复杂性。

4. **调试断言**: 在 `SK_DEBUG` 模式下，`type()` 纯虚函数用于运行时类型检查，确保后端数据与预期的 `GrBackendApi` 类型匹配。

## 依赖关系

- **`include/gpu/ganesh/GrBackendSurface.h`**: 核心公共类定义
- **`include/gpu/MutableTextureState.h`**: Vulkan 可变纹理状态
- **`include/core/SkRefCnt.h`**: `sk_sp` 智能指针
- **`include/private/gpu/ganesh/GrTypesPriv.h`**: `GrTextureType`、`GrColorFormatDesc` 等私有类型
- **`include/private/base/SkAssert.h`**: 调试断言宏

## 设计模式与设计决策

1. **桥接模式 (Bridge Pattern)**: 公共接口类（`GrBackendFormat` 等）通过持有抽象数据类的指针，将接口与实现解耦。这允许在不修改公共 API 的情况下添加新的 GPU 后端。

2. **模板工厂方法**: `GrBackendSurfacePriv` 的静态模板方法作为受控的创建入口，通过 friend 机制绕过公共类的访问限制，同时在编译时确保类型安全。

3. **final 类设计**: `GrBackendSurfacePriv` 被声明为 `final`，且只包含静态方法，不可实例化或继承，明确其作为纯工具类的角色。

4. **Vulkan 可选 API**: 通过在基类中提供默认空实现而非纯虚函数，避免强制所有后端实现 Vulkan 特有的功能。

## 性能考量

- **内联存储**: 使用 `copyTo()` 将后端数据复制到栈内联缓冲区，避免了堆分配开销，适合频繁创建和销毁的后端对象。
- **虚函数开销**: 抽象基类使用虚函数调用，但这些操作通常不在热路径上，因为后端表面对象的创建和查询频率远低于绘制操作。
- **const 与非 const 重载**: `GetBackendData` 提供了 const 和非 const 版本，允许在只读场景下避免不必要的拷贝或锁定。

## 相关文件

- `include/gpu/ganesh/GrBackendSurface.h` — 公共后端表面类定义
- `src/gpu/ganesh/gl/GrGLBackendSurface.cpp` — OpenGL 后端实现
- `src/gpu/ganesh/vk/GrVkBackendSurface.cpp` — Vulkan 后端实现
- `src/gpu/ganesh/mtl/GrMtlBackendSurface.mm` — Metal 后端实现
- `src/gpu/ganesh/mock/GrMockBackendSurface.cpp` — Mock 后端实现
- `include/gpu/MutableTextureState.h` — Vulkan 可变纹理状态
