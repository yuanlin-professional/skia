# GrGLUtil

> 源文件
> - src/gpu/ganesh/gl/GrGLUtil.h
> - src/gpu/ganesh/gl/GrGLUtil.cpp

## 概述

`GrGLUtil` 是 Skia Ganesh OpenGL 后端的工具模块，提供了一系列用于 OpenGL 版本解析、硬件检测、格式转换和能力查询的工具函数。该模块包含格式描述符、颜色通道查询、版本解析、厂商/渲染器识别、驱动版本解析等核心功能。

该模块定义了大量 constexpr 函数用于编译时格式信息查询，以及运行时的字符串解析函数用于识别特定 GPU 硬件和驱动版本。它是 OpenGL 后端能力检测和平台适配的基础设施。

## 架构位置

```
GrGLCaps (能力检测)
    ↓ (使用)
GrGLUtil (工具函数)
    ├── 版本解析
    ├── 硬件识别
    └── 格式转换

GrGLGpu (GPU 实现)
    ↓ (使用)
GrGLUtil (格式查询、宏辅助)
```

该模块是 OpenGL 后端的底层工具库，被 `GrGLCaps`、`GrGLGpu` 等核心组件广泛使用。

## 主要类与结构体

### 版本类型定义

| 类型名 | 定义 | 说明 |
|--------|------|------|
| `GrGLVersion` | `uint32_t` | OpenGL 版本号 |
| `GrGLSLVersion` | `uint32_t` | GLSL 版本号 |
| `GrGLDriverVersion` | `uint64_t` | 驱动版本号 |

### 版本宏

```cpp
#define GR_GL_VER(major, minor) ((static_cast<uint32_t>(major) << 16) | static_cast<uint32_t>(minor))
#define GR_GLSL_VER(major, minor) ((static_cast<uint32_t>(major) << 16) | static_cast<uint32_t>(minor))
#define GR_GL_DRIVER_VER(major, minor, point) ((static_cast<uint64_t>(major) << 32) | \
                                                (static_cast<uint64_t>(minor) << 16) | \
                                                 static_cast<uint64_t>(point))

#define GR_GL_MAJOR_VER(version) (static_cast<uint32_t>(version) >> 16)
#define GR_GL_MINOR_VER(version) (static_cast<uint32_t>(version) & 0xFFFF)

#define GR_GL_INVALID_VER GR_GL_VER(0, 0)
#define GR_GLSL_INVALID_VER GR_GLSL_VER(0, 0)
#define GR_GL_DRIVER_UNKNOWN_VER GR_GL_DRIVER_VER(0, 0, 0)
```

### 枚举类型

#### GrGLVendor

```cpp
enum class GrGLVendor {
    kARM,
    kGoogle,
    kImagination,
    kIntel,
    kQualcomm,
    kNVIDIA,
    kATI,
    kApple,
    kOther
};
```

#### GrGLRenderer

```cpp
enum class GrGLRenderer {
    kTegra_PreK1,  // Legacy Tegra
    kTegra,        // K1+
    kPowerVR54x,
    kPowerVRBSeries,
    kPowerVRRogue,
    kAdreno3xx,
    kAdreno430,
    kAdreno4xx_other,
    kAdreno530,
    kAdreno5xx_other,
    kAdreno6xx_other,
    kIntelSandyBridge,  // 6th gen
    kIntelIvyBridge,    // 7th gen
    kIntelHaswell,
    kIntelBroadwell,    // 8th gen
    kIntelSkyLake,      // 9th gen
    kIntelIceLake,      // 11th gen
    kIntelTigerLake,    // 12th gen
    kMaliT,             // T-6xx, T-7xx, T-8xx
    kMaliG,             // G-3x, G-5x, G-7x
    kAMDRadeonHD7xxx,
    kAMDRadeonPro5xxx,
    kApple,
    kWebGL,
    kOther
};
```

#### GrGLDriver

```cpp
enum class GrGLDriver {
    kMesa,
    kNVIDIA,
    kIntel,
    kQualcomm,
    kFreedreno,
    kAndroidEmulator,
    kImagination,
    kARM,
    kApple,
    kUnknown
};
```

#### GrGLANGLEBackend

```cpp
enum class GrGLANGLEBackend {
    kUnknown,
    kD3D9,
    kD3D11,
    kMetal,
    kOpenGL,
    kVulkan,
};
```

## 公共 API 函数

### 格式查询（constexpr）

- `constexpr uint32_t GrGLFormatChannels(GrGLFormat format)` - 获取格式的颜色通道掩码
- `constexpr GrColorFormatDesc GrGLFormatDesc(GrGLFormat format)` - 获取格式描述符

### 版本解析

- `GrGLStandard GrGLGetStandardInUseFromString(const char* versionString)` - 从版本字符串解析 GL 标准
- `GrGLVersion GrGLGetVersionFromString(const char* versionString)` - 从字符串解析 GL 版本
- `GrGLVersion GrGLGetVersion(const GrGLInterface* gl)` - 获取当前 GL 版本
- `static GrGLSLVersion get_glsl_version(const char* versionString)` - 解析 GLSL 版本

