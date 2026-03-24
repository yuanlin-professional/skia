# GaneshGLWindowContext_unix

> 源文件
> - tools/window/unix/GaneshGLWindowContext_unix.h
> - tools/window/unix/GaneshGLWindowContext_unix.cpp

## 概述

`GaneshGLWindowContext_unix` 是 Skia 在 Unix/Linux 平台上使用 Ganesh 渲染引擎和 OpenGL 图形 API 的窗口上下文实现。该模块通过 GLX（OpenGL Extension to the X Window System）接口在 X Window System 上创建和管理 OpenGL 渲染上下文。它支持现代 OpenGL Core Profile 和传统的 Compatibility Profile，并具备 RenderDoc 集成支持，是 Linux 桌面环境中 Skia GPU 渲染的重要实现。

该实现包含复杂的上下文创建逻辑，尝试创建最高版本的 OpenGL 上下文，支持垂直同步控制，并能处理各种错误情况。它是 Skia 测试工具和应用程序在 Linux 平台上的主要渲染后端之一。

## 架构位置

该模块位于 Skia 工具层的 Unix 平台窗口实现中：

```
skia/
├── tools/
│   └── window/
│       ├── GLWindowContext.h                  # OpenGL 窗口上下文基类
│       └── unix/
│           ├── GaneshGLWindowContext_unix.h        # 本模块头文件
│           ├── GaneshGLWindowContext_unix.cpp      # 本模块实现
│           ├── GaneshVulkanWindowContext_unix.cpp  # Vulkan 实现
│           └── XlibWindowInfo.h               # Xlib 窗口信息
├── include/
│   └── gpu/
│       └── ganesh/
│           └── gl/
│               ├── GrGLInterface.h            # OpenGL 接口抽象
│               └── glx/
│                   └── GrGLMakeGLXInterface.h # GLX 接口创建
└── src/
    └── gpu/
        └── ganesh/
            └── gl/                            # Ganesh OpenGL 后端
```

该模块的架构角色：
- **向上**：为测试工具提供 OpenGL 渲染能力
- **向下**：调用 GLX 和 OpenGL API
- **横向**：与 Vulkan、Dawn 实现并列

## 主要类与结构体

### GLWindowContext_xlib

匿名命名空间内的私有实现类，继承自 `GLWindowContext`。

**主要成员变量：**
- `Display* fDisplay`：X11 显示连接
- `XWindow fWindow`：X Window 窗口句柄
- `GLXFBConfig* fFBConfig`：GLX 帧缓冲配置
- `XVisualInfo* fVisualInfo`：X11 视觉信息
- `GLXContext fGLContext`：GLX OpenGL 上下文

**主要成员函数：**

```cpp
GLWindowContext_xlib(const XlibWindowInfo&, std::unique_ptr<const DisplayParams>)
```
构造函数，接收窗口信息并初始化上下文。

```cpp
~GLWindowContext_xlib() override
```
析构函数，清理资源。

```cpp
sk_sp<const GrGLInterface> onInitializeContext() override
```
创建 OpenGL 上下文并返回 Ganesh GL 接口。

```cpp
void onDestroyContext() override
```
销毁 OpenGL 上下文。

```cpp
void onSwapBuffers() override
```
交换前后缓冲区。

### XlibWindowInfo

定义在 `XlibWindowInfo.h` 中：
- `Display* fDisplay`：X11 显示连接
- `Window fWindow`：窗口句柄
- `GLXFBConfig* fFBConfig`：帧缓冲配置
- `XVisualInfo* fVisualInfo`：视觉信息
- `int fWidth`、`int fHeight`：窗口尺寸

### 全局错误处理

```cpp
static bool gCtxErrorOccurred = false;
static int ctxErrorHandler(Display* dpy, XErrorEvent* ev) {
    gCtxErrorOccurred = true;
    return 0;
}
```

用于捕获 X11 错误，支持上下文创建的重试逻辑。

## 公共 API 函数

### MakeGaneshGLForXlib

```cpp
namespace skwindow {
std::unique_ptr<WindowContext> MakeGaneshGLForXlib(
    const XlibWindowInfo& winInfo,
    std::unique_ptr<const DisplayParams> params);
}
```

**功能：** 创建 Unix/Linux 平台的 Ganesh OpenGL 窗口上下文。

**参数：**
- `winInfo`：包含 X Window 和 GLX 信息的结构体
- `params`：显示参数配置

**返回值：** 成功返回 `WindowContext` 智能指针，失败返回 `nullptr`

**使用场景：**
- Linux 桌面应用程序的 OpenGL 渲染
- 跨平台测试工具
- 兼容性要求较高的场景

## 内部实现细节

### 上下文初始化流程

`onInitializeContext()` 实现了复杂的上下文创建逻辑：

**第一阶段：尝试使用 glXCreateContextAttribsARB**

