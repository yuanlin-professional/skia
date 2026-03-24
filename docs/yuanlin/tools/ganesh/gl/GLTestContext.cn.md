# GLTestContext

> 源文件：tools/ganesh/gl/GLTestContext.h, tools/ganesh/gl/GLTestContext.cpp

## 概述

GLTestContext 是 Skia Ganesh 测试框架中用于 OpenGL/OpenGL ES 后端的测试上下文抽象类。该类继承自 TestContext，提供了 OpenGL 特定的接口和功能，包括 OpenGL 函数指针管理、GPU 计时、EGL 图像集成测试支持等。

该类是一个平台无关的抽象层，由平台特定的子类实现（如 GLX、EGL、CGL、WGL 等）。它还包含一个内置的 GPU 计时器实现（GLGpuTimer），用于测量 OpenGL 命令的执行时间。

主要特性包括：
- 管理 GrGLInterface 函数指针表
- 支持 OpenGL 和 OpenGL ES 标准
- GPU 性能计时（使用 GL 查询对象）
- EGL 图像扩展支持（用于纹理共享测试）
- 版本覆盖功能（用于测试不同 OpenGL 版本的行为）
- 上下文共享和克隆

## 架构位置

GLTestContext 位于 Ganesh 测试工具的 OpenGL 实现层：

- **基类**：TestContext
- **子类实现**：各平台的 GLTestContext（GLX、EGL、CGL、WGL 等）和 ANGLE 实现
- **配合组件**：GLGpuTimer（GPU 计时器）、GrGLInterface（OpenGL 函数表）
- **Ganesh 后端**：GrGLDirectContext（OpenGL 直接上下文）

## 主要类与结构体

### GLTestContext

```cpp
class GLTestContext : public TestContext {
public:
    GrBackendApi backend() override { return GrBackendApi::kOpenGL; }
    bool isValid() const;
    const GrGLInterface* gl() const;

    // EGL 图像测试支持
    virtual GrEGLImage texture2DToEGLImage(GrGLuint texID) const;
    virtual void destroyEGLImage(GrEGLImage) const;
    virtual GrGLuint eglImageToExternalTexture(GrEGLImage) const;

    void testAbandon() override;
    void overrideVersion(const char* version, const char* shadingLanguageVersion);
    virtual std::unique_ptr<GLTestContext> makeNew() const;

    template<typename Ret, typename... Args>
    void getGLProcAddress(Ret(GR_GL_FUNCTION_TYPE** out)(Args...),
                          const char* name, const char* ext = nullptr) const;

    sk_sp<GrDirectContext> makeContext(const GrContextOptions& options) override;

protected:
    void init(sk_sp<const GrGLInterface>);
    void teardown() override;
    virtual GrGLFuncPtr onPlatformGetProcAddress(const char*) const = 0;

private:
    sk_sp<const GrGLInterface> fOriginalGLInterface;
    sk_sp<const GrGLInterface> fGLInterface;
};
```

### GLGpuTimer（内部实现）

```cpp
class GLGpuTimer : public sk_gpu_test::GpuTimer {
    static std::unique_ptr<GLGpuTimer> MakeIfSupported(const GLTestContext*);
    QueryStatus checkQueryStatus(PlatformTimerQuery) override;
    std::chrono::nanoseconds getTimeElapsed(PlatformTimerQuery) override;
    void deleteQuery(PlatformTimerQuery) override;
};
```

GLGpuTimer 使用 OpenGL 查询对象（GL_TIME_ELAPSED）测量 GPU 执行时间，支持多种扩展：
- `GL_EXT_disjoint_timer_query`（支持检测 GPU 时钟不连续）
- `GL_ARB_timer_query`（OpenGL 3.3+ 核心功能）
- `GL_EXT_timer_query`（较老的扩展）

## 公共 API 函数

### isValid()
检查 OpenGL 上下文是否成功创建。返回 `gl()` 是否非空。

### gl()
返回 GrGLInterface 函数指针表，用于调用 OpenGL API。

