# webgl/ - WebGL 平台接口 (Emscripten/WASM)

## 概述

`webgl/` 目录提供 WebGL 平台的 OpenGL ES 接口加载实现，专为通过 Emscripten 编译到 WebAssembly 的场景设计。WebGL 是 OpenGL ES 在 Web 浏览器中的实现标准，Skia 通过此接口可以在浏览器中运行 GPU 加速绘制。

与其他平台不同，WebGL 版本**不使用** `GetProcAddress` 类机制获取函数指针。相反，它直接使用 Emscripten SDK 提供的头文件中声明的函数符号。这是因为在 WebAssembly 环境中，动态函数加载的代码体积较大，且 Emscripten 已经提供了所有有效的 WebGL 函数指针。

## 文件分类索引

### 1. WebGL 接口 — WebGL/Emscripten Platform Interface

| 文件 | 说明 |
|------|------|
| GrGLMakeNativeInterface_webgl.cpp | WebGL 接口创建实现（Emscripten 编译时链接） |

## 关键实现

### GrGLInterfaces::MakeWebGL()

```cpp
static GrGLFuncPtr webgl_get_gl_proc(void* ctx, const char name[]) {
    #define M(X) if (0 == strcmp(#X, name)) { return (GrGLFuncPtr) X; }
    M(glGetString)
    #undef M
    // 不使用GetProcAddress以减少代码体积
    SkASSERTF(false, "Can't lookup fn %s\n", name);
    return nullptr;
}

namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeWebGL() {
    return GrGLMakeAssembledWebGLInterface(nullptr, webgl_get_gl_proc);
}
}
```

**设计决策：**
1. 仅显式处理 `glGetString`（初始化阶段需要），其余函数由 `GrGLMakeAssembledWebGLInterface()` 内部的自动生成代码处理
2. 回退路径使用 `SkASSERTF(false, ...)` 标记不应到达的代码路径
3. 使用专用的 `GrGLMakeAssembledWebGLInterface()` 而非通用的 GL/GLES 版本

**为什么不使用 GetProcAddress：**
引用代码注释："We explicitly do not use GetProcAddress or something similar because its code size is quite large." Emscripten 通过头文件（`<GLES3/gl32.h>`）直接提供所有有效的函数指针，不需要运行时查找。

## WebGL 特殊性

- WebGL 是 OpenGL ES 的子集，有额外的安全限制
- WebGL 1.0 大致对应 OpenGL ES 2.0
- WebGL 2.0 大致对应 OpenGL ES 3.0
- 某些 ES 功能在 WebGL 中不可用（如多采样纹理的某些用法）
- 自动生成的 `GrGLAssembleWebGLInterfaceAutogen.cpp` 处理 WebGL 特有的函数集

## 编译条件

- 需要 Emscripten SDK
- 包含 `<GLES3/gl32.h>` 头文件
- 通常与 Skia 的 `wasm` 构建目标一起使用（CanvasKit）

## 依赖关系

- **上游：** 由 CanvasKit (Skia 的 WASM 构建) 初始化代码调用
- **下游：** 依赖 `GrGLMakeAssembledWebGLInterface()`（在 `GrGLAssembleWebGLInterfaceAutogen.cpp` 中）
- **系统依赖：** Emscripten WebGL 绑定

## 适用场景

- CanvasKit -- Skia 的 WebAssembly 发行版
- 基于浏览器的图形应用
- Progressive Web Apps (PWA) 中的 GPU 加速绘制
