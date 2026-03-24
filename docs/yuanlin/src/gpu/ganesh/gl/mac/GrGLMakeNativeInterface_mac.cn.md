# GrGLMakeNativeInterface (macOS)

> 源文件
> - src/gpu/ganesh/gl/mac/GrGLMakeNativeInterface_mac.cpp

## 概述

macOS 平台的 OpenGL 接口创建实现。该文件为 macOS 桌面系统提供完整的 OpenGL 函数加载机制，与 iOS 类似使用 `dlopen` 和 `dlsym`，但加载完整的 OpenGL API 而非 OpenGL ES。

## 公共 API 函数

### GrGLInterfaces::MakeMac

```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeMac();
}
```

**功能**：创建 macOS OpenGL 接口对象。

**返回值**：组装好的 OpenGL 接口。

**实现细节**：
```cpp
static const char kPath[] =
    "/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/libGL.dylib";
std::unique_ptr<void, SkFunctionObject<dlclose>> lib(dlopen(kPath, RTLD_LAZY));
return GrGLMakeAssembledGLInterface(lib.get(), [](void* ctx, const char* name) {
        return (GrGLFuncPtr)dlsym(ctx ? ctx : RTLD_DEFAULT, name); });
```

### GrGLMakeNativeInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

**功能**：Legacy 接口，转发到 `GrGLInterfaces::MakeMac()`。

## 内部实现细节

### 与 iOS 的差异

虽然代码结构几乎相同，但有关键区别：

| 特性 | macOS | iOS |
|------|-------|-----|
| OpenGL 版本 | 完整 OpenGL | OpenGL ES |
| 组装函数 | `GrGLMakeAssembledGLInterface` | `GrGLMakeAssembledGLESInterface` |
| API 集合 | 桌面 OpenGL API | 简化的移动 API |
| 库路径 | 相同 | 相同 |

### 动态库加载

**库路径**：
```
/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/libGL.dylib
```

macOS 和 iOS 使用相同的框架路径，但 macOS 版本包含完整的 OpenGL 实现。

### 函数查找逻辑

```cpp
[](void* ctx, const char* name) {
    return (GrGLFuncPtr)dlsym(ctx ? ctx : RTLD_DEFAULT, name);
}
```

与 iOS 相同的查找策略，支持从库或全局命名空间查找。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLAssembleInterface` | 接口组装工具 |
| `GrGLInterface` | GL 函数指针表 |
| `GrGLMakeMacInterface` | macOS 特定声明 |
| `SkTemplates` | `SkFunctionObject` 辅助类 |
| `<dlfcn.h>` | 动态链接函数 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| macOS 应用程序 | 初始化 Skia OpenGL 支持 |
| `GrDirectContext` | 创建 GL 上下文 |

## 设计模式与设计决策

### 代码复用

macOS 和 iOS 实现高度相似：
- 相同的资源管理策略
- 相同的查找逻辑
- 只在接口类型上不同

这种设计简化了维护。

### 编译条件

```cpp
#ifdef SK_BUILD_FOR_MAC
```

确保与其他 Apple 平台（iOS）分离编译。

## 性能考量

性能特性与 iOS 版本相同：
- 延迟符号解析
- 函数指针缓存
- 零运行时查找开销

## macOS 特定考虑

### OpenGL 支持状态

**重要提示**：macOS 在 OpenGL 3.2 Core Profile 后已弃用 OpenGL：
- macOS 10.14+ 推荐使用 Metal
- OpenGL 仍可用但不再更新
- 未来版本可能移除

### 系统库位置

macOS 的系统框架路径：
- 所有版本统一
- SIP（系统完整性保护）保证不被修改
- 可靠的加载路径

### 通用二进制

该代码支持 macOS 的多架构：
- Intel x86_64
- Apple Silicon (ARM64)
- 通过 `dlopen` 自动选择正确架构

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 接口组装函数 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| `include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h` | macOS 特定声明 |
| `include/private/base/SkTemplates.h` | `SkFunctionObject` 定义 |
| `include/core/SkTypes.h` | 基础类型和宏 |
