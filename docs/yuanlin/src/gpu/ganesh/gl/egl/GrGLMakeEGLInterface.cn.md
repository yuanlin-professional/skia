# GrGLMakeEGLInterface

> 源文件
> - include/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.h
> - src/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.cpp

## 概述

`GrGLMakeEGLInterface` 模块为 Ganesh 渲染引擎提供 EGL（Embedded-System Graphics Library）平台的 OpenGL ES 接口创建功能。EGL 是 Khronos 标准的平台无关 OpenGL ES 窗口系统层，广泛用于嵌入式设备、Android、Linux 等平台。

该模块通过 EGL API 和编译时链接的 OpenGL ES 核心函数，动态加载 OpenGL ES 扩展函数指针，并创建适用于 Skia 的 `GrGLInterface` 对象。

## 架构位置

该模块位于 Ganesh OpenGL 后端的平台特定层：

```
Skia Graphics Library
└── GPU (Ganesh)
    └── OpenGL Backend
        ├── GrGLInterface          ← 抽象接口
        ├── GrGLAssembleInterface  ← 接口组装器
        └── Platform Implementations
            ├── GrGLMakeEGLInterface   ← 当前模块（EGL/ES）
            ├── GrGLMakeWinInterface   ← Windows
            ├── GrGLMakeGLXInterface   ← Linux/X11
            └── GrGLMakeEpoxyEGLInterface ← Epoxy
```

## 主要类与结构体

该模块不定义类，仅提供工厂函数。

## 公共 API 函数

### GrGLInterfaces 命名空间

| 函数签名 | 功能描述 |
|---------|---------|
| `sk_sp<const GrGLInterface> MakeEGL()` | 创建 EGL OpenGL ES 接口对象 |

**返回值**:
- 成功: 返回包含所有 OpenGL ES 函数指针的 `GrGLInterface` 智能指针
- 失败: 返回 `nullptr`（无法组装接口）

### 遗留 API（可选）

| 函数签名 | 功能描述 |
|---------|---------|
| `sk_sp<const GrGLInterface> GrGLMakeEGLInterface()` | 旧版接口名称（调用 `MakeEGL()`） |

**注意**: 如果定义了 `SK_DISABLE_LEGACY_EGLINTERFACE_FACTORY`，此函数不可用。

## 内部实现细节

### 核心函数宏定义

使用宏定义方式直接链接 OpenGL ES 核心函数：

```cpp
#ifndef GL_GLEXT_PROTOTYPES
#define GL_GLEXT_PROTOTYPES
#endif
#include <GLES2/gl2.h>
```

- `GL_GLEXT_PROTOTYPES`: 启用 OpenGL ES 扩展函数原型声明
- `<GLES2/gl2.h>`: 包含 OpenGL ES 2.0 核心函数声明

### 函数指针获取策略

定义静态函数作为函数指针获取器：

```cpp
static GrGLFuncPtr egl_get_gl_proc(void* ctx, const char name[]) {
    SkASSERT(nullptr == ctx);

    // 1. 首先尝试从编译时链接的核心函数获取
    #define M(X) if (0 == strcmp(#X, name)) { return (GrGLFuncPtr) X; }
    GR_GL_CORE_FUNCTIONS_EACH(M)
    #undef M

    // 2. 然后尝试从 EGL 获取扩展函数
    return eglGetProcAddress(name);
}
```

**查找顺序**:
1. **核心函数**: 直接使用编译时链接的符号（如 `glGetString`、`glDrawArrays`）
2. **扩展函数**: 通过 `eglGetProcAddress` 动态获取（如 `glBindVertexArray`）

**优势**:
- 核心函数查找速度快，无需动态查询
- 扩展函数通过 EGL 动态加载，支持运行时扩展检测

### 核心函数宏展开

`GR_GL_CORE_FUNCTIONS_EACH` 宏展开所有 OpenGL ES 核心函数：

