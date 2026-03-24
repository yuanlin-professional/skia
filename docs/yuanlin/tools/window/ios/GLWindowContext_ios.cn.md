# GLWindowContext_ios - iOS OpenGL ES 窗口上下文

> 源文件: `tools/window/ios/GLWindowContext_ios.mm`

## 概述

`GLWindowContext_ios` 实现了 iOS 平台上使用 OpenGL ES 3.0 和 Ganesh 渲染后端的窗口上下文。它通过 `EAGLContext`（Apple 的 OpenGL ES 上下文管理类）和 `CAEAGLLayer` 创建 GL 渲染管线，手动管理帧缓冲对象（FBO）和渲染缓冲对象（RBO）进行屏幕渲染。

## 架构位置

- 继承自 `skwindow::internal::GLWindowContext`
- 由工厂函数 `MakeGLForIOS` 创建
- 使用 iOS 特有的 `EAGLContext` 和 `CAEAGLLayer`

## 主要类与结构体

### `GLView`（Objective-C）
- 继承自 `MainView`，覆盖 `+layerClass` 返回 `CAEAGLLayer`

### `GLWindowContext_ios`（匿名命名空间）
- 继承自 `GLWindowContext`
- 成员：`fWindow`, `fViewController`, `fGLView`, `fGLContext` (EAGLContext), `fFramebuffer`, `fRenderbuffer`

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeGLForIOS(IOSWindowInfo&, params)` | 工厂函数 |

## 内部实现细节

### 初始化流程 (`onInitializeContext`)
1. 创建 `GLView` 并添加到视图层级
2. 创建 OpenGL ES 3.0 上下文（`kEAGLRenderingAPIOpenGLES3`）
3. 配置 `CAEAGLLayer`：非保留后备、RGBA8 颜色格式、不透明、左上角对齐
4. 创建并绑定 FBO 和 RBO
5. 将 RBO 连接为 FBO 的颜色附件
6. 通过 `renderbufferStorage:fromDrawable:` 将 RBO 关联到 EAGLLayer
7. 验证帧缓冲完整性
8. 设置初始 GL 状态（清除模板和颜色缓冲区）
9. 硬编码模板位为 8、采样数为 1
10. 返回 `GrGLInterfaces::MakeIOS()` GL 接口

### 帧交换 (`onSwapBuffers`)
通过 `[fGLContext presentRenderbuffer:GL_RENDERBUFFER]` 呈现渲染缓冲区内容到屏幕。

### 资源清理 (`onDestroyContext`)
删除 FBO/RBO，重置 EAGLContext，释放 GL 上下文。

## 依赖关系

- `include/gpu/ganesh/gl/GrGLInterface.h` - GL 接口
- `include/gpu/ganesh/gl/ios/GrGLMakeIOSInterface.h` - iOS GL 接口创建
- `tools/window/GLWindowContext.h` - GL 基类
- `<OpenGLES/ES3/gl.h>` - OpenGL ES 3.0
- `<UIKit/UIKit.h>` - UIKit

## 设计模式与设计决策

- **手动 FBO 管理**: iOS 不提供默认帧缓冲区，需要手动创建 FBO/RBO 并关联到 CAEAGLLayer
- **OpenGL ES 3.0**: 选择 ES 3.0 以获得更完整的 GL 功能集
- **MSAA 未实现**: 采样数硬编码为 1，留有 TODO 注释
- **Objective-C 交互**: 通过 `renderbufferStorage:fromDrawable:` 将 GL 和 UIKit 层桥接

## 性能考量

- 手动 FBO/RBO 管理提供了对渲染管线的精确控制
- `presentRenderbuffer` 是 iOS 上标准的 GL 呈现方式
- 不支持 MSAA 会导致锯齿，但简化了缓冲区管理
- OpenGL ES 在较新的 iOS 版本中已被弃用，建议使用 Metal

## 相关文件

- `tools/window/ios/RasterWindowContext_ios.mm` - 基于 GL 的光栅化实现
- `tools/window/ios/MetalWindowContext_ios.mm` - Metal 替代方案
- `tools/window/GLWindowContext.h` - GL 基类
- `tools/window/ios/WindowContextFactory_ios.h` - iOS 工厂声明
