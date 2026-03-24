# GrGLBackendSurface

> 源文件
> - include/gpu/ganesh/gl/GrGLBackendSurface.h
> - src/gpu/ganesh/gl/GrGLBackendSurface.cpp

## 概述

`GrGLBackendSurface` 模块提供了 OpenGL 后端纹理和渲染目标的创建、查询和操作接口。它是 Skia Ganesh 架构中 OpenGL 后端表面抽象的核心实现,负责将通用的 `GrBackendTexture`、`GrBackendRenderTarget` 和 `GrBackendFormat` 与 OpenGL 特定的类型(如 `GrGLTextureInfo`、`GrGLFramebufferInfo`)进行转换和桥接。

该模块通过命名空间组织 API:
- **GrBackendFormats**: 创建和查询 OpenGL 纹理格式
- **GrBackendTextures**: 创建和管理 OpenGL 纹理
- **GrBackendRenderTargets**: 创建和管理 OpenGL 渲染目标

模块使用内部数据类(`GrGLBackendFormatData`、`GrGLBackendTextureData`、`GrGLBackendRenderTargetData`)封装 OpenGL 特定信息,实现了后端无关的表面抽象与 OpenGL 具体实现之间的解耦。

## 架构位置

在 Skia GPU 架构中的位置:

```
应用层 (SkImage, SkSurface)
    ↓
后端无关抽象层 (GrBackendTexture, GrBackendFormat, GrBackendRenderTarget)
    ↓
后端特定实现层
    ├─ GrGLBackendSurface (OpenGL) ← 当前模块
    ├─ GrVkBackendSurface (Vulkan)
    ├─ GrMtlBackendSurface (Metal)
    └─ GrD3DBackendSurface (Direct3D)
    ↓
GPU 驱动层 (OpenGL Driver)
```

## 主要类与结构体

### GrGLBackendFormatData

封装 OpenGL 纹理格式信息的内部类。

**继承关系:**
```
GrBackendFormatData
    ↓
GrGLBackendFormatData
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGLFormat` | `GrGLenum` | OpenGL 内部格式枚举值(如 `GL_RGBA8`) |

### GrGLBackendTextureData

封装 OpenGL 纹理资源信息的内部类。

**继承关系:**
```
GrBackendTextureData
    ↓
GrGLBackendTextureData
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGLInfo` | `GrGLTextureInfo` | OpenGL 纹理 ID、目标、格式等信息 |

### GrGLBackendRenderTargetData

封装 OpenGL 渲染目标信息的内部类。

**继承关系:**
```
GrBackendRenderTargetData
    ↓
GrGLBackendRenderTargetData
```

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fGLInfo` | `GrGLFramebufferInfo` | OpenGL 帧缓冲 ID 和格式 |

## 公共 API 函数

### GrBackendFormats 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `GrBackendFormat MakeGL(GrGLenum format, GrGLenum target)` | 创建指定目标类型的 OpenGL 格式(已废弃) |
| `GrBackendFormat MakeGL(GrGLenum format)` | 创建 `GL_TEXTURE_2D` 类型的 OpenGL 格式 |
| `GrBackendFormat MakeGLExternal()` | 创建 `GL_TEXTURE_EXTERNAL` 类型的格式 |
| `GrGLFormat AsGLFormat(const GrBackendFormat&)` | 将后端格式转换为 `GrGLFormat` 枚举 |
| `GrGLenum AsGLFormatEnum(const GrBackendFormat&)` | 获取 OpenGL 格式枚举值 |

### GrBackendTextures 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `GrBackendTexture MakeGL(int width, int height, skgpu::Mipmapped, const GrGLTextureInfo&, std::string_view label)` | 从 OpenGL 纹理信息创建后端纹理 |
| `bool GetGLTextureInfo(const GrBackendTexture&, GrGLTextureInfo*)` | 提取 OpenGL 纹理信息 |
| `void GLTextureParametersModified(GrBackendTexture*)` | 通知纹理参数已外部修改 |

### GrBackendRenderTargets 命名空间

| 函数签名 | 功能说明 |
|---------|---------|
| `GrBackendRenderTarget MakeGL(int width, int height, int sampleCnt, int stencilBits, const GrGLFramebufferInfo&)` | 从 OpenGL 帧缓冲信息创建渲染目标 |
| `bool GetGLFramebufferInfo(const GrBackendRenderTarget&, GrGLFramebufferInfo*)` | 提取 OpenGL 帧缓冲信息 |

## 内部实现细节

### 格式数据封装

`GrGLBackendFormatData` 实现了后端格式数据接口:

```cpp
class GrGLBackendFormatData final : public GrBackendFormatData {
public:
    GrGLBackendFormatData(GrGLenum format) : fGLFormat(format) {}

private:
    SkTextureCompressionType compressionType() const override {
        // 根据格式返回压缩类型
        switch (GrGLFormatFromGLEnum(fGLFormat)) {
            case GrGLFormat::kCOMPRESSED_ETC1_RGB8:
                return SkTextureCompressionType::kETC2_RGB8_UNORM;
            // ...
        }
    }

