# GraphiteDawnWindowContext_win - Windows Graphite Dawn 窗口上下文

> 源文件: `tools/window/win/GraphiteDawnWindowContext_win.cpp`

## 概述

`GraphiteDawnWindowContext_win` 实现了 Windows 平台上使用 Dawn（WebGPU 实现）作为底层图形 API 的 Graphite 渲染窗口上下文。它支持 D3D11 和 D3D12 两种 Dawn 后端类型，通过 WebGPU 表面描述符将 HWND 窗口连接到 Dawn 渲染管线。

## 架构位置

- 继承自 `skwindow::internal::GraphiteDawnWindowContext`
- 由工厂函数 `MakeGraphiteDawnForWin` 创建
- 位于匿名命名空间中
- 桥接 Windows 窗口系统与 Dawn/Graphite 渲染管线

## 主要类与结构体

### `GraphiteDawnWindowContext_win`（匿名命名空间）
- 继承自 `GraphiteDawnWindowContext`
- 成员变量：
  - `fWindow` (`HWND`) - Windows 窗口句柄
  - `fBackendType` (`wgpu::BackendType`) - Dawn 后端类型（D3D11 或 D3D12）

### 辅助函数
- `ToDawnBackendType()` - 将 `sk_app::Window::BackendType` 映射到 `wgpu::BackendType`

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeGraphiteDawnForWin(HWND, params, backendType)` | 工厂函数，创建 Dawn 窗口上下文 |

## 内部实现细节

### 初始化流程
1. 构造函数将后端类型从 Skia 枚举转换为 Dawn 枚举
2. 通过 `GetClientRect` 获取窗口尺寸并调用基类 `initializeContext`
3. `onInitializeContext()` 中：
   - 调用基类 `createDevice()` 创建 Dawn 设备
   - 创建 `wgpu::SurfaceSourceWindowsHWND` 描述符，设置 HWND 和 HINSTANCE
   - 通过 Dawn 实例创建 WebGPU 表面
   - 调用 `configureSurface()` 完成表面配置

### 后端类型映射
- `kGraphiteDawnD3D11` -> `wgpu::BackendType::D3D11`
- `kGraphiteDawnD3D12` -> `wgpu::BackendType::D3D12`
- 其他类型触发 `SkASSERT(false)` 并默认使用 D3D12

### 调整尺寸
`resize()` 仅调用 `configureSurface()` 重新配置表面，依赖 Dawn 的内部交换链管理。

## 依赖关系

- `tools/window/GraphiteDawnWindowContext.h` - Dawn 基类
- `tools/window/win/WindowContextFactory_win.h` - 工厂声明
- Dawn/WebGPU: `wgpu::SurfaceSourceWindowsHWND`, `wgpu::SurfaceDescriptor`
- `<Windows.h>` - `GetClientRect`, `GetModuleHandle`

## 设计模式与设计决策

- **策略模式**: 通过 `BackendType` 参数在运行时选择 D3D11 或 D3D12 后端
- **模板方法模式**: 基类定义上下文初始化骨架，子类实现平台特定部分
- **纹理格式**: 硬编码使用 `BGRA8Unorm` 纹理格式

## 性能考量

- Dawn 在 D3D12 后端通常提供更好的性能（更低的 CPU 开销）
- D3D11 后端兼容性更好，支持更多 Windows 版本
- 表面配置在 resize 时重新执行，开销较小
- Dawn 内部管理交换链和同步

## 相关文件

- `tools/window/GraphiteDawnWindowContext.h` - 跨平台 Dawn 上下文基类
- `tools/window/win/D3D12WindowContext_win.cpp` - 原生 D3D12 实现（Ganesh）
- `tools/window/win/WindowContextFactory_win.h` - 工厂声明
