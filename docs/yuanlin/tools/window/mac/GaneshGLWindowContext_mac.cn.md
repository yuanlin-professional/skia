# GaneshGLWindowContext_mac

> 源文件
> - tools/window/mac/GaneshGLWindowContext_mac.h
> - tools/window/mac/GaneshGLWindowContext_mac.mm

## 概述

`GaneshGLWindowContext_mac` 是 Skia 在 macOS 平台上使用 Ganesh 渲染引擎和 OpenGL 图形接口的窗口上下文实现。该模块负责在 macOS 环境下创建、配置和管理 OpenGL 渲染上下文，使 Skia 能够通过 NSOpenGL 框架进行硬件加速渲染。它是 Skia 跨平台窗口系统抽象层在 macOS 平台的具体实现，主要用于测试工具和示例应用程序。

该实现处理了 macOS 特定的 OpenGL 上下文创建、像素格式配置、视图绑定以及缓冲区交换等底层细节。它继承自通用的 `GLWindowContext` 基类，实现了平台相关的虚函数接口，为上层提供统一的渲染接口。

## 架构位置

该模块位于 Skia 的工具层窗口系统实现中：

```
skia/
├── tools/
│   └── window/                        # 窗口抽象层
│       ├── GLWindowContext.h          # OpenGL 窗口上下文基类
│       └── mac/                       # macOS 平台实现
│           ├── GaneshGLWindowContext_mac.h     # 本模块头文件
│           ├── GaneshGLWindowContext_mac.mm    # 本模块实现
│           ├── MacWindowInfo.h        # macOS 窗口信息结构
│           └── MacWindowGLUtils.h     # macOS OpenGL 工具函数
├── include/
│   └── gpu/
│       └── ganesh/
│           ├── gl/
│           │   └── GrGLInterface.h    # OpenGL 接口抽象
│           └── GrDirectContext.h      # Ganesh 上下文
└── src/
    └── gpu/
        └── ganesh/
            └── gl/                    # Ganesh OpenGL 后端
```

该模块在架构中的角色：
- **向上**：为测试工具和示例应用提供窗口渲染能力
- **向下**：调用 macOS NSOpenGL 框架和 Ganesh OpenGL 后端
- **横向**：与其他平台的窗口上下文实现（Unix、Windows）并列

## 主要类与结构体

### GLWindowContext_mac

匿名命名空间内的私有实现类，继承自 `GLWindowContext`。

**主要成员变量：**
- `NSView* fMainView`：macOS 主视图对象，用于承载 OpenGL 渲染表面
- `NSOpenGLContext* fGLContext`：macOS OpenGL 上下文对象，管理 OpenGL 状态
- `NSOpenGLPixelFormat* fPixelFormat`：像素格式配置对象，定义帧缓冲特性

**主要成员函数：**
- `GLWindowContext_mac(const MacWindowInfo&, std::unique_ptr<const DisplayParams>)`：构造函数，接收窗口信息和显示参数
- `~GLWindowContext_mac()`：析构函数，清理资源
- `onInitializeContext()`：初始化 OpenGL 上下文和 Ganesh 接口
- `onDestroyContext()`：销毁上下文（条件性）
- `onSwapBuffers()`：交换前后缓冲区
- `resize(int w, int h)`：处理窗口尺寸变化
- `teardownContext()`：完全拆除 OpenGL 上下文

### MacWindowInfo

定义在 `MacWindowInfo.h` 中，包含平台相关的窗口信息：
- `NSView* fMainView`：主渲染视图

### DisplayParams

显示参数配置，包括：
- MSAA 采样数量
- 垂直同步开关
- 颜色空间等渲染配置

## 公共 API 函数

### MakeGaneshGLForMac

```cpp
namespace skwindow {
std::unique_ptr<WindowContext> MakeGaneshGLForMac(
    const MacWindowInfo& info,
    std::unique_ptr<const DisplayParams> params);
}
```

**功能：** 创建 macOS 平台的 Ganesh OpenGL 窗口上下文。

**参数：**
- `info`：包含 `NSView` 指针的 macOS 窗口信息
- `params`：显示参数配置（MSAA、垂直同步等）

