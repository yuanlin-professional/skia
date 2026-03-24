# GraphiteDawnWindowContext

> 源文件: `tools/window/GraphiteDawnWindowContext.h`, `tools/window/GraphiteDawnWindowContext.cpp`

## 概述

GraphiteDawnWindowContext 是 Skia 窗口系统中基于 Graphite 后端与 Dawn（WebGPU 实现）的窗口渲染上下文。它管理 Dawn 实例、设备、队列和 wgpu::Surface，为支持 WebGPU 的平台提供 Graphite GPU 加速渲染能力。

Dawn 是 Google 的 WebGPU 原生实现，支持多种后端（Vulkan、Metal、D3D12、OpenGL），使 Skia 能够通过统一的 WebGPU 接口在不同平台上渲染。

## 架构位置

```
WindowContext (基类)
  +-- GraphiteDawnWindowContext  (Graphite + Dawn, 抽象) <-- 本文件
       +-- 各平台 Dawn 子类 (Metal/Vulkan/D3D12/...)
```

## 主要类与结构体

### `GraphiteDawnWindowContext`
- **命名空间**: `skwindow::internal`
- **继承**: `WindowContext`
- **成员**:
  - `fSurfaceFormat`: WebGPU 纹理格式
  - `fInstance`: Dawn 原生实例
  - `fDevice`: wgpu::Device
  - `fQueue`: wgpu::Queue
  - `fSurface`: wgpu::Surface

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `GraphiteDawnWindowContext(params, surfaceFormat)` | 构造函数 |
| `~GraphiteDawnWindowContext()` | 析构函数 |
| `getBackbufferSurface()` | 从 wgpu::Surface 获取当前纹理并包装为 SkSurface |
| `isValid()` | 检查 Device 有效性 |
| `setDisplayParams(params)` | 重建上下文 |

## 内部实现细节

### 构造与实例创建
在构造函数中创建 Dawn 原生实例，启用 `TimedWaitAny` 特性（支持超时等待），并应用实例级 toggles 配置。

### 设备创建（createDevice）
1. 设置 Dawn proc table
2. 根据后端类型（Vulkan/Metal/D3D12/OpenGL）配置适配器选项和特性级别
3. 枚举适配器，应用 adapter 级 toggles
4. 请求设备特性和限制
5. 配置设备丢失和未捕获错误回调
6. 可选启用 `disable_symbol_renaming` toggle（用于调试 WGSL 着色器）

### Surface 配置（configureSurface）
配置 wgpu::Surface 的格式、用途（RenderAttachment + TextureBinding + CopySrc + CopyDst）、尺寸和呈现模式（Fifo 或 Immediate）。

### 后缓冲获取
通过 `fSurface.GetCurrentTexture()` 获取当前纹理，包装为 Graphite BackendTexture，再创建 SkSurface。

### 缓冲交换
提交 GPU 工作后调用 `fSurface.Present()`。

## 依赖关系

- **Dawn**: `webgpu_cpp.h`, `dawn/native/DawnNative.h`, `dawn/dawn_proc.h`
- **Graphite Dawn**: `DawnBackendContext`, `DawnGraphiteTypes`
- **Graphite 核心**: `Context`, `Recorder`, `Recording`, `Surface`, `BackendTexture`
- **工具**: `WindowContext`, `GraphiteToolUtils`, `GraphiteDawnToggles`, `GraphiteDisplayParams`

## 设计模式与设计决策

1. **模板方法模式**: 子类实现 `onInitializeContext()` / `onDestroyContext()` 提供平台特定的 Surface 创建
2. **Toggle 管理**: 通过 `GraphiteDawnToggles` 集中管理实例、适配器和设备级别的 Dawn toggles
3. **特性级别适配**: OpenGL/OpenGLES 后端使用 Compatibility 特性级别，其他后端使用 Core 级别
4. **错误处理回调**: 设备丢失和未捕获错误通过 lambda 回调处理，使用 SKIA_LOG 记录

## 性能考量

- 呈现模式可通过 `disableVsync` 控制（Fifo vs Immediate）
- 纹理用途包含 CopySrc/CopyDst 以支持读回和拷贝操作

## 相关文件

- `tools/graphite/dawn/GraphiteDawnToggles.h` - Dawn toggle 配置
- `tools/graphite/TestOptions.h` - 测试选项定义
- `include/gpu/graphite/dawn/DawnBackendContext.h` - Dawn 后端上下文
