# GrGLAssembleGLInterfaceAutogen

> 源文件
> - src/gpu/ganesh/gl/GrGLAssembleGLInterfaceAutogen.cpp

## 概述

`GrGLAssembleGLInterfaceAutogen.cpp` 是一个自动生成的源文件，负责为桌面 OpenGL（非 ES）动态加载和组装 OpenGL 函数指针。该文件通过 `GrGLMakeAssembledGLInterface` 函数创建一个完整的 `GrGLInterface` 对象，包含所有 Skia 需要的 OpenGL 函数指针。代码根据 OpenGL 版本和可用扩展动态决定加载哪些函数。

**重要提示**：此文件由 `tools/ganesh/gl/interface/templates.go` 自动生成，不应手动编辑。

## 架构位置

该文件位于 Ganesh OpenGL 后端的接口层：

```
src/gpu/ganesh/gl/
├── GrGLInterface (接口类)
├── GrGLAssembleInterface.h (组装接口声明)
├── GrGLAssembleGLInterfaceAutogen.cpp (桌面 GL 实现)
├── GrGLAssembleGLESInterfaceAutogen.cpp (ES 实现)
└── GrGLAssembleWebGLInterfaceAutogen.cpp (WebGL 实现)
```

该文件是三个平台特定实现之一，专门处理桌面 OpenGL。

## 主要类与结构体

### GrGLInterface

该文件创建并填充 `GrGLInterface` 对象：

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFunctions` | `GrGLInterface::Functions` | 包含所有 OpenGL 函数指针的结构体 |
| `fStandard` | `GrGLStandard` | 标识为 `kGL_GrGLStandard`（桌面 GL） |
| `fExtensions` | `GrGLExtensions` | 支持的扩展列表 |

## 公共 API 函数

### GrGLMakeAssembledGLInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeAssembledGLInterface(void* ctx, GrGLGetProc get)
```

**参数：**
- `ctx`：平台特定的上下文指针（传递给 `get` 函数）
- `get`：函数指针获取回调，签名为 `void* (*)(void* ctx, const char* name)`

**返回值：**
- 成功：包含完整函数指针的 `GrGLInterface` 智能指针
- 失败：`nullptr`（如果 OpenGL 版本不足或扩展不支持）

**功能：**
1. 检查 OpenGL 版本（最低要求 2.0）
2. 初始化扩展列表
3. 加载核心函数
4. 根据版本和扩展加载可选函数
5. 返回完整的接口对象

## 内部实现细节

### 版本检查

```cpp
const char* versionString = (const char*) GetString(GR_GL_VERSION);
GrGLVersion glVer = GrGLGetVersionFromString(versionString);

if (glVer < GR_GL_VER(2,0) || GR_GL_INVALID_VER == glVer) {
    return nullptr;  // OpenGL 2.0 是最低要求
}
```

### 扩展初始化

使用 `GrGLExtensions::init` 加载扩展：
- 使用 `GetString(GL_EXTENSIONS)` （OpenGL < 3.0）
- 使用 `GetStringi` + `GetIntegerv(GL_NUM_EXTENSIONS)` （OpenGL >= 3.0）
- 支持 EGL 扩展查询（通过 `GrGetEGLQueryAndDisplay`）

### 函数加载宏

| 宏 | 用途 | 示例 |
|-----|------|------|
| `GET_PROC(F)` | 加载标准函数 | `GET_PROC(ActiveTexture)` → `glActiveTexture` |
| `GET_PROC_SUFFIX(F, S)` | 加载扩展函数 | `GET_PROC_SUFFIX(BindVertexArray, APPLE)` → `glBindVertexArrayAPPLE` |
| `GET_PROC_LOCAL(F)` | 加载局部函数（用于早期检查） | `GET_PROC_LOCAL(GetString)` |

### 核心函数加载

所有 OpenGL 2.0 核心函数都会被加载（62个），包括：
- 纹理操作：`ActiveTexture`, `BindTexture`, `TexImage2D`
- 着色器编译：`CreateShader`, `CompileShader`, `AttachShader`
- 缓冲区管理：`BindBuffer`, `BufferData`, `BufferSubData`
- 绘制指令：`DrawArrays`, `DrawElements`, `Viewport`
- 状态管理：`Enable`, `Disable`, `BlendFunc`

### 桌面特定函数

仅在桌面 OpenGL 中加载：
- `DrawBuffer`：设置绘制目标缓冲区
- `PolygonMode`：线框模式支持

### 条件加载逻辑

函数加载基于版本和扩展的组合：

**示例 1：VAO 支持**
```cpp
if (glVer >= GR_GL_VER(3,0)) {
    GET_PROC(BindVertexArray);
} else if (extensions.has("GL_ARB_vertex_array_object")) {
    GET_PROC(BindVertexArray);
} else if (extensions.has("GL_APPLE_vertex_array_object")) {
    GET_PROC_SUFFIX(BindVertexArray, APPLE);
}
```

