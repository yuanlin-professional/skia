# GrD3DBackendContext

> 源文件: `include/gpu/ganesh/d3d/GrD3DBackendContext.h`

## 概述
GrD3DBackendContext 定义了创建 Ganesh Direct3D 12 GPU 后端所需的上下文结构体。该结构体封装了与 D3D12 设备、命令队列、内存分配器等核心对象的引用,为 GrD3DGpu 的构建提供必要的 D3D12 基础设施。它是应用程序将现有 D3D12 资源传递给 Skia 的接口。

## 架构位置
该文件位于 `include/gpu/ganesh/d3d` Direct3D 后端的公共 API 层,是 Ganesh D3D 后端初始化的入口点。客户端应用程序创建或复用 D3D12 设备和队列,通过此结构体传递给 Skia,实现与现有 D3D12 管线的集成。

## 头文件包含警告

### Windows.h 符号污染
```cpp
// GrD3DTypes.h includes d3d12.h, which in turn includes windows.h, which redefines many
// common identifiers such as:
// * interface
// * small
// * near
// * far
// * CreateSemaphore
// * MemoryBarrier
//
// You should only include GrD3DBackendContext.h if you are prepared to rename those identifiers.
```

**问题**: Windows.h 通过宏定义重定义了许多常见标识符

**受影响的标识符**:
| 标识符 | Windows.h 定义 | 影响 |
|--------|----------------|------|
| interface | struct | C++ 类型关键字冲突 |
| small | char | 变量名冲突 |
| near | (空) | 旧图形 API 关键字 |
| far | (空) | 旧图形 API 关键字 |
| CreateSemaphore | CreateSemaphoreA/W | Win32 API 函数 |
| MemoryBarrier | _mm_mfence 等 | 内存屏障宏 |

**解决方案**:
```cpp
// 方法 1: 取消定义宏
#include "include/gpu/ganesh/d3d/GrD3DBackendContext.h"
#undef interface
#undef small
#undef near
#undef far
#undef CreateSemaphore
#undef MemoryBarrier

// 方法 2: 重命名冲突的标识符
namespace MyNamespace {
    using InterfaceType = IUnknown;  // 而非 interface
}

// 方法 3: 限制包含范围
// 仅在 .cpp 文件中包含,不放在公共头文件
```

**最佳实践**: 将 D3D 相关代码隔离在独立的编译单元中,避免污染整个项目命名空间。

## 核心结构体

### GrD3DBackendContext
```cpp
struct SK_API GrD3DBackendContext {
    gr_cp<IDXGIAdapter1> fAdapter;
    gr_cp<ID3D12Device> fDevice;
    gr_cp<ID3D12CommandQueue> fQueue;
    sk_sp<GrD3DMemoryAllocator> fMemoryAllocator;
    GrProtected fProtectedContext = GrProtected::kNo;
};
```

**职责**: 封装创建 GrD3DGpu 所需的所有 D3D12 基础对象

### 成员详解

#### fAdapter
```cpp
gr_cp<IDXGIAdapter1> fAdapter;
```
- **类型**: IDXGIAdapter1 COM 智能指针
- **功能**: 表示物理 GPU 适配器(显卡)
- **获取方式**:
  ```cpp
  Microsoft::WRL::ComPtr<IDXGIFactory4> factory;
  CreateDXGIFactory2(0, IID_PPV_ARGS(&factory));

  gr_cp<IDXGIAdapter1> adapter;
  factory->EnumAdapters1(0, &adapter);  // 枚举第一个适配器
  ```
- **用途**: Skia 可能查询适配器特性(显存大小、特性级别等)
- **可选性**: 通常必须提供,除非使用软件适配器

#### fDevice
```cpp
gr_cp<ID3D12Device> fDevice;
```
- **类型**: ID3D12Device COM 智能指针
- **功能**: D3D12 设备对象,所有 GPU 资源的创建入口
- **创建方式**:
  ```cpp
  gr_cp<ID3D12Device> device;
  D3D12CreateDevice(
      adapter.get(),
      D3D_FEATURE_LEVEL_11_0,
      IID_PPV_ARGS(&device)
  );
  ```