**返回值：** 返回 `WindowContext` 的智能指针，如果创建失败则返回 `nullptr`

**使用场景：** 应用程序初始化时调用，为指定的 macOS 视图创建 OpenGL 渲染上下文

## 内部实现细节

### 上下文初始化流程

`onInitializeContext()` 方法实现了完整的初始化逻辑：

1. **像素格式创建**
   - 调用 `skwindow::GetGLPixelFormat()` 根据 MSAA 采样数量获取像素格式
   - 像素格式定义了模板位深度、采样数量等帧缓冲特性

2. **OpenGL 上下文创建**
   - 使用 `NSOpenGLContext` 创建上下文对象
   - 关联像素格式，不共享上下文（`shareContext:nil`）

3. **视图绑定**
   - 设置视图启用最佳分辨率模式（支持 Retina 显示）
   - 将上下文绑定到主视图

4. **垂直同步配置**
   - 根据 `DisplayParams` 设置交换间隔（0 或 1）

5. **上下文激活**
   - 调用 `makeCurrentContext` 激活上下文

6. **Ganesh 接口创建**
   - 调用 `GrGLInterfaces::MakeMac()` 创建平台特定的 GL 接口
   - 初始化模板缓冲和颜色缓冲

7. **查询帧缓冲配置**
   - 查询实际的模板位数和采样数量
   - 计算考虑缩放因子的窗口尺寸

### 缓冲区交换机制

`onSwapBuffers()` 实现：
```cpp
void GLWindowContext_mac::onSwapBuffers() {
    GrDirectContext* dContext = fSurface->recordingContext()->asDirectContext();
    dContext->flush(fSurface.get(), SkSurfaces::BackendSurfaceAccess::kPresent, {});
    [fGLContext flushBuffer];
}
```

1. 先调用 Ganesh 的 `flush()` 提交 GPU 命令
2. 再调用 NSOpenGL 的 `flushBuffer` 完成缓冲区交换

### 窗口尺寸调整

`resize()` 方法：
- 调用 `[fGLContext update]` 更新上下文到新的视图尺寸
- 调用基类的 `resize(0, 0)` 触发表面重建
- 基类会重新调用 `onInitializeContext()` 获取新尺寸

### 上下文销毁策略

`onDestroyContext()` 采用条件性销毁：
- 仅在 MSAA 采样数量变化时才完全拆除上下文
- 避免不必要的上下文重建开销

### 资源清理

`teardownContext()` 方法：
```cpp
void GLWindowContext_mac::teardownContext() {
    [NSOpenGLContext clearCurrentContext];
    [fPixelFormat release];
    fPixelFormat = nil;
    [fGLContext release];
    fGLContext = nil;
}
```

按照 macOS 内存管理规范释放 Objective-C 对象。

## 依赖关系

### 外部依赖

**Skia 核心组件：**
- `GrDirectContext`：Ganesh 渲染上下文，管理 GPU 资源
- `GrGLInterface`：OpenGL 函数指针抽象层
- `GrGLInterfaces::MakeMac()`：创建 macOS 平台的 GL 接口
- `GrGLUtil.h`：OpenGL 宏和工具函数

**平台工具组件：**
- `GLWindowContext`：跨平台 OpenGL 窗口上下文基类
- `MacWindowInfo`：macOS 窗口信息封装
- `MacWindowGLUtils`：macOS OpenGL 工具函数（如 `GetGLPixelFormat`、`GetBackingScaleFactor`）

**系统框架：**
- `Cocoa.framework`：macOS 窗口系统
- `OpenGL.framework`：OpenGL 图形接口
- `NSOpenGLContext`、`NSOpenGLPixelFormat`、`NSView` 等 Objective-C 类

### 被依赖关系

该模块被以下组件调用：
- 测试工具（如 viewer、skpbench）
- 示例应用程序
- 平台特定的窗口管理器

## 设计模式与设计决策

### 设计模式

1. **工厂模式**
   - `MakeGaneshGLForMac()` 作为工厂函数创建平台特定的实现
   - 返回基类指针，隐藏实现细节

