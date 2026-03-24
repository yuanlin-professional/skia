# GrGLMakeNativeInterface (iOS)

> 源文件
> - src/gpu/ganesh/gl/iOS/GrGLMakeNativeInterface_iOS.cpp

## 概述

iOS 平台的 OpenGL ES 接口创建实现。该文件为 iOS 设备提供 OpenGL ES 函数加载机制，使用 `dlopen` 和 `dlsym` 从系统 OpenGL 框架动态加载函数指针。iOS 使用 OpenGL ES 而非完整的桌面 OpenGL API。

## 公共 API 函数

### GrGLInterfaces::MakeIOS

```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeIOS();
}
```

**功能**：创建 iOS OpenGL ES 接口对象。

**返回值**：组装好的 OpenGL ES 接口。

**实现细节**：
```cpp
static const char kPath[] =
    "/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/libGL.dylib";
std::unique_ptr<void, SkFunctionObject<dlclose>> lib(dlopen(kPath, RTLD_LAZY));
return GrGLMakeAssembledGLESInterface(lib.get(), [](void* ctx, const char* name) {
        return (GrGLFuncPtr)dlsym(ctx ? ctx : RTLD_DEFAULT, name); });
```

### GrGLMakeNativeInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

**功能**：Legacy 接口，转发到 `GrGLInterfaces::MakeIOS()`。

## 内部实现细节

### 动态库加载

**库路径**：
```
/System/Library/Frameworks/OpenGL.framework/Versions/A/Libraries/libGL.dylib
```

这是 iOS 系统 OpenGL 库的标准位置。

**加载标志**：
- `RTLD_LAZY`：延迟符号解析，首次调用时才解析函数地址
- 优化启动性能

### RAII 资源管理

```cpp
std::unique_ptr<void, SkFunctionObject<dlclose>> lib(...);
```

**工作原理**：
- `std::unique_ptr` 管理库句柄生命周期
- `SkFunctionObject<dlclose>` 作为删除器
- 自动在析构时调用 `dlclose` 关闭库

### 函数查找

Lambda 表达式定义查找逻辑：
```cpp
[](void* ctx, const char* name) {
    return (GrGLFuncPtr)dlsym(ctx ? ctx : RTLD_DEFAULT, name);
}
```

**查找策略**：
1. 如果提供了上下文（库句柄），从该库查找
2. 否则使用 `RTLD_DEFAULT`，从默认命名空间查找
3. 返回函数指针，类型转换为 `GrGLFuncPtr`

### OpenGL ES 接口

使用 `GrGLMakeAssembledGLESInterface`：
- 组装 OpenGL ES 特定的函数表
- 与桌面 OpenGL 接口不同（少部分函数，简化版本）

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLAssembleInterface` | 接口组装工具 |
| `GrGLInterface` | GL 函数指针表 |
| `GrGLMakeIOSInterface` | iOS 特定声明 |
| `SkTemplates` | `SkFunctionObject` 辅助类 |
| `<dlfcn.h>` | 动态链接函数 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| iOS 应用程序 | 初始化 Skia OpenGL ES 支持 |
| `GrDirectContext` | 创建 GL 上下文 |

## 设计模式与设计决策

### 延迟加载

`RTLD_LAZY` 标志实现延迟符号解析：
- 只有实际调用的函数才会解析
- 减少启动时间
- 节省内存（未使用的函数不占用地址空间）

### RAII 模式

使用智能指针管理资源：
- 异常安全
- 无需手动调用 `dlclose`
- 避免资源泄漏

### 回退机制

`dlsym` 的 `RTLD_DEFAULT` 回退：
- 允许从全局符号表查找
- 处理弱链接的 OpenGL 函数
- 提高兼容性

## 性能考量

### 延迟符号解析

`RTLD_LAZY` 的性能影响：
- 启动时间：减少（只解析最小必需符号）
- 首次调用：轻微延迟（动态解析）
- 后续调用：无开销（地址已缓存）

### 函数查找缓存

`GrGLMakeAssembledGLESInterface` 会缓存所有函数指针：
- 初始化时查找一次
- 运行时直接使用指针，无查找开销

### 智能指针开销

`std::unique_ptr` 的开销：
- 编译时：零开销（完全内联）
- 运行时：等同于原始指针
- 删除器调用：仅在析构时一次

## iOS 特定考虑

### OpenGL ES vs OpenGL

iOS 使用 OpenGL ES（嵌入式系统版本）：
- API 子集更小
- 针对移动 GPU 优化
- 不支持某些桌面 OpenGL 特性

### 系统框架路径

路径硬编码为系统位置：
- 所有 iOS 设备统一路径
- 由操作系统保证存在
- 不需要运行时搜索

### 编译条件

```cpp
#ifdef SK_BUILD_FOR_IOS
```

确保代码只在 iOS 平台编译，避免在其他平台引入 iOS 特定依赖。

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 接口组装函数 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| `include/gpu/ganesh/gl/ios/GrGLMakeIOSInterface.h` | iOS 特定声明 |
| `include/private/base/SkTemplates.h` | `SkFunctionObject` 定义 |
| `include/core/SkTypes.h` | 基础类型和宏 |
