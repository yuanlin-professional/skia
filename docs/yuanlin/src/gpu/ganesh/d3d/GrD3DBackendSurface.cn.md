# GrD3DBackendSurface

> 源文件
> - include/gpu/ganesh/d3d/GrD3DBackendSurface.h
> - src/gpu/ganesh/d3d/GrD3DBackendSurface.cpp

## 概述

`GrD3DBackendSurface` 模块提供了 Direct3D 12 后端纹理和渲染目标的创建、查询和操作接口。它是 Skia Ganesh 架构中 D3D12 后端表面抽象的核心实现,负责将通用的 `GrBackendTexture`、`GrBackendRenderTarget` 和 `GrBackendFormat` 与 Direct3D 12 特定的类型(如 `GrD3DTextureResourceInfo`、`DXGI_FORMAT`)进行转换和桥接。

该模块通过命名空间组织 API:
- **GrBackendFormats**: 创建和查询 D3D12 纹理格式
- **GrBackendTextures**: 创建和管理 D3D12 纹理资源
- **GrBackendRenderTargets**: 创建和管理 D3D12 渲染目标

模块使用内部数据类封装 D3D12 特定信息,并提供资源状态管理功能,这对于 D3D12 的显式状态转换至关重要。

## 架构位置

在 Skia GPU 架构中的位置:

```
应用层 (SkImage, SkSurface)
    ↓
后端无关抽象层 (GrBackendTexture, GrBackendFormat, GrBackendRenderTarget)
    ↓
后端特定实现层
    ├─ GrGLBackendSurface (OpenGL)
    ├─ GrVkBackendSurface (Vulkan)
    ├─ GrMtlBackendSurface (Metal)
    └─ GrD3DBackendSurface (Direct3D) ← 当前模块
    ↓
D3D12 驱动层
```

## 主要类与结构体

### GrD3DBackendFormatData

封装 Direct3D 12 纹理格式信息的内部类。

**继承关系:**
```
GrBackendFormatData
    ↓
GrD3DBackendFormatData
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFormat` | `DXGI_FORMAT` | DXGI 格式枚举(如 `DXGI_FORMAT_R8G8B8A8_UNORM`) |

### GrD3DBackendTextureData

封装 Direct3D 12 纹理资源信息的内部类。

**继承关系:**
```
GrBackendTextureData
    ↓
GrD3DBackendTextureData
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrD3DBackendSurfaceInfo` | D3D12 资源信息和状态 |

### GrD3DBackendRenderTargetData

封装 Direct3D 12 渲染目标信息的内部类。

**继承关系:**
```
GrBackendRenderTargetData
    ↓
GrD3DBackendRenderTargetData
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fInfo` | `GrD3DBackendSurfaceInfo` | D3D12 资源信息和状态 |

## 公共 API 函数

### GrBackendFormats 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `GrBackendFormat MakeD3D(DXGI_FORMAT)` | 从 DXGI 格式创建后端格式 |
| `DXGI_FORMAT AsDxgiFormat(const GrBackendFormat&)` | 提取 DXGI 格式枚举 |

### GrBackendTextures 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `GrBackendTexture MakeD3D(int width, int height, const GrD3DTextureResourceInfo&, std::string_view label)` | 从 D3D12 纹理信息创建后端纹理 |
| `GrD3DTextureResourceInfo GetD3DTextureResourceInfo(const GrBackendTexture&)` | 提取 D3D12 纹理信息快照 |
| `void SetD3DResourceState(GrBackendTexture*, GrD3DResourceStateEnum)` | 更新纹理资源状态 |

### GrBackendRenderTargets 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `GrBackendRenderTarget MakeD3D(int width, int height, const GrD3DTextureResourceInfo&)` | 从 D3D12 资源信息创建渲染目标 |
| `GrD3DTextureResourceInfo GetD3DTextureResourceInfo(const GrBackendRenderTarget&)` | 提取 D3D12 资源信息快照 |
| `void SetD3DResourceState(GrBackendRenderTarget*, GrD3DResourceStateEnum)` | 更新渲染目标资源状态 |

