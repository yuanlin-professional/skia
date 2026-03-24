# D3DTestUtils

> 源文件：tools/ganesh/d3d/D3DTestUtils.h, tools/ganesh/d3d/D3DTestUtils.cpp

## 概述

D3DTestUtils 提供用于创建 Direct3D 12 测试环境的工具函数。该模块封装了 D3D12 设备初始化的复杂细节，包括 DXGI 工厂创建、硬件适配器枚举、设备和命令队列创建等，为 D3D12 测试提供简洁的接口。

主要功能：
- 枚举并选择支持 D3D12 的硬件适配器
- 创建 D3D12 设备（Feature Level 11.0）
- 创建 Direct 类型的命令队列
- 可选的调试层支持
- 可选的受保护内存支持（未完全实现）

该模块是 D3DTestContext 的底层支撑，处理所有平台特定的 D3D12 初始化逻辑。

## 架构位置

- **调用者**：D3DTestContext
- **依赖**：D3D12 API、DXGI、GrD3DBackendContext
- **平台**：仅 Windows（条件编译保护）

## 公共 API 函数

### CreateD3DBackendContext

```cpp
bool CreateD3DBackendContext(GrD3DBackendContext* ctx,
                             bool isProtected = false);
```

创建并初始化 D3D12 后端上下文。

**参数**：
- `ctx` - 输出参数，填充创建的 D3D12 资源
- `isProtected` - 是否创建受保护内存上下文（当前未实现）

**返回值**：
- 成功返回 `true`
- 失败返回 `false`（如无兼容硬件、驱动程序过旧等）

**创建的资源**：
- `ctx->fAdapter` - DXGI 适配器（`IDXGIAdapter1`）
- `ctx->fDevice` - D3D12 设备（`ID3D12Device`）
- `ctx->fQueue` - D3D12 命令队列（`ID3D12CommandQueue`）
- `ctx->fProtectedContext` - 受保护内存标志

## 内部实现细节

### 调试层初始化

```cpp
#if defined(SK_ENABLE_D3D_DEBUG_LAYER)
{
    gr_cp<ID3D12Debug> debugController;
    if (SUCCEEDED(D3D12GetDebugInterface(IID_PPV_ARGS(&debugController)))) {
        debugController->EnableDebugLayer();
    }
}
#endif
```

调试层提供：
- API 使用错误检测
- 资源泄漏检测
- 性能警告
- 详细错误消息

仅在定义 `SK_ENABLE_D3D_DEBUG_LAYER` 时启用，因为有显著性能开销。

### DXGI 工厂创建

```cpp
gr_cp<IDXGIFactory4> factory;
if (!SUCCEEDED(CreateDXGIFactory1(IID_PPV_ARGS(&factory)))) {
    return false;
}
```

DXGI 工厂用于枚举显示适配器和创建交换链。

### 硬件适配器枚举

```cpp
void get_hardware_adapter(IDXGIFactory4* pFactory, IDXGIAdapter1** ppAdapter) {
    *ppAdapter = nullptr;
    for (UINT adapterIndex = 0; ; ++adapterIndex) {
        IDXGIAdapter1* pAdapter = nullptr;
        if (DXGI_ERROR_NOT_FOUND == pFactory->EnumAdapters1(adapterIndex, &pAdapter)) {
            break;  // 没有更多适配器
        }

        // 检查适配器是否支持 D3D12
        if (SUCCEEDED(D3D12CreateDevice(pAdapter, D3D_FEATURE_LEVEL_11_0,
                                        _uuidof(ID3D12Device), nullptr))) {
            *ppAdapter = pAdapter;
            return;
        }
        pAdapter->Release();
    }
}
```

枚举逻辑：
1. 按索引顺序枚举适配器
2. 对每个适配器尝试创建 D3D12 设备（不实际创建，仅检查）
3. 返回第一个支持 D3D_FEATURE_LEVEL_11_0 的适配器
4. 如果没有找到兼容适配器，返回 nullptr

