# GrGLFunctions

> 源文件: `include/gpu/ganesh/gl/GrGLFunctions.h`

## 概述
GrGLFunctions 定义了 Ganesh OpenGL 后端使用的所有 OpenGL 函数指针类型。该文件通过 typedef 声明了数百个 GL 函数签名,并提供了轻量级的函数对象封装器 GrGLFunction,用于存储和调用 OpenGL 函数指针。这是 Ganesh OpenGL 后端实现平台无关性的核心基础设施。

## 架构位置
该文件位于 `include/gpu/ganesh/gl` OpenGL 后端的核心层,是 GrGLInterface 的基础。所有 OpenGL 函数调用都通过这里定义的函数指针类型进行,实现了运行时加载 OpenGL 函数的能力,支持跨平台、跨版本的 OpenGL API 兼容。

## 核心类型定义

### OpenGL 函数指针 Typedef

文件定义了超过 200 个 OpenGL 函数指针类型,涵盖:
- **核心 GL 功能**: 纹理、缓冲区、着色器、渲染
- **扩展功能**: 同步对象、调试、实例化绘制
- **EGL 集成**: 图像创建、显示查询

#### 典型函数指针定义

**纹理操作**:
```cpp
using GrGLActiveTextureFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLenum texture);
using GrGLBindTextureFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLenum target, GrGLuint texture);
using GrGLTexImage2DFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum target, GrGLint level, GrGLint internalformat,
    GrGLsizei width, GrGLsizei height, GrGLint border,
    GrGLenum format, GrGLenum type, const GrGLvoid* pixels);
```

**缓冲区操作**:
```cpp
using GrGLBindBufferFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLenum target, GrGLuint buffer);
using GrGLBufferDataFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum target, GrGLsizeiptr size, const GrGLvoid* data, GrGLenum usage);
using GrGLBufferSubDataFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum target, GrGLintptr offset, GrGLsizeiptr size, const GrGLvoid* data);
```

**着色器与程序**:
```cpp
using GrGLCreateShaderFn = GrGLuint GR_GL_FUNCTION_TYPE(GrGLenum type);
using GrGLCompileShaderFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLuint shader);
using GrGLCreateProgramFn = GrGLuint GR_GL_FUNCTION_TYPE();
using GrGLLinkProgramFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLuint program);
using GrGLUseProgramFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLuint program);
```

**绘制命令**:
```cpp
using GrGLDrawArraysFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLenum mode, GrGLint first, GrGLsizei count);
using GrGLDrawElementsFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum mode, GrGLsizei count, GrGLenum type, const GrGLvoid* indices);
using GrGLDrawArraysInstancedFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum mode, GrGLint first, GrGLsizei count, GrGLsizei primcount);
```

**帧缓冲区**:
```cpp
using GrGLBindFramebufferFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLenum target, GrGLuint framebuffer);
using GrGLFramebufferTexture2DFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum target, GrGLenum attachment, GrGLenum textarget,
    GrGLuint texture, GrGLint level);
using GrGLCheckFramebufferStatusFn = GrGLenum GR_GL_FUNCTION_TYPE(GrGLenum target);
```

**同步对象 (ARB_sync)**:
```cpp
using GrGLFenceSyncFn = GrGLsync GR_GL_FUNCTION_TYPE(GrGLenum condition, GrGLbitfield flags);
using GrGLClientWaitSyncFn = GrGLenum GR_GL_FUNCTION_TYPE(
    GrGLsync sync, GrGLbitfield flags, GrGLuint64 timeout);
using GrGLDeleteSyncFn = GrGLvoid GR_GL_FUNCTION_TYPE(GrGLsync sync);
```

### 扩展功能函数

#### 实例化绘制 (EXT_base_instance)
```cpp
using GrGLDrawArraysInstancedBaseInstanceFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum mode, GrGLint first, GrGLsizei count,
    GrGLsizei instancecount, GrGLuint baseinstance);
using GrGLDrawElementsInstancedBaseVertexBaseInstanceFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum mode, GrGLsizei count, GrGLenum type, const void* indices,
    GrGLsizei instancecount, GrGLint basevertex, GrGLuint baseinstance);
```