### getGLProcAddress()
模板函数，获取 OpenGL 扩展函数指针。支持扩展后缀（如 "EXT"、"ARB"）。

**使用示例**：
```cpp
typedef void (GR_GL_FUNCTION_TYPE* GLGenQueriesProc)(GrGLsizei, GrGLuint*);
GLGenQueriesProc glGenQueries;
ctx->getGLProcAddress(&glGenQueries, "glGenQueries", "EXT");
```

### overrideVersion()
覆盖 `glGetString(GL_VERSION)` 和 `glGetString(GL_SHADING_LANGUAGE_VERSION)` 的返回值，用于测试版本特定的代码路径。

### makeNew()
创建一个新的同类型 OpenGL 上下文。用于上下文共享测试。基类实现返回 nullptr，子类应重写。

### EGL 图像函数
- **texture2DToEGLImage()**：将 GL_TEXTURE_2D 包装为 EGL Image
- **destroyEGLImage()**：销毁 EGL Image
- **eglImageToExternalTexture()**：将 EGL Image 包装为 GL_TEXTURE_EXTERNAL_OES

这些函数用于测试跨 API 纹理共享（如 OpenGL 与 Vulkan）。

## 内部实现细节

### 初始化流程

```cpp
void GLTestContext::init(sk_sp<const GrGLInterface> gl) {
    fGLInterface = std::move(gl);
    fOriginalGLInterface = fGLInterface;
    fFenceSupport = fence_is_supported(this);
    fGpuTimer = GLGpuTimer::MakeIfSupported(this);
}
```

初始化时：
1. 存储 OpenGL 接口（原始和当前）
2. 检测栅栏同步支持（`glFenceSync` 或扩展）
3. 创建 GPU 计时器（如果支持）

### 栅栏支持检测

```cpp
static bool fence_is_supported(const GLTestContext* ctx) {
    if (kGL_GrGLStandard == ctx->gl()->fStandard) {
        return GrGLGetVersion(ctx->gl()) >= GR_GL_VER(3, 2) ||
               ctx->gl()->hasExtension("GL_ARB_sync");
    } else {
        return ctx->gl()->hasExtension("GL_APPLE_sync") ||
               ctx->gl()->hasExtension("GL_NV_fence") ||
               GrGLGetVersion(ctx->gl()) >= GR_GL_VER(3, 0);
    }
}
```

支持检测区分 OpenGL 和 OpenGL ES，考虑核心版本和扩展。

### GPU 计时器实现

GLGpuTimer 使用查询对象测量时间：

```cpp
PlatformTimerQuery GLGpuTimer::onQueueTimerStart() const {
    GrGLuint queryID;
    fGLGenQueries(1, &queryID);
    fGLBeginQuery(GL_TIME_ELAPSED, queryID);
    return static_cast<PlatformTimerQuery>(queryID);
}

void GLGpuTimer::onQueueTimerStop(PlatformTimerQuery platformTimer) const {
    fGLEndQuery(GL_TIME_ELAPSED);
}
```

时间查询流程：
1. 生成查询对象
2. 开始查询（`glBeginQuery`）
3. 执行要测量的 OpenGL 命令
4. 结束查询（`glEndQuery`）
5. 检查查询完成（`glGetQueryObjectuiv(GL_QUERY_RESULT_AVAILABLE)`）
6. 获取结果（`glGetQueryObjectui64v(GL_QUERY_RESULT)`）

### 不连续检测

如果支持 `GL_EXT_disjoint_timer_query`，可以检测 GPU 时钟不连续（如 GPU 频率变化）：

```cpp
if (this->disjointSupport()) {
    GrGLint disjoint = 1;
    fGLGetIntegerv(GL_GPU_DISJOINT, &disjoint);
    if (disjoint) {
        return QueryStatus::kDisjoint;  // 时间测量不可靠
    }
}
```

### 版本覆盖实现

