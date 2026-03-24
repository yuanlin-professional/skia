# tools/ganesh/d3d - Ganesh Direct3D 后端测试上下文

## 概述

`tools/ganesh/d3d` 目录实现了 Ganesh GPU 后端的 Microsoft Direct3D 12 测试上下文。Direct3D 是 Microsoft 开发的图形 API，是 Windows 平台上游戏和高性能图形应用的主流选择。Skia 的 Direct3D 后端使用 D3D12 API，提供了现代化的低级 GPU 访问能力。

`D3DTestContext` 类继承自 `TestContext`，封装了 Direct3D 12 后端上下文的核心状态。`GrD3DBackendContext` 包含了 D3D12 的核心对象：`ID3D12Device`（D3D12 设备）、`ID3D12CommandQueue`（命令队列）以及 DXGI 适配器信息。

本目录包含四个文件。`D3DTestContext.h/.cpp` 定义了 `D3DTestContext` 类和 `CreatePlatformD3DTestContext()` 工厂函数。`D3DTestUtils.h/.cpp` 提供了 `CreateD3DBackendContext()` 辅助函数，用于初始化 D3D12 设备、命令队列等核心对象，并支持受保护内容（Protected Content）的创建选项。

与 Metal 类似，Direct3D 12 使用命令队列模型，没有传统的"当前上下文"概念。因此 `onPlatformMakeCurrent()` 和 `onPlatformMakeNotCurrent()` 是空操作。D3D 后端支持上下文所有权管理（`fOwnsContext` 标志），当测试上下文拥有 D3D 资源时，会在析构时正确清理。

所有代码受 `SK_DIRECT3D` 编译宏保护，仅在 Windows 平台上编译。

## 目录结构

```
tools/ganesh/d3d/
├── D3DTestContext.h      # Direct3D 测试上下文声明
├── D3DTestContext.cpp    # Direct3D 测试上下文实现
├── D3DTestUtils.h        # Direct3D 后端上下文创建工具声明
└── D3DTestUtils.cpp      # Direct3D 后端上下文创建工具实现
```

## 关键类与函数

### D3DTestContext
- **命名空间**: `sk_gpu_test`
- **基类**: `TestContext`
- **功能**: 封装 Direct3D 12 GPU 上下文的测试基础设施
- **核心成员**:
  - `fD3D` (`GrD3DBackendContext`) - D3D12 后端上下文，包含 Device 和 CommandQueue
  - `fOwnsContext` (`bool`) - 标记是否拥有 D3D 资源的所有权
- **核心方法**:
  - `backend()` - 返回 `GrBackendApi::kDirect3D`
  - `getD3DBackendContext()` - 获取 D3D12 后端上下文的常量引用

### CreatePlatformD3DTestContext
- **签名**: `D3DTestContext* CreatePlatformD3DTestContext(D3DTestContext* shareContext)`
- **功能**: 创建绑定到原生 D3D12 库的平台 Direct3D 测试上下文
- **参数**: `shareContext` - 可选的共享上下文

### CreateD3DBackendContext
- **命名空间**: `sk_gpu_test`
- **签名**: `bool CreateD3DBackendContext(GrD3DBackendContext* ctx, bool isProtected)`
- **功能**: 初始化 D3D12 后端上下文，创建设备、适配器和命令队列
- **参数**: `isProtected` - 是否创建支持受保护内容的上下文

## 依赖关系

- **上游依赖**: `tools/ganesh/TestContext.h`（基类）
- **D3D 依赖**: `include/gpu/ganesh/d3d/GrD3DBackendContext.h`、D3D12 SDK
- **编译条件**: 需要定义 `SK_DIRECT3D`，仅 Windows 平台
- **被引用**: `tools/ganesh/GrContextFactory.cpp`（通过 `ContextType::kDirect3D` 使用）
- **平台限制**: 需要 Windows 10 及以上版本（D3D12 要求）

## 相关文档与参考

- `tools/ganesh/TestContext.h` - 测试上下文基类
- `include/gpu/ganesh/d3d/GrD3DBackendContext.h` - D3D12 后端上下文数据结构
- `src/gpu/ganesh/d3d/` - Ganesh Direct3D 后端核心实现
- Microsoft D3D12 文档: https://docs.microsoft.com/en-us/windows/win32/direct3d12/
- `tools/ganesh/gl/angle/` - 也可通过 ANGLE D3D11 后端间接测试 D3D
