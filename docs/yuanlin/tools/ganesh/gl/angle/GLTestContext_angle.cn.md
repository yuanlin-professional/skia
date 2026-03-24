# GLTestContext_angle

> 源文件：tools/ganesh/gl/angle/GLTestContext_angle.h, tools/ganesh/gl/angle/GLTestContext_angle.cpp

## 概述

GLTestContext_angle 是 ANGLE（Almost Native Graphics Layer Engine）的 Skia 测试上下文实现。ANGLE 是一个开源项目，将 OpenGL ES API 调用转换为其他图形 API（Direct3D、Metal、OpenGL、Vulkan），主要用于 Chrome 浏览器在 Windows 和其他平台上提供一致的 OpenGL ES 支持。

该模块允许 Skia 测试在不同后端上运行 OpenGL ES 代码：
- **Windows**：D3D9、D3D11（主要使用）
- **macOS/iOS**：Metal
- **跨平台**：OpenGL（用于兼容性测试）

这对于测试跨平台一致性、验证 OpenGL ES 规范的实现以及在没有原生 OpenGL ES 支持的平台上运行测试至关重要。

## 架构位置

GLTestContext_angle 位于 OpenGL 测试上下文的特定实现层：

- **基类**：GLTestContext
- **同级实现**：原生 GL 实现（GLX、EGL、CGL、WGL）
- **使用的库**：ANGLE（libGLESv2、libEGL）
- **支持的后端**：D3D9、D3D11、Metal、OpenGL

## 主要类与结构体

### ANGLEBackend 枚举

```cpp
enum class ANGLEBackend {
    kD3D9,      // Direct3D 9
    kD3D11,     // Direct3D 11
    kOpenGL,    // OpenGL
    kMetal      // Metal
};
```

### ANGLEContextVersion 枚举

```cpp
enum class ANGLEContextVersion {
    kES2,   // OpenGL ES 2.0
    kES3    // OpenGL ES 3.0+
};
```

### MakeANGLETestContext（工厂函数）

```cpp
std::unique_ptr<GLTestContext> MakeANGLETestContext(
    ANGLEBackend backend,
    ANGLEContextVersion version,
    GLTestContext* shareContext = nullptr,
    void* display = nullptr);
```

创建 ANGLE 支持的 GLTestContext。

**参数**：
- `backend` - 要使用的图形后端
- `version` - OpenGL ES 版本（2.0 或 3.0）
- `shareContext` - 可选的共享上下文（用于纹理共享）
- `display` - 可选的 EGL display（用于跨上下文共享）

### ANGLEGLContext（内部实现类）

```cpp
class ANGLEGLContext : public sk_gpu_test::GLTestContext {
    ANGLEGLContext(ANGLEBackend, ANGLEContextVersion,
                   ANGLEGLContext* shareContext, void* display);
    ~ANGLEGLContext() override;

    GrEGLImage texture2DToEGLImage(GrGLuint texID) const override;
    void destroyEGLImage(GrEGLImage) const override;
    GrGLuint eglImageToExternalTexture(GrEGLImage) const override;
    std::unique_ptr<GLTestContext> makeNew() const override;
};
```

## 公共 API 函数

### CreateANGLEGLInterface()

```cpp
sk_sp<const GrGLInterface> CreateANGLEGLInterface();
```

创建 ANGLE 的 GrGLInterface 函数指针表。该函数：
1. 动态加载 ANGLE 库（libGLESv2.dll/so/dylib 和 libEGL.dll/so/dylib）
2. 使用 `GrGLMakeAssembledGLESInterface` 组装 OpenGL ES 接口
3. 返回可用于创建 Ganesh 上下文的接口

### MakeANGLETestContext()

创建完整配置的 ANGLE 测试上下文，包括：
- 创建 EGL display
- 选择配置
- 创建 EGL 上下文和 pbuffer 表面
- 初始化 ANGLE 追踪钩子
- 验证创建的上下文类型

**平台特定行为**：
- **Windows ARM64**：仅支持 D3D11
- **Windows**：不支持 Metal
- **macOS**：仅支持 Metal

## 内部实现细节

### Windows 平台初始化

在 Windows 上，需要创建不可见窗口以获取设备上下文：

```cpp
fWindow = CreateWindow(TEXT("ANGLE-win"),
                       TEXT("The Invisible Man"),
                       WS_OVERLAPPEDWINDOW,
                       0, 0, 1, 1,
                       nullptr, nullptr,
                       hInstance, nullptr);
fDeviceContext = GetDC(fWindow);
fDisplay = get_angle_egl_display(fDeviceContext, type);
```

