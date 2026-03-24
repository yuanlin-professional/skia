# VulkanBackendSemaphore

> 源文件
> - `src/gpu/graphite/vk/VulkanBackendSemaphore.cpp`

## 概述

`VulkanBackendSemaphore` 提供了 Vulkan 信号量在 Skia Graphite 跨平台信号量接口中的具体实现。该文件定义了 `VulkanBackendSemaphoreData` 类用于封装 `VkSemaphore` 句柄，并通过 `BackendSemaphores` 命名空间提供创建和访问 Vulkan 信号量的工厂函数和访问器。信号量是 GPU 同步的核心机制，用于协调不同队列或与外部系统（如显示合成器）之间的工作提交顺序。

## 架构位置

`VulkanBackendSemaphore` 位于 Graphite 的后端抽象层：

```
skgpu::graphite 同步机制
    ├── BackendSemaphore (跨平台信号量接口)
    │    ├── BackendSemaphoreData (数据基类)
    │    │    └── VulkanBackendSemaphoreData (Vulkan 实现)
    │    └── BackendSemaphorePriv (内部访问辅助)
    └── BackendSemaphores 命名空间
         ├── MakeVulkan() - 创建 Vulkan 信号量
         └── GetVkSemaphore() - 提取 VkSemaphore 句柄
```

它为上层 Graphite API 提供 Vulkan 后端的同步能力，隐藏 Vulkan 特定的实现细节。

## 主要类与结构体

### VulkanBackendSemaphoreData

```cpp
class VulkanBackendSemaphoreData final : public BackendSemaphoreData
```

封装 Vulkan 信号量的数据类。

**核心成员变量：**
- `VkSemaphore fVkSemaphore` - Vulkan 信号量句柄

**核心方法：**
- `VulkanBackendSemaphoreData(VkSemaphore sem)` - 构造函数
- `VkSemaphore semaphore() const` - 获取信号量句柄
- `skgpu::BackendApi type() const override` - 返回后端类型（调试版本）
- `void copyTo(AnyBackendSemaphoreData& dstData) const override` - 拷贝数据

## 公共 API 函数

### 创建 Vulkan 信号量

```cpp
BackendSemaphore BackendSemaphores::MakeVulkan(VkSemaphore sem)
```

从 Vulkan 信号量句柄创建跨平台的 `BackendSemaphore` 对象。

**参数：**
- `sem` - Vulkan 信号量句柄（`VkSemaphore`）

**返回值：**
包装了 Vulkan 信号量的 `BackendSemaphore` 对象。

**实现：**
```cpp
return BackendSemaphorePriv::Make(
    skgpu::BackendApi::kVulkan,
    VulkanBackendSemaphoreData(sem)
);
```

使用私有构造辅助类 `BackendSemaphorePriv::Make()` 创建对象，确保类型安全。

### 提取 Vulkan 信号量句柄

```cpp
VkSemaphore BackendSemaphores::GetVkSemaphore(const BackendSemaphore& sem)
```

从 `BackendSemaphore` 对象中提取底层的 `VkSemaphore` 句柄。

**参数：**
- `sem` - 跨平台信号量对象

**返回值：**
- 有效的 `VkSemaphore` 句柄（如果是 Vulkan 后端且有效）
- `VK_NULL_HANDLE`（如果无效或非 Vulkan 后端）

**实现：**
```cpp
if (!sem.isValid() || sem.backend() != skgpu::BackendApi::kVulkan) {
    return VK_NULL_HANDLE;
}
const VulkanBackendSemaphoreData* vkData = get_and_cast_data(sem);
SkASSERT(vkData);
return vkData->semaphore();
```

先验证信号量有效性和后端类型，然后安全地向下转型并提取句柄。

## 内部实现细节

### 数据封装

`VulkanBackendSemaphoreData` 作为 `BackendSemaphoreData` 的具体实现，仅存储一个 `VkSemaphore` 句柄。设计简洁，没有引用计数或生命周期管理——调用者负责 `VkSemaphore` 的创建和销毁。

