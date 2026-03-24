# ganesh_gl

> 源文件: example/external_client/src/ganesh_gl.cpp

## 概述

ganesh_gl 是一个跨平台的 Ganesh OpenGL 后端渲染示例,支持 Linux (GLX)、macOS (CGL) 和 Windows (WGL) 三大桌面平台。程序创建平台特定的 OpenGL 上下文,使用 Skia Ganesh 进行 GPU 渲染(红色背景上的蓝色圆角矩形),并将结果编码为 WebP 图像保存。展示了如何在不同操作系统上初始化 OpenGL 并集成 Skia。

这是外部客户端在桌面平台上使用 Ganesh GL 后端的完整参考实现,包含了各平台 OpenGL 上下文创建的详细代码。

## 架构位置

```
skia/example/external_client/src/
├── ganesh_gl.cpp            # OpenGL 示例(258行)
├── gl_context_helper.h/mm   # macOS 辅助模块
└── ganesh_metal.cpp         # Metal 对比示例
```

## 主要类与结构体

### 平台特定类型

#### Linux (GLX)
```cpp
Display* display;            // X11 显示
GLXFBConfig* fbConfig;       // 帧缓冲配置
GLXContext glContext;        // OpenGL 上下文
Window window;               // X11 窗口
```

#### macOS (CGL)
```cpp
// 封装在 gl_context_helper.mm 中
```

#### Windows (WGL)
```cpp
HWND window;                 // 窗口句柄
HDC deviceContext;           // 设备上下文
HGLRC glrc;                  // OpenGL 渲染上下文
```

## 公共 API 函数

### main()

```cpp
int main(int argc, char** argv);
```

**参数**: `argv[1]` - 输出 WebP 文件路径

**执行流程**:
1. 初始化平台特定的 OpenGL 上下文
2. 创建 GrGLInterface (OpenGL 函数指针表)
3. 创建 GrDirectContext
4. 创建渲染表面
5. 绘制图形
6. 编码为 WebP
7. 写入文件

### 平台初始化函数

#### initialize_gl_linux() (Linux)

```cpp
bool initialize_gl_linux();
```

**功能**: 在 Linux 上创建 GLX 上下文

**实现要点**:
- 打开 X Display
- 选择 FBConfig (双缓冲,模板缓冲)
- 创建 GLXContext
- 创建离屏 X Window
- 设置为当前上下文

**关键配置**:
```cpp
static int constexpr kChooseFBConfigAtt[] = {
    GLX_RENDER_TYPE, GLX_RGBA_BIT,
    GLX_DOUBLEBUFFER, True,
    GLX_STENCIL_SIZE, 8,
    None
};
```

#### initialize_gl_mac() (macOS)

由 `gl_context_helper.mm` 提供,创建 OpenGL 3.2 Core Profile 上下文。

#### initialize_gl_win() (Windows)

```cpp
bool initialize_gl_win();
```

**功能**: 在 Windows 上创建 WGL 上下文

**实现要点**:
- 注册窗口类
- 创建隐藏窗口
- 获取设备上下文
- 设置像素格式
- 创建 OpenGL 渲染上下文

**像素格式配置**:
```cpp
PIXELFORMATDESCRIPTOR pfd = {
    sizeof(PIXELFORMATDESCRIPTOR),
    1,
    PFD_DRAW_TO_WINDOW | PFD_SUPPORT_OPENGL | PFD_DOUBLEBUFFER,
    PFD_TYPE_RGBA,
    32,  // 32-bit 颜色深度
    // ...
    24,  // 24-bit 深度缓冲
    8,   // 8-bit 模板缓冲
    // ...
};
```

## 内部实现细节

### GL 接口创建

```cpp
#if defined(__linux__)
    sk_sp<const GrGLInterface> iface = GrGLInterfaces::MakeGLX();
#elif defined(__APPLE__) && TARGET_OS_MAC == 1
    sk_sp<const GrGLInterface> iface = GrGLInterfaces::MakeMac();
#elif defined(_MSC_VER)
    sk_sp<const GrGLInterface> iface = GrGLInterfaces::MakeWin();
#endif
```

**平台抽象**: 每个平台提供特定的 GL 函数加载器

### 上下文创建

```cpp
GrContextOptions opts;
opts.fSuppressPrints = true;  // 抑制调试输出

sk_sp<GrDirectContext> ctx = GrDirectContexts::MakeGL(iface, opts);
```

**配置**: 禁用调试打印以保持输出清洁

### 渲染流程

```cpp
SkImageInfo imageInfo = SkImageInfo::Make(200, 400, kRGBA_8888_SkColorType, kPremul_SkAlphaType);

sk_sp<SkSurface> surface = SkSurfaces::RenderTarget(ctx.get(), skgpu::Budgeted::kYes, imageInfo);

SkCanvas* canvas = surface->getCanvas();
canvas->clear(SK_ColorRED);
SkRRect rrect = SkRRect::MakeRectXY(SkRect::MakeLTRB(10, 20, 50, 70), 10, 10);

SkPaint paint;
paint.setColor(SK_ColorBLUE);
paint.setAntiAlias(true);

canvas->drawRRect(rrect, paint);
```

