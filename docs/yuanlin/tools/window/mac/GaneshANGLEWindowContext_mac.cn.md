# GaneshANGLEWindowContext_mac

> 源文件
> - tools/window/mac/GaneshANGLEWindowContext_mac.h
> - tools/window/mac/GaneshANGLEWindowContext_mac.mm

## 概述

`GaneshANGLEWindowContext_mac` 是 Skia 在 macOS 平台上使用 ANGLE（Almost Native Graphics Layer Engine）实现的窗口上下文。ANGLE 是一个将 OpenGL ES API 转换为底层平台图形 API 的转换层，在 macOS 上将 OpenGL ES 调用转换为 Metal 调用。该模块使 Skia 能够通过 ANGLE + Metal 的组合获得更好的性能和稳定性，同时保持 OpenGL ES 的 API 接口。

相比直接使用 NSOpenGL（已被 Apple 废弃），ANGLE 方案通过 Metal 后端提供了更现代化的渲染路径，同时保持了跨平台的 OpenGL ES API 兼容性。该实现主要用于测试和验证 ANGLE 在 macOS 上的集成效果。

## 架构位置

该模块位于 Skia 工具层的窗口系统实现中：

```
skia/
├── tools/
│   └── window/
│       ├── ANGLEWindowContext.h           # ANGLE 窗口上下文基类
│       └── mac/
│           ├── GaneshANGLEWindowContext_mac.h   # 本模块头文件
│           ├── GaneshANGLEWindowContext_mac.mm  # 本模块实现
│           ├── GaneshGLWindowContext_mac.mm     # 原生 OpenGL 实现
│           ├── MacWindowInfo.h           # macOS 窗口信息
│           └── MacWindowGLUtils.h        # OpenGL 工具函数
├── include/
│   └── gpu/
│       └── ganesh/
│           └── gl/
│               └── GrGLInterface.h       # OpenGL 接口抽象
└── third_party/
    └── externals/
        └── angle/                        # ANGLE 库
```

该模块的架构角色：
- **向上**：为测试工具提供基于 ANGLE 的渲染能力
- **向下**：通过 EGL 调用 ANGLE，ANGLE 再调用 Metal
- **横向**：与原生 OpenGL 实现、Graphite 实现并列

## 主要类与结构体

### ANGLEWindowContext_mac

匿名命名空间内的私有实现类，继承自 `ANGLEWindowContext`。

**主要成员变量：**
- `NSView* fMainView`：macOS 主视图对象，用于获取 CALayer 作为渲染表面

**主要成员函数：**

```cpp
ANGLEWindowContext_mac(const MacWindowInfo&, std::unique_ptr<const DisplayParams>)
```
构造函数，接收窗口信息和显示参数，自动初始化上下文。

```cpp
EGLDisplay onGetEGLDisplay(PFNEGLGETPLATFORMDISPLAYEXTPROC eglGetPlatformDisplayEXT) const override
```
获取 EGL 显示对象，配置 ANGLE 使用 Metal 后端。

```cpp
NativeWindowType onGetNativeWindow() const override
```
获取原生窗口句柄，返回 NSView 的 CALayer。

```cpp
SkISize onGetSize() const override
```
获取窗口尺寸，考虑 Retina 显示的缩放因子。

```cpp
int onGetStencilBits() const override
```
获取模板缓冲位深度。

### MacWindowInfo

定义在 `MacWindowInfo.h` 中：
- `NSView* fMainView`：主渲染视图

### DisplayParams

显示参数配置：
- MSAA 采样数量
- 颜色空间
- 垂直同步等选项

## 公共 API 函数

### MakeGaneshANGLEForMac

```cpp
namespace skwindow {
std::unique_ptr<WindowContext> MakeGaneshANGLEForMac(
    const MacWindowInfo& info,
    std::unique_ptr<const DisplayParams> params);
}
```

**功能：** 创建使用 ANGLE 的 macOS Ganesh 窗口上下文。

**参数：**
- `info`：包含 `NSView` 指针的窗口信息
- `params`：显示参数配置

**返回值：** 成功返回 `WindowContext` 智能指针，失败返回 `nullptr`

**使用场景：**
- 在需要通过 ANGLE 使用 Metal 后端的场景
- 测试 ANGLE 集成的正确性
- 验证跨平台 OpenGL ES 代码