## 内部实现细节

### 格式数据封装

```cpp
class GrD3DBackendFormatData final : public GrBackendFormatData {
public:
    GrD3DBackendFormatData(DXGI_FORMAT format) : fFormat(format) {}

    DXGI_FORMAT asDxgiFormat() const { return fFormat; }

private:
    SkTextureCompressionType compressionType() const override {
        switch (fFormat) {
            case DXGI_FORMAT_BC1_UNORM:
                return SkTextureCompressionType::kBC1_RGBA8_UNORM;
            default:
                return SkTextureCompressionType::kNone;
        }
    }

    size_t bytesPerBlock() const override {
        return GrDxgiFormatBytesPerBlock(fFormat);
    }

    uint32_t channelMask() const override {
        return GrDxgiFormatChannels(fFormat);
    }
    // ...
};
```

### 纹理资源状态管理

D3D12 要求显式管理资源状态,模块提供了状态设置和获取接口:

```cpp
void SetD3DResourceState(GrBackendTexture* tex, GrD3DResourceStateEnum state) {
    SkASSERT(tex);
    if (!tex->isValid() || tex->backend() != GrBackendApi::kDirect3D) {
        SkDEBUGFAIL("Mismatching backend or uninitialized GrBackendTexture\n");
        return;
    }
    GrD3DBackendTextureData* data = get_and_cast_data(tex);
    SkASSERT(data);
    data->setResourceState(state);
}
```

### 资源状态跟踪

使用 `GrD3DResourceState` 智能指针跟踪资源状态:

```cpp
GrBackendTexture MakeD3D(int width, int height,
                         const GrD3DTextureResourceInfo& d3dInfo,
                         std::string_view label) {
    GrD3DBackendTextureData data(
            d3dInfo,
            sk_sp<GrD3DResourceState>(new GrD3DResourceState(
                    static_cast<D3D12_RESOURCE_STATES>(d3dInfo.fResourceState))));
    return GrBackendSurfacePriv::MakeGrBackendTexture(
            width, height, label,
            skgpu::Mipmapped(d3dInfo.fLevelCount > 1),
            GrBackendApi::kDirect3D,
            GrTextureType::k2D,
            data);
}
```

### 状态快照

`GetD3DTextureResourceInfo` 返回资源信息的快照,包含当前状态:

```cpp
GrD3DTextureResourceInfo GetD3DTextureResourceInfo(const GrBackendTexture& tex) {
    if (!tex.isValid() || tex.backend() != GrBackendApi::kDirect3D) {
        SkDEBUGFAIL("Mismatching backend or uninitialized GrBackendTexture\n");
        return {};
    }
    const GrD3DBackendTextureData* data = get_and_cast_data(tex);
    SkASSERT(data);
    return data->snapTextureResourceInfo();  // 返回当前状态快照
}
```

### Mipmap 级别检测

从纹理信息中自动检测是否有 mipmap:

```cpp
skgpu::Mipmapped(d3dInfo.fLevelCount > 1)
```

### 采样数标准化

确保采样数至少为 1:

```cpp
std::max(1U, d3dInfo.fSampleCount)
```

### 压缩格式支持

支持 BC1 压缩格式:

