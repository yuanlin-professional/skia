# GrD3DSemaphore

> 源文件
> - `src/gpu/ganesh/d3d/GrD3DSemaphore.h`
> - `src/gpu/ganesh/d3d/GrD3DSemaphore.cpp`

## 概述

`GrD3DSemaphore` 是 Skia 图形库中用于 Direct3D 12 后端的同步原语封装类。它基于 D3D12 的 Fence 对象实现了 Ganesh 的信号量抽象,用于在 GPU 操作之间实现同步和命令队列协调。

在 D3D12 中,Fence 是一个由 CPU 和 GPU 共享的计数器,GPU 可以向其发出信号,CPU 可以等待特定值。`GrD3DSemaphore` 将这个机制封装为 Skia 的通用信号量接口,支持跨队列同步、CPU-GPU 同步以及与外部 D3D12 代码的互操作。

## 架构位置

```
Skia GPU Backend (Ganesh)
└── 同步原语层
    ├── GrSemaphore (抽象接口)
    │   ├── GrD3DSemaphore (D3D12 实现)
    │   ├── GrVkSemaphore (Vulkan 实现)
    │   └── GrMtlSemaphore (Metal 实现)
    └── GrD3DGpu (使用信号量进行同步)
```

该类是 Ganesh 同步机制在 D3D12 后端的具体实现,与 GPU 命令提交和资源管理紧密配合。

## 主要类与结构体

### GrD3DSemaphore