```cpp
// 示例展开结果
if (0 == strcmp("glActiveTexture", name)) { return (GrGLFuncPtr) glActiveTexture; }
if (0 == strcmp("glAttachShader", name)) { return (GrGLFuncPtr) glAttachShader; }
if (0 == strcmp("glBindBuffer", name)) { return (GrGLFuncPtr) glBindBuffer; }
// ... 数十个核心函数
```

### 接口组装

调用通用的接口组装函数：

```cpp
sk_sp<const GrGLInterface> MakeEGL() {
    return GrGLMakeAssembledInterface(nullptr, egl_get_gl_proc);
}
```

**组装过程**:
- 遍历所有 Skia 需要的 OpenGL ES 函数
- 使用 `egl_get_gl_proc` 查找每个函数的地址
- 填充 `GrGLInterface` 结构体的函数指针表
- 验证必需的函数是否都已找到
- 根据可用的扩展函数设置接口能力标志

### 遗留 API 包装

提供旧版 API 的兼容性包装：

```cpp
#if !defined(SK_DISABLE_LEGACY_EGLINTERFACE_FACTORY)
sk_sp<const GrGLInterface> GrGLMakeEGLInterface() {
    return GrGLInterfaces::MakeEGL();
}
#endif
```

允许代码在不修改的情况下继续使用旧接口名称。

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖原因 |
|---------|---------|
| `GrGLInterface` | 提供 OpenGL 接口抽象 |
| `GrGLAssembleInterface` | 提供接口组装函数 |
| `GrGLCoreFunctions` | 定义核心函数列表宏 |
| `GrGLUtil` | 提供 OpenGL 工具函数 |
| `<EGL/egl.h>` | EGL API 头文件 |
| `<GLES2/gl2.h>` | OpenGL ES 2.0 头文件 |

### 被依赖的模块

| 模块名称 | 使用方式 |
|---------|---------|
| `GrContext` | 创建 EGL OpenGL ES 上下文 |
| `SkSurface` | 创建 EGL OpenGL ES 表面 |
| Android 应用 | Android 平台的 Skia GPU 支持 |
| Linux 应用 | Linux 嵌入式设备的 GPU 支持 |

## 设计模式与设计决策

### 1. 工厂模式

`MakeEGL()` 是工厂函数，负责创建和初始化复杂的 `GrGLInterface` 对象。

### 2. 策略模式

通过函数指针传递函数获取策略，允许不同平台使用不同的实现。

### 3. 宏元编程

使用 `GR_GL_CORE_FUNCTIONS_EACH` 宏遍历核心函数，避免手动枚举数十个函数。

### 4. 编译时绑定 + 运行时加载

核心函数在编译时链接，扩展函数在运行时通过 EGL 动态加载，平衡性能和灵活性。

### 5. 命名空间隔离

使用 `GrGLInterfaces` 命名空间避免全局命名冲突。

### 6. 遗留 API 兼容

通过条件编译提供旧版 API，支持平滑迁移。

## 性能考量

### 1. 核心函数零开销

核心函数直接使用编译时链接的符号，无需运行时查找。

### 2. 扩展函数缓存

创建的 `GrGLInterface` 对象缓存所有函数指针，避免重复查找。

### 3. 宏展开效率

字符串比较在编译时优化为跳转表或哈希查找，实际运行时效率高。

### 4. 无上下文参数

`ctx` 参数为 `nullptr`，避免不必要的上下文传递开销。

### 5. 智能指针开销

使用 `sk_sp` 智能指针管理接口生命周期，引用计数开销可忽略。

## 相关文件

| 文件路径 | 作用 |
|---------|------|
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 接口抽象定义 |
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 接口组装函数声明 |
| `src/gpu/ganesh/gl/GrGLCoreFunctions.h` | 核心函数列表宏定义 |
| `src/gpu/ganesh/gl/GrGLUtil.h` | OpenGL 工具函数 |
| `include/gpu/ganesh/GrTypes.h` | Ganesh 基础类型 |
| `include/core/SkRefCnt.h` | 智能指针定义 |
| `<EGL/egl.h>` | EGL API 头文件（系统提供） |
| `<GLES2/gl2.h>` | OpenGL ES 2.0 头文件（系统提供） |
