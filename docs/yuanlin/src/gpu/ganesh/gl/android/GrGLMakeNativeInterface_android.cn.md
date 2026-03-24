# GrGLMakeNativeInterface (Android)

> 源文件
> - src/gpu/ganesh/gl/android/GrGLMakeNativeInterface_android.cpp

## 概述

Android 平台的 OpenGL ES 接口创建实现。Android 使用 EGL 作为 OpenGL ES 的平台接口层，因此该实现直接包含 EGL 相关的实现文件。这是一个极简的文件，通过包含其他源文件来复用 EGL 实现。

## 实现方式

### 源文件包含

```cpp
#include "src/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.cpp"
#include "src/gpu/ganesh/gl/egl/GrGLMakeNativeInterface_egl.cpp"
```

**工作原理**：
- 直接包含 `.cpp` 文件而非头文件
- 将 EGL 实现编译到 Android 构建中
- 避免代码重复

## 内部实现细节

### 代码复用策略

Android 不需要独立实现，因为：
- Android 标准使用 EGL
- EGL 实现已经完全满足需求
- 无需 Android 特定的调整

### 包含 `.cpp` 文件的原因

通常不推荐包含 `.cpp` 文件，但这里这样做是因为：
1. **避免重复编译**：如果 EGL 文件单独编译，需要在构建系统中特殊处理
2. **简化构建**：Android 构建只需编译这一个文件
3. **代码一致性**：确保 Android 使用与其他 EGL 平台完全相同的实现

### 包含的文件功能

**GrGLMakeEGLInterface.cpp**：
- 实现 `GrGLMakeEGLInterface()` 函数
- 使用 `eglGetProcAddress` 加载 OpenGL ES 函数
- 组装函数指针表

**GrGLMakeNativeInterface_egl.cpp**：
- 实现 `GrGLMakeNativeInterface()` 函数
- 转发到 `GrGLMakeEGLInterface()`

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| EGL 实现文件 | 提供实际功能 |
| `GrGLInterface` | GL 函数指针表（间接依赖） |
| Android EGL 库 | 系统提供的 EGL 实现 |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| Android 应用程序 | 初始化 Skia OpenGL ES 支持 |
| `GrDirectContext` | 创建 GL 上下文 |
| Android 游戏/图形应用 | 硬件加速渲染 |

## 设计模式与设计决策

### 代码复用

通过包含 EGL 实现避免：
- 维护重复代码
- 平台差异导致的不一致
- 额外的测试负担

### 构建系统集成

这种方式简化了构建配置：
- CMake/GN 只需编译一个文件
- 自动获得 EGL 实现
- 无需条件编译逻辑

## 性能考量

### 与直接 EGL 实现相同

性能特性：
- 无额外开销
- 编译后与直接编译 EGL 文件相同
- 函数可以跨文件内联优化

## Android 特定考虑

### Android NDK

Android 应用使用 NDK（Native Development Kit）：
- 提供标准 EGL API
- OpenGL ES 2.0/3.0/3.1/3.2 支持
- 跨设备兼容性

### 系统 EGL 实现

Android 系统提供：
- `libEGL.so`：EGL 库
- `libGLESv2.so`：OpenGL ES 2.0+ 实现
- 驱动特定优化

### API 级别

EGL 和 OpenGL ES 支持取决于 Android API 级别：
- API 9+：OpenGL ES 2.0
- API 18+：OpenGL ES 3.0
- API 21+：OpenGL ES 3.1
- API 24+：OpenGL ES 3.2

### 扩展支持

通过 `eglGetProcAddress` 查询：
- 标准扩展（如压缩纹理）
- 厂商扩展（不同 GPU 差异）
- 运行时检测并适配

## 构建系统考虑

### 编译单元

这种方式将三个逻辑文件合并为一个编译单元：
- 减少编译时间（少一次头文件解析）
- 增加内联优化机会
- 简化依赖追踪

### 符号可见性

包含的文件中的静态函数/变量：
- 只在该编译单元内可见
- 避免符号冲突
- 优化器可以更激进地优化

## 相关文件

| 文件路径 | 关系说明 |
|----------|----------|
| `src/gpu/ganesh/gl/egl/GrGLMakeEGLInterface.cpp` | 被包含的 EGL 实现 |
| `src/gpu/ganesh/gl/egl/GrGLMakeNativeInterface_egl.cpp` | 被包含的平台入口 |
| `include/gpu/ganesh/gl/GrGLInterface.h` | GL 接口定义 |
| Android NDK EGL 头文件 | 系统 EGL API |
