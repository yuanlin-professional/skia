# GrGLAssembleGLESInterfaceAutogen

> 源文件
> - src/gpu/ganesh/gl/GrGLAssembleGLESInterfaceAutogen.cpp

## 概述

`GrGLAssembleGLESInterfaceAutogen.cpp` 是一个自动生成的源文件，负责为 OpenGL ES（Embedded Systems）动态加载和组装 OpenGL ES 函数指针。该文件通过 `GrGLMakeAssembledGLESInterface` 函数创建一个完整的 `GrGLInterface` 对象，包含所有 Skia 在 OpenGL ES 环境下需要的函数指针。代码根据 OpenGL ES 版本和可用扩展动态决定加载哪些函数。

**重要提示**：此文件由 `tools/ganesh/gl/interface/templates.go` 自动生成，不应手动编辑。

## 架构位置

该文件位于 Ganesh OpenGL 后端的接口层：

```
src/gpu/ganesh/gl/
├── GrGLInterface (接口类)
├── GrGLAssembleInterface.h (组装接口声明)
├── GrGLAssembleGLInterfaceAutogen.cpp (桌面 GL)
├── GrGLAssembleGLESInterfaceAutogen.cpp (OpenGL ES - 本文件)
└── GrGLAssembleWebGLInterfaceAutogen.cpp (WebGL)
```

该文件是三个平台特定实现之一，专门处理 OpenGL ES（主要用于移动设备）。

## 主要类与结构体

### GrGLInterface

该文件创建并填充 `GrGLInterface` 对象：

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFunctions` | `GrGLInterface::Functions` | 包含所有 OpenGL ES 函数指针的结构体 |
| `fStandard` | `GrGLStandard` | 标识为 `kGLES_GrGLStandard` |
| `fExtensions` | `GrGLExtensions` | 支持的扩展列表 |

## 公共 API 函数

### GrGLMakeAssembledGLESInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeAssembledGLESInterface(void* ctx, GrGLGetProc get)
```

**参数：**
- `ctx`：平台特定的上下文指针（传递给 `get` 函数）
- `get`：函数指针获取回调，签名为 `void* (*)(void* ctx, const char* name)`

**返回值：**
- 成功：包含完整函数指针的 `GrGLInterface` 智能指针
- 失败：`nullptr`（如果 OpenGL ES 版本不足）

**功能：**
1. 检查 OpenGL ES 版本（最低要求 2.0）
2. 初始化扩展列表（包括 EGL 扩展）
3. 加载核心函数
4. 根据版本和扩展加载可选函数
5. 返回完整的接口对象

## 内部实现细节

### 版本检查

```cpp
const char* verStr = reinterpret_cast<const char*>(GetString(GR_GL_VERSION));
GrGLVersion glVer = GrGLGetVersionFromString(verStr);

if (glVer < GR_GL_VER(2,0)) {
    return nullptr;  // OpenGL ES 2.0 是最低要求
}
```

### EGL 扩展集成

OpenGL ES 通常与 EGL 一起使用，因此支持 EGL 扩展查询：
```cpp
GrEGLQueryStringFn* queryString;
GrEGLDisplay display;
GrGetEGLQueryAndDisplay(&queryString, &display, ctx, get);
GrGLExtensions extensions;
if (!extensions.init(kGLES_GrGLStandard, GetString, GetStringi, GetIntegerv,
                     queryString, display)) {
    return nullptr;
}
```

### 函数加载宏

| 宏 | 用途 | 示例 |
|-----|------|------|
| `GET_PROC(F)` | 加载标准函数 | `GET_PROC(ActiveTexture)` → `glActiveTexture` |
| `GET_PROC_SUFFIX(F, S)` | 加载扩展函数 | `GET_PROC_SUFFIX(BindVertexArray, OES)` → `glBindVertexArrayOES` |
| `GET_PROC_LOCAL(F)` | 加载局部函数（用于早期检查） | `GET_PROC_LOCAL(GetString)` |

### 核心函数加载

所有 OpenGL ES 2.0 核心函数都会被加载（40个），包括：
- 纹理操作：`ActiveTexture`, `BindTexture`, `TexImage2D`
- 着色器编译：`CreateShader`, `CompileShader`, `AttachShader`
- 缓冲区管理：`BindBuffer`, `BufferData`, `BufferSubData`
- 绘制指令：`DrawArrays`, `DrawElements`, `Viewport`
- 帧缓冲区：`BindFramebuffer`, `CheckFramebufferStatus`

## OpenGL ES 特定特性

### VAO 支持

