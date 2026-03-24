# GrMtlTypesPriv

> 源文件
> - src/gpu/ganesh/mtl/GrMtlTypesPriv.h
> - src/gpu/ganesh/mtl/GrMtlTypesPriv.mm

## 概述

`GrMtlTypesPriv` 提供 Metal 后端的内部类型定义和 SDK 版本检测机制，是 Skia Ganesh Metal 后端的基础设施层。该文件负责定义 Metal SDK 版本宏、ARC（Automatic Reference Counting）属性宏，以及 Metal 纹理规格与表面信息之间的转换工具。这些定义和工具函数确保 Skia Metal 后端能够在不同版本的 macOS、iOS 和 tvOS SDK 上正确编译和运行。

## 架构位置

`GrMtlTypesPriv` 位于 Skia GPU 渲染管线的以下位置：

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **作用**：内部类型和工具定义
- **使用者**：所有 Metal 后端组件
- **平台**：仅在 Apple 平台（macOS、iOS、tvOS）编译

## 主要类与结构体

### GrMtlTextureSpec

```cpp
struct GrMtlTextureSpec
```

**核心成员**：
- `GrMTLPixelFormat fFormat` - Metal 像素格式
- `GrMTLTextureUsage fUsage` - 纹理用途标志
- `GrMTLStorageMode fStorageMode` - 存储模式

**构造函数**：
- `GrMtlTextureSpec()` - 默认构造，所有字段初始化为 0
- `GrMtlTextureSpec(const GrMtlSurfaceInfo&)` - 从表面信息构造

**用途**：简化的纹理规格表示，用于内部传递 Metal 纹理配置参数。

## 公共 API 函数

### GrMtlTextureSpecToSurfaceInfo

```cpp
GrMtlSurfaceInfo GrMtlTextureSpecToSurfaceInfo(
    const GrMtlTextureSpec& mtlSpec,
    uint32_t sampleCount,
    uint32_t levelCount,
    skgpu::Protected isProtected)
```

**功能**：将 Metal 纹理规格转换为完整的表面信息结构

**参数**：
- `mtlSpec` - Metal 纹理规格
- `sampleCount` - MSAA 采样数
- `levelCount` - Mipmap 层级数
- `isProtected` - 是否为受保护纹理

**返回**：填充完整的 `GrMtlSurfaceInfo` 结构

**实现**：
```cpp
GrMtlSurfaceInfo info;
info.fSampleCount = sampleCount;
info.fLevelCount = levelCount;
info.fProtected = isProtected;
info.fFormat = mtlSpec.fFormat;
info.fUsage = mtlSpec.fUsage;
info.fStorageMode = mtlSpec.fStorageMode;
return info;
```

## 内部实现细节

### Metal SDK 版本检测

**macOS 版本映射**：
```cpp
#if __MAC_OS_X_VERSION_MAX_ALLOWED >= 130000
#define GR_METAL_SDK_VERSION 300  // macOS 13.0+ (Metal 3.0)
#elif __MAC_OS_X_VERSION_MAX_ALLOWED >= 120000
#define GR_METAL_SDK_VERSION 240  // macOS 12.0+ (Metal 2.4)
#elif __MAC_OS_X_VERSION_MAX_ALLOWED >= 110000
#define GR_METAL_SDK_VERSION 230  // macOS 11.0+ (Metal 2.3)
#elif __MAC_OS_X_VERSION_MAX_ALLOWED >= 101500
#define GR_METAL_SDK_VERSION 220  // macOS 10.15+ (Metal 2.2)
#elif __MAC_OS_X_VERSION_MAX_ALLOWED >= 101400
#define GR_METAL_SDK_VERSION 210  // macOS 10.14+ (Metal 2.1)
#else
#error Must use at least 10.14 SDK to build Metal backend for MacOS
#endif
```

