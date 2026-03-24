# GrVkSemaphore

> 源文件
> - src/gpu/ganesh/vk/GrVkSemaphore.h
> - src/gpu/ganesh/vk/GrVkSemaphore.cpp

## 概述

`GrVkSemaphore` 是 Skia Ganesh Vulkan 后端中封装 Vulkan 信号量（Semaphore）的类。它继承自 `GrSemaphore`，提供了跨 GPU 队列和跨 API 的同步机制。Vulkan 信号量用于同步 GPU 操作，确保命令按正确的顺序执行，特别是在多个命令缓冲区或队列间协调工作时。

主要职责包括：
- 封装 `VkSemaphore` 对象及其生命周期管理
- 追踪信号量的信号（signal）和等待（wait）状态
- 支持创建新信号量和包装外部信号量
- 管理信号量的所有权（自有或借用）
- 防止信号量的重复信号或等待

该类是 GPU 同步机制的核心组件，用于跨队列提交、跨表面渲染、以及与其他图形 API 的互操作。

## 架构位置

`GrVkSemaphore` 在 Vulkan 同步系统中的位置：

```
Skia GPU 同步机制
  ├─ GrSemaphore (平台无关抽象)
  │   ├─ GrGLSemaphore (OpenGL 实现)
  │   ├─ GrMtlSemaphore (Metal 实现)
  │   └─ GrVkSemaphore (Vulkan 实现) ← 当前类
  │       └─ Resource (Vulkan 资源封装)
  └─ 使用场景
      ├─ 队列提交同步
      ├─ 表面呈现
      └─ 跨 API 互操作
```

该类作为 Vulkan 特定的信号量实现，提供了跨队列和跨表面的同步能力。

## 主要类与结构体

### 核心类

| 类名 | 父类 | 说明 |
|------|------|------|
| `GrVkSemaphore` | `GrSemaphore` | Vulkan 信号量封装 |
| `GrVkSemaphore::Resource` | `GrVkManagedResource` | 信号量资源管理 |

### GrVkSemaphore::Resource

```cpp
class Resource : public GrVkManagedResource {
    VkSemaphore fSemaphore;                          // Vulkan 信号量句柄
    bool fHasBeenSubmittedToQueueForSignal;          // 是否已提交信号操作
    bool fHasBeenSubmittedToQueueForWait;            // 是否已提交等待操作
    bool fIsOwned;                                   // 是否拥有所有权

public:
    VkSemaphore semaphore() const;
    bool shouldSignal() const;                       // 是否应该信号
    bool shouldWait() const;                         // 是否应该等待
    void markAsSignaled();                           // 标记为已信号
    void markAsWaited();                             // 标记为已等待
    void setIsOwned();                               // 设置所有权
};
```

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fResource` | `Resource*` | 信号量资源对象 |

## 公共 API 函数

### 静态工厂方法

```cpp
static std::unique_ptr<GrVkSemaphore> Make(GrVkGpu* gpu, bool isOwned);
```
创建新的 Vulkan 信号量。

**参数**：
- `gpu`：GPU 设备
- `isOwned`：是否拥有所有权（决定析构时是否销毁）

**返回**：信号量的唯一指针，失败返回 `nullptr`

**用途**：在内部创建用于同步的新信号量。

```cpp
static std::unique_ptr<GrVkSemaphore> MakeWrapped(
    GrVkGpu* gpu,
    VkSemaphore semaphore,
    GrSemaphoreWrapType wrapType,
    GrWrapOwnership ownership);
```
包装外部创建的 Vulkan 信号量。

**参数**：
- `gpu`：GPU 设备
- `semaphore`：外部信号量句柄
- `wrapType`：包装类型（`kWillWait` 或 `kWillSignal`）
- `ownership`：所有权（`kBorrow` 或 `kAdopt`）

**返回**：信号量的唯一指针，失败返回 `nullptr`

**用途**：集成外部创建的信号量（如跨 API 互操作）。

### 访问器

```cpp
GrBackendSemaphore backendSemaphore() const override;
```
返回后端无关的信号量表示，用于跨 API 传递。

```cpp
Resource* getResource();
```
返回底层资源对象，供内部使用。

### 所有权管理

```cpp
void setIsOwned() override;
```
将信号量标记为自有，析构时会销毁 Vulkan 对象。

## 内部实现细节

### 信号量创建

`Make` 方法创建新的 Vulkan 信号量：

```cpp
std::unique_ptr<GrVkSemaphore> GrVkSemaphore::Make(GrVkGpu* gpu, bool isOwned) {
    VkSemaphoreCreateInfo createInfo;
    memset(&createInfo, 0, sizeof(VkSemaphoreCreateInfo));
    createInfo.sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO;
    createInfo.pNext = nullptr;
    createInfo.flags = 0;

    VkSemaphore semaphore = VK_NULL_HANDLE;
    VkResult result;
    GR_VK_CALL_RESULT(gpu, result,
        CreateSemaphore(gpu->device(), &createInfo, nullptr, &semaphore));

    if (result != VK_SUCCESS) {
        return nullptr;
    }

    return std::unique_ptr<GrVkSemaphore>(
        new GrVkSemaphore(gpu, semaphore, false, false, isOwned));
}
```

**创建流程**：
1. 初始化创建信息结构体
2. 调用 `vkCreateSemaphore` 创建信号量
3. 检查创建结果
4. 封装为 `GrVkSemaphore` 对象（初始状态：未信号、未等待）

### 包装外部信号量

`MakeWrapped` 方法包装外部信号量：

```cpp
std::unique_ptr<GrVkSemaphore> GrVkSemaphore::MakeWrapped(
    GrVkGpu* gpu,
    VkSemaphore semaphore,
    GrSemaphoreWrapType wrapType,
    GrWrapOwnership ownership) {

    if (VK_NULL_HANDLE == semaphore) {
        SkDEBUGFAIL("Trying to wrap an invalid VkSemaphore");
        return nullptr;
    }

    bool prohibitSignal = GrSemaphoreWrapType::kWillWait == wrapType;
    bool prohibitWait = GrSemaphoreWrapType::kWillSignal == wrapType;

    return std::unique_ptr<GrVkSemaphore>(
        new GrVkSemaphore(gpu, semaphore, prohibitSignal, prohibitWait,
                         kBorrow_GrWrapOwnership != ownership));
}
```

**包装逻辑**：
- **kWillWait**：外部已经信号（或将信号），Skia 只能等待
  - `prohibitSignal = true`：禁止 Skia 再次信号
  - `prohibitWait = false`：允许 Skia 等待
- **kWillSignal**：外部将等待，Skia 需要信号
  - `prohibitSignal = false`：允许 Skia 信号
  - `prohibitWait = true`：禁止 Skia 等待（外部已等待或将等待）

这种设计防止了信号量的误用，确保信号和等待操作的配对正确。

### 状态追踪

`Resource` 类追踪信号量的使用状态：

**shouldSignal()**：
```cpp
bool shouldSignal() const {
    return !fHasBeenSubmittedToQueueForSignal;
}
```
仅当信号量尚未提交信号操作时返回 `true`。Vulkan 信号量只能信号一次（直到被等待）。

**shouldWait()**：
```cpp
bool shouldWait() const {
    return !fHasBeenSubmittedToQueueForWait;
}
```
仅当信号量尚未提交等待操作时返回 `true`。等待未信号的信号量会导致死锁。

**状态更新**：
```cpp
void markAsSignaled() {
    fHasBeenSubmittedToQueueForSignal = true;
}