## 内部实现细节

### EGL 显示初始化

`onGetEGLDisplay()` 方法配置 ANGLE 使用 Metal 后端：

```cpp
EGLDisplay ANGLEWindowContext_mac::onGetEGLDisplay(
        PFNEGLGETPLATFORMDISPLAYEXTPROC eglGetPlatformDisplayEXT) const {
    static constexpr EGLint kType = EGL_PLATFORM_ANGLE_TYPE_METAL_ANGLE;
    static constexpr EGLint attribs[] = {EGL_PLATFORM_ANGLE_TYPE_ANGLE, kType, EGL_NONE};
    return eglGetPlatformDisplayEXT(
            EGL_PLATFORM_ANGLE_ANGLE,
            reinterpret_cast<void*>(EGL_DEFAULT_DISPLAY),
            attribs);
}
```

**关键参数：**
- `EGL_PLATFORM_ANGLE_ANGLE`：指定使用 ANGLE 平台
- `EGL_PLATFORM_ANGLE_TYPE_METAL_ANGLE`：指定 ANGLE 使用 Metal 作为底层实现
- `EGL_DEFAULT_DISPLAY`：使用默认显示设备

这种配置使得：
1. EGL API 调用被 ANGLE 拦截
2. ANGLE 将 OpenGL ES 命令转换为 Metal 命令
3. Metal 在 GPU 上执行实际渲染

### 原生窗口获取

`onGetNativeWindow()` 方法返回 CALayer：

```cpp
NativeWindowType ANGLEWindowContext_mac::onGetNativeWindow() const {
    [fMainView setWantsLayer:YES];
    return fMainView.layer;
}
```

**实现细节：**
- 设置视图启用 layer-backed 模式
- 返回 NSView 的 `CALayer` 对象
- ANGLE 将 Metal 渲染结果输出到此 layer

这种设计使得：
- 可以利用 Core Animation 的硬件加速
- Metal 可以直接渲染到 CALayer
- 与 macOS 窗口系统无缝集成

### 尺寸计算

`onGetSize()` 考虑 Retina 显示：

```cpp
SkISize ANGLEWindowContext_mac::onGetSize() const {
    CGFloat backingScaleFactor = skwindow::GetBackingScaleFactor(fMainView);
    return SkISize::Make(fMainView.bounds.size.width * backingScaleFactor,
                         fMainView.bounds.size.height * backingScaleFactor);
}
```

- 获取视图的缩放因子（Retina 屏幕通常为 2.0 或 3.0）
- 返回实际像素尺寸而非逻辑尺寸
- 确保渲染清晰度

### 模板位查询

`onGetStencilBits()` 通过 OpenGL 像素格式查询：

```cpp
int ANGLEWindowContext_mac::onGetStencilBits() const {
    GLint stencilBits;
    NSOpenGLPixelFormat* pixelFormat =
            skwindow::GetGLPixelFormat(fDisplayParams->msaaSampleCount());
    [pixelFormat getValues:&stencilBits
                  forAttribute:NSOpenGLPFAStencilSize
              forVirtualScreen:0];
    return stencilBits;
}
```

虽然使用 ANGLE，但模板位配置仍然基于 OpenGL 像素格式，确保配置一致性。

### 初始化流程

构造函数的执行顺序：

1. 调用基类 `ANGLEWindowContext` 构造函数
2. 保存 `fMainView` 成员
3. 调用 `initializeContext()`
4. 基类 `initializeContext()` 会依次调用：
   - `onGetEGLDisplay()` 获取 EGL 显示
   - `onGetNativeWindow()` 获取原生窗口
   - 创建 EGL 表面和上下文
   - 创建 Ganesh GrDirectContext
   - `onGetSize()` 获取窗口尺寸
   - 创建渲染表面

## 依赖关系

### 外部依赖

**Skia 组件：**
- `ANGLEWindowContext`：ANGLE 窗口上下文基类，处理 EGL 相关逻辑
- `WindowContext`：窗口上下文抽象基类
- `MacWindowGLUtils`：macOS OpenGL 工具函数
  - `GetGLPixelFormat()`：获取像素格式
  - `GetBackingScaleFactor()`：获取缩放因子