**iOS/tvOS 版本映射**：
```cpp
#if __IPHONE_OS_VERSION_MAX_ALLOWED >= 160000 || __TV_OS_VERSION_MAX_ALLOWED >= 160000
#define GR_METAL_SDK_VERSION 300  // iOS 16+ / tvOS 16+ (Metal 3.0)
#elif __IPHONE_OS_VERSION_MAX_ALLOWED >= 150000 || __TV_OS_VERSION_MAX_ALLOWED >= 150000
#define GR_METAL_SDK_VERSION 240  // iOS 15+ / tvOS 15+ (Metal 2.4)
// ... 更早版本
#else
#error Must use at least 12.00 SDK to build Metal backend for iOS
#endif
```

**用途**：
- 条件编译新版本 Metal API
- 功能探测和降级处理
- 确保最低 SDK 版本要求

### ARC 属性宏

**GR_NORETAIN 宏定义**：
```cpp
#if __has_feature(objc_arc) && __has_attribute(objc_externally_retained)
#define GR_NORETAIN __attribute__((objc_externally_retained))
#define GR_NORETAIN_BEGIN \
    _Pragma("clang attribute push (__attribute__((objc_externally_retained)), apply_to=any(function,objc_method))")
#define GR_NORETAIN_END _Pragma("clang attribute pop")
#else
#define GR_NORETAIN
#define GR_NORETAIN_BEGIN
#define GR_NORETAIN_END
#endif
```

**功能**：
- `objc_externally_retained` 属性告诉 ARC 编译器，对象的所有权由外部管理
- 用于跨越 C++/Objective-C++ 边界的对象传递
- 避免不必要的 retain/release 开销

**使用场景**：
```cpp
GR_NORETAIN_BEGIN
// 这个区域的函数不会自动 retain 参数和返回值
std::unique_ptr<GrGpu> MakeGpu(...) {
    return GrMtlGpu::Make(...);
}
GR_NORETAIN_END
```

## 依赖关系

**公共接口依赖**：
- `include/gpu/ganesh/mtl/GrMtlTypes.h` - 公共 Metal 类型定义
- `include/gpu/ganesh/GrTypes.h` - Ganesh 通用类型

**平台依赖**：
- `<TargetConditionals.h>` - Apple 平台检测

**使用者**：
- 所有 `src/gpu/ganesh/mtl/*.mm` 文件
- Metal 后端的 Objective-C++ 实现

## 设计模式与设计决策

### 平台抽象

通过宏定义统一不同 Apple 平台的版本检测：
- 单一 `GR_METAL_SDK_VERSION` 宏
- 跨 macOS、iOS、tvOS 的一致性
- 简化条件编译代码

### 编译时检查

使用 `#error` 强制最低 SDK 版本：
- macOS 10.14+（Metal 2.1）
- iOS/tvOS 12.0+（Metal 2.1）
- 防止在不支持的平台编译

### ARC 优化

`GR_NORETAIN` 宏优化内存管理：
- 减少不必要的引用计数操作
- 提高跨语言边界调用性能
- 保持代码在非 ARC 环境的兼容性（宏为空）

### 类型转换工具

`GrMtlTextureSpecToSurfaceInfo` 提供单一转换点：
- 集中管理字段映射
- 避免重复的结构体填充代码
- 类型安全的转换

## 性能考量

### ARC 开销减少

`objc_externally_retained` 属性避免：
- 函数参数的自动 retain
- 返回值的自动 retain/autorelease
- 临时对象的引用计数操作

### 编译时优化

宏定义在预处理阶段展开：
- 零运行时开销
- 条件编译避免无用代码
- SDK 版本检测仅影响编译时

### 内联转换

`GrMtlTextureSpecToSurfaceInfo` 是简单赋值，易于编译器内联优化。

## 相关文件

**公共接口**：
- `include/gpu/ganesh/mtl/GrMtlTypes.h` - Metal 公共类型

**Metal 后端核心**：
- `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` - Metal GPU 实现
- `src/gpu/ganesh/mtl/GrMtlTexture.h/mm` - Metal 纹理
- `src/gpu/ganesh/mtl/GrMtlRenderTarget.h/mm` - Metal 渲染目标

**跨语言桥接**：
- `src/gpu/ganesh/mtl/GrMtlTrampoline.h/mm` - C++ 到 Objective-C++ 桥接
