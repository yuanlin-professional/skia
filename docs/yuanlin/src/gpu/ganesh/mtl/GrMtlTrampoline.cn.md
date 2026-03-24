# GrMtlTrampoline

> 源文件
> - src/gpu/ganesh/mtl/GrMtlTrampoline.h
> - src/gpu/ganesh/mtl/GrMtlTrampoline.mm

## 概述

`GrMtlTrampoline` 是 Skia Ganesh Metal 后端的跨语言桥接类，负责从纯 C++ 代码跳转（trampoline）到 Objective-C++ Metal 实现。该类提供静态工厂方法来创建 Metal GPU 对象，隐藏 Objective-C++ 实现细节，使得上层 C++ 代码无需直接处理 Metal API 的 Objective-C 绑定。这种设计模式保持了 Skia 代码库的语言边界清晰，便于维护和跨平台开发。

## 架构位置

`GrMtlTrampoline` 位于 Skia GPU 渲染管线的以下位置：

- **模块层级**：`src/gpu/ganesh/mtl/` - Ganesh Metal 后端
- **作用**：C++ 到 Objective-C++ 桥接层
- **调用者**：`GrDirectContext` 创建逻辑（纯 C++ 代码）
- **被调用者**：`GrMtlGpu` 创建（Objective-C++ 实现）

## 主要类与结构体

### GrMtlTrampoline

```cpp
class GrMtlTrampoline
```

**设计特点**：
- 纯静态类，无实例成员
- 头文件为纯 C++，可包含在任何 C++ 文件中
- 实现文件为 Objective-C++（.mm），直接调用 Metal API

**核心职责**：
- 作为语言边界的桥接点
- 隔离 Objective-C++ 实现细节
- 提供 C++ 风格的工厂方法

## 公共 API 函数

### MakeGpu

```cpp
static std::unique_ptr<GrGpu> MakeGpu(
    const GrMtlBackendContext& backendContext,
    const GrContextOptions& options,
    GrDirectContext* direct)
```

**功能**：创建 Metal GPU 实例

**参数**：
- `backendContext` - Metal 后端上下文，包含 `id<MTLDevice>` 和 `id<MTLCommandQueue>`
- `options` - Ganesh 上下文选项
- `direct` - 直接上下文指针

**返回**：`std::unique_ptr<GrGpu>` - 指向 `GrMtlGpu` 实例的智能指针

**实现**：
```cpp
std::unique_ptr<GrGpu> GrMtlTrampoline::MakeGpu(
        const GrMtlBackendContext& backendContext,
        const GrContextOptions& options,
        GrDirectContext* direct) {
    return GrMtlGpu::Make(backendContext, options, direct);
}
```

**ARC 保护**：
```cpp
GR_NORETAIN_BEGIN
// MakeGpu 实现
GR_NORETAIN_END
```
使用 `GR_NORETAIN` 宏避免 ARC 对返回值进行不必要的引用计数操作。

## 内部实现细节

### 编译时检查

```cpp
#if !__has_feature(objc_arc)
#error This file must be compiled with Arc. Use -fobjc-arc flag
#endif
```

**强制 ARC 编译**：
- `.mm` 文件必须使用 `-fobjc-arc` 编译标志
- 确保 Metal 对象（`id<MTLDevice>` 等）自动管理生命周期
- 防止手动内存管理错误

### 语言边界

**头文件（.h）**：
- 纯 C++ 代码
- 仅前向声明 Metal 相关类型
- 可安全包含在任何 `.cpp` 文件中

**实现文件（.mm）**：
- Objective-C++ 代码
- 包含 Metal 框架头文件
- 直接访问 `GrMtlGpu` Objective-C++ 实现

### 引用计数优化

**GR_NORETAIN 使用**：
```cpp
GR_NORETAIN_BEGIN
std::unique_ptr<GrGpu> MakeGpu(...) {
    return GrMtlGpu::Make(...);
}
GR_NORETAIN_END
```

**效果**：
- 告诉 ARC 编译器返回值由 `std::unique_ptr` 管理
- 避免自动 retain/autorelease
- 减少引用计数操作开销

## 依赖关系

**直接依赖**：
- `src/gpu/ganesh/mtl/GrMtlGpu.h` - Metal GPU 实现
- `src/gpu/ganesh/mtl/GrMtlTypesPriv.h` - Metal 内部类型（`GR_NORETAIN` 宏）

**公共接口依赖**：
- `include/gpu/ganesh/GrTypes.h` - Ganesh 通用类型
- `include/gpu/ganesh/mtl/GrMtlTypes.h` - Metal 公共类型（`GrMtlBackendContext`）

**使用者**：
- `src/gpu/ganesh/GrDirectContext.cpp` - 上下文创建逻辑
- Metal 后端初始化代码

## 设计模式与设计决策

### Trampoline 模式（蹦床模式）

**定义**：提供一个跳转点，将调用从一种语言/环境转发到另一种语言/环境

**实现**：
- `GrMtlTrampoline` 是 C++ 可见的跳板
- 内部跳转到 Objective-C++ 实现（`GrMtlGpu::Make`）
- 隔离语言边界复杂性

### 静态工厂模式

**特点**：
- 无构造函数，纯静态类
- 通过 `MakeGpu` 静态方法创建对象
- 返回基类指针（`GrGpu*`），隐藏实现类型

### Pimpl 变体

虽然不是严格的 Pimpl 模式，但实现了类似的隔离效果：
- 头文件隐藏实现细节
- 实现文件使用不同语言（Objective-C++）
- 客户端无需了解 Metal API

### 编译时安全

**强制 ARC**：
- 使用 `#error` 防止非 ARC 编译
- 确保 Metal 对象正确管理
- 避免内存泄漏和悬空指针

**前向声明**：
- 头文件仅声明类型，不包含定义
- 减少编译依赖
- 加快编译速度

## 性能考量

### 引用计数优化

**GR_NORETAIN 减少开销**：
- 避免返回时的自动 retain
- 避免自动 autorelease
- 直接转移所有权到 `std::unique_ptr`

**估计节省**：
- 每次调用节省 2 次原子操作（retain + autorelease）
- Metal 对象创建是低频操作，但优化仍有价值

### 内联潜力

`MakeGpu` 实现简单，编译器可能内联优化：
- 消除函数调用开销
- 直接跳转到 `GrMtlGpu::Make`

### 编译隔离

将 Objective-C++ 代码隔离到 `.mm` 文件：
- 纯 C++ 文件编译速度更快
- 减少 Metal 框架头文件的传递包含
- 并行编译更高效

## 相关文件

**Metal GPU 实现**：
- `src/gpu/ganesh/mtl/GrMtlGpu.h/mm` - Metal GPU 核心实现

**基类**：
- `src/gpu/ganesh/GrGpu.h` - GPU 抽象基类

**上下文**：
- `src/gpu/ganesh/GrDirectContext.h/cpp` - 直接上下文（调用 MakeGpu）

**类型定义**：
- `include/gpu/ganesh/mtl/GrMtlTypes.h` - Metal 公共类型
- `src/gpu/ganesh/mtl/GrMtlTypesPriv.h` - Metal 内部类型

**其他后端桥接**：
- `src/gpu/ganesh/gl/GrGLMakeNativeInterface_*.cpp` - OpenGL 桥接
- `src/gpu/ganesh/vk/GrVkBackendContext.cpp` - Vulkan 桥接
