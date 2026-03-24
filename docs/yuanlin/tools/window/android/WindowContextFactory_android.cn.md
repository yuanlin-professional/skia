# WindowContextFactory_android

> 源文件: tools/window/android/WindowContextFactory_android.h

## 概述

`WindowContextFactory_android.h` 是 Skia 在 Android 平台上的窗口上下文工厂接口头文件。该文件定义了一组工厂函数，用于创建不同渲染后端的窗口上下文，包括 Vulkan（Ganesh 和 Graphite）、Dawn（Graphite）、OpenGL ES（Ganesh）和软件光栅化。

该接口是 Android 平台上所有窗口上下文的统一入口点，为上层应用提供了简洁的 API 来创建各种类型的渲染上下文，隐藏了底层平台特定的初始化细节。

## 架构位置

该文件位于 Skia 工具层的 Android 平台窗口实现中：

```
skia/
  tools/
    window/
      android/
        WindowContextFactory_android.h          # 本文件（工厂接口）
        VulkanWindowContext_android.cpp         # Ganesh Vulkan 实现
        GraphiteVulkanWindowContext_android.cpp # Graphite Vulkan 实现
        GraphiteDawnWindowContext_android.cpp   # Graphite Dawn 实现
        GLWindowContext_android.cpp             # OpenGL ES 实现
        RasterWindowContext_android.cpp         # 软件光栅化实现
      WindowContext.h                           # 窗口上下文接口
      DisplayParams.h                           # 显示参数配置
    sk_app/
      Window.h                                  # 窗口抽象
```

在 Skia 架构层次：
- **工厂层**: 提供统一的创建接口
- **平台抽象层**: 隔离平台特定实现
- **应用层接口**: 上层应用的主要入口点

## 主要类与结构体

该头文件不定义类，仅声明工厂函数。所有函数都在 `skwindow` 命名空间中。

### 前置声明

```cpp
class WindowContext;
class DisplayParams;
```

这两个类的完整定义在其他头文件中，这里使用前置声明减少编译依赖。

## 公共 API 函数

### MakeVulkanForAndroid

```cpp
std::unique_ptr<WindowContext> MakeVulkanForAndroid(
    ANativeWindow*,
    std::unique_ptr<const DisplayParams>);
```

**功能**: 创建 Ganesh Vulkan 窗口上下文。

**参数**:
- `ANativeWindow*`: Android 原生窗口句柄
- `std::unique_ptr<const DisplayParams>`: 显示参数配置

**返回值**:
- `WindowContext` 智能指针，失败返回 `nullptr`

**使用场景**:
- 使用 Ganesh 渲染引擎的 Vulkan 后端
- 需要成熟稳定的 Vulkan 实现

### MakeGraphiteVulkanForAndroid

```cpp
std::unique_ptr<WindowContext> MakeGraphiteVulkanForAndroid(
    ANativeWindow*,
    std::unique_ptr<const DisplayParams>);
```

**功能**: 创建 Graphite Vulkan 窗口上下文。

**参数**: 与 `MakeVulkanForAndroid` 相同

**返回值**: `WindowContext` 智能指针

**使用场景**:
- 使用新一代 Graphite 渲染引擎
- 需要更好的多线程性能
- 追求更高的 GPU 利用率

### MakeGraphiteDawnForAndroid

```cpp
std::unique_ptr<WindowContext> MakeGraphiteDawnForAndroid(
    ANativeWindow*,
    std::unique_ptr<const DisplayParams>,
    sk_app::Window::BackendType backendType);
```

**功能**: 创建 Graphite Dawn 窗口上下文。

**参数**:
- `ANativeWindow*`: Android 原生窗口句柄
- `std::unique_ptr<const DisplayParams>`: 显示参数配置
- `sk_app::Window::BackendType`: Dawn 后端类型
  - `kGraphiteDawnVulkan`: Dawn 的 Vulkan 后端
  - `kGraphiteDawnOpenGLES`: Dawn 的 OpenGL ES 后端

**返回值**: `WindowContext` 智能指针

**使用场景**:
- 使用 WebGPU Dawn 作为抽象层
- 需要跨平台的统一 API
- 未来迁移到 WebGPU

### MakeGLForAndroid

```cpp
std::unique_ptr<WindowContext> MakeGLForAndroid(
    ANativeWindow*,
    std::unique_ptr<const DisplayParams>);
```

**功能**: 创建 Ganesh OpenGL ES 窗口上下文。

**参数**: 与 `MakeVulkanForAndroid` 相同

**返回值**: `WindowContext` 智能指针

**使用场景**:
- 使用 Ganesh 渲染引擎的 OpenGL ES 后端
- 兼容旧设备（不支持 Vulkan）
- 调试和开发（OpenGL 工具链更成熟）

### MakeRasterForAndroid

```cpp
std::unique_ptr<WindowContext> MakeRasterForAndroid(
    ANativeWindow*,
    std::unique_ptr<const DisplayParams>);
```

**功能**: 创建软件光栅化窗口上下文。

**参数**: 与 `MakeVulkanForAndroid` 相同

**返回值**: `WindowContext` 智能指针

**使用场景**:
- 不支持 GPU 的设备
- 调试和测试
- 像素精确控制

## 内部实现细节

### 头文件保护

```cpp
#ifndef WindowContextFactory_android_DEFINED
#define WindowContextFactory_android_DEFINED
```

使用传统的宏保护防止重复包含。

### 依赖项

```cpp
#include <android/native_window_jni.h>  // ANativeWindow 定义
#include <memory>                       // std::unique_ptr
#include "tools/sk_app/Window.h"        // BackendType 枚举
```

**最小化依赖**: 仅包含必要的头文件，使用前置声明减少编译依赖。

### 命名空间

