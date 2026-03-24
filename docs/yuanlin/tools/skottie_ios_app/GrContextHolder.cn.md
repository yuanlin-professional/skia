# GrContextHolder

> 源文件：tools/skottie_ios_app/GrContextHolder.h, tools/skottie_ios_app/GrContextHolder.mm

## 概述

GrContextHolder 是一个轻量级的 RAII 包装器，用于管理 GrDirectContext 的生命周期。该模块提供了智能指针式的所有权管理，确保 Ganesh 上下文在不再需要时正确释放。此外，它还提供了创建 OpenGL 上下文的便捷工厂函数。

主要特性：
- 使用 std::unique_ptr 管理 GrDirectContext
- 自定义删除器确保正确释放
- 工厂函数简化 OpenGL 上下文创建
- 条件编译支持（仅在 SK_GANESH 定义时可用）

该模块虽然代码量小，但对于正确的资源管理至关重要。

## 架构位置

- **角色**：资源管理包装器
- **使用者**：SkMetalViewBridge、iOS 应用代码
- **管理对象**：GrDirectContext（Ganesh GPU 上下文）

## 主要组件

### GrContextRelease（自定义删除器）

```cpp
struct GrContextRelease {
    void operator()(GrDirectContext* ptr);
};
```

自定义删除器，调用 `SkSafeUnref` 释放上下文。

**实现**：
```cpp
#if defined(SK_GANESH)
void GrContextRelease::operator()(GrDirectContext* ptr) {
    SkSafeUnref(ptr);
}
#else
void GrContextRelease::operator()(GrDirectContext*) {
    SkDEBUGFAIL("");  // 不应在禁用 Ganesh 时调用
}
#endif
```

### GrContextHolder（类型别名）

```cpp
using GrContextHolder = std::unique_ptr<GrDirectContext, GrContextRelease>;
```

使用 unique_ptr 和自定义删除器的智能指针。

### SkMakeGLContext（工厂函数）

```cpp
GrContextHolder SkMakeGLContext();
```

创建默认的 OpenGL Ganesh 上下文。

**实现**：
```cpp
#ifdef SK_GL
GrContextHolder SkMakeGLContext() {
    return GrContextHolder(
        GrDirectContexts::MakeGL(nullptr, GrContextOptions()).release()
    );
}
#endif
```

参数说明：
- `nullptr` - 使用默认 GrGLInterface（自动检测）
- `GrContextOptions()` - 使用默认选项

## 内部实现细节

### 所有权转移

```cpp
GrDirectContexts::MakeGL(...).release()
```

`MakeGL` 返回 `sk_sp`（Skia 智能指针），调用 `release()` 转移所有权到 `unique_ptr`。

### 条件编译

整个模块使用多层条件编译：
```cpp
#if defined(SK_GANESH)
#ifdef SK_GL
// OpenGL 特定代码
#endif
#endif
```

确保仅在支持时编译。

### 引用计数管理

GrDirectContext 使用 Skia 的引用计数系统（`SkRefCnt`）：
- `SkSafeUnref` 安全递减引用计数
- 引用计数为 0 时自动删除对象

### 错误处理

在禁用 Ganesh 时尝试删除上下文会触发调试断言：
```cpp
SkDEBUGFAIL("");
```

这防止在不支持的配置中误用。

## 依赖关系

### Skia Ganesh
- `include/gpu/ganesh/GrDirectContext.h` - 直接上下文接口
- `include/gpu/ganesh/GrContextOptions.h` - 上下文选项
- `include/gpu/ganesh/gl/GrGLDirectContext.h` - OpenGL 上下文

### Skia 核心
- `include/core/SkTypes.h` - 基础类型和宏
- `include/core/SkRefCnt.h` - 引用计数（隐式）

## 设计模式与设计决策

### RAII 模式
GrContextHolder 遵循 RAII（Resource Acquisition Is Initialization）：
- 构造时获取资源
- 析构时自动释放
- 异常安全

### 自定义删除器
使用自定义删除器适配 Skia 的引用计数系统：
```cpp
std::unique_ptr<GrDirectContext, GrContextRelease>
```

### 类型别名简化
`using GrContextHolder = ...` 简化类型声明：
```cpp
// 使用前
std::unique_ptr<GrDirectContext, GrContextRelease> ctx;

// 使用后
GrContextHolder ctx;
```

### 工厂函数封装
`SkMakeGLContext` 封装创建细节，提供简洁接口：
```cpp
auto ctx = SkMakeGLContext();  // 简单！
```

### 所有权语义
使用 `unique_ptr` 明确唯一所有权，防止意外共享。

## 性能考量

- unique_ptr 零开销抽象
- 引用计数的小量原子操作开销
- 避免手动内存管理的错误

## 相关文件

- `tools/skottie_ios_app/SkMetalViewBridge.h/.mm` - 使用 GrContextHolder
- `include/gpu/ganesh/GrDirectContext.h` - Ganesh 直接上下文
- `include/gpu/ganesh/gl/GrGLDirectContext.h` - OpenGL 上下文创建
- `include/gpu/ganesh/mtl/GrMtlDirectContext.h` - Metal 上下文创建
