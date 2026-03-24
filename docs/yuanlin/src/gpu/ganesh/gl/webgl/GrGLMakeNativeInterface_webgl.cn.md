# GrGLMakeNativeInterface (WebGL)

> 源文件
> - src/gpu/ganesh/gl/webgl/GrGLMakeNativeInterface_webgl.cpp

## 概述

WebGL 平台的 OpenGL 接口创建实现。WebGL 是浏览器中的 OpenGL ES API，通过 Emscripten 编译为 WebAssembly。该实现使用静态函数映射而非动态加载，优化了代码体积。函数指针由 Emscripten 的头文件直接提供，无需运行时查找。

## 公共 API 函数

### GrGLInterfaces::MakeWebGL

```cpp
namespace GrGLInterfaces {
sk_sp<const GrGLInterface> MakeWebGL();
}
```

**功能**：创建 WebGL 接口对象。

**返回值**：组装好的 WebGL 接口。

### GrGLMakeNativeInterface

```cpp
sk_sp<const GrGLInterface> GrGLMakeNativeInterface();
```

**功能**：Legacy 接口，转发到 `GrGLInterfaces::MakeWebGL()`。

## 内部实现细节

### 函数查找机制

```cpp
static GrGLFuncPtr webgl_get_gl_proc(void* ctx, const char name[]) {
    #define M(X) if (0 == strcmp(#X, name)) { return (GrGLFuncPtr) X; }
    M(glGetString)
    #undef M

    SkASSERTF(false, "Can't lookup fn %s\n", name);
    return nullptr;
}
```

**工作原理**：
1. 使用宏 `M(X)` 将函数名与函数指针映射
2. 通过字符串比较查找匹配的函数
3. 找不到函数时触发断言（开发模式）

**当前映射**：
- `glGetString`：示例映射，实际使用中会有更多函数

### 代码体积优化

注释中说明了设计决策：
```cpp
// 我们明确不使用 GetProcAddress 或类似机制，因为其代码体积相当大。
// 我们不需要 GetProcAddress，因为 emscripten 通过包含的头文件
// 为我们提供了所有有效的 WebGL 函数指针。
```

**优化理由**：
- WebGL 环境中，所有函数在编译时已知
- `GetProcAddress` 风格的动态查找会增加数十 KB 代码
- 静态映射方案代码体积小，性能更好

### Emscripten 集成

Emscripten 头文件提供：
- 所有 WebGL 函数的声明和定义
- 函数指针在编译时可用
- 参考链接：`emscripten/html5_webgl.h`

### 接口组装

```cpp
return GrGLMakeAssembledWebGLInterface(nullptr, webgl_get_gl_proc);
```

调用通用的接口组装函数：
- 第一个参数：上下文指针（WebGL 不需要，传 `nullptr`）
- 第二个参数：函数查找回调

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLAssembleInterface` | 接口组装工具 |
| `GrGLInterface` | GL 函数指针表 |
| `GrGLMakeWebGLInterface` | WebGL 特定声明 |
| `<GLES3/gl32.h>` | OpenGL ES 3.2 函数声明 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| WebAssembly 应用 | 初始化 Skia WebGL 支持 |
| `GrDirectContext` | 创建 WebGL 上下文 |

## 设计模式与设计决策

### 静态函数表

使用编译时静态表而非运行时动态查找：
- 减少代码体积
- 消除查找开销
- 类型安全（编译时检查）

### 断言驱动开发

```cpp
SkASSERTF(false, "Can't lookup fn %s\n", name);
```

未映射的函数在开发时立即发现，避免运行时错误。

### 命名空间封装

```cpp
namespace GrGLInterfaces {
    sk_sp<const GrGLInterface> MakeWebGL();
}
```

将平台特定实现组织在命名空间中，避免全局命名冲突。

## 性能考量

### 编译时解析

所有函数地址在编译时确定：
- 零运行时查找开销
- 可内联优化
- 无动态库加载延迟

### 代码体积

静态映射方案：
- 每个函数约 20 字节代码
- 50 个函数约 1KB
- `GetProcAddress` 方案可能需要 10-50KB

### 字符串比较优化

虽然使用 `strcmp`，但：
- 只在接口初始化时调用一次
- 之后使用缓存的函数指针
- 对运行时性能无影响

## WebGL 特定考虑

### OpenGL ES 版本

```cpp
#include <GLES3/gl32.h>
```

使用 OpenGL ES 3.2 API，支持现代 WebGL 2.0 功能。

### 浏览器兼容性

该实现依赖 Emscripten 的 WebGL 绑定，兼容：
- Chrome/Edge（Blink 引擎）
- Firefox（Gecko 引擎）
- Safari（WebKit 引擎）

### 无上下文参数

WebGL 函数不需要显式上下文参数：
- 浏览器管理 WebGL 上下文
- Emscripten 自动处理上下文切换

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `include/gpu/ganesh/gl/GrGLAssembleInterface.h` | 接口组装函数 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| `include/gpu/ganesh/gl/GrGLMakeWebGLInterface.h` | WebGL 特定声明 |
| `emscripten/html5_webgl.h` | Emscripten WebGL 绑定 |