### 硬件识别

- `static GrGLVendor get_vendor(const char* vendorString)` - 识别 GPU 厂商
- `static GrGLRenderer get_renderer(const char* rendererString, const GrGLExtensions& extensions)` - 识别 GPU 型号

### 辅助宏

```cpp
// 安全的 glGetIntegerv 调用（初始化为0）
#define GR_GL_GetIntegerv(gl, e, p) \
    do { \
        *(p) = GR_GL_INIT_ZERO; \
        GR_GL_CALL(gl, GetIntegerv(e, p)); \
    } while (0)

// 其他安全的 GL 调用宏
#define GR_GL_GetFloatv(gl, e, p) ...
#define GR_GL_GetFramebufferAttachmentParameteriv(gl, t, a, pname, p) ...
#define GR_GL_GetTexLevelParameteriv(gl, t, l, pname, p) ...
```

## 内部实现细节

### 格式通道查询

```cpp
static constexpr uint32_t GrGLFormatChannels(GrGLFormat format) {
    switch (format) {
        case GrGLFormat::kUnknown:               return 0;
        case GrGLFormat::kRGBA8:                 return kRGBA_SkColorChannelFlags;
        case GrGLFormat::kR8:                    return kRed_SkColorChannelFlag;
        case GrGLFormat::kALPHA8:                return kAlpha_SkColorChannelFlag;
        case GrGLFormat::kLUMINANCE8:            return kGray_SkColorChannelFlag;
        case GrGLFormat::kBGRA8:                 return kRGBA_SkColorChannelFlags;
        case GrGLFormat::kRGB565:                return kRGB_SkColorChannelFlags;
        // ... 更多格式
    }
    SkUNREACHABLE;
}
```

### 格式描述符

```cpp
static constexpr GrColorFormatDesc GrGLFormatDesc(GrGLFormat format) {
    switch (format) {
        case GrGLFormat::kRGBA8:
            return GrColorFormatDesc::MakeRGBA(8, GrColorTypeEncoding::kUnorm);
        case GrGLFormat::kR8:
            return GrColorFormatDesc::MakeR(8, GrColorTypeEncoding::kUnorm);
        case GrGLFormat::kRGBA16F:
            return GrColorFormatDesc::MakeRGBA(16, GrColorTypeEncoding::kFloat);
        case GrGLFormat::kRGB565:
            return GrColorFormatDesc::MakeRGB(5, 6, 5, GrColorTypeEncoding::kUnorm);
        // ... 更多格式
    }
    SkUNREACHABLE;
}
```

### GL 标准解析

```cpp
GrGLStandard GrGLGetStandardInUseFromString(const char* versionString) {
    if (!versionString) {
        return kNone_GrGLStandard;
    }

    int major, minor;

    // 检测桌面 GL: "3.3"
    if (2 == sscanf(versionString, "%d.%d", &major, &minor)) {
        return kGL_GrGLStandard;
    }

    // 检测 WebGL: "OpenGL ES 2.0 (WebGL 1.0 ...)"
    int esMajor, esMinor;
    if (4 == sscanf(versionString, "OpenGL ES %d.%d (WebGL %d.%d",
                    &esMajor, &esMinor, &major, &minor)) {
        return kWebGL_GrGLStandard;
    }

    // 检测 GLES: "OpenGL ES 3.0"
    if (2 == sscanf(versionString, "OpenGL ES %d.%d", &major, &minor)) {
        return kGLES_GrGLStandard;
    }

    return kNone_GrGLStandard;
}
```

### 版本号解析

```cpp
GrGLVersion GrGLGetVersionFromString(const char* versionString) {
    if (!versionString) {
        return GR_GL_INVALID_VER;
    }

    int major, minor;

    // Mesa: "3.3 Mesa 20.0.8"
    int mesaMajor, mesaMinor;
    if (4 == sscanf(versionString, "%d.%d Mesa %d.%d", &major, &minor, &mesaMajor, &mesaMinor)) {
        return GR_GL_VER(major, minor);
    }

    // 标准格式: "3.3"
    if (2 == sscanf(versionString, "%d.%d", &major, &minor)) {
        return GR_GL_VER(major, minor);
    }

    // WebGL: "OpenGL ES 2.0 (WebGL 1.0)"
    int esMajor, esMinor;
    if (4 == sscanf(versionString, "OpenGL ES %d.%d (WebGL %d.%d",
                    &esMajor, &esMinor, &major, &minor)) {
        return GR_GL_VER(major, minor);
    }

    // OpenGL ES: "OpenGL ES 3.0"
    if (2 == sscanf(versionString, "OpenGL ES %d.%d", &major, &minor)) {
        return GR_GL_VER(major, minor);
    }

    return GR_GL_INVALID_VER;
}
```

### GPU 厂商识别