```cpp
CreateContextAttribsFn* createContextAttribs = (CreateContextAttribsFn*)glXGetProcAddressARB(
        (const GLubyte*)"glXCreateContextAttribsARB");
if (createContextAttribs && fFBConfig) {
    // 安装错误处理器
    int (*oldHandler)(Display*, XErrorEvent*) = XSetErrorHandler(&ctxErrorHandler);

    // 尝试 OpenGL 3.0, 3.1, 3.2
    for (int minor = 2; minor >= 0 && !fGLContext; --minor) {
        // 尝试 Core Profile 和 Compatibility Profile
        for (int profile : {GLX_CONTEXT_CORE_PROFILE_BIT_ARB,
                           GLX_CONTEXT_COMPATIBILITY_PROFILE_BIT_ARB}) {
            gCtxErrorOccurred = false;
            int attribs[] = {GLX_CONTEXT_MAJOR_VERSION_ARB, 3,
                           GLX_CONTEXT_MINOR_VERSION_ARB, minor,
                           GLX_CONTEXT_PROFILE_MASK_ARB, profile,
                           0};
            fGLContext = createContextAttribs(fDisplay, *fFBConfig, nullptr, True, attribs);

            XSync(fDisplay, False);
            if (gCtxErrorOccurred) {
                continue;
            }

            // RenderDoc 特殊处理
            if (fGLContext && profile == GLX_CONTEXT_COMPATIBILITY_PROFILE_BIT_ARB &&
                glXMakeCurrent(fDisplay, fWindow, fGLContext)) {
                interface = make_interface();
                if (interface && interface->fExtensions.has("GL_EXT_debug_tool")) {
                    // RenderDoc 需要 Core Profile，重新创建
                    interface.reset();
                    glXMakeCurrent(fDisplay, None, nullptr);
                    glXDestroyContext(fDisplay, fGLContext);
                    fGLContext = nullptr;
                }
            }
            if (fGLContext) {
                break;
            }
        }
    }

    XSetErrorHandler(oldHandler);
}
```

**关键点：**
- 优先尝试 `glXCreateContextAttribsARB` 以支持 RenderDoc
- 从 OpenGL 3.2 向下尝试到 3.0
- 优先尝试 Core Profile，再尝试 Compatibility Profile
- 检测 RenderDoc（通过 `GL_EXT_debug_tool` 扩展）并强制使用 Core Profile

**第二阶段：回退到 glXCreateContext**

```cpp
if (!fGLContext) {
    fGLContext = glXCreateContext(fDisplay, fVisualInfo, nullptr, GL_TRUE);
}
if (!fGLContext) {
    return nullptr;
}
```

如果现代方法失败，使用传统 API 创建兼容性上下文。

**第三阶段：激活上下文并配置**

```cpp
if (!current && !glXMakeCurrent(fDisplay, fWindow, fGLContext)) {
    return nullptr;
}

// 配置垂直同步
const char* glxExtensions = glXQueryExtensionsString(fDisplay, DefaultScreen(fDisplay));
if (glxExtensions && strstr(glxExtensions, "GLX_EXT_swap_control")) {
    PFNGLXSWAPINTERVALEXTPROC glXSwapIntervalEXT =
            (PFNGLXSWAPINTERVALEXTPROC)glXGetProcAddressARB(
                    (const GLubyte*)"glXSwapIntervalEXT");
    glXSwapIntervalEXT(fDisplay, fWindow, fDisplayParams->disableVsync() ? 0 : 1);
}

// 初始化 OpenGL 状态
glClearStencil(0);
glClearColor(0, 0, 0, 0);
glStencilMask(0xffffffff);
glClear(GL_STENCIL_BUFFER_BIT | GL_COLOR_BUFFER_BIT);

// 查询配置
glXGetConfig(fDisplay, fVisualInfo, GLX_STENCIL_SIZE, &fStencilBits);
glXGetConfig(fDisplay, fVisualInfo, GLX_SAMPLES_ARB, &fSampleCount);
fSampleCount = std::max(fSampleCount, 1);

// 查询窗口尺寸
XGetGeometry(fDisplay, fWindow, &root, &x, &y,
             (unsigned int*)&fWidth, (unsigned int*)&fHeight,
             &border_width, &depth);
glViewport(0, 0, fWidth, fHeight);
```

### 缓冲区交换

```cpp
void GLWindowContext_xlib::onSwapBuffers() {
    if (fDisplay && fGLContext) {
        glXSwapBuffers(fDisplay, fWindow);
    }
}
```

调用 GLX 的双缓冲交换函数，将后缓冲区内容显示到屏幕。

### 上下文销毁

```cpp
void GLWindowContext_xlib::onDestroyContext() {
    if (!fDisplay || !fGLContext) {
        return;
    }
    glXMakeCurrent(fDisplay, None, nullptr);
    glXDestroyContext(fDisplay, fGLContext);
    fGLContext = nullptr;
}
```

取消上下文绑定并销毁 GLX 上下文。

### RenderDoc 集成

