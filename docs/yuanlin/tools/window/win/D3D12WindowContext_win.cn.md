# D3D12WindowContext_win - Windows Direct3D 12 窗口上下文

> 源文件: `tools/window/win/D3D12WindowContext_win.cpp`

## 概述

`D3D12WindowContext` 实现了 Windows 平台上基于 Direct3D 12 图形 API 的窗口上下文。它是所有 Windows 窗口上下文中最复杂的实现之一，直接管理 D3D12 设备、命令队列、交换链、渲染目标、围栏同步等底层资源。通过 Ganesh 的 D3D 后端将 D3D12 资源集成到 Skia 的渲染管线中。

## 架构位置

- 直接继承自 `WindowContext`（不使用中间基类）
- 由工厂函数 `MakeD3D12ForWin` 创建
- 使用 Ganesh D3D 后端（`GrD3DDirectContext`、`GrD3DBackendSurface` 等）
- 自行管理双缓冲交换链和 GPU 同步

## 主要类与结构体

### `D3D12WindowContext`（匿名命名空间）
- 继承自 `WindowContext`
- 核心成员变量：
  - `fDevice` (`gr_cp<ID3D12Device>`) - D3D12 设备
  - `fQueue` (`gr_cp<ID3D12CommandQueue>`) - 命令队列
  - `fSwapChain` (`gr_cp<IDXGISwapChain3>`) - DXGI 交换链
  - `fBuffers[kNumFrames]` (`gr_cp<ID3D12Resource>`) - 帧缓冲资源
  - `fSurfaces[kNumFrames]` (`sk_sp<SkSurface>`) - 对应的 Skia 表面
  - `fFence` / `fFenceEvent` / `fFenceValues` - CPU-GPU 同步原语
- `kNumFrames = 2` - 双缓冲

### 辅助宏
- `GR_D3D_CALL_ERRCHECK` - D3D API 调用错误检查宏

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `MakeD3D12ForWin(HWND, unique_ptr<const DisplayParams>)` | 工厂函数 |
| `getBackbufferSurface()` | 获取当前帧的后台缓冲区表面 |
| `resize(int, int)` | 调整渲染尺寸，重建交换链缓冲区 |
| `setDisplayParams(unique_ptr<const DisplayParams>)` | 完全重建上下文 |
| `isValid()` | 检查 D3D12 设备是否有效 |

## 内部实现细节

### 初始化流程 (`initializeContext`)
1. 通过 `sk_gpu_test::CreateD3DBackendContext` 创建 D3D12 后端上下文
2. 使用 `GrDirectContexts::MakeD3D` 创建 Ganesh D3D 上下文
3. 创建 DXGI 交换链（FLIP_DISCARD 模式，RGBA8 格式）
4. 禁用全屏切换（`DXGI_MWA_NO_ALT_ENTER`）
5. 设置围栏同步对象
6. 调用 `setupSurfaces` 创建渲染表面

### 表面创建 (`setupSurfaces`)
- 获取交换链的后台缓冲区资源
- 根据 MSAA 采样数选择创建方式：
  - 多重采样：通过 `WrapBackendTexture` 创建纹理类型表面
  - 单采样：通过 `WrapBackendRenderTarget` 创建渲染目标表面

### 帧同步 (`getBackbufferSurface`)
1. 记录当前围栏值
2. 切换到下一个缓冲区索引
3. 如果前一帧在该缓冲区上的 GPU 工作尚未完成，通过围栏等待
4. 设置下一帧的围栏值

### 帧呈现 (`onSwapBuffers`)
1. 刷新 Ganesh 上下文（flush + submit）
2. 调用 `fSwapChain->Present(1, 0)` 呈现（VSync 开启）
3. 在命令队列上发送围栏信号

### 尺寸调整 (`resize`)
1. 刷新并等待所有 GPU 工作完成
2. 释放所有表面和缓冲区资源
3. 调用 `ResizeBuffers` 调整交换链
4. 重新创建表面

## 依赖关系

- Ganesh D3D 后端: `GrD3DDirectContext`, `GrD3DBackendContext`, `GrD3DBackendSurface`
- D3D12 API: `ID3D12Device`, `ID3D12CommandQueue`, `ID3D12Fence`
- DXGI: `IDXGISwapChain3`, `IDXGIFactory4`
- `tools/ganesh/d3d/D3DTestUtils.h` - D3D 后端上下文创建

## 设计模式与设计决策

- **显式帧同步**: 使用 D3D12 围栏（Fence）手动管理 CPU-GPU 同步
- **双缓冲**: `kNumFrames = 2` 实现经典双缓冲
- **FLIP_DISCARD 交换**: 使用现代的翻转模式交换效果
- **围栏值递增**: 每帧递增围栏值，高初始值（10000）便于 PIX 调试工具追踪
- **完全重建策略**: `setDisplayParams` 采用销毁后重建的方式，简化参数变更处理

## 性能考量

- 双缓冲设计平衡了延迟和吞吐量
- `Present(1, 0)` 启用 VSync，避免画面撕裂但可能限制帧率
- 围栏等待使用 `WaitForSingleObjectEx`，在 GPU 忙碌时 CPU 进入睡眠状态
- `resize` 操作需要同步等待所有帧完成，是一个重量级操作
- FLIP_DISCARD 交换效果比传统的 BitBlt 更高效

## 相关文件

- `tools/ganesh/d3d/D3DTestUtils.h` - D3D12 后端上下文创建工具
- `include/gpu/ganesh/d3d/GrD3DDirectContext.h` - D3D Ganesh 上下文
- `include/gpu/ganesh/d3d/GrD3DBackendSurface.h` - D3D 后端表面
- `tools/window/win/WindowContextFactory_win.h` - 工厂声明
- `tools/window/win/GraphiteDawnWindowContext_win.cpp` - Dawn/D3D 替代方案
