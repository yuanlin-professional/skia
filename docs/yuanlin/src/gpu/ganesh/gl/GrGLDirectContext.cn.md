# GrGLDirectContext

> 源文件
> - include/gpu/ganesh/gl/GrGLDirectContext.h
> - src/gpu/ganesh/gl/GrGLDirectContext.cpp

## 概述

`GrGLDirectContext` 模块提供了创建 OpenGL 后端 `GrDirectContext` 的工厂函数集合。`GrDirectContext` 是 Skia Ganesh GPU 后端的执行上下文,负责提交绘制命令到 GPU 并管理 GPU 资源。该模块是 OpenGL 后端的入口点,应用程序通过这些工厂函数将 OpenGL 上下文桥接到 Skia 的渲染系统。

模块提供了多个重载版本的 `MakeGL` 函数,支持:
- 使用已有的 `GrGLInterface` 创建上下文
- 使用平台默认的 OpenGL 接口(已废弃)
- 自定义 `GrContextOptions` 配置

在测试模式下,还支持随机 OOM(Out Of Memory)注入功能,用于测试错误处理路径。

## 架构位置

在 Skia GPU 初始化流程中的位置:

```
应用程序
    ↓
GrDirectContexts::MakeGL ← 当前模块
    ↓
├─ 创建 GrDirectContext 框架
├─ 组装或使用现有 GrGLInterface
├─ 创建 GrGLGpu 实例
└─ 初始化上下文
    ↓
GrDirectContext (可执行的 GPU 上下文)
    ↓
绘制管道 (SkCanvas, SkSurface)
```

## 主要类与结构体

该模块不定义类,仅提供命名空间函数。

### GrDirectContexts 命名空间

包含所有 OpenGL 上下文创建函数。

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `sk_sp<GrDirectContext> MakeGL(sk_sp<const GrGLInterface>)` | 使用默认选项从 GL 接口创建上下文 |
| `sk_sp<GrDirectContext> MakeGL(sk_sp<const GrGLInterface>, const GrContextOptions&)` | 使用自定义选项从 GL 接口创建上下文 |
| `sk_sp<GrDirectContext> MakeGL()` | 使用平台默认接口创建上下文(已废弃) |
| `sk_sp<GrDirectContext> MakeGL(const GrContextOptions&)` | 使用平台默认接口和自定义选项(已废弃) |

### 函数参数说明

- `glInterface`: `GrGLInterface` 智能指针,封装 OpenGL 函数指针和能力信息
- `options`: `GrContextOptions` 引用,配置上下文行为(缓存大小、驱动 bug 规避等)

## 内部实现细节

### 主要创建函数实现

```cpp
sk_sp<GrDirectContext> MakeGL(sk_sp<const GrGLInterface> glInterface,
                              const GrContextOptions& options) {
#if defined(SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE)
    SkASSERT(glInterface);  // 某些配置要求必须提供接口
#endif

    // 1. 创建上下文框架
    auto direct = GrDirectContextPriv::Make(
            GrBackendApi::kOpenGL,
            options,
            GrContextThreadSafeProxyPriv::Make(GrBackendApi::kOpenGL, options));

#if defined(GPU_TEST_UTILS)
    // 2. 可选:注入随机 OOM
    if (options.fRandomGLOOM) {
        auto copy = sk_make_sp<GrGLInterface>(*glInterface);
        copy->fFunctions.fGetError =
                make_get_error_with_random_oom(glInterface->fFunctions.fGetError);
#if GR_GL_CHECK_ERROR
        copy->suppressErrorLogging();
#endif
        glInterface = std::move(copy);
    }
#endif

    // 3. 创建 GPU 实例
    GrDirectContextPriv::SetGpu(direct,
                                GrGLGpu::Make(std::move(glInterface), options, direct.get()));

    // 4. 初始化上下文
    if (!GrDirectContextPriv::Init(direct)) {
        return nullptr;
    }

    return direct;
}
```

### 默认接口版本(已废弃)

```cpp
sk_sp<GrDirectContext> MakeGL(const GrContextOptions& options) {
    return MakeGL(nullptr, options);  // nullptr 触发平台默认接口查找
}
```

在未定义 `SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE` 时可用,会自动调用 `GrGLMakeNativeInterface()` 获取平台默认接口。

### 随机 OOM 注入机制(测试用)

```cpp
#if defined(GPU_TEST_UTILS)
GrGLFunction<GrGLGetErrorFn> make_get_error_with_random_oom(
        GrGLFunction<GrGLGetErrorFn> original) {
    struct GetErrorContext {
        SkRandom fRandom;
        GrGLFunction<GrGLGetErrorFn> fGetError;
    };

    auto errorContext = new GetErrorContext;
#if defined(SK_ENABLE_SCOPED_LSAN_SUPPRESSIONS)
    __lsan_ignore_object(errorContext);  // 故意泄漏以简化捕获
#endif
    errorContext->fGetError = original;

    return GrGLFunction<GrGLGetErrorFn>([errorContext]() {
        GrGLenum error = errorContext->fGetError();
        if (error == GR_GL_NO_ERROR && (errorContext->fRandom.nextU() % 300) == 0) {
            error = GR_GL_OUT_OF_MEMORY;  // 1/300 概率返回 OOM
        }
        return error;
    });
}
#endif
```