### 类型安全检查

```cpp
#if defined(SK_DEBUG)
    skgpu::BackendApi type() const override { return skgpu::BackendApi::kVulkan; }
#endif
```

在调试版本中提供类型标识，用于断言检查，确保不会错误地将 Vulkan 信号量当作其他后端处理。

### 拷贝语义

```cpp
void copyTo(AnyBackendSemaphoreData& dstData) const override {
    dstData.emplace<VulkanBackendSemaphoreData>(fVkSemaphore);
}
```

通过 `emplace` 就地构造新的 `VulkanBackendSemaphoreData`，实现数据拷贝。拷贝的是句柄值，而非底层 Vulkan 对象的深拷贝。

### 辅助函数

```cpp
static const VulkanBackendSemaphoreData* get_and_cast_data(const BackendSemaphore& sem)
```

从 `BackendSemaphore` 中提取数据指针并转型为 Vulkan 特定类型，包含类型断言以确保安全性。

## 依赖关系

**直接依赖：**
- `BackendSemaphore` - 跨平台信号量接口
- `BackendSemaphoreData` - 信号量数据基类
- `BackendSemaphorePriv` - 内部访问辅助类
- `skgpu::BackendApi` - 后端 API 枚举
- `VkSemaphore` - Vulkan 信号量类型（来自 `SkiaVulkan.h`）

**被依赖者：**
- `VulkanQueueManager` - 使用信号量同步队列提交
- `VulkanSharedContext` - 创建和管理信号量
- Graphite 上层录制和提交 API - 通过 `BackendSemaphore` 接口使用
- 外部集成（如窗口系统）- 使用信号量与 Vulkan 交互

## 设计模式与设计决策

### 桥接模式（Bridge Pattern）
将跨平台的 `BackendSemaphore` 接口与 Vulkan 特定的实现分离，允许上层代码统一处理不同后端的同步原语。

### 工厂模式
`MakeVulkan()` 提供统一的创建接口，隐藏内部的 `BackendSemaphorePriv` 构造细节。

### 类型擦除（Type Erasure）
`BackendSemaphore` 使用类型擦除技术封装不同后端的数据，通过 `BackendSemaphoreData` 虚拟接口实现多态。

### 句柄传递
不管理 `VkSemaphore` 的生命周期，仅传递句柄。这种设计将所有权管理责任留给创建者，避免引用计数开销。

### 防御性编程
`GetVkSemaphore()` 在提取句柄前进行多重检查（有效性、后端类型），返回 `VK_NULL_HANDLE` 而非崩溃，提高鲁棒性。

## 性能考量

1. **零开销抽象**
   `VulkanBackendSemaphoreData` 仅存储一个指针大小的句柄，封装开销极小。

2. **避免引用计数**
   不使用智能指针管理 `VkSemaphore`，避免原子操作开销。调用者负责生命周期管理。

3. **内联友好**
   `semaphore()` 等简单访问器易于内联，编译器可优化为直接内存访问。

4. **调试开销隔离**
   `type()` 方法仅在调试版本中存在，发布版本无类型检查开销。

5. **空检查优化**
   `GetVkSemaphore()` 的多重检查在发布版本中可能被编译器优化为单次分支。

## 相关文件

| 文件路径 | 功能描述 |
|---------|---------|
| `include/gpu/graphite/BackendSemaphore.h` | 跨平台信号量接口 |
| `src/gpu/graphite/BackendSemaphorePriv.h` | 信号量内部访问辅助 |
| `include/private/gpu/vk/SkiaVulkan.h` | Vulkan 类型定义 |
| `include/gpu/GpuTypes.h` | GPU 通用类型定义 |
| `src/gpu/graphite/vk/VulkanQueueManager.h` | Vulkan 队列管理器 |
| `src/gpu/graphite/vk/VulkanSharedContext.h` | Vulkan 共享上下文 |
