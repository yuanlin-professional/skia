# include/gpu/ganesh/d3d - Ganesh Direct3D 12 后端公共 API

## 概述

`include/gpu/ganesh/d3d` 目录包含 Ganesh 渲染引擎中 Direct3D 12 后端的公共 API。Direct3D 12
是 Microsoft 的低级图形 API，在 Windows 平台上提供高性能的 GPU 加速渲染。Skia 通过此后端
支持 Windows 平台上使用 D3D12 的应用程序。

此目录提供了 D3D12 后端上下文、后端表面工厂方法、信号量封装以及 D3D12 特有的类型定义。
`GrD3DTypes.h` 是核心类型定义文件，它包含了 `d3d12.h` 和 `dxgi1_4.h` 等 Windows 头文件，
因此客户端在包含此头文件时需要注意 Windows 头文件可能重定义某些常见标识符
（如 `interface`、`near`、`far`、`CreateSemaphore` 等）。

`gr_cp` 是 Skia 为 COM 对象提供的智能指针模板类，类似于 Microsoft 的 `ComPtr`，
管理 COM 对象的 `AddRef()` 和 `Release()` 生命周期。

注意：Direct3D 后端仅在 Ganesh 中可用，Graphite 不支持 Direct3D。

## 架构图

```
include/gpu/ganesh/d3d/
    |
    +-- GrD3DTypes.h            <-- D3D12 类型定义（包含 d3d12.h）
    |       |
    |       +-- gr_cp<T>           (COM 智能指针)
    |       +-- GrD3DMemoryAllocator (内存分配器基类)
    |       +-- GrD3DTextureResourceInfo (纹理资源信息)
    |       +-- GrD3DFenceInfo     (围栏信息)
    |
    +-- GrD3DBackendContext.h   <-- D3D12 后端上下文
    |       |
    |       +-- IDXGIAdapter1, ID3D12Device, ID3D12CommandQueue
    |
    +-- GrD3DBackendSurface.h   <-- D3D12 后端纹理/渲染目标工厂
    +-- GrD3DBackendSemaphore.h <-- D3D12 后端信号量
    +-- GrD3DDirectContext.h    <-- D3D12 上下文创建入口
```

## 目录结构

| 文件 | 说明 |
|------|------|
| `GrD3DTypes.h` | D3D12 核心类型：`gr_cp` 智能指针、`GrD3DMemoryAllocator`、资源信息 |
| `GrD3DBackendContext.h` | D3D12 后端上下文结构体 |
| `GrD3DBackendSurface.h` | D3D12 后端纹理和渲染目标的创建与查询 |
| `GrD3DBackendSemaphore.h` | D3D12 后端信号量封装 |
| `GrD3DDirectContext.h` | `GrDirectContexts::MakeDirect3D()` 工厂方法 |

## 关键类与函数

### `GrD3DBackendContext` 结构体

```cpp
struct GrD3DBackendContext {
    gr_cp<IDXGIAdapter1>      fAdapter;
    gr_cp<ID3D12Device>       fDevice;
    gr_cp<ID3D12CommandQueue>  fQueue;
    sk_sp<GrD3DMemoryAllocator> fMemoryAllocator;
    GrProtected fProtectedContext = GrProtected::kNo;
};
```

### `gr_cp<T>` COM 智能指针

```cpp
template <typename T> class gr_cp {
    gr_cp();
    gr_cp(T* obj);              // 接管所有权
    gr_cp(const gr_cp& that);   // AddRef
    gr_cp(gr_cp&& that);        // 移动
    ~gr_cp();                   // Release
    T* get() const;
    T* release();               // 释放所有权
    void reset(T* obj = nullptr);
    T** operator&();
};
```

### `GrD3DMemoryAllocator` 抽象类

D3D12 内存分配器基类，需要客户端提供实现。通常基于 D3D12 Memory Allocator (D3D12MA) 库。

### 上下文创建

```cpp
namespace GrDirectContexts {
    sk_sp<GrDirectContext> MakeDirect3D(const GrD3DBackendContext&, const GrContextOptions&);
    sk_sp<GrDirectContext> MakeDirect3D(const GrD3DBackendContext&);
}
```

## 依赖关系

- **上游依赖**: `include/gpu/ganesh/GrTypes.h`, `include/gpu/GpuTypes.h`
- **系统依赖**: `d3d12.h`, `dxgi1_4.h` (Windows SDK)
- **平台限制**: 仅 Windows
- **注意**: 包含此头文件会引入 Windows 头文件，可能导致宏冲突
- **实现代码**: `src/gpu/ganesh/d3d/`

## 相关文档与参考

- `include/gpu/ganesh/` - Ganesh 引擎主目录
- Direct3D 12 文档: https://docs.microsoft.com/en-us/windows/win32/direct3d12/
- D3D12 Memory Allocator: https://github.com/GPUOpen-LibrariesAndSDKs/D3D12MemoryAllocator
