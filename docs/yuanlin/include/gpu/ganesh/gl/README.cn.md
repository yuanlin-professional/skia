# include/gpu/ganesh/gl - Ganesh OpenGL 后端公共 API

## 概述

`include/gpu/ganesh/gl` 目录包含 Ganesh 渲染引擎中 OpenGL 后端的公共 API。OpenGL 是 Skia
最早支持的 GPU 后端之一，此目录提供了 OpenGL 接口函数表、类型定义、后端表面工厂方法以及
上下文创建入口等。

Ganesh 的 OpenGL 后端支持三种 GL 标准：桌面 OpenGL（`kGL_GrGLStandard`）、OpenGL ES
（`kGLES_GrGLStandard`）和 WebGL（`kWebGL_GrGLStandard`）。通过条件编译宏（如
`SK_ASSUME_GL_ES`），可以在编译时仅保留特定标准的支持以减小代码体积。

`GrGLInterface` 是 OpenGL 后端的核心结构体，它包含了所有 OpenGL 函数指针。由于 OpenGL 函数
指针在某些平台上（如 Windows）可能因上下文而异，客户端需要确保为正确的 OpenGL 上下文提供
函数指针。`GrGLFunctions.h` 定义了所有所需 GL 函数指针的类型。

各平台特定的 GL 接口创建函数分布在子目录中：`egl/`（EGL/Android）、`glx/`（X11/Linux）、
`win/`（WGL/Windows）、`mac/`（CGL/macOS）、`ios/`（EAGL/iOS）和 `epoxy/`（libepoxy）。

`GrGLDirectContext.h` 提供了使用 OpenGL 后端创建 `GrDirectContext` 的工厂方法。
`GrGLBackendSurface.h` 提供了创建 GL 特定的后端纹理和渲染目标的工厂方法。

## 架构图

```
include/gpu/ganesh/gl/
    |
    +-- GrGLTypes.h               <-- GL 类型定义（GrGLTextureInfo 等）
    +-- GrGLConfig.h              <-- GL 编译配置
    +-- GrGLFunctions.h           <-- 所有 GL 函数指针类型定义
    +-- GrGLExtensions.h          <-- GL 扩展查询管理
    +-- GrGLInterface.h           <-- GL 函数指针接口集合
    +-- GrGLAssembleInterface.h   <-- GL 接口组装辅助
    +-- GrGLAssembleHelpers.h     <-- GL 接口组装辅助函数
    |
    +-- GrGLDirectContext.h       <-- MakeGL() 工厂方法
    +-- GrGLBackendSurface.h      <-- GL 后端纹理/渲染目标工厂
    +-- GrGLMakeWebGLInterface.h  <-- WebGL 接口创建
    |
    +-- egl/                      <-- EGL (Android/Linux)
    |   +-- GrGLMakeEGLInterface.h
    +-- glx/                      <-- GLX (X11/Linux)
    |   +-- GrGLMakeGLXInterface.h
    +-- win/                      <-- WGL (Windows)
    |   +-- GrGLMakeWinInterface.h
    +-- mac/                      <-- CGL (macOS)
    |   +-- GrGLMakeMacInterface.h
    +-- ios/                      <-- EAGL (iOS)
    |   +-- GrGLMakeIOSInterface.h
    +-- epoxy/                    <-- libepoxy (Linux)
        +-- GrGLMakeEpoxyEGLInterface.h
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrGLTypes.h` | GL 类型定义：`GrGLStandard`、`GrGLFormat`、`GrGLTextureInfo`、`GrGLFramebufferInfo` |
| `GrGLConfig.h` | GL 编译配置宏 |
| `GrGLFunctions.h` | 所有 GL 函数指针的 typedef（约 200+ 个函数） |
| `GrGLExtensions.h` | GL 扩展查询与管理（`GrGLExtensions` 类） |
| `GrGLInterface.h` | `GrGLInterface` 结构体，包含所有 GL 函数指针 |
| `GrGLAssembleInterface.h` | 通过平台函数指针获取接口组装 GL 接口 |
| `GrGLAssembleHelpers.h` | GL 接口组装的辅助声明 |
| `GrGLDirectContext.h` | `GrDirectContexts::MakeGL()` 工厂方法 |
| `GrGLBackendSurface.h` | GL 后端格式、纹理、渲染目标的创建与查询 |
| `GrGLMakeWebGLInterface.h` | WebGL 接口创建 |