void markAsWaited() {
    fHasBeenSubmittedToQueueForWait = true;
}
```
在提交命令时调用，标记信号量的当前状态。

### 资源释放

`Resource::freeGPUData` 根据所有权决定是否销毁信号量：

```cpp
void GrVkSemaphore::Resource::freeGPUData() const {
    if (fIsOwned) {
        GR_VK_CALL(fGpu->vkInterface(),
                   DestroySemaphore(fGpu->device(), fSemaphore, nullptr));
    }
}
```

**所有权规则**：
- **自有（Owned）**：由 Skia 创建或采用（adopt），析构时销毁
- **借用（Borrowed）**：外部创建，Skia 不销毁

### 跨 API 互操作

`backendSemaphore()` 方法提供后端无关的表示：

```cpp
GrBackendSemaphore GrVkSemaphore::backendSemaphore() const {
    return GrBackendSemaphores::MakeVk(fResource->semaphore());
}
```

这允许将 Vulkan 信号量传递给其他 API（如 OpenGL 通过 GL_EXT_semaphore 扩展）。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrSemaphore` | 基类，提供平台无关接口 |
| `GrVkManagedResource` | 资源管理基类 |
| `GrVkGpu` | GPU 设备访问 |
| `GrBackendSemaphore` | 跨 API 信号量表示 |
| `GrVkUtil` | Vulkan 工具宏 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrVkGpu` | 创建和管理信号量 |
| `GrVkCommandBuffer` | 在提交时使用信号量同步 |
| `GrDirectContext` | 跨表面和跨队列同步 |
| 表面呈现 | 与 swapchain 同步 |

## 设计模式与设计决策

### 资源-包装器模式
将 Vulkan 资源（`Resource`）与逻辑包装器（`GrVkSemaphore`）分离，`Resource` 负责生命周期，包装器提供高层接口。

### 状态追踪
通过显式追踪信号和等待状态，防止了常见的信号量使用错误（重复信号、等待未信号的信号量）。

### 包装类型区分
`GrSemaphoreWrapType` 明确了外部信号量的使用意图，避免了同步错误。

### 所有权灵活性
支持自有和借用两种所有权模式，适应不同的使用场景（内部创建 vs 外部集成）。

### 跨 API 设计
通过 `GrBackendSemaphore` 提供统一接口，支持 Vulkan 与 OpenGL、Metal 等的互操作。

### 防御性编程
在调试模式下使用 `SkDEBUGFAIL` 检测无效的信号量句柄，早期捕获错误。

## 性能考量

### 轻量级对象
`GrVkSemaphore` 本身只包含一个指针，创建和销毁开销极小。

### 引用计数
`Resource` 使用引用计数，允许多个对象共享同一信号量资源，减少创建开销。

### 状态追踪开销
状态追踪只需两个布尔变量，内存和计算开销几乎为零，但能防止昂贵的同步错误。

### 信号量复用
通过状态追踪，Skia 可以在信号量完成后重用它（虽然当前实现未明确支持，但架构允许）。

### 跨队列同步成本
Vulkan 信号量是跨队列同步的标准机制，相比其他方案（如栅栏 + 轮询）更高效。

### 避免过度同步
通过 `shouldSignal` 和 `shouldWait` 检查，避免提交不必要的同步操作。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/GrSemaphore.h` | 父类 | 平台无关信号量抽象 |
| `src/gpu/ganesh/vk/GrVkManagedResource.h` | 基类 | Vulkan 资源管理 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 依赖 | GPU 设备 |
| `src/gpu/ganesh/vk/GrVkCommandBuffer.h` | 使用者 | 命令缓冲区同步 |
| `include/gpu/ganesh/GrBackendSemaphore.h` | 依赖 | 跨 API 信号量表示 |
| `include/gpu/ganesh/vk/GrVkBackendSemaphore.h` | 依赖 | Vulkan 后端信号量工具 |
