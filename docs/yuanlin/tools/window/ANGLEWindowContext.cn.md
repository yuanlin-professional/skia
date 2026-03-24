# ANGLEWindowContext

> 源文件: `tools/window/ANGLEWindowContext.h`, `tools/window/ANGLEWindowContext.cpp`

## 概述

ANGLEWindowContext 是 Skia 窗口系统中通过 ANGLE（Almost Native Graphics Layer Engine）提供 OpenGL ES 渲染能力的窗口上下文实现。ANGLE 将 OpenGL ES 调用转译为底层图形 API（如 Direct3D、Metal 或原生 OpenGL），使 Skia 能够在不同平台上通过统一的 GL ES 接口进行 Ganesh 渲染。

该类继承自 GLWindowContext，是一个抽象基类，平台特定子类需要实现 EGL 显示获取、原生窗口获取等方法。

## 架构位置

```
WindowContext (基类)
  +-- GLWindowContext (GL 窗口上下文基类)
       +-- ANGLEWindowContext  (ANGLE 抽象基类) <-- 本文件
            +-- 各平台 ANGLE 子类 (Windows/Linux/...)
```

## 主要类与结构体

### `ANGLEWindowContext`
- **命名空间**: `skwindow::internal`
- **继承**: `GLWindowContext`
- **性质**: 抽象基类
- **成员**:
  - `fDisplay`: EGL 显示连接
  - `fEGLContext`: EGL 渲染上下文
  - `fEGLSurface`: EGL 窗口表面

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `~ANGLEWindowContext()` | 析构函数，销毁上下文 |

### 子类需实现的纯虚方法

| 函数 | 说明 |
|------|------|
| `onGetEGLDisplay(eglGetPlatformDisplayEXT)` | 获取平台特定的 EGL 显示 |
| `onGetNativeWindow()` | 获取原生窗口句柄 |
| `onGetSize()` | 获取窗口尺寸 |
| `onGetStencilBits()` | 获取模板缓冲位数 |

## 内部实现细节

### 初始化流程（onInitializeContext）
1. 获取 `eglGetPlatformDisplayEXT` 扩展函数
2. 通过子类回调获取平台 EGL 显示
3. 初始化 EGL，配置 OpenGL ES 3.0 上下文属性（RGBA8888 + 可选 MSAA）
4. 创建 EGL 上下文和窗口表面
5. 设为当前上下文后，通过 `GrGLMakeAssembledInterface` 组装 GL 接口
6. 初始化 OpenGL 状态（清除模板和颜色缓冲）

### 销毁流程（onDestroyContext）
按 EGL 规范依次：解绑当前上下文 -> 销毁 EGL 上下文 -> 销毁 EGL 表面 -> 终止 EGL 显示。

### 缓冲交换
调用 `eglSwapBuffers` 完成前后缓冲切换。

## 依赖关系

- **EGL**: `<EGL/egl.h>`, `<EGL/eglext.h>`
- **Ganesh GL**: `GrGLAssembleInterface`, `GrGLDefines`
- **工具**: `GLWindowContext`, `DisplayParams`

## 设计模式与设计决策

1. **模板方法模式**: `onInitializeContext` 定义 EGL 初始化骨架，子类提供平台特定的显示和窗口
2. **仅支持 ES 3.0**: 当前硬编码为 OpenGL ES 3.0，注释明确说明这一限制
3. **ANGLE 扩展依赖**: 要求 `eglGetPlatformDisplayEXT` 扩展可用

## 性能考量

- ANGLE 引入了 API 转译层，相比原生 Vulkan/Metal 有额外开销
- MSAA 通过 EGL 配置属性在驱动层实现

## 相关文件

- `tools/window/GLWindowContext.h` - GL 窗口上下文基类
- `include/gpu/ganesh/gl/GrGLAssembleInterface.h` - GL 接口组装
- `tools/window/DisplayParams.h` - 显示参数定义
