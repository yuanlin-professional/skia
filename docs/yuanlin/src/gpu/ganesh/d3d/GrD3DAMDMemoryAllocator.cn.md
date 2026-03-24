# GrD3DAMDMemoryAllocator

> 源文件: `src/gpu/ganesh/d3d/GrD3DAMDMemoryAllocator.h`, `src/gpu/ganesh/d3d/GrD3DAMDMemoryAllocator.cpp`

## 概述

`GrD3DAMDMemoryAllocator` 是 Skia Ganesh D3D12 后端的内存分配器实现，基于 AMD 的 D3D12 Memory Allocator (D3D12MA) 库。它封装了 `D3D12MA::Allocator`，提供 D3D12 资源的创建和内存子分配功能，包括常规资源创建和别名资源（aliasing resource）创建。

## 架构位置

位于 Ganesh D3D12 后端的内存管理层。`GrD3DMemoryAllocator` 是抽象基类，定义了 D3D12 资源创建接口。`GrD3DAMDMemoryAllocator` 是其基于 AMD D3D12MA 库的具体实现，负责高效的 GPU 内存子分配。

## 主要类与结构体

### `GrD3DAMDMemoryAllocator`
- 继承自 `GrD3DMemoryAllocator`
- 持有 `D3D12MA::Allocator*` 分配器实例
- 提供 `createResource()` 和 `createAliasingResource()` 方法

### `Alloc`（内部类）
- 继承自 `GrD3DAlloc`
- 封装 `D3D12MA::Allocation*`，析构时调用 `Release()`
- 通过 `sk_sp` 智能指针管理生命周期

## 公共 API 函数

### `Make()`
```cpp
static sk_sp<GrD3DMemoryAllocator> Make(IDXGIAdapter* adapter, ID3D12Device* device);
```
工厂方法。创建 `D3D12MA::Allocator`，使用 `ALLOCATOR_FLAG_SINGLETHREADED` 标志（Skia 的单线程访问模式下更快）。

### `createResource()`
```cpp
gr_cp<ID3D12Resource> createResource(D3D12_HEAP_TYPE, const D3D12_RESOURCE_DESC*,
    D3D12_RESOURCE_STATES initialResourceState,
    sk_sp<GrD3DAlloc>* allocation, const D3D12_CLEAR_VALUE*);
```
创建新的 D3D12 资源并关联内存分配。使用 `D3D12MA::CreateResource` 进行子分配，返回 `ID3D12Resource` 和 `Alloc` 对象。

### `createAliasingResource()`
```cpp
gr_cp<ID3D12Resource> createAliasingResource(sk_sp<GrD3DAlloc>& allocation,
    uint64_t localOffset, const D3D12_RESOURCE_DESC*,
    D3D12_RESOURCE_STATES initialResourceState, const D3D12_CLEAR_VALUE*);
```
在已有分配上创建别名资源（共享同一块内存）。用于内存复用场景，如 render target 和纹理共享同一内存。

## 内部实现细节

- `D3D12MA::ALLOCATOR_DESC::Flags` 设为 `SINGLETHREADED`，因为 Skia 保证单线程访问分配器
- `D3D12MA::ALLOCATION_DESC::HeapType` 直接传递调用方指定的堆类型
- 资源创建失败时返回 `nullptr`，不抛出异常
- 分配器和分配对象都通过 `Release()` 手动管理（COM 风格）
- `Alloc` 对象通过 `sk_sp` 引用计数管理，确保在资源使用期间分配不被释放

## 依赖关系

- **GrD3DMemoryAllocator / GrD3DAlloc** - 基类和分配对象基类（定义在 `GrD3DTypes.h`）
- **D3D12MA (D3D12MemAlloc.h)** - AMD D3D12 Memory Allocator 第三方库
- **GrD3DUtil** - D3D12 工具函数
- **IDXGIAdapter / ID3D12Device** - D3D12 适配器和设备接口

## 设计模式与设计决策

1. **第三方库封装**: 通过 Skia 的抽象接口（`GrD3DMemoryAllocator`）封装 AMD D3D12MA，支持替换为其他分配器
2. **单线程优化**: `SINGLETHREADED` 标志避免了不必要的锁开销
3. **子分配**: D3D12MA 自动进行内存子分配（使用 `CreatePlacedResource`），避免每个资源一个堆的浪费
4. **Clang 警告抑制**: `D3D12MemAlloc.h` 包含时抑制 `deprecated-dynamic-exception-spec` 警告

## 性能考量

- 子分配减少了 D3D12 堆创建的开销（创建堆是昂贵操作）
- 单线程模式下分配器无锁，最大化分配/释放性能
- 别名资源支持内存复用，减少总内存占用
- TODO 注释提到未来需要确定更合适的分配标志以支持预算感知分配

## 相关文件

- `include/gpu/ganesh/d3d/GrD3DTypes.h` - D3D12 类型定义和基类
- `src/gpu/ganesh/d3d/GrD3DGpu.h` - D3D12 GPU 实现
- `src/gpu/ganesh/d3d/GrD3DUtil.h` - D3D12 工具函数
- `src/gpu/ganesh/d3d/GrD3DBuffer.h` - D3D12 缓冲区实现
