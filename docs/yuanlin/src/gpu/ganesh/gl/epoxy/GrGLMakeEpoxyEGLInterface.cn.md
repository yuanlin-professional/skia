# GrGLMakeEpoxyEGLInterface

> 源文件
> - include/gpu/ganesh/gl/epoxy/GrGLMakeEpoxyEGLInterface.h
> - src/gpu/ganesh/gl/epoxy/GrGLMakeEpoxyEGLInterface.cpp

## 概述

`GrGLMakeEpoxyEGLInterface` 模块为 Ganesh 渲染引擎提供基于 Epoxy 库的 OpenGL ES 接口创建功能。Epoxy 是一个 OpenGL 函数指针管理库，提供跨平台的 OpenGL 函数加载和调用机制，自动处理不同 OpenGL 版本和扩展的兼容性问题。

该模块是 EGL 接口的 Epoxy 变体，适用于使用 Epoxy 库的应用程序（如某些 Linux 发行版的图形栈）。

## 架构位置

该模块位于 Ganesh OpenGL 后端的平台特定层：

```
Skia Graphics Library
└── GPU (Ganesh)
    └── OpenGL Backend
        ├── GrGLInterface          ← 抽象接口
        ├── GrGLAssembleInterface  ← 接口组装器
        └── Platform Implementations
            ├── GrGLMakeEpoxyEGLInterface ← 当前模块（Epoxy/EGL）
            ├── GrGLMakeEGLInterface      ← 标准 EGL
            ├── GrGLMakeWinInterface      ← Windows
            └── GrGLMakeGLXInterface      ← Linux/X11
```

## 主要类与结构体

该模块不定义类，仅提供工厂函数。

## 公共 API 函数

### GrGLInterfaces 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `sk_sp<const GrGLInterface> MakeEpoxyEGL()` | 创建基于 Epoxy 的 EGL OpenGL ES 接口对象 |

**返回值**:
- 成功: 返回包含所有 OpenGL ES 函数指针的 `GrGLInterface` 智能指针
- 失败: 返回 `nullptr`（无法组装接口）

## 内部实现细节

### Epoxy 头文件包含

包含 Epoxy 提供的 OpenGL 和 EGL 头文件：

```cpp
#include <epoxy/egl.h>
#include <epoxy/gl.h>
```

Epoxy 提供了统一的 OpenGL 函数声明和加载机制，简化了跨版本和跨平台的兼容性处理。

### 函数指针获取策略

定义静态函数作为函数指针获取器：

```cpp
static GrGLFuncPtr epoxy_get_gl_proc(void* ctx, const char name[]) {
    SkASSERT(nullptr == ctx);

    // 1. 首先尝试从 Epoxy 包装的核心函数获取
    #define M(X) if (0 == strcmp(#X, name)) { return (GrGLFuncPtr) epoxy_ ## X; }
    GR_GL_CORE_FUNCTIONS_EACH(M)
    #undef M

    // 2. 然后尝试从 Epoxy 的 EGL 扩展加载器获取
    return epoxy_eglGetProcAddress(name);
}
```

**查找顺序**:
1. **Epoxy 包装的核心函数**: 使用 `epoxy_` 前缀的函数（如 `epoxy_glGetString`）
2. **扩展函数**: 通过 `epoxy_eglGetProcAddress` 动态获取

### Epoxy 函数命名约定

Epoxy 为所有 OpenGL 函数添加 `epoxy_` 前缀：

```cpp
// 原生 OpenGL 函数
glActiveTexture(...)

// Epoxy 包装的函数
epoxy_glActiveTexture(...)
```

这种命名约定允许 Epoxy 拦截所有 OpenGL 调用，动态解析正确的函数指针。

### 宏展开示例

`GR_GL_CORE_FUNCTIONS_EACH` 宏在 Epoxy 环境下展开：

```cpp
// 示例展开结果
if (0 == strcmp("glActiveTexture", name)) {
    return (GrGLFuncPtr) epoxy_glActiveTexture;
}
if (0 == strcmp("glAttachShader", name)) {
    return (GrGLFuncPtr) epoxy_glAttachShader;
}
// ... 数十个核心函数
```

### 接口组装

调用通用的接口组装函数：

```cpp
sk_sp<const GrGLInterface> MakeEpoxyEGL() {
    return GrGLMakeAssembledInterface(nullptr, epoxy_get_gl_proc);
}
```

**Epoxy 的优势**:
- 自动检测 OpenGL 版本和扩展
- 延迟加载函数指针，仅在首次调用时解析
- 处理多上下文场景，每个上下文可以有不同的函数指针

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGLInterface` | 提供 OpenGL 接口抽象 |
| `GrGLAssembleInterface` | 提供接口组装函数 |
| `GrGLCoreFunctions` | 定义核心函数列表宏 |
| `GrGLUtil` | 提供 OpenGL 工具函数 |
| `<epoxy/egl.h>` | Epoxy EGL 头文件 |
| `<epoxy/gl.h>` | Epoxy OpenGL 头文件 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrContext` | 创建基于 Epoxy 的 OpenGL 上下文 |
| `SkSurface` | 创建 Epoxy OpenGL 表面 |
| Linux 应用 | 使用 Epoxy 的 Linux 应用的 GPU 支持 |
| Wayland 应用 | Wayland 图形栈通常使用 Epoxy |

## 设计模式与设计决策

### 1. 适配器模式

将 Epoxy 的 OpenGL 函数适配为 Skia 的 `GrGLInterface` 接口。

### 2. 工厂模式

`MakeEpoxyEGL()` 是工厂函数，负责创建和初始化复杂的 `GrGLInterface` 对象。

### 3. 策略模式

通过函数指针传递 Epoxy 特定的函数获取策略。

### 4. 宏元编程

使用宏遍历核心函数，避免手动维护函数列表。

### 5. 命名空间隔离

使用 `GrGLInterfaces` 命名空间避免全局命名冲突。

### 6. 库依赖封装

将 Epoxy 的使用细节封装在实现文件中，头文件不暴露 Epoxy API。

## 性能考量

### 1. Epoxy 延迟加载

Epoxy 首次调用时才解析函数指针，后续调用直接使用缓存的指针，性能接近直接调用。

### 2. 函数指针缓存

创建的 `GrGLInterface` 对象缓存所有函数指针，避免重复查找。

### 3. 宏展开优化

编译器优化后，字符串比较转换为高效的跳转表。

### 4. 无额外间接层

Epoxy 的函数包装开销极小，发布版本几乎无性能损失。

### 5. 智能指针开销

使用 `sk_sp` 智能指针管理接口生命周期，引用计数开销可忽略。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 接口抽象定义 |
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 接口组装函数声明 |
| `src/gpu/ganesh/gl/GrGLCoreFunctions.h` | 核心函数列表宏定义 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
| `include/core/SkRefCnt.h` | 智能指针定义 |
| `<epoxy/egl.h>` | Epoxy EGL 头文件（外部库） |
| `<epoxy/gl.h>` | Epoxy OpenGL 头文件（外部库） |