**继承关系**
- 继承自: `GrSemaphore` - Ganesh 的通用信号量抽象

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fFenceInfo` | `GrD3DFenceInfo` | 封装了 D3D12 Fence 对象和关联值的结构体 |

### GrD3DFenceInfo 结构体

虽然未在源文件中定义,但该结构体包含:
- `fFence`: `gr_cp<ID3D12Fence>` - D3D12 Fence 对象的 COM 智能指针
- `fValue`: `uint64_t` - Fence 的信号值

## 公共 API 函数

### 创建新信号量

```cpp
static std::unique_ptr<GrD3DSemaphore> Make(GrD3DGpu* gpu);
```

创建新的 D3D12 信号量对象。内部调用 `ID3D12Device::CreateFence` 创建 Fence 对象。

**初始化参数:**
- 初始值: 0 (通过 CreateFence 的第一个参数)
- 标志: `D3D12_FENCE_FLAG_NONE` (无特殊标志)
- 信号值: 1 (存储在 `fFenceInfo.fValue`)

**返回:** 独占所有权的 `unique_ptr`,确保资源唯一性。

### 封装外部信号量

```cpp
static std::unique_ptr<GrD3DSemaphore> MakeWrapped(const GrD3DFenceInfo& fenceInfo);
```

封装外部创建的 D3D12 Fence 对象,实现跨 API 边界的同步。

**用途:**
- 与外部 D3D12 代码共享同步点
- 支持多个命令队列之间的协调
- 实现与其他图形库的互操作

### 访问器方法

```cpp
ID3D12Fence* fence() const;
```
返回底层的 D3D12 Fence 对象指针,用于 D3D12 API 调用。

```cpp
uint64_t value() const;
```
返回当前的信号值。GPU 操作会等待 Fence 达到或超过此值。

### 后端信号量转换

```cpp
GrBackendSemaphore backendSemaphore() const override;
```

将 D3D12 特定的信号量转换为 Ganesh 的跨平台信号量表示,通过 `GrBackendSemaphores::MakeD3D` 实现。

## 内部实现细节

### 简洁的实现

该类的实现非常简洁,主要原因:
- D3D12 的 Fence 机制本身就很简单清晰
- 大部分同步逻辑在 `GrD3DGpu` 中处理
- 该类主要作为 Fence 的封装和生命周期管理器

### Fence 创建流程

`Make` 方法的步骤:
1. 声明 `GrD3DFenceInfo` 结构体
2. 调用 `CreateFence(0, D3D12_FENCE_FLAG_NONE, ...)` 创建初始值为 0 的 Fence
3. 设置 `fValue = 1` 作为首次信号目标值
4. 构造 `GrD3DSemaphore` 对象

**信号值语义**: 初始 Fence 值为 0,首次信号时会设置为 1,后续递增。

### 所有权模型

使用 `std::unique_ptr` 而非 `sk_sp`:
- 信号量不需要共享所有权
- 每个信号量由单一的提交或等待操作拥有
- 避免引用计数的开销

### 空的 setIsOwned

```cpp
void setIsOwned() override {}
```

该方法在 D3D12 实现中为空,因为:
- D3D12 的 Fence 没有所有权标记的概念
- Fence 对象通过 COM 引用计数自动管理
- 不需要区分借用和拥有的语义

### 头文件保护宏问题

注意头文件中的保护宏名称:
```cpp
#ifndef GrMtlSemaphore_DEFINED  // 错误: 应该是 GrD3DSemaphore_DEFINED
```

这是一个复制粘贴遗留的小错误,虽然不影响功能,但应该修正为 `GrD3DSemaphore_DEFINED`。

### 后端信号量转换

`backendSemaphore` 方法简单地包装了 `GrD3DFenceInfo`:
- 允许信号量在不同 API 层之间传递
- 支持应用代码检查信号量状态
- 便于调试和日志记录

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrSemaphore` | 提供信号量抽象基类 |
| `GrD3DGpu` | GPU 设备,用于创建 Fence |
| `GrD3DTypes` | D3D12 类型定义(包括 `GrD3DFenceInfo`) |
| `GrBackendSemaphore` | 跨后端信号量表示 |
| `GrD3DBackendSemaphore` | D3D12 后端信号量转换 |
| `GrTypesPriv` | Ganesh 私有类型 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrD3DGpu` | 创建和使用信号量进行命令同步 |
| `GrContext` | 通过 GPU 后端使用信号量 |
| 外部 D3D12 代码 | 封装和互操作场景 |

## 设计模式与设计决策

### 轻量级封装

该类采用最小化封装策略:
- 仅存储 `GrD3DFenceInfo` 结构体
- 不缓存额外的状态信息
- 直接暴露底层 Fence 对象

这种设计提供零开销抽象,保持与原生 D3D12 代码的互操作性。

### 工厂方法模式

提供两个静态工厂方法:
- `Make` - 创建 Skia 管理的新信号量
- `MakeWrapped` - 封装外部信号量

明确区分了资源所有权和来源。

### 值语义的信号机制

使用递增的整数值而非布尔状态:
- 支持多次信号操作
- 可以等待特定的完成点
- 允许乱序完成检测

### 独占所有权

返回 `std::unique_ptr` 而非共享指针:
- 信号量通常只在单个提交上下文使用
- 简化生命周期管理
- 防止意外的跨上下文共享

### 分离的信号值

Fence 对象和信号值分离存储:
- **Fence**: GPU 操作的同步点
- **Value**: 特定的完成标记
- 同一 Fence 可以用于多个不同的同步点(通过递增值)

## 性能考量

### 无共享内存开销

使用 `D3D12_FENCE_FLAG_NONE`:
- 不创建跨进程共享的 Fence
- 避免额外的系统资源开销
- 适用于单进程内的同步

### CPU 等待效率

D3D12 Fence 支持事件通知:
- 可以高效地等待 GPU 完成
- 避免忙等待和轮询
- 支持超时等待

### 细粒度同步

通过递增的值支持细粒度同步:
- 可以等待特定批次的命令完成
- 不需要为每个同步点创建新 Fence
- 减少 Fence 对象的创建和销毁开销

### 跨队列同步

D3D12 Fence 天然支持多队列同步:
- 一个队列发出信号
- 另一个队列等待相同值
- 实现图形、计算和复制队列的协调

### 零拷贝封装

封装外部 Fence 不需要拷贝资源:
- `gr_cp<ID3D12Fence>` 只增加引用计数
- 不涉及 GPU 状态的拷贝
- 支持高效的跨 API 传递

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrSemaphore.h` | 父类 | Ganesh 信号量抽象基类 |
| `src/gpu/ganesh/d3d/GrD3DGpu.h` | 依赖 | GPU 设备,用于创建 Fence |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | 依赖 | 包含 `GrD3DFenceInfo` 定义 |
| `include/gpu/ganesh/GrBackendSemaphore.h` | 依赖 | 跨后端信号量表示 |
| `include/gpu/ganesh/d3d/GrD3DBackendSemaphore.h` | 依赖 | D3D12 信号量转换 |
| `include/private/gpu/ganesh/GrTypesPriv.h` | 依赖 | Ganesh 私有类型 |