- **要求**: 必须是有效的 D3D12 设备
- **共享**: 可与应用程序其他渲染代码共享同一设备

#### fQueue
```cpp
gr_cp<ID3D12CommandQueue> fQueue;
```
- **类型**: ID3D12CommandQueue COM 智能指针
- **功能**: 命令队列,用于提交 GPU 工作
- **创建方式**:
  ```cpp
  D3D12_COMMAND_QUEUE_DESC queueDesc = {};
  queueDesc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
  queueDesc.Flags = D3D12_COMMAND_QUEUE_FLAG_NONE;

  gr_cp<ID3D12CommandQueue> queue;
  device->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&queue));
  ```
- **队列类型**: 通常为 DIRECT 类型(支持图形和计算)
- **专用队列**: Skia 可能与应用程序共享队列,或使用专用队列

#### fMemoryAllocator
```cpp
sk_sp<GrD3DMemoryAllocator> fMemoryAllocator;
```
- **类型**: Skia 智能指针,指向内存分配器接口
- **功能**: 管理 GPU 资源的内存分配
- **默认行为**: 如果为 nullptr,Skia 使用内置的简单分配器
- **自定义分配器**: 可集成 D3D12 Memory Allocator (D3D12MA) 等第三方库
- **接口**: 必须实现 GrD3DMemoryAllocator 抽象接口(见 GrD3DTypes.h)

**示例自定义分配器**:
```cpp
class MyD3DAllocator : public GrD3DMemoryAllocator {
    gr_cp<ID3D12Resource> createResource(
        D3D12_HEAP_TYPE heapType,
        const D3D12_RESOURCE_DESC* desc,
        D3D12_RESOURCE_STATES initialState,
        sk_sp<GrD3DAlloc>* allocation,
        const D3D12_CLEAR_VALUE* clearValue) override {
        // 使用 D3D12MA 或自定义内存池
        // ...
    }
};
```

#### fProtectedContext
```cpp
GrProtected fProtectedContext = GrProtected::kNo;
```
- **类型**: GrProtected 枚举(kYes/kNo)
- **功能**: 标识上下文是否用于受保护内容(DRM)
- **默认值**: kNo(非保护)
- **受保护上下文**: 支持播放加密视频等受 DRM 保护的内容
- **要求**: 需要硬件和驱动程序支持 D3D12 受保护资源会话

**启用受保护内容**:
```cpp
GrD3DBackendContext backendContext;
// ... 初始化其他成员 ...
backendContext.fProtectedContext = GrProtected::kYes;
```

## 使用流程

### 1. 创建 D3D12 资源
```cpp
// 创建 DXGI 工厂
ComPtr<IDXGIFactory4> factory;
CreateDXGIFactory2(0, IID_PPV_ARGS(&factory));

// 枚举适配器
gr_cp<IDXGIAdapter1> adapter;
factory->EnumAdapters1(0, &adapter);

// 创建设备
gr_cp<ID3D12Device> device;
D3D12CreateDevice(adapter.get(), D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&device));

// 创建命令队列
D3D12_COMMAND_QUEUE_DESC queueDesc = {};
queueDesc.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
gr_cp<ID3D12CommandQueue> queue;
device->CreateCommandQueue(&queueDesc, IID_PPV_ARGS(&queue));
```

### 2. 填充 BackendContext
```cpp
GrD3DBackendContext backendContext;
backendContext.fAdapter = adapter;
backendContext.fDevice = device;
backendContext.fQueue = queue;
backendContext.fMemoryAllocator = nullptr;  // 使用默认分配器
backendContext.fProtectedContext = GrProtected::kNo;
```

### 3. 创建 GrDirectContext
```cpp
sk_sp<GrDirectContext> context = GrDirectContext::MakeDirect3D(backendContext);
if (!context) {
    // 创建失败,检查设备能力
}
```

