# GLWindowContext - OpenGL 窗口上下文基类

> 源文件:
> - [tools/window/GLWindowContext.h](../../../tools/window/GLWindowContext.h)
> - [tools/window/GLWindowContext.cpp](../../../tools/window/GLWindowContext.cpp)

## 概述

GLWindowContext 是所有 OpenGL 窗口上下文的抽象基类，提供了通用的 Ganesh GL 上下文初始化、Surface 管理和参数切换逻辑。各平台（macOS、Linux、iOS、Android）的 GL 窗口上下文通过继承此类并实现平台特定的 `onInitializeContext()` / `onDestroyContext()` 来完成集成。

## 架构位置

位于 `tools/window/` 目录下，是窗口上下文层次结构的中间层。继承自 `WindowContext`，被各平台的 GL 窗口上下文实现继承。

## 主要类与结构体

### `GLWindowContext`
继承 `WindowContext`，管理 GrGLInterface 和 SkSurface。
- `fBackendContext` - GL 接口（sk_sp<GrGLInterface>）
- `fSurface` - 后缓冲 Surface

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `getBackbufferSurface()` | 获取后缓冲 Surface（延迟创建） |
| `isValid()` | 检查 GL 上下文是否有效 |
| `resize(w, h)` | 调整大小（销毁并重建上下文） |
| `setDisplayParams(params)` | 更新显示参数（销毁并重建上下文） |

## 内部实现细节

- **MSAA 降级**：如果创建 GrDirectContext 失败且 MSAA > 1，自动将采样数减半并递归重试。
- **后缓冲 Surface**：延迟创建，通过 `glGetIntegerv(GL_FRAMEBUFFER_BINDING)` 获取当前 FBO，包装为 `GrBackendRenderTarget`。
- **Surface 方向**：使用 `kBottomLeft_GrSurfaceOrigin`（GL 默认原点在左下）。
- **上下文销毁**：调用 `abandonContext()` 处理可能存在的外部引用（如 Lua 绑定）。
- **MSAA 向上取整**：构造时通过 `DisplayParamsBuilder::roundUpMSAA()` 处理参数。

## 依赖关系

- **Ganesh GL**：GrGLInterface、GrGLDirectContext、GrBackendRenderTarget
- **Skia 核心**：SkSurface、SkCanvas
- **窗口框架**：WindowContext 基类、DisplayParams

## 设计模式与设计决策

- **模板方法模式**：`initializeContext()` 调用子类的 `onInitializeContext()`，`destroyContext()` 调用 `onDestroyContext()`。
- **MSAA 优雅降级**：自动降低采样数直到成功创建上下文。
- **延迟 Surface 创建**：避免在无效上下文上创建 Surface。

## 性能考量

- `resize` 和 `setDisplayParams` 都会完全销毁并重建上下文，开销较大但执行频率低。
- Surface 缓存，仅在首次调用 `getBackbufferSurface()` 时创建。

## 相关文件

- `tools/window/WindowContext.h` - 窗口上下文基类
- `tools/window/mac/GaneshGLWindowContext_mac.h` - macOS GL 实现
- `tools/window/unix/GaneshGLWindowContext_unix.h` - Linux GL 实现