## 关键类与函数

### `GrGLInterface` 结构体 (GrGLInterface.h)

```cpp
struct GrGLInterface : public SkRefCnt {
    bool validate() const;            // 验证函数指针完整性
    GrGLStandard fStandard;           // GL/GLES/WebGL
    GrGLExtensions fExtensions;       // 已加载的扩展
    struct Functions { ... } fFunctions; // 所有 GL 函数指针
};
```

### GL 标准枚举 (GrGLTypes.h)

```cpp
enum GrGLStandard {
    kNone_GrGLStandard,
    kGL_GrGLStandard,    // 桌面 OpenGL
    kGLES_GrGLStandard,  // OpenGL ES
    kWebGL_GrGLStandard, // WebGL
};
```

### GL 格式枚举 (GrGLTypes.h)

```cpp
enum class GrGLFormat {
    kUnknown, kRGBA8, kR8, kALPHA8, kBGRA8,
    kRGB565, kRGBA16F, kRGB10_A2, kSRGB8_ALPHA8,
    kCOMPRESSED_ETC1_RGB8, kSTENCIL_INDEX8,
    kDEPTH24_STENCIL8, // ... 等
};
```

### GL 纹理/帧缓冲信息 (GrGLTypes.h)

```cpp
struct GrGLTextureInfo {
    GrGLenum fTarget;   // GL_TEXTURE_2D 等
    GrGLuint fID;       // GL 纹理 ID
    GrGLenum fFormat;   // 内部格式
    skgpu::Protected fProtected;
};

struct GrGLFramebufferInfo {
    GrGLuint fFBOID;
    GrGLenum fFormat;
    skgpu::Protected fProtected;
};
```

### 上下文创建 (GrGLDirectContext.h)

```cpp
namespace GrDirectContexts {
    sk_sp<GrDirectContext> MakeGL(sk_sp<const GrGLInterface>, const GrContextOptions&);
    sk_sp<GrDirectContext> MakeGL(sk_sp<const GrGLInterface>);
    sk_sp<GrDirectContext> MakeGL();  // 使用 GrGLMakeNativeInterface()
}
```

### 后端纹理工厂 (GrGLBackendSurface.h)

```cpp
namespace GrBackendFormats {
    GrBackendFormat MakeGL(GrGLenum format);  // GL_TEXTURE_2D
    GrBackendFormat MakeGLExternal();         // GL_TEXTURE_EXTERNAL
    GrGLFormat AsGLFormat(const GrBackendFormat&);
}

namespace GrBackendTextures {
    GrBackendTexture MakeGL(int w, int h, skgpu::Mipmapped, const GrGLTextureInfo&);
    bool GetGLTextureInfo(const GrBackendTexture&, GrGLTextureInfo*);
}

namespace GrBackendRenderTargets {
    GrBackendRenderTarget MakeGL(int w, int h, int sampleCnt, int stencilBits, const GrGLFramebufferInfo&);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/GrTypes.h`, `include/gpu/ganesh/GrBackendSurface.h`
- **上游依赖**: `include/gpu/GpuTypes.h`, `include/core/SkRefCnt.h`
- **子目录**: `egl/`, `glx/`, `win/`, `mac/`, `ios/`, `epoxy/`（平台特定接口）
- **实现代码**: `src/gpu/ganesh/gl/`

## 相关文档与参考

- `include/gpu/ganesh/` - Ganesh 引擎主目录
- `include/gpu/ganesh/gl/egl/` - EGL 平台接口
- `include/gpu/ganesh/gl/glx/` - GLX 平台接口
- `include/gpu/ganesh/gl/win/` - Windows WGL 平台接口
- `include/gpu/ganesh/gl/mac/` - macOS CGL 平台接口
- `include/gpu/ganesh/gl/ios/` - iOS EAGL 平台接口
- OpenGL 规范: https://www.khronos.org/opengl/