```cpp
void GLTestContext::overrideVersion(const char* version,
                                    const char* shadingLanguageVersion) {
    auto getString = [wrapped = &fOriginalGLInterface->fFunctions.fGetString,
                      version,
                      shadingLanguageVersion](GrGLenum name) {
        if (name == GR_GL_VERSION) {
            return reinterpret_cast<const GrGLubyte*>(version);
        } else if (name == GR_GL_SHADING_LANGUAGE_VERSION) {
            return reinterpret_cast<const GrGLubyte*>(shadingLanguageVersion);
        }
        return (*wrapped)(name);
    };
    auto newInterface = sk_make_sp<GrGLInterface>(*fOriginalGLInterface);
    newInterface->fFunctions.fGetString = getString;
    fGLInterface = std::move(newInterface);
}
```

通过 lambda 捕获和替换 `glGetString` 实现版本覆盖，其他查询仍使用原始接口。

### 上下文放弃

```cpp
void GLTestContext::testAbandon() {
    INHERITED::testAbandon();
#if defined(GPU_TEST_UTILS)
    if (fGLInterface) {
        fGLInterface->abandon();
        fOriginalGLInterface->abandon();
    }
#endif
}
```

调用接口的 `abandon()` 方法，标记所有函数指针为无效，用于测试资源清理。

## 依赖关系

### 核心依赖
- **GrGLInterface**：OpenGL 函数指针表
- **GrGLUtil**：OpenGL 工具函数（版本解析、扩展检查）
- **GrDirectContexts::MakeGL**：创建 OpenGL Ganesh 上下文

### GPU 计时
- **GpuTimer**：GPU 计时器基类
- OpenGL 查询对象扩展

### EGL 图像
- **EGL_KHR_image**：EGL 图像扩展
- **GL_OES_EGL_image_external**：外部纹理扩展

## 设计模式与设计决策

### 模板方法模式
GLTestContext 定义 OpenGL 上下文管理的框架，子类实现平台特定的细节（如 `onPlatformGetProcAddress`）。

### 双接口存储
保留原始接口和当前接口：
- `fOriginalGLInterface`：未修改的接口
- `fGLInterface`：可能被版本覆盖修改的接口

这支持版本覆盖功能，同时保持原始函数的可访问性。

### 工厂函数模式
`GLGpuTimer::MakeIfSupported` 根据扩展可用性创建计时器或返回 nullptr，遵循"可选功能"模式。

### 模板化函数指针获取
`getGLProcAddress` 使用模板保持类型安全，避免手动类型转换。

## 性能考量

### GPU 计时开销
查询对象会增加小量 CPU 和 GPU 开销。测试框架仅在需要性能测量时创建计时器。

### 不连续检测
检查 `GL_GPU_DISJOINT` 标志确保时间测量的准确性，对于性能基准测试至关重要。

### 栅栏同步
支持的栅栏同步允许异步等待 GPU 完成，比忙等待（busy-waiting）更高效。

### 版本覆盖
版本覆盖通过 lambda 重定向，有微小的间接调用开销，但对测试可接受。

## 相关文件

### 基类和同级实现
- `tools/ganesh/TestContext.h/cpp` - 测试上下文基类
- `tools/ganesh/vk/VkTestContext.h/cpp` - Vulkan 实现
- `tools/ganesh/mtl/MtlTestContext.h/.mm` - Metal 实现
- `tools/ganesh/d3d/D3DTestContext.h/cpp` - Direct3D 实现

### OpenGL 特定实现
- `tools/ganesh/gl/angle/GLTestContext_angle.h/cpp` - ANGLE (OpenGL ES on D3D/Metal)
- 各平台原生实现（GLX、EGL、CGL、WGL）

### Ganesh OpenGL 支持
- `include/gpu/ganesh/gl/GrGLInterface.h` - OpenGL 函数接口
- `include/gpu/ganesh/gl/GrGLDirectContext.h` - OpenGL 直接上下文
- `src/gpu/ganesh/gl/GrGLUtil.h` - OpenGL 工具函数

### 计时和扩展
- `tools/ganesh/GpuTimer.h` - GPU 计时器抽象
- `include/gpu/ganesh/gl/GrGLAssembleInterface.h` - 接口组装
