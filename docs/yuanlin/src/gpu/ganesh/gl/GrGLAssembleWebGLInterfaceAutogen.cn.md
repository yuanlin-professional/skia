# GrGLAssembleWebGLInterfaceAutogen

> 源文件
> - src/gpu/ganesh/gl/GrGLAssembleWebGLInterfaceAutogen.cpp

## 概述

`GrGLAssembleWebGLInterfaceAutogen.cpp` 是一个自动生成的源文件，专门为 WebGL 环境（基于 Emscripten 编译到 WebAssembly）加载和组装 OpenGL 函数指针。该文件通过 `GrGLMakeAssembledWebGLInterface` 函数创建针对 WebGL 优化的 `GrGLInterface` 对象，使用 Emscripten 提供的静态绑定而非动态加载。

**重要提示**：此文件由 `tools/ganesh/gl/interface/templates.go` 自动生成，不应手动编辑。

## 架构位置

该文件位于 Ganesh OpenGL 后端的 WebGL 实现层：

```
src/gpu/ganesh/gl/
├── GrGLInterface (接口类)
├── GrGLAssembleGLInterfaceAutogen.cpp (桌面 GL)
├── GrGLAssembleGLESInterfaceAutogen.cpp (OpenGL ES)
└── GrGLAssembleWebGLInterfaceAutogen.cpp (WebGL - 本文件)
```

该文件是三个平台特定实现之一，专门处理 WebGL 1.0/2.0 环境。

## 主要类与结构体

### GrGLInterface

该文件创建并填充 `GrGLInterface` 对象：

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFunctions` | `GrGLInterface::Functions` | 包含所有 WebGL 函数指针的结构体 |
| `fStandard` | `GrGLStandard` | 标识为 `kWebGL_GrGLStandard` |
| `fExtensions` | `GrGLExtensions` | 支持的 WebGL 扩展列表 |

## 公共 API 函数

### GrGLMakeAssembledWebGLInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeAssembledWebGLInterface(void* ctx, GrGLGetProc get)
```

**参数：**
- `ctx`：上下文指针（WebGL 中未使用）
- `get`：函数指针获取回调（WebGL 中未使用，使用静态绑定）

**返回值：**
- 成功：包含完整函数指针的 `GrGLInterface` 智能指针
- 失败：`nullptr`（如果 WebGL 版本不足）

**编译条件：**
- 需要 `__EMSCRIPTEN__` 宏定义
- 不能定义 `SK_DISABLE_WEBGL_INTERFACE`

## 内部实现细节

### 编译时禁用

如果不在 Emscripten 环境或被禁用，返回空实现：
```cpp
#if SK_DISABLE_WEBGL_INTERFACE || !defined(__EMSCRIPTEN__)
sk_sp<const GrGLInterface> GrGLMakeAssembledWebGLInterface(void *ctx, GrGLGetProc get) {
    return nullptr;
}
#endif
```

### WebGL 头文件

包含 Emscripten 提供的 WebGL 头文件：
```cpp
#include <webgl/webgl1.h>
#include <webgl/webgl1_ext.h>
#include <webgl/webgl2.h>
#include <webgl/webgl2_ext.h>
```

### 版本检查

WebGL 1.0 是最低要求：
```cpp
const char* verStr = reinterpret_cast<const char*>(glGetString(GR_GL_VERSION));
GrGLVersion glVer = GrGLGetVersionFromString(verStr);
if (glVer < GR_GL_VER(1,0)) {
    return nullptr;
}
```

### 函数绑定宏

WebGL 使用静态绑定而非动态加载：

| 宏 | 用途 | 示例 |
|-----|------|------|
| `GET_PROC(F)` | 绑定标准函数 | `GET_PROC(ActiveTexture)` → `emscripten_glActiveTexture` |
| `GET_PROC_SUFFIX(F, S)` | 绑定扩展函数 | `GET_PROC_SUFFIX(BindVertexArray, OES)` → `emscripten_glBindVertexArrayOES` |

**关键差异**：不使用 `get(ctx, name)` 动态查找，直接使用 Emscripten 编译时绑定的函数。

### 扩展初始化

WebGL 扩展查询更简单：
```cpp
GrGLExtensions extensions;
if (!extensions.init(kWebGL_GrGLStandard, glGetString, glGetStringi, glGetIntegerv)) {
    return nullptr;
}
```

不需要 EGL 查询，因为 WebGL 有标准的扩展机制。

## 支持的功能分类

### 核心 WebGL 1.0 函数（40个）

所有 WebGL 1.0 核心函数都被绑定：
- 纹理操作：`ActiveTexture`, `BindTexture`, `TexImage2D`
- 着色器：`CreateShader`, `CompileShader`, `LinkProgram`
- 缓冲区：`BindBuffer`, `BufferData`, `BufferSubData`
- 绘制：`DrawArrays`, `DrawElements`, `Viewport`
- 帧缓冲区：`BindFramebuffer`, `CheckFramebufferStatus`

### WebGL 2.0 特性

基于版本条件加载：
```cpp
if (glVer >= GR_GL_VER(2,0)) {
    GET_PROC(GetStringi);
    GET_PROC(BindVertexArray);
    GET_PROC(DrawArraysInstanced);
    GET_PROC(DrawBuffers);
    GET_PROC(TexStorage2D);
    // ... 更多 WebGL 2.0 函数
}
```

### WebGL 1.0 扩展回退

当 WebGL 版本 < 2.0 时，尝试加载扩展：

**VAO 支持**：
```cpp
if (glVer >= GR_GL_VER(2,0)) {
    GET_PROC(BindVertexArray);
} else if (extensions.has("GL_OES_vertex_array_object") ||
           extensions.has("OES_vertex_array_object")) {
    GET_PROC_SUFFIX(BindVertexArray, OES);
}
```