**示例 2：实例化绘制**
```cpp
if (glVer >= GR_GL_VER(3,1)) {
    GET_PROC(DrawArraysInstanced);
} else if (extensions.has("GL_ARB_draw_instanced")) {
    GET_PROC(DrawArraysInstanced);
} else if (extensions.has("GL_EXT_draw_instanced")) {
    GET_PROC_SUFFIX(DrawArraysInstanced, EXT);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLInterface` | 接口类定义 |
| `GrGLExtensions` | 扩展查询和管理 |
| `GrGLUtil` | 版本解析（`GrGLGetVersionFromString`） |
| `GrGLDefines` | OpenGL 常量定义 |
| `GrGLFunctions` | 函数指针类型定义 |
| `GrGLAssembleHelpers` | EGL 查询辅助函数 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|---------|
| `GrGLGpu` | 使用返回的接口进行 OpenGL 调用 |
| `GrDirectContext` | 通过 `MakeGL` 创建 OpenGL 上下文时调用 |

## 设计模式与设计决策

### 自动代码生成

**优点：**
- 减少手动维护错误
- 确保三个平台（GL/GLES/WebGL）逻辑一致
- 方便批量更新函数列表

**生成工具**：`tools/ganesh/gl/interface/templates.go`

### 编译时禁用

通过 `SK_DISABLE_GL_INTERFACE` 宏可以完全禁用：
```cpp
#if SK_DISABLE_GL_INTERFACE
sk_sp<const GrGLInterface> GrGLMakeAssembledGLInterface(void *ctx, GrGLGetProc get) {
    return nullptr;
}
#endif
```

### 扩展回退机制

优先使用核心功能，然后尝试 ARB 扩展，最后尝试厂商扩展：
1. **Core** → 2. **ARB** → 3. **EXT/APPLE/NV**

示例：纹理屏障支持
```cpp
if (glVer >= GR_GL_VER(4,5)) {
    GET_PROC(TextureBarrier);
} else if (extensions.has("GL_ARB_texture_barrier")) {
    GET_PROC(TextureBarrier);
} else if (extensions.has("GL_NV_texture_barrier")) {
    GET_PROC_SUFFIX(TextureBarrier, NV);
}
```

### 空指针检查

关键函数缺失直接返回 `nullptr`：
```cpp
if (nullptr == GetString || nullptr == GetIntegerv) {
    return nullptr;
}
```

### EGL 集成

支持通过 EGL 查询额外扩展：
```cpp
GrEGLQueryStringFn* queryString;
GrEGLDisplay display;
GrGetEGLQueryAndDisplay(&queryString, &display, ctx, get);
```

## 性能考量

### 函数指针缓存

所有函数指针在初始化时一次性加载，避免运行时查找开销。

### 扩展检查优化

`GrGLExtensions` 使用哈希表存储扩展名，查询复杂度为 O(1)。

### 条件编译

未使用的函数不会被加载，减少接口对象大小。

## 加载的函数类别

| 类别 | 函数数量（约） | 示例函数 |
|------|-------------|---------|
| 核心 2.0 函数 | 62 | `DrawElements`, `UseProgram` |
| 纹理操作 | 8 | `TexStorage2D`, `ClearTexImage` |
| 缓冲区操作 | 12 | `MapBufferRange`, `CopyBufferSubData` |
| 帧缓冲区 | 15 | `BindFramebuffer`, `BlitFramebuffer` |
| 查询对象 | 8 | `BeginQuery`, `GetQueryObjectui64v` |
| 同步对象 | 5 | `FenceSync`, `ClientWaitSync` |
| 调试支持 | 7 | `DebugMessageCallback`, `ObjectLabel` |
| 多重绘制 | 4 | `MultiDrawArraysIndirect` |
| 采样器对象 | 6 | `BindSampler`, `SamplerParameteri` |
| 实例化绘制 | 4 | `DrawArraysInstanced`, `VertexAttribDivisor` |
| 高级特性 | 10+ | `PatchParameteri`, `MemoryBarrier` |

## 相关文件

| 文件 | 关系 | 说明 |
|------|------|------|
| `GrGLInterface.h` | 定义 | 接口类定义 |
| `GrGLAssembleInterface.h` | 声明 | 函数声明头文件 |
| `GrGLAssembleGLESInterfaceAutogen.cpp` | 兄弟文件 | OpenGL ES 实现 |
| `GrGLAssembleWebGLInterfaceAutogen.cpp` | 兄弟文件 | WebGL 实现 |
| `GrGLUtil.h/cpp` | 工具 | 版本解析和工具函数 |
| `GrGLExtensions.h/cpp` | 扩展管理 | 扩展查询和存储 |
| `tools/ganesh/gl/interface/templates.go` | 生成工具 | 代码生成器 |