### Wine 检测

代码检测是否在 Wine（Windows 模拟器）下运行，如果是则跳过 D3D 后端（因为不稳定）：

```cpp
static IsWine is_wine() {
    HMODULE ntdll = GetModuleHandle("ntdll.dll");
    return GetProcAddress(ntdll, "wine_get_version") == nullptr ? IsWine::kNo : IsWine::kYes;
}
```

### EGL Display 创建

使用 ANGLE 特定的扩展创建 EGL display：

```cpp
void* get_angle_egl_display(void* nativeDisplay, ANGLEBackend type) {
    PFNEGLGETPLATFORMDISPLAYEXTPROC eglGetPlatformDisplayEXT =
        (PFNEGLGETPLATFORMDISPLAYEXTPROC)eglGetProcAddress("eglGetPlatformDisplayEXT");

    EGLint typeNum = ...; // 根据后端类型选择
    const EGLint attribs[] = { EGL_PLATFORM_ANGLE_TYPE_ANGLE, typeNum, EGL_NONE };
    return eglGetPlatformDisplayEXT(EGL_PLATFORM_ANGLE_ANGLE, nativeDisplay, attribs);
}
```

`EGL_PLATFORM_ANGLE_TYPE_ANGLE` 属性告诉 ANGLE 使用哪个底层图形 API。

### ANGLE 追踪集成

将 ANGLE 的追踪事件连接到 Skia 的追踪系统：

```cpp
angle::GetDisplayPlatformFunc getPlatform =
    reinterpret_cast<angle::GetDisplayPlatformFunc>(
        eglGetProcAddress("ANGLEGetDisplayPlatform"));

if (getPlatform) {
    angle::PlatformMethods* platformMethods = ...;
    platformMethods->addTraceEvent = ANGLE_addTraceEvent;
    platformMethods->getTraceCategoryEnabledFlag = ANGLE_getTraceCategoryEnabledFlag;
    platformMethods->updateTraceEventDuration = ANGLE_updateTraceEventDuration;
    platformMethods->monotonicallyIncreasingTime = ANGLE_monotonicallyIncreasingTime;
}
```

这允许在 Chrome 追踪工具（chrome://tracing）中查看 ANGLE 内部事件。

### 上下文创建

```cpp
int versionNum = ANGLEContextVersion::kES2 == version ? 2 : 3;
std::vector<EGLint> contextAttribs = {
    EGL_CONTEXT_CLIENT_VERSION, versionNum,
};

// 禁用向后兼容性（如果支持）
if (strstr(extensions, "EGL_ANGLE_create_context_backwards_compatible")) {
    contextAttribs.push_back(EGL_CONTEXT_OPENGL_BACKWARDS_COMPATIBLE_ANGLE);
    contextAttribs.push_back(EGL_FALSE);
}

fContext = eglCreateContext(fDisplay, surfaceConfig,
                            eglShareContext, contextAttribs.data());
```

### Pbuffer 表面

使用 pbuffer（离屏缓冲区）而非窗口表面：

```cpp
static const EGLint surfaceAttribs[] = {
    EGL_WIDTH, 1,
    EGL_HEIGHT, 1,
    EGL_NONE
};
fSurface = eglCreatePbufferSurface(fDisplay, surfaceConfig, surfaceAttribs);
```

最小的 1x1 pbuffer 足够测试使用，节省内存。

### 后端验证

在调试构建中验证创建的是正确的后端：

```cpp
#ifdef SK_DEBUG
const GrGLubyte* rendererUByte;
GR_GL_CALL_RET(gl.get(), rendererUByte, GetString(GR_GL_RENDERER));
const char* renderer = reinterpret_cast<const char*>(rendererUByte);
switch (type) {
case ANGLEBackend::kD3D9:
    SkASSERT(strstr(renderer, "Direct3D9"));
    break;
case ANGLEBackend::kD3D11:
    SkASSERT(strstr(renderer, "Direct3D11"));
    break;
// ...
}
#endif
```

### EGL 图像支持

实现 EGL_KHR_image 扩展以支持纹理共享测试：

```cpp
GrEGLImage ANGLEGLContext::texture2DToEGLImage(GrGLuint texID) const {
    if (!this->gl()->hasExtension("EGL_KHR_gl_texture_2D_image")) {
        return GR_EGL_NO_IMAGE;
    }
    EGLint attribs[] = { GR_EGL_GL_TEXTURE_LEVEL, 0,
                         GR_EGL_IMAGE_PRESERVED, GR_EGL_TRUE,
                         GR_EGL_NONE };
    GrEGLClientBuffer clientBuffer = reinterpret_cast<GrEGLClientBuffer>((uint64_t)texID);
    return fCreateImage(fDisplay, fContext, GR_EGL_GL_TEXTURE_2D, clientBuffer, attribs);
}
```