### 4. 资源生命周期管理
- **引用计数**: gr_cp 和 sk_sp 自动管理引用计数
- **销毁顺序**: 先销毁 GrDirectContext,再释放 D3D 资源
- **共享资源**: 可与应用程序其他 D3D 代码共享设备和队列

## 内部实现细节

### gr_cp 智能指针
- 自定义 COM 智能指针(见 GrD3DTypes.h)
- 自动调用 AddRef/Release
- 支持移动语义和拷贝语义

### 资源验证
GrDirectContext::MakeDirect3D 内部验证:
- 设备特性级别(最低 11.0)
- 队列类型(必须支持图形命令)
- 适配器与设备匹配
- 受保护上下文的硬件支持

### 内存分配器集成
如果提供自定义 fMemoryAllocator:
- Skia 所有纹理/缓冲区通过该分配器创建
- 可实现统一内存池、预算管理、碎片整理等
- 必须线程安全

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| include/gpu/ganesh/d3d/GrD3DTypes.h | gr_cp 智能指针、D3D 类型定义 |
| include/gpu/ganesh/GrTypes.h | GrProtected 枚举 |
| d3d12.h | Direct3D 12 API |
| dxgi1_4.h | DXGI 适配器管理 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| GrDirectContext | 通过 MakeDirect3D 创建 D3D 上下文 |
| GrD3DGpu | D3D 后端 GPU 实现,使用此结构体初始化 |

## 设计模式与设计决策

### 构造函数隐式默认
- 使用聚合初始化,无需定义构造函数
- 简化客户端代码
- C++11 统一初始化语法:
  ```cpp
  GrD3DBackendContext ctx{adapter, device, queue, allocator, GrProtected::kNo};
  ```

### 智能指针所有权
- 使用 gr_cp 和 sk_sp 避免手动引用计数
- 共享所有权语义:Skia 和应用程序共同持有引用
- 销毁安全:任一方释放不影响另一方

### 可选内存分配器
- 默认 nullptr 提供简单使用路径
- 高级用户可自定义实现更好的性能

## 性能考量

### 共享队列 vs 专用队列
- **共享队列**: 节省资源,但需同步
- **专用队列**: 更好的并行性,适合重度 Skia 使用

### 内存分配器选择
- **默认分配器**: 简单,直接调用 D3D12 API
- **D3D12MA**: 减少碎片,提升大量小资源分配性能
- **自定义池**: 预分配大块内存,避免运行时分配

### 受保护内容开销
- 启用受保护上下文可能限制某些优化
- 仅在必要时(播放 DRM 内容)启用

## 平台相关说明

### Windows 版本要求
- Windows 10 版本 1809 或更高
- D3D12 需要 WDDM 2.0 驱动

### 硬件要求
- 支持 Direct3D 12 的 GPU
- 特性级别 11.0 或更高
- 受保护内容需要硬件 DRM 支持

### Xbox 平台
- Xbox One X/S 和 Xbox Series X/S 支持
- 可能需要特定的队列优先级设置

## 错误处理

### 创建失败原因
- 设备特性级别不足
- 队列类型不支持
- 受保护上下文不可用
- 内存不足

### 调试建议
```cpp
auto context = GrDirectContext::MakeDirect3D(backendContext);
if (!context) {
    // 检查 D3D12 调试层输出
    // 验证设备能力:
    D3D12_FEATURE_DATA_D3D12_OPTIONS options;
    device->CheckFeatureSupport(D3D12_FEATURE_D3D12_OPTIONS, &options, sizeof(options));
}
```

## 相关文件
| 文件 | 关系 |
|------|------|
| include/gpu/ganesh/d3d/GrD3DTypes.h | 类型定义和智能指针 |
| include/gpu/GrDirectContext.h | MakeDirect3D 工厂函数 |
| src/gpu/ganesh/d3d/GrD3DGpu.h | D3D GPU 后端实现 |
| src/gpu/ganesh/d3d/GrD3DResourceProvider.h | 资源管理器 |
