# GrGLAssembleHelpers

> 源文件
> - include/gpu/ganesh/gl/GrGLAssembleHelpers.h
> - src/gpu/ganesh/gl/GrGLAssembleHelpers.cpp

## 概述

`GrGLAssembleHelpers` 是 Skia Ganesh OpenGL 后端中的辅助工具模块,专门用于获取 EGL 扩展查询功能。该模块提供了一个核心函数 `GrGetEGLQueryAndDisplay()`,用于在运行时动态获取 EGL 的字符串查询函数指针和当前显示句柄。

这是一个非常轻量级的模块,仅包含一个函数和少量依赖。它在 OpenGL 接口组装过程中被使用,帮助确定可用的 EGL 扩展,从而正确配置 OpenGL 功能集。该模块特别关注 EGL(Embedded-System Graphics Library)环境,这是 OpenGL ES 在移动设备和嵌入式系统上的窗口系统集成层。

## 架构位置

该模块位于 OpenGL 接口组装流程的底层:

```
GrGLInterface 创建流程
    ↓
GrGLAssembleInterface (组装 GL 函数指针)
    ↓
GrGLAssembleHelpers (EGL 查询辅助) ← 当前模块
    ↓
动态库函数查找 (dlsym/GetProcAddress)
```

在 GPU 后端初始化阶段,当需要在 EGL 环境下创建 OpenGL 上下文时,该模块帮助查询 EGL 扩展信息,以便正确配置 GL 接口。

## 主要类与结构体

该模块不包含类或结构体,仅提供函数式接口。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `void GrGetEGLQueryAndDisplay(GrEGLQueryStringFn**, GrEGLDisplay*, void*, GrGLGetProc)` | 获取 EGL 查询字符串函数指针和当前显示句柄 |

### 函数参数详解

**GrGetEGLQueryAndDisplay:**
- `queryString`: 输出参数,返回 `eglQueryString` 函数指针
- `display`: 输出参数,返回当前 EGL 显示句柄
- `ctx`: 上下文指针,传递给 `get` 函数
- `get`: 函数指针获取器,用于动态查找符号

## 内部实现细节

### 函数实现逻辑

```cpp
void GrGetEGLQueryAndDisplay(GrEGLQueryStringFn** queryString,
                             GrEGLDisplay* display,
                             void* ctx,
                             GrGLGetProc get) {
    // 尝试获取 eglQueryString 函数指针
    *queryString = (GrEGLQueryStringFn*)get(ctx, "eglQueryString");

    // 默认设置显示为无效值
    *display = GR_EGL_NO_DISPLAY;

    if (*queryString) {
        // 如果成功获取查询函数,尝试获取当前显示句柄
        GrEGLGetCurrentDisplayFn* getCurrentDisplay =
                (GrEGLGetCurrentDisplayFn*)get(ctx, "eglGetCurrentDisplay");

        if (getCurrentDisplay) {
            *display = getCurrentDisplay();
        } else {
            // 如果无法获取显示句柄,则查询函数也无效
            *queryString = nullptr;
        }
    }
}
```

### 实现要点

1. **防御性编程**: 所有函数指针都通过动态查找获取,需要处理查找失败的情况
2. **原子性保证**: 如果无法同时获取查询函数和显示句柄,则都返回空/无效值
3. **类型转换**: 使用 C 风格转换将 `void*` 转为具体函数指针类型

### 依赖的 EGL 函数

- `eglQueryString`: 查询 EGL 字符串信息(如扩展列表、版本等)
- `eglGetCurrentDisplay`: 获取当前线程的 EGL 显示连接

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrGLAssembleInterface.h` | 提供函数类型定义和接口 |
| `GrGLFunctions.h` | 定义 GL 和 EGL 函数指针类型 |
| `GrGLTypes.h` | 定义 GL 和 EGL 基础类型 |
| `GrGLDefines.h` | 定义 GL 和 EGL 常量(如 `GR_EGL_NO_DISPLAY`) |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| `GrGLAssembleInterface.cpp` | 在组装 OpenGL 接口时调用此辅助函数 |
| `GrGLAssembleGLESInterface.cpp` | 组装 OpenGL ES 接口时使用 |
| 各平台 GL 集成代码 | Android、Linux、嵌入式系统的 GL 初始化 |

## 设计模式与设计决策

### 单一职责原则

该模块只做一件事:获取 EGL 查询能力。这使得代码易于理解、测试和维护。

### 函数式接口

使用纯函数而非类,因为:
- 无需维护状态
- 避免对象创建开销
- 更容易在 C 接口环境中使用
- 更清晰的依赖关系

### 显式输出参数

使用指针作为输出参数而非返回结构体:
- 允许单个函数返回多个值
- 避免结构体构造和拷贝
- 更接近 C 语言风格(EGL 本身是 C API)

### 失败时的清理策略

如果只获取到部分功能(只有 `eglQueryString` 但没有 `eglGetCurrentDisplay`),则将查询函数也设为 null:

```cpp
if (getCurrentDisplay) {
    *display = getCurrentDisplay();
} else {
    *queryString = nullptr;  // 部分功能无效,全部作废
}
```

这确保调用者不会在不完整的 EGL 环境下误用查询功能。

### 平台中立性

通过函数指针获取器抽象,该模块不依赖特定的动态链接机制:
- Windows: 使用 `GetProcAddress`
- Linux/Android: 使用 `dlsym` 或 `eglGetProcAddress`
- 其他平台: 自定义实现

## 性能考量

### 最小化开销

该函数仅在 OpenGL 上下文初始化时调用一次,不在渲染循环中使用,因此性能不是关键考虑因素。

### 避免重复查找

查询结果被缓存在 `GrGLInterface` 对象中,不需要重复调用此函数。

### 直接函数调用

获取到的函数指针可以直接调用,无需额外的间接层。

### 编译器优化

该函数足够简单,编译器可以轻松内联和优化。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 定义接口组装函数 |
| `src/gpu/ganesh/gl/GrGLAssembleInterface.cpp` | 使用此辅助函数组装接口 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 接口类定义 |
| `include/gpu/ganesh/gl/GrGLFunctions.h` | GL/EGL 函数指针类型 |
| `include/gpu/ganesh/gl/GrGLTypes.h` | GL/EGL 基础类型 |
| `src/gpu/ganesh/gl/GrGLDefines.h` | GL/EGL 常量定义 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | 其他 GL 工具函数 |