```cpp
static GrGLVendor get_vendor(const char* vendorString) {
    SkASSERT(vendorString);
    if (0 == strcmp(vendorString, "ARM")) {
        return GrGLVendor::kARM;
    }
    if (0 == strcmp(vendorString, "Google Inc.")) {
        return GrGLVendor::kGoogle;
    }
    if (0 == strcmp(vendorString, "Imagination Technologies")) {
        return GrGLVendor::kImagination;
    }
    if (0 == strncmp(vendorString, "Intel ", 6) || 0 == strcmp(vendorString, "Intel")) {
        return GrGLVendor::kIntel;
    }
    if (0 == strcmp(vendorString, "Qualcomm") || 0 == strcmp(vendorString, "freedreno")) {
        return GrGLVendor::kQualcomm;
    }
    if (0 == strcmp(vendorString, "NVIDIA Corporation")) {
        return GrGLVendor::kNVIDIA;
    }
    if (0 == strcmp(vendorString, "ATI Technologies Inc.")) {
        return GrGLVendor::kATI;
    }
    if (0 == strcmp(vendorString, "Apple")) {
        return GrGLVendor::kApple;
    }
    return GrGLVendor::kOther;
}
```

### GPU 渲染器识别

```cpp
static GrGLRenderer get_renderer(const char* rendererString, const GrGLExtensions& extensions) {
    // NVIDIA Tegra
    if (0 == strncmp(rendererString, "NVIDIA Tegra", 12)) {
        return extensions.has("GL_NV_path_rendering") ? GrGLRenderer::kTegra
                                                      : GrGLRenderer::kTegra_PreK1;
    }

    // Adreno
    int adrenoNumber;
    if (1 == sscanf(rendererString, "Adreno (TM) %d", &adrenoNumber) ||
        1 == sscanf(rendererString, "FD%d", &adrenoNumber)) {
        if (adrenoNumber >= 600) {
            if (adrenoNumber == 615) return GrGLRenderer::kAdreno615;
            if (adrenoNumber == 620) return GrGLRenderer::kAdreno620;
            if (adrenoNumber == 630) return GrGLRenderer::kAdreno630;
            if (adrenoNumber == 640) return GrGLRenderer::kAdreno640;
            return GrGLRenderer::kAdreno6xx_other;
        }
        if (adrenoNumber >= 500) {
            return adrenoNumber == 530 ? GrGLRenderer::kAdreno530
                                       : GrGLRenderer::kAdreno5xx_other;
        }
        if (adrenoNumber >= 400) {
            return adrenoNumber >= 430 ? GrGLRenderer::kAdreno430
                                       : GrGLRenderer::kAdreno4xx_other;
        }
        if (adrenoNumber >= 300) {
            return GrGLRenderer::kAdreno3xx;
        }
    }

    // Intel
    if (const char* intelString = strstr(rendererString, "Intel")) {
        if (strstr(intelString, "RKL")) {
            return GrGLRenderer::kIntelRocketLake;
        }
        if (strstr(intelString, "TGL")) {
            return GrGLRenderer::kIntelTigerLake;
        }
        // ... 更多 Intel GPU 检测
    }

    return GrGLRenderer::kOther;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | OpenGL 接口 |
| `GrGLExtensions` | 扩展查询 |
| `GrTypesPriv` | 颜色格式描述符 |
| `SkColor` | 颜色通道标志 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrGLCaps` | 使用版本解析和硬件识别 |
| `GrGLGpu` | 使用格式查询和宏 |
| `GrGLInterfaceAutogen` | 使用版本查询 |

## 设计模式与设计决策

### 1. Constexpr 编译时计算

所有格式查询函数都是 `constexpr`：

```cpp
static constexpr uint32_t GrGLFormatChannels(GrGLFormat format) { ... }
```

**优势**: 编译器可以在编译时计算结果，零运行时开销

### 2. 宏辅助函数

使用宏包装 GL 调用：

```cpp
#define GR_GL_GetIntegerv(gl, e, p) \
    do { \
        *(p) = GR_GL_INIT_ZERO; \
        GR_GL_CALL(gl, GetIntegerv(e, p)); \
    } while (0)
```

**目的**: 某些驱动要求参数预初始化为 0

### 3. 版本编码

使用位移编码版本号：

```cpp
// 版本 3.3 编码为: (3 << 16) | 3 = 0x00030003
GrGLVersion ver = GR_GL_VER(3, 3);
```

**优势**: 快速比较版本大小

## 性能考量

### 1. 编译时常量

格式查询完全在编译时完成：

```cpp
constexpr uint32_t channels = GrGLFormatChannels(GrGLFormat::kRGBA8);
```

### 2. 字符串解析缓存

版本和硬件信息解析结果会被 `GrGLCaps` 缓存。

### 3. 最小化驱动查询

使用宏预初始化参数，避免驱动内部错误检查。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/gl/GrGLDefines.h` | 依赖 | GL 常量定义 |
| `src/gpu/ganesh/gl/GrGLCaps.h` | 使用者 | 能力检测 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 使用者 | GPU 实现 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | 依赖 | GL 接口 |
| `include/gpu/ganesh/gl/GrGLExtensions.h` | 依赖 | 扩展查询 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | 格式描述符 |