### WebGL 特定扩展

#### 实例化基础顶点扩展

```cpp
if (extensions.has("GL_WEBGL_draw_instanced_base_vertex_base_instance")) {
    GET_PROC_SUFFIX(DrawArraysInstancedBaseInstance, WEBGL);
    GET_PROC_SUFFIX(DrawElementsInstancedBaseVertexBaseInstance, WEBGL);
}
```

#### 多重绘制扩展

```cpp
if (extensions.has("GL_WEBGL_multi_draw_instanced_base_vertex_base_instance")) {
    GET_PROC_SUFFIX(MultiDrawArraysInstancedBaseInstance, WEBGL);
    GET_PROC_SUFFIX(MultiDrawElementsInstancedBaseVertexBaseInstance, WEBGL);
}
```

### 计时器查询扩展

WebGL 1.0 和 2.0 使用不同的扩展：

**WebGL 2.0**：
```cpp
if (extensions.has("EXT_disjoint_timer_query_webgl2") ||
    extensions.has("GL_EXT_disjoint_timer_query_webgl2")) {
    GET_PROC_SUFFIX(QueryCounter, EXT);
    GET_PROC_SUFFIX(GetQueryObjecti64v, EXT);
    GET_PROC_SUFFIX(GetQueryObjectui64v, EXT);
}
```

**WebGL 1.0**：
```cpp
if (extensions.has("EXT_disjoint_timer_query") ||
    extensions.has("GL_EXT_disjoint_timer_query")) {
    GET_PROC_SUFFIX(BeginQuery, EXT);
    GET_PROC_SUFFIX(EndQuery, EXT);
    // ...
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | 接口类定义 |
| `GrGLExtensions` | 扩展查询和管理 |
| `GrGLUtil` | 版本解析工具 |
| `Emscripten WebGL` | 底层 WebGL 绑定 |
| `GrGLAssembleHelpers` | 辅助函数（较少使用） |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrGLGpu` | 使用返回的接口进行 WebGL 调用 |
| `GrDirectContext` | 通过 `MakeGL` 创建 WebGL 上下文时调用 |

## 设计模式与设计决策

### 静态绑定 vs 动态加载

**WebGL 特点**：
- 使用 Emscripten 的静态绑定（`emscripten_gl*` 函数）
- 不需要 `dlsym` 或 `eglGetProcAddress`
- 编译时确定所有函数地址

**优势**：
- 更快的函数调用（无间接跳转）
- 减小代码体积（未使用的函数可被链接器移除）
- 避免运行时查找失败

### 扩展名格式兼容

同时支持带 `GL_` 前缀和不带前缀的扩展名：
```cpp
extensions.has("GL_OES_vertex_array_object") ||
extensions.has("OES_vertex_array_object")
```

这是因为 WebGL 规范中扩展名可能出现两种格式。

### WebGL 限制处理

#### 不支持的功能

WebGL 明确不支持某些桌面 GL 功能：
- 没有 `DrawBuffer` 和 `PolygonMode`
- 没有客户端侧数组（VAO 必须使用）
- 没有 `glMapBuffer`（内存映射）

#### 特殊的查询支持

必须支持着色器精度查询：
```cpp
GET_PROC(GetShaderPrecisionFormat);  // WebGL 1.0 必需
```

### 编译时优化

通过 `#if` 指令完全移除非 WebGL 平台代码：
```cpp
#if SK_DISABLE_WEBGL_INTERFACE || !defined(__EMSCRIPTEN__)
    return nullptr;  // 零开销
#endif
```

## 性能考量

### 静态绑定性能

- **函数调用开销**：与本地 C 函数相同（无虚函数表）
- **代码体积**：未使用的函数会被链接器优化掉
- **初始化开销**：极低，只是赋值指针

### 扩展检查优化

只在初始化时检查一次扩展，运行时直接使用函数指针。

### WebAssembly 优化

- Emscripten 会将 `emscripten_gl*` 函数内联到 WASM
- 通过 JS 绑定调用浏览器 WebGL API
- 支持 SIMD 和其他 WASM 优化

## WebGL 版本差异

| 功能 | WebGL 1.0 | WebGL 2.0 | 扩展 |
|------|-----------|-----------|------|
| VAO | 需要扩展 | 核心 | `OES_vertex_array_object` |
| 实例化绘制 | 无 | 核心 | - |
| 多重绘制 | 无 | 扩展 | `WEBGL_multi_draw_*` |
| 纹理存储 | 无 | 核心 | - |
| 整数支持 | 无 | 核心 | - |
| 采样器对象 | 无 | 核心 | - |
| 查询对象 | 扩展 | 核心 | `EXT_disjoint_timer_query` |
| 帧缓冲区 Blit | 无 | 核心 | - |

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrGLInterface.h` | 定义 | 接口类定义 |
| `GrGLAssembleInterface.h` | 声明 | 函数声明头文件 |
| `GrGLAssembleGLInterfaceAutogen.cpp` | 兄弟文件 | 桌面 OpenGL 实现 |
| `GrGLAssembleGLESInterfaceAutogen.cpp` | 兄弟文件 | OpenGL ES 实现 |
| `GrGLUtil.h/cpp` | 工具 | 版本解析和工具函数 |
| `GrGLExtensions.h/cpp` | 扩展管理 | 扩展查询和存储 |
| `tools/ganesh/gl/interface/templates.go` | 生成工具 | 代码生成器 |
| `webgl/webgl1.h` | 依赖 | Emscripten WebGL 1.0 绑定 |
| `webgl/webgl2.h` | 依赖 | Emscripten WebGL 2.0 绑定 |