### 上下文共享

`makeNew()` 创建共享同一 EGL display 的新上下文：

```cpp
std::unique_ptr<GLTestContext> ANGLEGLContext::makeNew() const {
    // EGL 图像在上下文间共享需要相同的 display
    return MakeANGLETestContext(fType, fVersion, nullptr, fDisplay);
}
```

### 资源清理

```cpp
void ANGLEGLContext::destroyGLContext() {
    if (eglGetCurrentContext() == fContext) {
        eglMakeCurrent(fDisplay, EGL_NO_SURFACE, EGL_NO_SURFACE, EGL_NO_CONTEXT);
    }

    if (fContext != EGL_NO_CONTEXT) {
        eglDestroyContext(fDisplay, fContext);
    }

    if (fSurface != EGL_NO_SURFACE) {
        eglDestroySurface(fDisplay, fSurface);
    }

    if (fResetPlatform) {
        fResetPlatform(fDisplay);
    }

    if (fOwnsDisplay) {
        eglTerminate(fDisplay);
    }
}
```

清理顺序很重要：先解除当前绑定，再销毁上下文、表面，最后终止 display。

## 依赖关系

### ANGLE 库
- `libGLESv2.dll/so/dylib` - OpenGL ES 实现
- `libEGL.dll/so/dylib` - EGL 实现
- `third_party/externals/angle2/include/platform/PlatformMethods.h` - 平台钩子

### EGL
- EGL 1.4+ API
- `EGL_EXT_platform_angle` 扩展
- `EGL_KHR_image` 扩展（可选）

### 底层图形 API
- Direct3D 9/11（Windows）
- Metal（macOS/iOS）
- OpenGL（跨平台）

### Skia 组件
- `GrGLAssembleInterface` - 接口组装
- `SkTraceEvent` - 追踪系统
- `SkTime` - 时间工具

## 设计模式与设计决策

### 适配器模式
ANGLE 作为适配器，将 OpenGL ES API 适配到不同的底层图形 API。

### 工厂模式
`MakeANGLETestContext` 根据后端类型和版本创建不同配置的上下文。

### RAII 资源管理
使用 `SkScopeExit` 自动恢复之前的上下文：
```cpp
SkScopeExit restorer(context_restorer());
```

### 条件编译
根据平台和架构使用条件编译：
```cpp
#if defined(SK_BUILD_FOR_WIN) && defined(_M_ARM64)
// ARM64 Windows 特定代码
#endif
```

### 延迟加载
库在首次使用时加载并永久保留：
```cpp
static Libs gLibs = { nullptr, nullptr };
if (nullptr == gLibs.fGLLib) {
    gLibs.fGLLib = SkLoadDynamicLibrary("libGLESv2.dll");
    // ...
}
```

## 性能考量

### 追踪开销
ANGLE 追踪集成有小量开销，但对于性能分析非常有价值。

### 后端性能差异
不同后端的性能特征差异很大：
- **D3D11**：通常最快且最稳定（Windows）
- **Metal**：macOS 上的首选
- **OpenGL**：最兼容但可能较慢
- **D3D9**：旧且较慢，主要用于兼容性测试

### Pbuffer vs 窗口
使用 pbuffer 而非窗口表面避免了窗口系统开销和可见性问题。

### 上下文共享
共享 EGL display 避免了重复初始化开销，但需要注意线程安全。

## 相关文件

### 基类
- `tools/ganesh/gl/GLTestContext.h/cpp` - OpenGL 测试上下文基类

### ANGLE 库
- `third_party/externals/angle2/` - ANGLE 源代码
- `third_party/externals/angle2/include/platform/PlatformMethods.h` - 平台钩子

### EGL 头文件
- `<EGL/egl.h>` - EGL API
- `<EGL/eglext.h>` - EGL 扩展

### Skia 工具
- `tools/library/LoadDynamicLibrary.h` - 动态库加载
- `src/core/SkTraceEvent.h` - 追踪事件
- `src/base/SkTime.h` - 时间工具

### Ganesh OpenGL
- `include/gpu/ganesh/gl/GrGLAssembleInterface.h` - 接口组装
- `include/gpu/ganesh/gl/GrGLInterface.h` - OpenGL 接口
