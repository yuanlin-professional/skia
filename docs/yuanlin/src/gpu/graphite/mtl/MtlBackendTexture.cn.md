# MtlBackendTexture - Metal 后端纹理

> 源文件: `src/gpu/graphite/mtl/MtlBackendTexture.mm`

## 概述

MtlBackendTexture.mm 实现了 Skia Graphite Metal 后端的纹理封装。它定义了 `MtlBackendTextureData` 类作为 Metal 特定的纹理数据存储，并在 `BackendTextures` 命名空间中提供了创建和查询 Metal 后端纹理的公共工厂函数。

BackendTexture 是 Skia 的跨后端纹理抽象，允许应用程序将已有的 Metal 纹理对象传入 Skia 进行渲染，或从 Skia 创建的纹理中提取 Metal 纹理对象。

## 架构位置

```
Graphite 后端抽象层
  -> BackendTexture (跨后端纹理接口)
    -> MtlBackendTextureData (Metal 实现)
      -> CFTypeRef (id<MTLTexture>)
```

MtlBackendTexture 是 Graphite 跨后端纹理系统的 Metal 特定实现。

## 主要类与结构体

### `MtlBackendTextureData`（内部类）
- **基类**: `BackendTextureData`
- **成员**: `fMtlTexture` (`CFTypeRef`) - 持有 `id<MTLTexture>` 对象
- **方法**:
  - `texture()`: 返回 Metal 纹理对象
  - `type()`: 返回 `BackendApi::kMetal`（仅调试构建）
  - `copyTo()`: 将数据拷贝到 `AnyBackendTextureData` 容器
  - `equal()`: 通过比较 `CFTypeRef` 判断两个纹理是否相同

## 公共 API 函数

| 函数 | 命名空间 | 说明 |
|------|----------|------|
| `MakeMetal(SkISize, CFTypeRef)` | `BackendTextures` | 从 Metal 纹理创建 BackendTexture |
| `GetMtlTexture(const BackendTexture&)` | `BackendTextures` | 从 BackendTexture 中提取 Metal 纹理 |

## 内部实现细节

### 创建流程
`MakeMetal` 的实现：
1. 调用 `TextureInfos::MakeMetal(mtlTexture)` 从 Metal 纹理提取纹理信息（格式、用途等）
2. 使用 `BackendTexturePriv::Make` 将尺寸、纹理信息和 Metal 数据组合为 BackendTexture

### 相等性判断
`equal()` 方法通过直接比较 `CFTypeRef` 指针来判断两个 MtlBackendTextureData 是否引用同一个 Metal 纹理对象。这是正确的，因为同一个 Metal 纹理在进程中只有一个对象标识。

### 安全提取
`GetMtlTexture` 首先验证 `BackendTexture` 的有效性和后端类型，无效时返回 `nullptr`。内部辅助函数 `get_and_cast_data` 使用 `static_cast` 并在调试构建中验证类型。

### CFTypeRef 生命周期
`MtlBackendTextureData` 存储的 `CFTypeRef` 不自动管理引用计数。调用者需要确保在 BackendTexture 使用期间 Metal 纹理对象保持有效。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/BackendTexturePriv.h` | BackendTexture 私有创建接口 |
| `include/gpu/graphite/mtl/MtlGraphiteTypes_cpp.h` | Metal Graphite 类型定义 |
| `src/gpu/graphite/mtl/MtlGraphiteUtils.h` | Metal 工具函数（TextureInfos::MakeMetal） |
| `include/gpu/MutableTextureState.h` | 纹理状态 |
| `<Metal/Metal.h>` | Metal 框架 |

## 设计模式与设计决策

1. **类型擦除**: 通过 `BackendTextureData` 基类和 `AnyBackendTextureData` 容器实现跨后端的统一纹理接口。

2. **不可变数据**: MtlBackendTextureData 仅存储 CFTypeRef 引用，不持有额外状态。纹理属性通过 TextureInfo 单独管理。

3. **组合创建**: MakeMetal 同时创建 TextureInfo 和 BackendTexture，确保两者一致。

## 性能考量

1. **指针比较**: `equal()` 使用简单的指针比较，O(1) 复杂度。
2. **轻量封装**: MtlBackendTextureData 仅存储一个指针，拷贝操作极其廉价。

## 相关文件

- `src/gpu/graphite/BackendTexturePriv.h` - BackendTexture 私有 API
- `include/gpu/graphite/BackendTexture.h` - 公共纹理接口
- `src/gpu/graphite/mtl/MtlTextureInfo.mm` - Metal 纹理信息（被 MakeMetal 使用）
- `src/gpu/graphite/mtl/MtlGraphiteUtils.h` - Metal 工具函数