这允许测试代码路径在 GPU 内存不足时的行为。

### 初始化失败处理

如果 `GrDirectContextPriv::Init` 失败(例如,OpenGL 版本不支持或驱动有问题),返回 `nullptr`:

```cpp
if (!GrDirectContextPriv::Init(direct)) {
    return nullptr;
}
```

调用者需要检查返回值。

### 简化版本的重载

```cpp
sk_sp<GrDirectContext> MakeGL(sk_sp<const GrGLInterface> glInterface) {
    GrContextOptions defaultOptions;
    return MakeGL(std::move(glInterface), defaultOptions);
}
```

提供便利接口,使用默认配置。

## 依赖关系

**依赖的模块:**

| 模块名 | 依赖说明 |
|--------|---------|
| `GrDirectContext` | 目标上下文类 |
| `GrDirectContextPriv` | 上下文私有实现辅助 |
| `GrGLInterface` | OpenGL 函数接口封装 |
| `GrGLGpu` | OpenGL GPU 实现 |
| `GrContextOptions` | 上下文配置选项 |
| `GrContextThreadSafeProxy` | 线程安全上下文代理 |
| `GrContextThreadSafeProxyPriv` | 代理私有实现 |
| `SkRandom` | 随机数生成器(测试用) |

**被依赖的模块:**

| 模块名 | 使用场景 |
|--------|---------|
| 应用程序主代码 | 初始化 Skia GPU 渲染 |
| 单元测试和基准测试 | 创建测试用 GPU 上下文 |
| 示例和演示程序 | 展示 GPU 渲染功能 |
| 平台集成层 | Android、iOS、桌面平台的 GPU 初始化 |

## 设计模式与设计决策

### 工厂方法模式

所有创建函数都是静态工厂方法,封装复杂的上下文构造过程:
- 创建上下文框架
- 关联 GPU 实现
- 执行初始化
- 处理失败情况

### 重载提供灵活性

多个重载版本满足不同使用场景:
- 最小接口:仅接口指针
- 完整接口:接口指针 + 选项
- 便利接口:使用默认配置

### 废弃 API 的渐进式迁移

通过条件编译控制废弃接口:

```cpp
#if !defined(SK_DISABLE_LEGACY_GL_MAKE_NATIVE_INTERFACE)
SK_API sk_sp<GrDirectContext> MakeGL(const GrContextOptions&);
SK_API sk_sp<GrDirectContext> MakeGL();
#endif
```

允许逐步迁移而不破坏现有代码。

### 测试功能条件编译

随机 OOM 注入仅在 `GPU_TEST_UTILS` 定义时编译,避免生产代码膨胀:

```cpp
#if defined(GPU_TEST_UTILS)
    if (options.fRandomGLOOM) {
        // 注入逻辑
    }
#endif
```

### 智能指针管理生命周期

使用 `sk_sp` 管理上下文和接口生命周期,自动处理引用计数。

### 移动语义避免拷贝

```cpp
GrDirectContextPriv::SetGpu(direct,
                            GrGLGpu::Make(std::move(glInterface), ...));
```

使用 `std::move` 转移接口所有权,避免不必要的引用计数操作。

## 性能考量

### 一次性初始化

上下文创建是一次性操作,不在性能敏感路径中。

### 移动语义减少引用计数开销

在可能的情况下使用移动语义传递智能指针,减少原子操作。

### 延迟初始化验证

复杂的能力检测和资源分配延迟到 `GrDirectContextPriv::Init` 中,失败时可以快速退出。

### 测试功能零开销

在非测试构建中,随机 OOM 代码完全不存在,无运行时开销。

### 内联小函数

简单的重载函数(如不带选项的版本)会被编译器内联。

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/gpu/ganesh/GrDirectContext.h` | 目标上下文类定义 |
| `src/gpu/ganesh/GrDirectContextPriv.h` | 上下文私有实现 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | OpenGL 接口类 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | OpenGL GPU 实现 |
| `include/gpu/ganesh/GrContextOptions.h` | 上下文配置选项 |
| `src/gpu/ganesh/GrContextThreadSafeProxyPriv.h` | 线程安全代理私有接口 |
| `src/gpu/ganesh/gl/GrGLAssembleInterface.h` | OpenGL 接口组装 |
| 平台特定文件(如 `src/gpu/ganesh/gl/win/GrGLMakeNativeInterface_win.cpp`) | 平台默认接口提供 |