**特性级别**：
- `D3D_FEATURE_LEVEL_11_0` 是 Skia 所需的最低级别
- 支持 Shader Model 5.0
- 支持计算着色器
- Windows 7+ 广泛支持

### 设备创建

```cpp
gr_cp<ID3D12Device> device;
if (!SUCCEEDED(D3D12CreateDevice(hardwareAdapter.get(),
                                 D3D_FEATURE_LEVEL_11_0,
                                 IID_PPV_ARGS(&device)))) {
    return false;
}
```

创建 D3D12 设备，这是 D3D12 的核心对象，用于创建资源、命令列表等。

### 命令队列创建

```cpp
gr_cp<ID3D12CommandQueue> queue;
D3D12_COMMAND_QUEUE_DESC queueDesc = {};
queueDesc.Flags = D3D12_COMMAND_QUEUE_FLAG_NONE;
queueDesc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;

if (!SUCCEEDED(device->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&queue)))) {
    return false;
}
```

**命令队列类型**：
- `DIRECT` - 支持所有 GPU 操作（图形、计算、复制）
- Skia 使用 Direct 队列进行渲染

### 后端上下文填充

```cpp
ctx->fAdapter = hardwareAdapter;
ctx->fDevice = device;
ctx->fQueue = queue;
ctx->fProtectedContext = GrProtected::kNo;  // TODO: 实现受保护内存
```

将创建的 D3D12 对象填充到 `GrD3DBackendContext` 中，供 Ganesh 使用。

**受保护内存**：
注释表明受保护内存支持尚未实现。受保护内存用于 DRM 内容渲染，防止未授权访问 GPU 资源。

## 依赖关系

### Windows SDK
- `<d3d12.h>` - D3D12 核心 API
- `<d3d12sdklayers.h>` - 调试层
- `<dxgi1_4.h>` - DXGI 接口

### Skia 组件
- `GrD3DBackendContext` - D3D12 后端上下文结构
- `gr_cp` - COM 智能指针包装器

## 设计模式与设计决策

### 工具函数设计
使用独立的工具函数而非类封装，简化测试代码的使用。

### 首个兼容适配器策略
选择第一个支持 D3D12 的适配器，而非最强的 GPU。这确保测试在最广泛的硬件上运行。

### Feature Level 选择
使用 Feature Level 11.0 而非更高版本，确保最大兼容性。

### 智能指针使用
使用 `gr_cp`（类似 `Microsoft::WRL::ComPtr`）自动管理 COM 对象引用计数，防止资源泄漏。

### 错误处理
使用 `SUCCEEDED` 宏检查 HRESULT，失败时返回 false 而非异常。

### 调试层条件编译
调试层仅在开发构建中启用：
```cpp
#if defined(SK_ENABLE_D3D_DEBUG_LAYER)
```

## 性能考量

### 调试层开销
调试层有显著性能开销（可能降低 50%+ 性能），仅用于开发和调试。

### 适配器枚举
适配器枚举是一次性操作，但在有多个 GPU 的系统上可能需要几毫秒。

### Feature Level
Feature Level 11.0 是最低要求，更高级别可能提供更好性能，但牺牲兼容性。

### 命令队列类型
使用 Direct 队列而非 Copy 或 Compute 队列，支持所有操作，但可能在特定工作负载上不是最优。

## 相关文件

### 同目录文件
- `tools/ganesh/d3d/D3DTestContext.h/cpp` - D3D12 测试上下文

### Ganesh D3D12 支持
- `include/gpu/ganesh/d3d/GrD3DBackendContext.h` - D3D12 后端上下文
- `src/gpu/ganesh/d3d/GrD3DGpu.h` - D3D12 GPU 实现
- `src/gpu/ganesh/d3d/GrD3DUtil.h` - D3D12 工具函数

### 基类
- `tools/ganesh/TestContext.h/cpp` - 测试上下文基类

### Windows SDK 头文件
- `<d3d12.h>` - D3D12 API
- `<dxgi.h>` - DirectX Graphics Infrastructure
