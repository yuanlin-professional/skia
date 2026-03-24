# WebGPU Bazel Demo 绑定

> 源文件: `experimental/webgpu-bazel/src/bindings.cpp`

## 概述

`bindings.cpp` 是一个基于 WebGPU/Dawn 后端的 Skia Web 渲染演示程序。它通过 Emscripten 在浏览器中运行，支持三种渲染模式：纯色、径向渐变和 SkSL 运行时着色器效果。该程序展示了如何使用 Skia 的 Ganesh GPU 后端配合 WebGPU API 进行 Web 端 GPU 渲染。

## 架构位置

位于 `experimental/webgpu-bazel/src/` 目录，使用 Bazel 构建系统。这是 Skia 在 Web 平台上使用 WebGPU 后端的实验性演示。

## 主要类与结构体

- **`DemoKind`** (enum class): 演示类型枚举
  - `SOLID_COLOR`, `GRADIENT`, `RUNTIME_EFFECT`
- **`DemoUniforms`**: SkSL 着色器 uniform 参数
  - `width`, `height`, `time`
- **`Demo`** (final class): 主要演示类
  - `fFrameCount`: 帧计数器
  - `fWidth` / `fHeight`: 画布尺寸
  - `fCanvasSurface`: WebGPU Surface
  - `fContext`: GrDirectContext
  - `fEffect`: SkRuntimeEffect（SkSL 着色器）

## 公共 API 函数

- **`Demo::init(canvasSelector, width, height)`**: 初始化 WebGPU 设备和 Skia 上下文
- **`Demo::setKind(kind)`**: 设置渲染模式
- **`Demo::draw(timestamp)`**: 执行一帧渲染

## 内部实现细节

1. **WebGPU 初始化** (`getSurfaceForCanvas`):
   - 使用 `SurfaceDescriptorFromCanvasHTMLSelector` 关联 HTML Canvas
   - 配置 BGRA8Unorm 格式和 Fifo 展示模式
2. **Skia 上下文** (`init`):
   - 通过 `emscripten_webgpu_get_device()` 获取 WebGPU 设备
   - 使用 `GrDirectContext::MakeDawn` 创建 Ganesh 上下文
   - 编译 SkSL 运行时着色器
3. **渲染流程** (`draw`):
   - 获取当前 Surface Texture 并创建 View
   - 构造 `GrBackendRenderTarget` 包装 WebGPU 纹理
   - 通过 `SkSurfaces::WrapBackendRenderTarget` 创建 Skia Surface
   - 根据 DemoKind 执行不同渲染
   - `flushAndSubmit` 提交并等待 GPU 完成
4. **SkSL 着色器**: 实现了一个基于时间的三层波浪特效

## 依赖关系

- Skia 核心: `SkCanvas`, `SkPaint`, `SkSurface`, `SkRect`
- Skia GPU (Ganesh): `GrDirectContext`, `GrBackendSurface`, `SkSurfaceGanesh`
- Skia 效果: `SkGradient`, `SkRuntimeEffect`
- Emscripten: `emscripten/bind.h`, `emscripten/html5.h`, `emscripten/html5_webgpu.h`
- WebGPU C/C++ API: `webgpu/webgpu.h`, `webgpu/webgpu_cpp.h`

## 设计模式与设计决策

- Emscripten bindings 将 `Demo` 类和 `DemoKind` 枚举暴露给 JavaScript
- 帧计数器实现纯色闪烁效果（奇偶帧交替颜色）
- `syncSubmit=true` 确保每帧渲染完成后再返回，避免 WebGPU 异步问题
- SkSL 着色器硬编码在 C++ 中，避免额外的资源加载

## 性能考量

- 每帧创建新的 Surface 和 BackendRenderTarget（WebGPU 要求获取当前纹理）
- `flushAndSubmit` 带同步等待可能影响帧率，但简化了资源管理
- SkSL 着色器在初始化时一次性编译，渲染时仅更新 uniform

## 相关文件

- `include/gpu/ganesh/GrDirectContext.h`: Ganesh GPU 上下文
- `include/effects/SkRuntimeEffect.h`: SkSL 运行时效果
- `modules/canvaskit/`: CanvasKit 的生产级 WebAssembly 绑定