    size_t bytesPerBlock() const override {
        return GrGLFormatBytesPerBlock(GrGLFormatFromGLEnum(fGLFormat));
    }

    uint32_t channelMask() const override {
        return GrGLFormatChannels(GrGLFormatFromGLEnum(fGLFormat));
    }
    // ...
};
```

### 纹理目标转换

将 OpenGL 纹理目标转换为 Skia 内部类型:

```cpp
static GrTextureType gl_target_to_gr_target(GrGLenum target) {
    switch (target) {
        case GR_GL_TEXTURE_NONE:      return GrTextureType::kNone;
        case GR_GL_TEXTURE_2D:        return GrTextureType::k2D;
        case GR_GL_TEXTURE_RECTANGLE: return GrTextureType::kRectangle;
        case GR_GL_TEXTURE_EXTERNAL:  return GrTextureType::kExternal;
        default: SkUNREACHABLE;
    }
}
```

### 纹理参数状态管理

`GrGLBackendTextureData` 持有 `GrGLTextureParameters` 对象,跟踪纹理参数状态:

```cpp
GrGLBackendTextureData::GrGLBackendTextureData(const GrGLTextureInfo& info,
                                               sk_sp<GrGLTextureParameters> params)
        : fGLInfo(info, params) {}
```

当纹理参数被外部修改时,需要调用 `GLTextureParametersModified()` 使缓存失效:

```cpp
void GLTextureParametersModified(GrBackendTexture* tex) {
    if (tex && tex->isValid() && tex->backend() == GrBackendApi::kOpenGL) {
        GrGLBackendTextureData* data = get_and_cast_data(tex);
        data->info().parameters()->invalidate();
    }
}
```

### 外部纹理格式处理

`GL_TEXTURE_EXTERNAL` 纹理(主要用于 Android 的 SurfaceTexture)使用占位格式:

```cpp
GrBackendFormat MakeGLExternal() {
    // 外部纹理的实际格式未知,使用 GL_RGBA8 作为占位符
    return GrBackendSurfacePriv::MakeGrBackendFormat(
            GrTextureType::kExternal,
            GrBackendApi::kOpenGL,
            GrGLBackendFormatData(GR_GL_RGBA8));
}
```

### 渲染目标采样数处理

创建渲染目标时确保采样数至少为 1:

```cpp
return GrBackendSurfacePriv::MakeGrBackendRenderTarget(
        width, height,
        std::max(1, sampleCnt),  // 至少为 1
        stencilBits,
        GrBackendApi::kOpenGL,
        /*framebufferOnly=*/false,
        GrGLBackendRenderTargetData(glInfo));