```cpp
case DXGI_FORMAT_BC1_UNORM:
    return SkTextureCompressionType::kBC1_RGBA8_UNORM;
```

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrBackendSurface` | 后端无关的表面抽象基类 |
| `GrBackendSurfacePriv` | 后端表面私有实现辅助 |
| `GrD3DTypes` | D3D12 类型定义 |
| `GrD3DResourceState` | D3D12 资源状态管理 |
| `GrD3DUtil` | D3D12 工具函数 |
| `GrD3DBackendSurfacePriv` | D3D12 后端表面私有接口 |
| `SkTextureCompressionType` | 纹理压缩类型枚举 |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| `GrD3DGpu` | 创建和操作 D3D12 纹理和渲染目标 |
| `GrD3DTexture` | D3D12 纹理资源包装 |
| `GrD3DRenderTarget` | D3D12 渲染目标资源包装 |
| `SkImage_Ganesh` | 从 D3D12 纹理创建图像 |
| `SkSurface_Ganesh` | 从 D3D12 渲染目标创建表面 |
| 跨进程资源共享 | 通过序列化资源信息在进程间共享 D3D12 纹理 |

## 设计模式与设计决策

### 命名空间组织 API

与 OpenGL 版本保持一致的 API 组织方式:

```cpp
namespace GrBackendFormats { /* 格式相关 */ }
namespace GrBackendTextures { /* 纹理相关 */ }
namespace GrBackendRenderTargets { /* 渲染目标相关 */ }
```

### 显式资源状态管理

D3D12 要求应用程序显式管理资源状态转换,模块提供了状态设置接口:

```cpp
// 应用程序在 D3D12 命令列表中转换状态后,需要通知 Skia
GrBackendTextures::SetD3DResourceState(&texture, newState);
```

### 智能指针管理状态对象

使用 `sk_sp<GrD3DResourceState>` 管理状态对象,多个纹理视图可以共享状态:

```cpp
sk_sp<GrD3DResourceState>(new GrD3DResourceState(...))
```

### 内部数据类封装

使用 `final` 类封装后端特定数据:

```cpp
class GrD3DBackendFormatData final : public GrBackendFormatData {
    // 实现虚接口
};
```

### 类型安全的数据提取

提供辅助函数进行类型检查和转换:

```cpp
static const GrD3DBackendFormatData* get_and_cast_data(const GrBackendFormat& format) {
    auto data = GrBackendSurfacePriv::GetBackendData(format);
    SkASSERT(!data || data->type() == GrBackendApi::kDirect3D);
    return static_cast<const GrD3DBackendFormatData*>(data);
}
```

### 状态快照设计

`GetD3DTextureResourceInfo` 返回快照而非引用,避免外部修改内部状态:

```cpp
GrD3DTextureResourceInfo snapTextureResourceInfo() const {
    return fInfo.snapTextureResourceInfo();
}
```

## 性能考量

### 智能指针共享状态

多个纹理视图可以共享同一个 `GrD3DResourceState` 对象,减少内存占用和状态同步开销。

### 最小化虚函数调用

后端数据类的虚函数只在创建、查询和销毁时调用,不在渲染热路径中。

### 内联的格式查询

小函数可以被编译器内联:

```cpp
DXGI_FORMAT AsDxgiFormat(const GrBackendFormat& format) {
    if (!format.isValid() || format.backend() != GrBackendApi::kDirect3D) {
        return DXGI_FORMAT_UNKNOWN;
    }
    const GrD3DBackendFormatData* data = get_and_cast_data(format);
    return data->asDxgiFormat();
}
```

### 采样数标准化

在创建时处理边界情况,避免运行时检查:

```cpp
std::max(1U, d3dInfo.fSampleCount)
```

### Debug 断言优化

类型检查断言只在 Debug 模式下执行,Release 模式下被优化掉。

### 状态转换最小化

通过显式状态管理,应用程序可以批量转换多个资源的状态,减少 D3D12 API 调用。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/GrBackendSurface.h` | 后端无关的表面抽象 |
| `src/gpu/ganesh/GrBackendSurfacePriv.h` | 后端表面私有实现辅助 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | D3D12 类型定义 |
| `src/gpu/ganesh/d3d/GrD3DResourceState.h` | D3D12 资源状态管理 |
| `src/gpu/ganesh/d3d/GrD3DUtil.h` | D3D12 工具函数 |
| `src/gpu/ganesh/d3d/GrD3DBackendSurfacePriv.h` | D3D12 后端表面私有接口 |
| `src/gpu/ganesh/d3d/GrD3DTexture.h` | D3D12 纹理资源 |
| `src/gpu/ganesh/d3d/GrD3DRenderTarget.h` | D3D12 渲染目标资源 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | D3D12 GPU 实现 |
| `include/private/gpu/ganesh/GrD3DTypesMinimal.h` | D3D12 最小类型定义 |