#### 多绘制间接 (EXT_multi_draw_indirect)
```cpp
using GrGLMultiDrawArraysIndirectFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum mode, const GrGLvoid* indirect, GrGLsizei drawcount, GrGLsizei stride);
using GrGLMultiDrawElementsIndirectFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum mode, GrGLenum type, const GrGLvoid* indirect,
    GrGLsizei drawcount, GrGLsizei stride);
```

#### 调试扩展 (KHR_debug)
```cpp
using GrGLDebugMessageControlFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum source, GrGLenum type, GrGLenum severity,
    GrGLsizei count, const GrGLuint* ids, GrGLboolean enabled);
using GrGLPushDebugGroupFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLenum source, GrGLuint id, GrGLsizei length, const GrGLchar* message);
using GrGLPopDebugGroupFn = GrGLvoid GR_GL_FUNCTION_TYPE();
```

#### EGL 函数
```cpp
using GrEGLCreateImageFn = GrEGLImage GR_GL_FUNCTION_TYPE(
    GrEGLDisplay dpy, GrEGLContext ctx, GrEGLenum target,
    GrEGLClientBuffer buffer, const GrEGLint* attrib_list);
using GrEGLDestroyImageFn = GrEGLBoolean GR_GL_FUNCTION_TYPE(
    GrEGLDisplay dpy, GrEGLImage image);
```

## GrGLFunction 类模板

### 设计目标
提供比 std::function 更轻量级的函数对象封装,减少代码体积和编译时间,同时仅支持 Ganesh 所需的精确用例。

### 类定义
```cpp
template <typename R, typename... Args>
class GrGLFunction<R GR_GL_FUNCTION_TYPE(Args...)> {
public:
    using Fn = R GR_GL_FUNCTION_TYPE(Args...);

    // 构造函数
    GrGLFunction() = default;
    GrGLFunction(std::nullptr_t) {}
    GrGLFunction(Fn* fn_ptr);
    template <typename Closure>
    GrGLFunction(Closure closure);

    // 调用运算符
    R operator()(Args... args) const;

    // 有效性检查
    explicit operator bool() const;

    // 重置
    void reset();

private:
    using Call = R(const void* buf, Args...);
    Call* fCall = nullptr;
    size_t fBuf[4];  // 32 字节小缓冲区
};
```

### 关键成员

#### 存储机制
- **fBuf**: 4 个 size_t 的小缓冲区(32/64 字节,取决于架构)
- **fCall**: 实际调用逻辑的函数指针

#### 构造函数

**从函数指针构造**:
```cpp
GrGLFunction(Fn* fn_ptr) {
    static_assert(sizeof(fn_ptr) <= sizeof(fBuf), "fBuf is too small");
    if (fn_ptr) {
        memcpy(fBuf, &fn_ptr, sizeof(fn_ptr));
        fCall = [](const void* buf, Args... args) {
            return (*(Fn* const*)buf)(std::forward<Args>(args)...);
        };
    }
}
```
- 将函数指针存储在 fBuf 中
- 创建调用包装器

**从闭包构造**:
```cpp
template <typename Closure>
GrGLFunction(Closure closure) {
    static_assert(sizeof(Closure) <= sizeof(fBuf), "fBuf is too small");
    static_assert(std::is_trivially_copyable<Closure>::value, "");
    static_assert(std::is_trivially_destructible<Closure>::value, "");

    memcpy(fBuf, &closure, sizeof(closure));
    fCall = [](const void* buf, Args... args) {
        auto closure = (const Closure*)buf;
        return (*closure)(args...);
    };
}
```
- 要求闭包满足:
  - 大小 ≤ 32/64 字节
  - 平凡可拷贝
  - 平凡可析构
- 避免堆分配

#### 调用运算符
```cpp
R operator()(Args... args) const {
    SkASSERT(fCall);
    return fCall(fBuf, std::forward<Args>(args)...);
}
```
- 通过 fCall 间接调用存储的函数或闭包
- 使用完美转发避免拷贝开销

#### 有效性检查
```cpp
explicit operator bool() const { return fCall != nullptr; }
```
- 检查是否持有有效的可调用对象