**第三方库：**
- ANGLE：OpenGL ES 到 Metal 的转换层
  - EGL API：窗口系统绑定
  - OpenGL ES API：渲染接口

**系统框架：**
- Cocoa.framework：macOS 窗口系统
- Metal.framework：通过 ANGLE 间接使用
- QuartzCore.framework：CALayer 支持

### 被依赖关系

该模块被以下组件使用：
- 测试工具（viewer、dm）
- ANGLE 集成测试
- 性能基准测试

## 设计模式与设计决策

### 设计模式

1. **工厂模式**
   - `MakeGaneshANGLEForMac()` 作为工厂函数
   - 隐藏实现细节，返回基类指针

2. **模板方法模式**
   - 继承 `ANGLEWindowContext` 基类
   - 实现平台相关的虚函数
   - 基类控制初始化流程

3. **桥接模式**
   - ANGLE 作为桥接层连接 OpenGL ES 和 Metal
   - 解耦渲染 API 和底层实现

### 设计决策

1. **选择 Metal 后端**
   ```cpp
   static constexpr EGLint kType = EGL_PLATFORM_ANGLE_TYPE_METAL_ANGLE;
   ```
   - Metal 是 Apple 推荐的现代图形 API
   - NSOpenGL 已被标记为废弃
   - Metal 性能更好，支持更新

2. **使用 CALayer 而非 NSView**
   - CALayer 可以被 Metal 直接渲染
   - 硬件加速合成
   - 更好的性能

3. **复用 OpenGL 像素格式**
   - 保持与原生 OpenGL 实现的一致性
   - 简化配置管理
   - 虽然后端是 Metal，但前端接口仍是 OpenGL ES

4. **匿名命名空间**
   - 隐藏实现类 `ANGLEWindowContext_mac`
   - 避免符号冲突
   - 强制通过工厂函数创建

5. **自动初始化**
   - 构造函数中自动调用 `initializeContext()`
   - 简化使用，避免忘记初始化
   - 可以通过 `isValid()` 检查初始化结果

## 性能考量

### 优势

1. **Metal 后端性能**
   - Metal 是 Apple 优化的原生 API
   - 比废弃的 NSOpenGL 更快
   - CPU 开销更低

2. **CALayer 硬件合成**
   - 利用 Core Animation 加速
   - 减少 CPU 干预
   - 高效的窗口合成

3. **ANGLE 优化**
   - ANGLE 持续优化 OpenGL ES 到 Metal 的转换
   - 减少不必要的状态切换
   - 批处理优化

### 潜在开销

1. **API 转换成本**
   - OpenGL ES 到 Metal 的转换有一定开销
   - 状态跟踪和映射需要 CPU 时间
   - 比直接使用 Metal API 略慢

2. **内存复制**
   - EGL 表面可能涉及额外的缓冲区复制
   - 取决于 ANGLE 的实现细节

3. **兼容性层开销**
   - 需要加载和维护 ANGLE 库
   - 增加二进制体积

### 性能建议

- 对于生产环境，考虑直接使用 Graphite + Metal
- ANGLE 主要用于测试和跨平台兼容性
- 在需要 OpenGL ES API 兼容时使用

## 相关文件

**同平台其他实现：**
- `tools/window/mac/GaneshGLWindowContext_mac.mm`：原生 OpenGL 实现
- `tools/window/mac/GraphiteDawnMetalWindowContext_mac.mm`：Graphite + Dawn + Metal
- `tools/window/mac/RasterWindowContext_mac.mm`：软件光栅化

**基类和工具：**
- `tools/window/ANGLEWindowContext.h`：ANGLE 窗口上下文基类
- `tools/window/WindowContext.h`：窗口上下文抽象
- `tools/window/mac/MacWindowGLUtils.h`：macOS OpenGL 工具

**其他平台 ANGLE 实现：**
- `tools/window/win/GaneshANGLEWindowContext_win.cpp`：Windows ANGLE 实现
- `tools/window/unix/GaneshANGLEWindowContext_unix.cpp`：Unix/Linux ANGLE 实现

**ANGLE 相关：**
- `third_party/externals/angle/`：ANGLE 源代码
- EGL 头文件和库

**测试和应用：**
- `tools/viewer/Viewer.cpp`：可视化测试工具
- `dm/DM.cpp`：测试框架
- `tools/sk_app/`：应用程序框架