```

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrBackendSurface` | 后端无关的表面抽象基类 |
| `GrBackendSurfacePriv` | 后端表面私有实现辅助 |
| `GrGLTypes` | OpenGL 类型定义 |
| `GrGLTypesPriv` | OpenGL 内部类型和工具 |
| `GrGLUtil` | OpenGL 工具函数 |
| `GrGLTextureParameters` | 纹理参数状态管理 |
| `SkTextureCompressionType` | 纹理压缩类型枚举 |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| `GrGLGpu` | 创建和操作 OpenGL 纹理和渲染目标 |
| `GrGLTexture` | OpenGL 纹理资源包装 |
| `GrGLRenderTarget` | OpenGL 渲染目标资源包装 |
| `SkImage_Ganesh` | 从 OpenGL 纹理创建图像 |
| `SkSurface_Ganesh` | 从 OpenGL 渲染目标创建表面 |
| 跨进程纹理共享 | 通过序列化纹理信息在进程间共享 |

## 设计模式与设计决策

### 命名空间组织 API

使用命名空间而非类成员函数:

```cpp
namespace GrBackendFormats {
    GrBackendFormat MakeGL(...);
}
namespace GrBackendTextures {
    GrBackendTexture MakeGL(...);
}
```

优势:
- 清晰的功能分组
- 避免类层次膨胀
- 更好的代码组织

### 内部数据类封装

使用 `final` 类封装后端特定数据:

```cpp
class GrGLBackendFormatData final : public GrBackendFormatData {
    // 实现虚接口
};
```

这种设计:
- 隐藏 OpenGL 特定细节
- 统一的多态接口
- 类型安全的向下转型

### 类型安全的数据提取

提供辅助函数进行类型检查和转换:

```cpp
static const GrGLBackendFormatData* get_and_cast_data(const GrBackendFormat& format) {
    auto data = GrBackendSurfacePriv::GetBackendData(format);
    SkASSERT(!data || data->type() == GrBackendApi::kOpenGL);
    return static_cast<const GrGLBackendFormatData*>(data);
}
```

Debug 模式下断言类型正确性,Release 模式下快速转换。

### 纹理参数自动失效

创建纹理时假设参数未知:

```cpp
GrBackendTexture MakeGL(...) {
    auto tex = GrBackendSurfacePriv::MakeGrBackendTexture(...);
    GLTextureParametersModified(&tex);  // 自动标记为脏
    return tex;
}
```

这确保 Skia 不会错误地假设纹理状态。

### 智能指针管理纹理参数

使用 `sk_sp<GrGLTextureParameters>` 管理参数对象,多个纹理视图可以共享参数状态。

## 性能考量

### 最小化虚函数调用

后端数据类虽然使用虚函数,但这些调用只在创建、查询和销毁时发生,不在渲染热路径中。

### 内联的格式查询

格式查询函数很小,编译器可以轻松内联:

```cpp
GrGLenum AsGLFormatEnum(const GrBackendFormat& format) {
    if (format.isValid() && format.backend() == GrBackendApi::kOpenGL) {
        const GrGLBackendFormatData* data = get_and_cast_data(format);
        return data->asEnum();
    }
    return 0;
}
```

### 共享纹理参数对象

多个纹理对象可以通过 `sk_sp` 共享同一个参数对象,避免重复存储。

### 采样数标准化

在创建时就处理边界情况(`std::max(1, sampleCnt)`),避免运行时重复检查。

### Debug 断言优化

类型检查断言只在 Debug 模式下执行,Release 模式下被优化掉。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/GrBackendSurface.h` | 后端无关的表面抽象 |
| `src/gpu/ganesh/GrBackendSurfacePriv.h` | 后端表面私有实现辅助 |
| `include/gpu/ganesh/gl/GrGLTypes.h` | OpenGL 类型定义 |
| `src/gpu/ganesh/gl/GrGLTypesPriv.h` | OpenGL 内部类型 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
| `src/gpu/ganesh/gl/GrGLBackendSurfacePriv.h` | OpenGL 后端表面私有接口 |
| `src/gpu/ganesh/gl/GrGLTexture.h` | OpenGL 纹理资源 |
| `src/gpu/ganesh/gl/GrGLRenderTarget.h` | OpenGL 渲染目标资源 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | OpenGL GPU 实现 |
