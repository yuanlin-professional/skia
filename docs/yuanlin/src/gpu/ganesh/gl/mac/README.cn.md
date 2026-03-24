# mac/ - macOS 平台 OpenGL 接口

## 概述

`mac/` 目录提供 macOS 平台上的原生 OpenGL 接口加载实现。该目录通过 macOS 的动态链接机制（`dlopen`/`dlsym`）加载系统 OpenGL 框架中的函数指针，组装成 Skia 所需的 `GrGLInterface` 对象。

macOS 上使用的是桌面版 OpenGL（Desktop GL），而非 OpenGL ES。函数指针从 Apple 的 OpenGL 框架动态库中获取。

**注意：** Apple 从 macOS 10.14 (Mojave) 开始弃用了 OpenGL，推荐使用 Metal。但 Skia 仍然支持 macOS 上的 OpenGL 后端以保持兼容性。

## 文件分类索引

### 1. macOS GL 接口 — macOS Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeNativeInterface_mac.cpp | macOS Desktop GL 接口创建实现（dlopen/dlsym） |

## 关键实现

### GrGLInterfaces::MakeMac()

```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeMac() {
    static const char kPath[] =
        "/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/libGL.dylib";
    std::unique_ptr<void, SkFunctionObject<dlclose>> lib(dlopen(kPath, RTLD_LAZY));
    return GrGLMakeAssembledGLInterface(lib.get(), [](void* ctx, const char* name) {
            return (GrGLFuncPtr)dlsym(ctx ? ctx : RTLD_DEFAULT, name); });
}
}
```

**实现细节：**
1. 使用 `dlopen` 以 `RTLD_LAZY` 模式加载 OpenGL 框架的动态库
2. 使用 `dlsym` 按名称查找每个 GL 函数的地址
3. 如果传入的库句柄为空，则回退到 `RTLD_DEFAULT`（搜索所有已加载的共享库）
4. 调用 `GrGLMakeAssembledGLInterface()` 组装**桌面 GL**接口（非 GLES）
5. 库句柄通过 `SkFunctionObject<dlclose>` 自动管理生命周期

### 旧版兼容

文件中还提供了旧版的 `GrGLMakeNativeInterface()` 全局函数，仅在未定义 `SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE` 时可用。新代码应使用 `GrGLInterfaces::MakeMac()`。

## 编译条件

整个文件包含在 `#ifdef SK_BUILD_FOR_MAC` 守卫中，仅在 macOS 构建环境下编译。

## 依赖关系

- **上游：** 由 `GrGLDirectContext.cpp` 或用户代码调用以创建 macOS GL 上下文
- **下游：** 依赖 `GrGLMakeAssembledGLInterface()`（定义在 `GrGLAssembleGLInterfaceAutogen.cpp`）
- **系统依赖：** macOS OpenGL.framework, `<dlfcn.h>`