**绘制内容**:
- 200x400 像素表面
- 红色背景
- 蓝色圆角矩形 (10,20)-(50,70),圆角半径 10
- 启用抗锯齿

### WebP 编码

```cpp
ctx->flush();  // 确保绘制完成

sk_sp<SkImage> img = surface->makeImageSnapshot();
sk_sp<SkData> webp = SkWebpEncoder::Encode(ctx.get(), img.get(), {});
```

**编码流程**:
1. flush 确保 GL 命令执行
2. 创建图像快照
3. 在 GPU 上编码为 WebP (如果支持)

## 依赖关系

### 核心头文件
```cpp
#include "include/gpu/ganesh/GrDirectContext.h"
#include "include/gpu/ganesh/SkSurfaceGanesh.h"
#include "include/gpu/ganesh/gl/GrGLDirectContext.h"
#include "include/gpu/ganesh/gl/GrGLInterface.h"
#include "include/encode/SkWebpEncoder.h"
```

### 平台特定头文件

#### Linux
```cpp
#include "include/gpu/ganesh/gl/glx/GrGLMakeGLXInterface.h"
#include <X11/Xlib.h>
#include <GL/glx.h>
#include <GL/gl.h>
```

#### macOS
```cpp
#include "include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h"
#include "gl_context_helper.h"
```

#### Windows
```cpp
#include <windows.h>
#include "include/gpu/ganesh/gl/win/GrGLMakeWinInterface.h"
```

## 设计模式与设计决策

### 1. 条件编译模式

使用预处理器指令隔离平台特定代码:
```cpp
#if defined(__linux__)
    // Linux 代码
#elif defined(__APPLE__) && TARGET_OS_MAC == 1
    // macOS 代码
#elif defined(_MSC_VER)
    // Windows 代码
#endif
```

### 2. 策略模式

每个平台实现相同的 `initialize_gl_*()` 接口,提供不同的初始化策略。

### 3. 设计决策

#### (1) 为何创建离屏窗口?

```cpp
// Linux
Window window = XCreateWindow(...);  // 创建但不显示

// Windows
CreateWindow(..., CS_OWNDC, 0, 0, 1, 1, ...);  // 1x1 像素窗口
```

- **必要性**: GLX/WGL 需要窗口关联的上下文
- **不可见**: 不需要用户交互
- **最小化**: 1x1 像素减少资源占用

#### (2) 为何使用双缓冲?

```cpp
GLX_DOUBLEBUFFER, True  // Linux
PFD_DOUBLEBUFFER        // Windows
```

- **平滑性**: 避免闪烁
- **标准配置**: 大多数 GL 应用都使用
- **兼容性**: 确保驱动程序支持

#### (3) 为何输出 WebP 而非 PNG/JPEG?

- **现代格式**: WebP 提供更好的压缩
- **GPU 编码**: Skia 可能在 GPU 上编码 WebP
- **示例价值**: 展示新格式支持

## 性能考量

### 1. 上下文创建开销

平台初始化是一次性操作,但开销差异大:

| 平台 | 典型耗时 | 主要开销 |
|------|---------|---------|
| Linux | 50-200ms | X Server 通信 |
| macOS | 10-50ms | CGL 初始化 |
| Windows | 20-100ms | 窗口创建 |

### 2. 渲染性能

```cpp
canvas->drawRRect(rrect, paint);
```

- **GPU 加速**: 圆角矩形在 GPU 上渲染
- **抗锯齿开销**: 约 2-3x 片段着色器执行时间
- **批处理**: Skia 自动批处理几何体

### 3. WebP 编码性能

```cpp
SkWebpEncoder::Encode(ctx.get(), img.get(), {});
```

- **GPU 编码**: 如果支持,在 GPU 上执行
- **CPU 回退**: 否则在 CPU 上编码
- **压缩质量**: 默认设置平衡质量和速度

## 相关文件

### 平台辅助
- **gl_context_helper.h/mm**: macOS OpenGL 初始化
- **tools/gpu/gl/**: Skia 内部 GL 工具(参考实现)

### 其他后端示例
- **ganesh_metal.cpp**: Metal 后端
- **ganesh_vulkan.cpp**: Vulkan 后端
- **VulkanBasic.cpp**: 完整 Vulkan 示例

### Ganesh GL API
- **include/gpu/ganesh/gl/GrGLInterface.h**: GL 函数指针表
- **include/gpu/ganesh/gl/GrGLDirectContext.h**: GL DirectContext
- **src/gpu/ganesh/gl/**: Ganesh GL 实现

### 编码器
- **include/encode/SkWebpEncoder.h**: WebP 编码 API
- **third_party/libwebp/**: WebP 库

该示例是学习跨平台 OpenGL 集成的宝贵资源,展示了如何在不同操作系统上正确初始化 GL 上下文并使用 Skia 进行渲染。