### 使用示例
```cpp
// 存储函数指针
GrGLFunction<GrGLActiveTextureFn> activeTexture(glActiveTexture);
activeTexture(GL_TEXTURE0);

// 存储小闭包
int textureUnit = 0;
GrGLFunction<GrGLActiveTextureFn> activeTex([textureUnit](GrGLenum) {
    printf("Activating texture %d\n", textureUnit);
});
activeTex(GL_TEXTURE0);
```

## Emscripten 特殊处理

### 同步函数超时参数
```cpp
#if defined(__EMSCRIPTEN__) && (__EMSCRIPTEN_major__ < 5)
using GrGLClientWaitSyncFn = GrGLenum GR_GL_FUNCTION_TYPE(
    GrGLsync sync, GrGLbitfield flags, GrGLint timeoutLo, GrGLint timeoutHi);
using GrGLWaitSyncFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLsync sync, GrGLbitfield flags, GrGLuint timeoutLo, GrGLuint timeoutHi);
#else
using GrGLClientWaitSyncFn = GrGLenum GR_GL_FUNCTION_TYPE(
    GrGLsync sync, GrGLbitfield flags, GrGLuint64 timeout);
using GrGLWaitSyncFn = GrGLvoid GR_GL_FUNCTION_TYPE(
    GrGLsync sync, GrGLbitfield flags, GrGLuint64 timeout);
#endif
```
- **原因**: 旧版 Emscripten 不支持 64 位整数参数
- **解决**: 拆分为两个 32 位整数(高位/低位)

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/gpu/ganesh/gl/GrGLTypes.h | GL 类型定义(GrGLenum, GrGLuint 等) |
| include/gpu/ganesh/gl/GrGLConfig.h | GR_GL_FUNCTION_TYPE 宏 |
| include/private/base/SkTLogic.h | 类型特性辅助 |
| <cstring> | memcpy |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| GrGLInterface | 存储所有 GL 函数指针 |
| GrGLGpu | 通过接口调用 GL 函数 |
| GrGLUtil | GL 辅助工具 |

## 设计模式与设计决策

### 类型安全的函数指针
使用 typedef 而非 void* 确保:
- 编译时类型检查
- 自文档化(函数签名即文档)
- IDE 自动补全支持

### 轻量级函数对象
GrGLFunction 相比 std::function:
- **优势**:
  - 更小的代码体积
  - 更快的编译速度
  - 避免堆分配
  - 确定性的性能
- **限制**:
  - 闭包大小受限(32/64 字节)
  - 仅支持平凡类型
  - 无类型擦除的灵活性

### 小缓冲区优化
fBuf[4] 设计:
- 64 位系统: 32 字节
- 32 位系统: 16 字节
- 足以存储函数指针 + 少量捕获变量
- 避免大多数场景的堆分配

## 性能考量

### 间接调用开销
- 函数指针调用比直接调用慢(无法内联)
- 现代 CPU 分支预测减轻影响
- Ganesh 使用缓存减少重复调用

### 内存占用
- 每个 GrGLFunction: 40-48 字节(fCall + fBuf)
- GrGLInterface 包含 ~200 个函数: ~8-10KB
- 相比直接链接 GL 库,增加少量内存开销

### 编译时间
- 大量 typedef 增加编译时间
- GrGLFunction 模板实例化开销
- 相比 std::function 仍显著更快

## 平台相关说明

### Windows
- 使用 `__stdcall` 调用约定
- 匹配 opengl32.dll 导出

### Unix/Linux/macOS
- 默认 C 调用约定
- 通过 dlsym 加载函数

### WebGL/Emscripten
- 函数映射到 JavaScript WebGL API
- 64 位整数参数需特殊处理

### Android/iOS
- OpenGL ES 函数子集
- 部分扩展函数可能不可用

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/gl/GrGLTypes.h | GL 基础类型定义 |
| include/gpu/ganesh/gl/GrGLConfig.h | 调用约定配置 |
| include/gpu/ganesh/gl/GrGLInterface.h | 函数指针存储和管理 |
| src/gpu/ganesh/gl/GrGLUtil.h | GL 辅助工具 |
| src/gpu/ganesh/gl/GrGLGpu.cpp | GL 函数调用实现 |
