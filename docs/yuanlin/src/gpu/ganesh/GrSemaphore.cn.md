# GrSemaphore

> 源文件: [src/gpu/ganesh/GrSemaphore.h](../../../../src/gpu/ganesh/GrSemaphore.h)

## 概述

`GrSemaphore` 是 Skia Ganesh GPU 后端中表示 GPU 信号量同步原语的抽象基类。GPU 信号量用于在多个 GPU 命令队列或 CPU 与 GPU 之间进行同步，确保操作按正确的顺序执行。该类定义了一个最小的纯虚接口，由各 GPU 后端（Vulkan、Metal、D3D 等）的具体信号量类来实现。

## 架构位置

`GrSemaphore` 位于 Ganesh GPU 同步机制的核心：

```
用户代码 / GrContext
  |
  v (flush with signal/wait semaphores)
GrGpu (GPU 设备抽象)
  |
  +-- insertSemaphore() / waitSemaphore()
  |
  v
GrSemaphore (抽象信号量接口)
  |
  +-- GrVkSemaphore    (Vulkan VkSemaphore 封装)
  +-- GrMtlSemaphore   (Metal MTLEvent 封装)
  +-- GrD3DSemaphore   (Direct3D 12 ID3D12Fence 封装)
  |
  v
GrBackendSemaphore (公共 API 信号量句柄)
```

`GrSemaphore` 作为内部抽象接口，由 `GrGpu` 创建和管理。当用户需要在 flush 操作中进行跨队列或跨 API 同步时，`GrSemaphore` 提供了统一的内部表示。

## 主要类与结构体

### `GrSemaphore` — GPU 信号量抽象基类

一个纯虚基类，定义了 GPU 信号量的基本接口。

**特征：**

| 特征 | 说明 |
|------|------|
| 虚析构函数 | `virtual ~GrSemaphore() {}`，确保派生类正确析构 |
| 纯虚接口 | 包含两个纯虚函数，必须由后端实现 |
| 不可复制 | 作为 GPU 资源的代表，信号量对象不应被复制 |

## 公共 API 函数

### `virtual GrBackendSemaphore backendSemaphore() const = 0`

返回该信号量对应的 `GrBackendSemaphore`（公共 API 句柄）。这用于在 flush 操作中将内部创建的信号量暴露给客户端，使客户端能够在其他 API 调用或其他 `GrContext` 中使用该信号量。

- **返回：** 包含后端特定信号量句柄的 `GrBackendSemaphore` 对象

### `virtual void setIsOwned() = 0`（私有）

将信号量标记为"已拥有"（owned）。这是一个私有纯虚方法，仅由友元类 `GrGpu` 调用。

**使用场景**：当 `GrGpu` 创建了一个"借用"（borrowed）模式的信号量（即信号量的生命周期由外部管理），但提交失败时，需要将信号量切换为"已拥有"模式，以确保信号量被正确删除，防止资源泄漏。

## 内部实现细节

1. **友元关系**：`GrGpu` 被声明为友元类，用于调用私有方法 `setIsOwned()`。这种设计将信号量的所有权管理权限限制在 GPU 设备抽象层。

2. **借用 vs 拥有语义**：信号量可以处于两种所有权状态：
   - **借用（borrowed）**：信号量由外部（通常是用户代码）管理生命周期，`GrGpu` 使用后不会删除它。
   - **拥有（owned）**：信号量由 Ganesh 内部管理，`GrGpu` 负责在适当时机删除它。
   - 当借用的信号量提交失败时，如果不切换为拥有状态就可能导致信号量永远不会被释放。

3. **纯虚接口设计**：类中没有任何数据成员，是一个纯粹的接口类。所有状态（如平台信号量句柄、所有权标志）都存储在后端特定的派生类中。

4. **虚析构函数**：空的虚析构函数确保通过基类指针删除派生类对象时能够正确调用派生类析构函数，释放后端 GPU 资源。

## 依赖关系

- **`include/gpu/ganesh/GrBackendSemaphore.h`**：提供 `GrBackendSemaphore` 公共句柄类

## 设计模式与设计决策

1. **策略/桥接模式**：`GrSemaphore` 作为抽象接口，将信号量的使用（`GrGpu`）与具体实现（后端特定类）分离。`GrGpu` 通过统一的 `GrSemaphore` 接口操作信号量，无需了解后端细节。

2. **所有权转移安全机制**：`setIsOwned()` 方法是一种防御性设计，处理了"借用信号量提交失败"这一边界情况。通过将借用切换为拥有，确保信号量不会因为异常路径而泄漏。

3. **最小接口原则**：接口仅包含必要的两个方法（`backendSemaphore()` 和 `setIsOwned()`），将复杂性推迟到后端实现中，保持基类简洁。

4. **内部 vs 公共类型分离**：`GrSemaphore` 是内部类型（定义在 `src/` 中），而 `GrBackendSemaphore` 是公共类型（定义在 `include/` 中）。用户通过 `GrBackendSemaphore` 与信号量交互，内部通过 `GrSemaphore` 管理生命周期。

## 性能考量

- **虚函数开销**：作为纯虚接口，调用 `backendSemaphore()` 和 `setIsOwned()` 需要通过虚函数表进行间接调用。但信号量操作本身频率很低（通常每帧仅几次），虚函数开销可忽略不计。
- **无数据成员**：基类不占用额外内存（除虚函数表指针外），所有数据由派生类管理。
- **值返回 `GrBackendSemaphore`**：`backendSemaphore()` 返回值而非引用，`GrBackendSemaphore` 使用小对象优化（24 字节内联存储），因此复制开销极低。

## 相关文件

- `include/gpu/ganesh/GrBackendSemaphore.h`：公共信号量句柄类
- `src/gpu/ganesh/GrBackendSemaphorePriv.h`：信号量内部数据访问
- `src/gpu/ganesh/GrGpu.h`：GPU 设备抽象基类，创建和管理信号量
- `src/gpu/ganesh/vk/GrVkSemaphore.h`：Vulkan 信号量实现
- `src/gpu/ganesh/mtl/GrMtlSemaphore.h`：Metal 信号量实现
- `src/gpu/ganesh/d3d/GrD3DSemaphore.h`：Direct3D 信号量实现