OpenGL ES 3.0 核心功能，ES 2.0 需扩展：
```cpp
if (glVer >= GR_GL_VER(3,0)) {
    GET_PROC(BindVertexArray);
    GET_PROC(DeleteVertexArrays);
    GET_PROC(GenVertexArrays);
} else if (extensions.has("GL_OES_vertex_array_object")) {
    GET_PROC_SUFFIX(BindVertexArray, OES);
    GET_PROC_SUFFIX(DeleteVertexArrays, OES);
    GET_PROC_SUFFIX(GenVertexArrays, OES);
}
```

### 实例化绘制

ES 3.0 核心，ES 2.0 通过多个扩展支持：
```cpp
if (glVer >= GR_GL_VER(3,0)) {
    GET_PROC(DrawArraysInstanced);
    GET_PROC(DrawElementsInstanced);
} else if (extensions.has("GL_EXT_draw_instanced")) {
    GET_PROC_SUFFIX(DrawArraysInstanced, EXT);
    GET_PROC_SUFFIX(DrawElementsInstanced, EXT);
} else if (extensions.has("GL_ANGLE_instanced_arrays")) {
    GET_PROC_SUFFIX(DrawArraysInstanced, ANGLE);
    GET_PROC_SUFFIX(DrawElementsInstanced, ANGLE);
}
```

### 多重采样渲染

支持多种 MSAA 扩展实现：
```cpp
if (glVer >= GR_GL_VER(3,0)) {
    GET_PROC(RenderbufferStorageMultisample);
} else if (extensions.has("GL_CHROMIUM_framebuffer_multisample")) {
    GET_PROC_SUFFIX(RenderbufferStorageMultisample, CHROMIUM);
} else if (extensions.has("GL_ANGLE_framebuffer_multisample")) {
    GET_PROC_SUFFIX(RenderbufferStorageMultisample, ANGLE);
}
```

### 多重采样渲染到纹理

特殊的 MSAA 扩展（IMG/EXT）：
```cpp
if (extensions.has("GL_EXT_multisampled_render_to_texture")) {
    GET_PROC_SUFFIX(FramebufferTexture2DMultisample, EXT);
    functions->fRenderbufferStorageMultisampleES2EXT =
        (GrGLRenderbufferStorageMultisampleFn*)get(ctx, "glRenderbufferStorageMultisampleEXT");
}

if (extensions.has("GL_IMG_multisampled_render_to_texture")) {
    GET_PROC_SUFFIX(FramebufferTexture2DMultisample, IMG);
    functions->fRenderbufferStorageMultisampleES2EXT =
        (GrGLRenderbufferStorageMultisampleFn*)get(ctx, "glRenderbufferStorageMultisampleIMG");
}
```

### Apple MSAA 扩展

```cpp
if (extensions.has("GL_APPLE_framebuffer_multisample")) {
    GET_PROC_SUFFIX(ResolveMultisampleFramebuffer, APPLE);
    functions->fRenderbufferStorageMultisampleES2APPLE =
        (GrGLRenderbufferStorageMultisampleFn*)get(ctx, "glRenderbufferStorageMultisampleAPPLE");
}
```

### 内存映射支持

OpenGL ES 2.0 原生不支持，需扩展：
```cpp
if (extensions.has("GL_OES_mapbuffer")) {
    GET_PROC_SUFFIX(MapBuffer, OES);
}

if (glVer >= GR_GL_VER(3,0)) {
    GET_PROC(UnmapBuffer);
} else if (extensions.has("GL_OES_mapbuffer")) {
    GET_PROC_SUFFIX(UnmapBuffer, OES);
}

if (glVer >= GR_GL_VER(3,0) || extensions.has("GL_EXT_map_buffer_range")) {
    GET_PROC_SUFFIX(FlushMappedBufferRange, EXT);
    GET_PROC_SUFFIX(MapBufferRange, EXT);
}
```

### Chromium 特定扩展

针对 Chrome OS 和 Android 上的 Chrome 浏览器：
```cpp
if (extensions.has("GL_CHROMIUM_map_sub")) {
    GET_PROC_SUFFIX(MapBufferSubData, CHROMIUM);
    GET_PROC_SUFFIX(MapTexSubImage2D, CHROMIUM);
    GET_PROC_SUFFIX(UnmapBufferSubData, CHROMIUM);
    GET_PROC_SUFFIX(UnmapTexSubImage2D, CHROMIUM);
}
```

### 平铺渲染支持

QCOM（Qualcomm Adreno）特定扩展：
```cpp
if (extensions.has("GL_QCOM_tiled_rendering")) {
    GET_PROC_SUFFIX(EndTiling, QCOM);
    GET_PROC_SUFFIX(StartTiling, QCOM);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | 接口类定义 |
| `GrGLExtensions` | 扩展查询和管理 |
| `GrGLUtil` | 版本解析工具 |
| `GrGLDefines` | OpenGL ES 常量定义 |
| `GrGLFunctions` | 函数指针类型定义 |
| `GrGLAssembleHelpers` | EGL 查询辅助函数 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrGLGpu` | 使用返回的接口进行 OpenGL ES 调用 |
| `GrDirectContext` | 通过 `MakeGL` 创建 OpenGL ES 上下文时调用 |

