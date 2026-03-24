# iOS/ - iOS 平台 OpenGL ES 接口

## 概述

`iOS/` 目录提供 iOS 平台上的 OpenGL ES 接口加载实现。与 macOS 使用桌面 GL 不同，iOS 使用 OpenGL ES 标准。该目录通过 `dlopen`/`dlsym` 机制加载 iOS 系统的 OpenGL 框架，组装 GL ES 接口。

**重要说明：** Apple 从 iOS 12 开始弃用了 OpenGL ES，推荐使用 Metal。iOS 上的 OpenGL ES 最高支持到 3.0 版本。Skia 保留此后端主要是为了向后兼容。在新的 iOS 项目中，建议优先使用 Skia 的 Metal 后端。

## 文件分类索引

### 1. iOS GL ES 接口 — iOS Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeNativeInterface_iOS.cpp | iOS GL ES 接口创建实现（dlopen/dlsym） |

## 关键实现

### GrGLInterfaces::MakeIOS()

```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeIOS() {
    static const char kPath[] =
        "/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/libGL.dylib";
    std::unique_ptr<void, SkFunctionObject<dlclose>> lib(dlopen(kPath, RTLD_LAZY));
    return GrGLMakeAssembledGLESInterface(lib.get(), [](void* ctx, const char* name) {
            return (GrGLFuncPtr)dlsym(ctx ? ctx : RTLD_DEFAULT, name); });
}
}
```

**与 macOS 实现的关键区别：**
- iOS 调用 `GrGLMakeAssembledGLESInterface()`（GL ES），而非 macOS 的 `GrGLMakeAssembledGLInterface()`（Desktop GL）
- GL ES 接口仅包含 ES 规范中定义的函数子集

**实现细节：**
1. 通过 `dlopen` 加载 OpenGL 框架动态库
2. 使用 `dlsym` 查找函数地址
3. 回退到 `RTLD_DEFAULT` 搜索所有已加载的库
4. 组装 GL ES 接口（支持 ES 2.0/3.0）

## 编译条件

整个文件包含在 `#ifdef SK_BUILD_FOR_IOS` 守卫中，仅在 iOS 构建环境下编译。

## 旧版兼容

提供旧版 `GrGLMakeNativeInterface()` 全局函数，在未定义 `SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE` 时可用。新代码应使用 `GrGLInterfaces::MakeIOS()`。

## 依赖关系

- **上游：** 由 iOS 应用代码或 `GrGLDirectContext.cpp` 调用
- **下游：** 依赖 `GrGLMakeAssembledGLESInterface()`
- **系统依赖：** iOS OpenGLES.framework, `<dlfcn.h>`

## 注意事项

- iOS 模拟器和真机设备的 GL ES 实现可能有差异
- 某些高级 GL ES 3.0 特性在旧设备上不可用
- Apple 推荐迁移至 Metal，OpenGL ES 在未来的 iOS 版本中可能被移除
