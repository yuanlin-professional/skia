# VulkanSharedContext

> 源文件: `src/gpu/graphite/vk/VulkanSharedContext.h`, `src/gpu/graphite/vk/VulkanSharedContext.cpp`

## 概述

`VulkanSharedContext` 是 Skia Graphite Vulkan 后端的共享上下文，继承自 `SharedContext` 基类。它持有所有 Recorder 和 Context 共享的 Vulkan 状态——包括 Vulkan 设备、物理设备、接口、内存分配器和管线缓存。作为线程安全的共享资源，它在 Context 的整个生命周期中存在，被所有关联的 Recorder 引用。

## 架构位置

- **上层**: 继承自 `SharedContext`，由 `Context` 持有
- **核心角色**: Vulkan 全局状态的持有者和线程安全的资源创建入口
- **下游**: 被 `VulkanResourceProvider`、`VulkanCommandBuffer` 和所有 Vulkan 资源类引用

## 主要类与结构体

### `VulkanThreadSafeResourceProvider` 类

继承自 `ThreadSafeResourceProvider`，提供线程安全的渲染通道查找/创建。

### `VulkanSharedContext` 类

**核心 Vulkan 对象**:
- `fInterface` — Vulkan 接口函数指针表
- `fMemoryAllocator` — Vulkan 内存分配器
- `fPhysDevice` — 物理设备
- `fDevice` — 逻辑设备
- `fQueueIndex` — 图形队列索引

**管线缓存**:
- `fPipelineCache` — `VkPipelineCache` 句柄
- `fHasNewVkPipelineCacheData` — 原子标记，指示是否有新的管线数据需要持久化
- `fLastKnownPersistentPipelineStorageSize` — 上次持久化时的缓存大小

**设备丢失追踪**:
- `fDeviceIsLost` — 互斥保护的设备丢失标志
- `fDeviceLostContext` / `fDeviceLostProc` — 设备丢失回调

## 公共 API 函数

### 工厂和访问器

- **`Make(VulkanBackendContext, ContextOptions)`** — 静态工厂方法，验证 Vulkan 上下文并创建实例
- **`vulkanCaps()`** — 返回 Vulkan 特有的能力对象
- **`interface()`** — 返回 Vulkan 接口
- **`memoryAllocator()`** — 返回内存分配器
- **`physDevice()`** / **`device()`** — 返回物理/逻辑设备
- **`queueIndex()`** — 返回图形队列索引

### 资源管理

- **`makeResourceProvider(SingleOwner*, uint32_t recorderID, size_t resourceBudget)`** — 为 Recorder 创建新的资源提供者
- **`threadSafeResourceProvider()`** — 返回线程安全的资源提供者

### 管线缓存

- **`getPipelineCache()`** — 返回 VkPipelineCache 句柄
- **`pipelineCompileWasRequired()`** — 标记有新的管线编译
- **`syncPipelineData(PersistentPipelineStorage*, size_t maxSize)`** — 将管线缓存数据同步到持久存储

### 错误处理

- **`checkVkResult(VkResult)`** — 检查 Vulkan 操作结果，设备丢失时更新状态
- **`isDeviceLost()`** — 线程安全地检查设备是否已丢失

## 内部实现细节

### 创建流程

`Make()` 工厂方法执行以下验证和初始化：
1. 验证 `VulkanBackendContext` 中的必要句柄（instance、physicalDevice、device、queue）
2. 验证 `fGetProc` 函数指针有效
3. 通过 `skgpu::MakeInterface()` 创建 Vulkan 接口
4. 创建 `VulkanCaps`（查询设备特性和扩展）
5. 验证内存分配器存在
6. 构造 VulkanSharedContext

### 管线缓存持久化

`createPipelineCache()` 支持从持久存储加载管线缓存：
1. 从 `PersistentPipelineStorage` 加载缓存数据
2. 验证缓存头部格式（V1 header，16 + VK_UUID_SIZE 字节）
3. 检查 vendorID、deviceID 和 pipelineCacheUUID 匹配
4. 匹配成功则使用缓存数据初始化 VkPipelineCache

`syncPipelineData()` 将新的管线缓存数据写入持久存储，仅在有新的管线编译发生时执行。

### 设备丢失处理

设备丢失状态通过互斥锁（`fDeviceIsLostMutex`）保护，确保多线程下的安全读写。`checkVkResult()` 在检测到 `VK_ERROR_DEVICE_LOST` 时更新此状态并调用用户注册的回调。

### 线程安全资源提供者

`VulkanThreadSafeResourceProvider` 封装了一个独立的 `ResourceProvider`，提供线程安全的渲染通道查找/创建。其资源预算使用独立的 `kThreadedSafeResourceBudget`。

## 依赖关系

- `SharedContext` — 基类
- `VulkanCaps` — Vulkan 能力查询
- `VulkanInterface` — Vulkan API 函数指针
- `VulkanMemoryAllocator` — GPU 内存分配
- `VulkanBackendContext` — 外部传入的 Vulkan 上下文信息
- `PersistentPipelineStorage` — 管线缓存持久化存储

## 设计模式与设计决策

### 共享所有权

VulkanSharedContext 由 Context 持有，所有 Recorder 通过 SharedContext 引用共享 Vulkan 状态。这避免了每个 Recorder 持有 Vulkan 设备的独立副本。

### 管线缓存持久化

支持跨应用启动的管线缓存复用，通过 `PersistentPipelineStorage` 接口抽象持久化策略。缓存数据包含设备标识验证，防止在不同设备间误用。

### 原子管线标记

`fHasNewVkPipelineCacheData` 使用 `std::atomic<bool>`，避免在频繁的管线编译路径上使用互斥锁。

## 性能考量

- **管线缓存**: 跨运行的管线缓存复用显著减少首次绘制延迟
- **线程安全**: 设备丢失检测使用互斥锁但操作极少（仅在出错时）
- **共享资源**: 避免每个 Recorder 重复创建 Vulkan 对象

## 相关文件

- `src/gpu/graphite/SharedContext.h` — 基类
- `include/gpu/vk/VulkanBackendContext.h` — Vulkan 后端上下文
- `src/gpu/graphite/vk/VulkanCaps.h` — Vulkan 能力
- `src/gpu/graphite/vk/VulkanResourceProvider.h` — 资源提供者
- `include/gpu/graphite/PersistentPipelineStorage.h` — 管线缓存持久化