2. **模板方法模式**
   - 继承 `GLWindowContext` 基类
   - 实现虚函数 `onInitializeContext()`、`onDestroyContext()`、`onSwapBuffers()`
   - 基类控制整体流程，子类提供平台实现

3. **RAII 模式**
   - 构造函数中初始化上下文
   - 析构函数中自动清理资源
   - 使用智能指针管理对象生命周期

### 设计决策

1. **使用匿名命名空间**
   - `GLWindowContext_mac` 类定义在匿名命名空间内
   - 实现信息隐藏，防止符号冲突

2. **禁用 NSOpenGL 弃用警告**
   ```cpp
   #pragma clang diagnostic push
   #pragma clang diagnostic ignored "-Wdeprecated-declarations"
   ```
   - NSOpenGL 在 macOS 新版本中已弃用（推荐使用 Metal）
   - 为了兼容性保留 OpenGL 支持

3. **条件性上下文销毁**
   - `onDestroyContext()` 仅在 MSAA 设置变化时销毁上下文
   - 避免频繁重建带来的性能损失

4. **Retina 显示支持**
   ```cpp
   [fMainView setWantsBestResolutionOpenGLSurface:YES];
   CGFloat backingScaleFactor = skwindow::GetBackingScaleFactor(fMainView);
   ```
   - 启用高分辨率渲染
   - 根据缩放因子计算实际像素尺寸

5. **resize 实现策略**
   - 总是传递 `(0, 0)` 给基类，强制重新查询尺寸
   - 因为 macOS 视图尺寸在 `update()` 后自动同步

## 性能考量

### 优化策略

1. **上下文复用**
   - 避免在 MSAA 设置未变化时重建上下文
   - 减少昂贵的 OpenGL 初始化开销

2. **垂直同步控制**
   - 支持通过 `DisplayParams` 禁用垂直同步
   - 在基准测试场景下可提高帧率

3. **缓冲区管理**
   - 明确的 flush 流程确保命令及时提交
   - 避免 GPU 空闲等待

### 潜在瓶颈

1. **上下文切换**
   - `makeCurrentContext` 在多窗口场景下可能成为瓶颈
   - macOS 上下文切换开销相对较高

2. **缓冲区交换**
   - 双缓冲交换会阻塞等待垂直同步（如果启用）
   - 可能限制帧率到显示器刷新率

3. **Retina 显示**
   - 高分辨率显示器的像素填充率需求更高
   - 实际渲染分辨率是视图尺寸的 2-3 倍

### 内存管理

- Objective-C 对象使用手动引用计数（MRR）
- 通过 `release` 显式释放对象
- 析构函数确保资源被正确清理

## 相关文件

**平台实现对比：**
- `tools/window/unix/GaneshGLWindowContext_unix.cpp`：Unix/Linux 平台实现
- `tools/window/win/GaneshGLWindowContext_win.cpp`：Windows 平台实现
- `tools/window/android/GaneshGLWindowContext_android.cpp`：Android 平台实现

**同平台其他后端：**
- `tools/window/mac/GaneshANGLEWindowContext_mac.mm`：使用 ANGLE 的 OpenGL 实现
- `tools/window/mac/GraphiteDawnMetalWindowContext_mac.mm`：使用 Graphite + Dawn + Metal
- `tools/window/mac/RasterWindowContext_mac.mm`：软件光栅化实现

**基类和工具：**
- `tools/window/GLWindowContext.h`：OpenGL 窗口上下文基类
- `tools/window/WindowContext.h`：窗口上下文抽象基类
- `tools/window/mac/MacWindowGLUtils.h`：macOS OpenGL 工具函数

**Ganesh 后端：**
- `src/gpu/ganesh/gl/GrGLGpu.h`：Ganesh OpenGL GPU 实现
- `include/gpu/ganesh/gl/GrGLInterface.h`：OpenGL 函数表接口
- `include/gpu/ganesh/gl/mac/GrGLMakeMacInterface.h`：macOS GL 接口创建函数

**应用示例：**
- `tools/viewer/Viewer.cpp`：主要的可视化测试工具
- `tools/sk_app/mac/main_mac.mm`：macOS 应用程序入口