## 设计模式与设计决策

### 自动代码生成

**优点：**
- 减少手动维护错误
- 确保三个平台（GL/GLES/WebGL）逻辑一致
- 方便批量更新函数列表

**生成工具**：`tools/ganesh/gl/interface/templates.go`

### 编译时禁用

通过 `SK_DISABLE_GL_ES_INTERFACE` 宏可以完全禁用：
```cpp
#if SK_DISABLE_GL_ES_INTERFACE
sk_sp<const GrGLInterface> GrGLMakeAssembledGLESInterface(void *ctx, GrGLGetProc get) {
    return nullptr;
}
#endif
```

### 扩展回退机制

OpenGL ES 的扩展更加碎片化，支持多级回退：
1. **ES 3.0 Core** → 2. **EXT Extension** → 3. **Vendor Extension** (OES/ANGLE/CHROMIUM)

示例：缓冲区映射
```cpp
if (glVer >= GR_GL_VER(3,0)) {
    GET_PROC(MapBufferRange);
} else if (extensions.has("GL_EXT_map_buffer_range")) {
    GET_PROC_SUFFIX(MapBufferRange, EXT);
}
```

### 特殊的 MSAA 函数处理

某些扩展使用不同的函数名但签名相同：
```cpp
// EXT 和 IMG 扩展共享同一函数指针
functions->fRenderbufferStorageMultisampleES2EXT = ...
```

### KHR_debug 扩展特殊处理

针对某些设备的 bug 处理：
```cpp
if (extensions.has("GL_KHR_debug")) {
    // ... 加载函数
}

// 验证函数指针
if (!interface->fFunctions.fDebugMessageControl) {
    extensions.remove("GL_KHR_debug");  // 移除无效扩展
}
```

**场景**：某些设备声称支持 `GL_KHR_debug` 但未提供函数实现（如使用 APITRACE 时）

## 性能考量

### 函数指针缓存

所有函数指针在初始化时一次性加载，避免运行时查找开销。

### 扩展检查优化

`GrGLExtensions` 使用哈希表存储扩展名，查询复杂度为 O(1)。

### 条件编译

未使用的函数不会被加载，减少接口对象大小。

### EGL 集成开销

相比桌面 GL，需要额外的 EGL 扩展查询，但这是一次性开销。

## OpenGL ES 版本差异

| 功能 | ES 2.0 | ES 3.0 | 扩展 |
|------|--------|--------|------|
| VAO | 需要扩展 | 核心 | `OES_vertex_array_object` |
| 实例化绘制 | 需要扩展 | 核心 | `EXT_draw_instanced`, `ANGLE_instanced_arrays` |
| 整数纹理 | 不支持 | 核心 | - |
| 多重渲染目标 | 需要扩展 | 核心 | `EXT_draw_buffers` |
| 采样器对象 | 不支持 | 核心 | - |
| 纹理存储 | 需要扩展 | 核心 | `EXT_texture_storage` |
| 查询对象 | 需要扩展 | 核心 | `EXT_disjoint_timer_query` |
| 变换反馈 | 不支持 | 核心 | - |
| 统一缓冲区对象 | 不支持 | 核心 | - |

## 移动平台优化

### ARM Mali GPU

- 支持平铺渲染（`GL_EXT_discard_framebuffer`）
- 优化平铺延迟架构性能

### Qualcomm Adreno

- 支持 `GL_QCOM_tiled_rendering` 扩展
- 针对平铺渲染架构优化

### PowerVR SGX/Rogue

- 支持 `GL_IMG_multisampled_render_to_texture`
- 无需 MSAA renderbuffer 的 MSAA 实现

### Apple A 系列

- 支持 `GL_APPLE_framebuffer_multisample`
- 专有的 MSAA 实现

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrGLInterface.h` | 定义 | 接口类定义 |
| `GrGLAssembleInterface.h` | 声明 | 函数声明头文件 |
| `GrGLAssembleGLInterfaceAutogen.cpp` | 兄弟文件 | 桌面 OpenGL 实现 |
| `GrGLAssembleWebGLInterfaceAutogen.cpp` | 兄弟文件 | WebGL 实现 |
| `GrGLUtil.h/cpp` | 工具 | 版本解析和工具函数 |
| `GrGLExtensions.h/cpp` | 扩展管理 | 扩展查询和存储 |
| `GrGLAssembleHelpers.h` | 辅助 | EGL 查询辅助函数 |
| `tools/ganesh/gl/interface/templates.go` | 生成工具 | 代码生成器 |