```cpp
namespace skwindow {
    // 所有工厂函数
}
```

所有工厂函数都在 `skwindow` 命名空间中，避免符号冲突。

### 参数传递约定

1. **窗口句柄**: 裸指针传递（生命周期由外部管理）
2. **显示参数**: `unique_ptr` 移动语义（转移所有权）
3. **返回值**: `unique_ptr` 传递所有权给调用者

## 依赖关系

**直接依赖**:
- `<android/native_window_jni.h>`: Android NDK 的窗口 API
- `<memory>`: C++ 标准库智能指针
- `tools/sk_app/Window.h`: 窗口抽象和后端类型枚举

**间接依赖**:
- `tools/window/WindowContext.h`: 窗口上下文接口（前置声明）
- `tools/window/DisplayParams.h`: 显示参数配置（前置声明）

**实现依赖** (不在头文件中):
- 各个 `.cpp` 实现文件（Vulkan、Dawn、GL、Raster）

**依赖图**:
```
应用代码
    ↓
WindowContextFactory_android.h (本文件)
    ↓
实现文件 (.cpp)
    ↓
平台特定 API (Vulkan/EGL/ANativeWindow)
```

## 设计模式与设计决策

### 设计模式

1. **抽象工厂模式**: 提供创建相关对象族的接口
2. **工厂方法模式**: 每个函数是一个工厂方法
3. **策略模式**: 不同渲染后端作为不同策略

### 设计决策

**1. 函数级工厂而非类**:
```cpp
// 选择函数工厂
std::unique_ptr<WindowContext> MakeGLForAndroid(...);

// 而非类工厂
class WindowContextFactory {
    virtual std::unique_ptr<WindowContext> create(...) = 0;
};
```
- 更简单直接
- 无需虚函数开销
- 编译期选择后端

**2. 统一的参数签名**:
- 所有函数（除 Dawn）接受相同参数
- 简化客户端代码
- 便于封装和切换后端

**3. 智能指针所有权转移**:
```cpp
std::unique_ptr<const DisplayParams> params  // 转移所有权
```
- 避免拷贝开销
- 明确所有权语义
- 防止悬空引用

**4. 返回空指针表示失败**:
- 不抛出异常，符合 Skia 风格
- 客户端必须检查返回值
- 简单明了的错误处理

**5. 平台特定头文件**:
- 每个平台有自己的工厂头文件
- 避免跨平台符号冲突
- 清晰的平台隔离

**6. 前置声明优化**:
```cpp
class WindowContext;  // 而非 #include "WindowContext.h"
```
- 减少编译依赖
- 加快编译速度
- 减少头文件包含链

### 后端选择决策表

| 后端 | 渲染引擎 | 性能 | 兼容性 | 推荐场景 |
|------|---------|------|--------|---------|
| Vulkan | Ganesh | 高 | 中 | 成熟应用 |
| GraphiteVulkan | Graphite | 极高 | 中 | 高性能应用 |
| Dawn | Graphite | 高 | 中高 | 跨平台应用 |
| OpenGL ES | Ganesh | 中高 | 极高 | 兼容性优先 |
| Raster | CPU | 低 | 100% | 调试/低端设备 |

## 性能考量

### 工厂函数开销

- **创建开销**: 一次性，仅在初始化时调用
- **内联可能性**: 编译器可内联简单工厂
- **虚函数**: 无虚函数开销（非类工厂）

### 智能指针开销

```cpp
std::unique_ptr<WindowContext>
```
- **内存开销**: 与裸指针相同（零开销抽象）
- **性能开销**: 无（编译期优化）
- **安全性**: 自动内存管理

### 后端选择性能影响

| 后端 | 初始化时间 | 帧率 | 功耗 |
|------|-----------|------|------|
| Vulkan | 中 | 极高 | 中 |
| Dawn | 高 | 高 | 中 |
| OpenGL ES | 低 | 高 | 中 |
| Raster | 极低 | 低 | 低 |

## 相关文件

### 实现文件（同目录）
- `tools/window/android/VulkanWindowContext_android.cpp`: Ganesh Vulkan 实现
- `tools/window/android/GraphiteVulkanWindowContext_android.cpp`: Graphite Vulkan 实现
- `tools/window/android/GraphiteDawnWindowContext_android.cpp`: Graphite Dawn 实现
- `tools/window/android/GLWindowContext_android.cpp`: OpenGL ES 实现
- `tools/window/android/RasterWindowContext_android.cpp`: 软件光栅化实现

### 接口定义
- `tools/window/WindowContext.h`: 窗口上下文接口
- `tools/window/DisplayParams.h`: 显示参数配置
- `tools/sk_app/Window.h`: 窗口抽象和后端枚举

### 其他平台工厂
- `tools/window/win/WindowContextFactory_win.h`: Windows 工厂
- `tools/window/mac/WindowContextFactory_mac.h`: macOS 工厂
- `tools/window/unix/WindowContextFactory_unix.h`: Linux 工厂

### 基类实现
- `tools/window/VulkanWindowContext.h`: Ganesh Vulkan 基类
- `tools/window/GraphiteNativeVulkanWindowContext.h`: Graphite Vulkan 基类
- `tools/window/GraphiteDawnWindowContext.h`: Graphite Dawn 基类
- `tools/window/GLWindowContext.h`: OpenGL 基类
- `tools/window/RasterWindowContext.h`: 软件渲染基类

### 使用示例（推测）
```cpp
// 应用代码示例
#include "tools/window/android/WindowContextFactory_android.h"

auto params = std::make_unique<DisplayParams>();
auto ctx = skwindow::MakeVulkanForAndroid(nativeWindow, std::move(params));
if (!ctx) {
    // 失败处理
}
// 使用 ctx 进行渲染
```