RenderDoc 是流行的图形调试工具，代码通过检测 `GL_EXT_debug_tool` 扩展识别其存在：

```cpp
if (interface && interface->fExtensions.has("GL_EXT_debug_tool")) {
    // RenderDoc 需要 Core Profile
    // 销毁 Compatibility Profile 上下文，重新尝试 Core Profile
}
```

这确保在使用 RenderDoc 时创建兼容的上下文。

## 依赖关系

### 外部依赖

**Skia 组件：**
- `GLWindowContext`：OpenGL 窗口上下文基类
- `GrGLInterface`：OpenGL 函数指针抽象
- `GrGLInterfaces::MakeGLX()`：创建 GLX 接口

**系统库：**
- `X11`：X Window System
- `GL`：OpenGL 核心库
- `GLX`：OpenGL X Window System 扩展

**GLX 扩展：**
- `GLX_ARB_create_context`：创建特定版本上下文
- `GLX_EXT_swap_control`：垂直同步控制
- `GLX_ARB_multisample`：多重采样支持

### 被依赖关系

该模块被以下组件使用：
- Viewer 测试工具
- DM 测试框架
- 基准测试工具
- Linux 平台 Skia 应用程序

## 设计模式与设计决策

### 设计模式

1. **工厂模式**
   - `MakeGaneshGLForXlib()` 创建平台实现
   - 返回基类指针

2. **模板方法模式**
   - 继承 `GLWindowContext`
   - 实现虚函数接口

3. **策略模式**
   - 多种上下文创建策略（现代/传统）
   - 多种 Profile 选择策略

### 设计决策

1. **优先尝试 glXCreateContextAttribsARB**
   - 支持指定 OpenGL 版本和 Profile
   - RenderDoc 调试工具要求
   - 更好的控制和兼容性

2. **版本降级策略**
   - 从 3.2 降级到 3.0
   - 确保在各种驱动上都能工作
   - 提供最佳可用版本

3. **Profile 选择顺序**
   ```cpp
   {GLX_CONTEXT_CORE_PROFILE_BIT_ARB, GLX_CONTEXT_COMPATIBILITY_PROFILE_BIT_ARB}
   ```
   - 优先 Core Profile（Ganesh 偏好）
   - 回退到 Compatibility Profile

4. **错误处理机制**
   - 自定义 X11 错误处理器
   - 捕获异步错误
   - 使用 `XSync()` 强制同步

5. **RenderDoc 特殊处理**
   - 检测调试工具存在
   - 强制使用 Core Profile
   - 确保调试兼容性

6. **传统 API 回退**
   - 保留 `glXCreateContext` 作为最后手段
   - 支持旧驱动和系统

## 性能考量

### 优势

1. **成熟的驱动支持**
   - OpenGL 在 Linux 上广泛支持
   - 驱动优化良好

2. **低启动开销**
   - 上下文创建相对快速
   - 库通常已加载

3. **广泛兼容性**
   - 支持旧硬件和驱动
   - 降级策略确保可用性

### 潜在瓶颈

1. **上下文创建重试**
   - 多次尝试可能耗时
   - X11 同步操作开销

2. **垂直同步等待**
   - 启用时限制帧率
   - 可通过 `disableVsync` 禁用

3. **GLX 扩展查询**
   - 字符串查找操作
   - 可缓存优化

### 优化建议

- 缓存扩展查询结果
- 优先使用 Direct Rendering
- 考虑升级到 Vulkan 以获得更好性能

## 相关文件

**同平台其他实现：**
- `tools/window/unix/GaneshVulkanWindowContext_unix.cpp`：Vulkan 实现
- `tools/window/unix/GraphiteNativeVulkanWindowContext_unix.cpp`：Graphite Vulkan
- `tools/window/unix/GraphiteDawnXlibWindowContext_unix.cpp`：Graphite Dawn
- `tools/window/unix/RasterWindowContext_unix.cpp`：软件光栅化

**基类和工具：**
- `tools/window/GLWindowContext.h`：OpenGL 窗口上下文基类
- `tools/window/WindowContext.h`：窗口上下文抽象
- `tools/window/unix/XlibWindowInfo.h`：Xlib 窗口信息

**其他平台 OpenGL 实现：**
- `tools/window/mac/GaneshGLWindowContext_mac.mm`：macOS 实现
- `tools/window/win/GaneshGLWindowContext_win.cpp`：Windows 实现
- `tools/window/android/GaneshGLWindowContext_android.cpp`：Android 实现

**Ganesh OpenGL 后端：**
- `src/gpu/ganesh/gl/GrGLGpu.h`：Ganesh OpenGL GPU 实现
- `include/gpu/ganesh/gl/GrGLInterface.h`：GL 接口抽象
- `include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h`：GLX 接口创建

**应用示例：**
- `tools/viewer/Viewer.cpp`：可视化测试工具
- `dm/DM.cpp`：测试框架
- `tools/sk_app/unix/main_unix.cpp`：Unix 应用入口
