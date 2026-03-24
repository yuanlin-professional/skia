# Buffer

> 源文件
> - src/gpu/graphite/Buffer.h
> - src/gpu/graphite/Buffer.cpp

## 概述

`Buffer` 是 Graphite 渲染系统中 GPU 缓冲区的抽象基类，提供统一的内存映射接口。它封装了不同后端（Vulkan、Metal、D3D12）的缓冲区对象，支持同步和异步映射操作，并管理缓冲区的生命周期和保护状态。

主要功能包括：
- **内存映射**：提供同步 `map()` 和异步 `asyncMap()` 接口
- **映射状态管理**：跟踪缓冲区是否已映射
- **保护内存支持**：标识缓冲区是否使用受保护内存
- **资源生命周期**：继承自 `Resource`，支持引用计数和缓存
- **后端抽象**：通过虚函数实现特定后端的映射逻辑

## 架构位置

`Buffer` 位于 Graphite 资源管理层的核心：

```
Graphite Resource System
└── Resource (基类)
    └── Buffer (本类) ← GPU 缓冲区抽象
        ├── VulkanBuffer (Vulkan 实现)
        ├── MetalBuffer (Metal 实现)
        └── DawnBuffer (Dawn 实现)
```

使用关系：
```
BufferManager (缓冲区分配)
    ↓
Buffer (缓冲区对象)
    ↓
CommandBuffer (绑定缓冲区)
```

## 主要类与结构体

### Buffer 类

**类定义**：
```cpp
class Buffer : public Resource
```

### 继承关系

```
Resource (基类)
    ↓
Buffer (缓冲区基类)
    ↓
具体后端实现（VulkanBuffer、MetalBuffer 等）
```

### 关键成员变量

| 类型 | 名称 | 说明 |
|------|------|------|
| `void*` | `fMapPtr` | 映射后的 CPU 可访问指针（`nullptr` 表示未映射） |
| `size_t` | `fSize` | 缓冲区大小（字节） |
| `Protected` | `fIsProtected` | 是否为受保护内存 |

## 公共 API 函数

### 1. 属性查询

```cpp
size_t size() const
```
返回缓冲区大小（字节）。

```cpp
Protected isProtected() const
```
返回缓冲区是否使用受保护内存（用于 DRM 内容保护）。

```cpp
bool isMapped() const
```
返回缓冲区是否已映射（`fMapPtr != nullptr`）。

```cpp
virtual bool isUnmappable() const
```
返回缓冲区是否处于不可取消映射状态（默认实现：等价于 `isMapped()`）。

### 2. 内存映射操作

```cpp
void* map()
```

**功能**：同步映射缓冲区，返回 CPU 可访问的内存指针

**行为**：
- 如果已映射，直接返回 `fMapPtr`
- 如果有待完成的异步映射，等待完成
- 否则执行同步映射操作（调用 `onMap()`）

**前提条件**：
- 缓冲区不是受保护内存（`isProtected() == Protected::kNo`）
- 后端不使用异步映射或缓冲区可立即映射

**断言**：
```cpp
SkASSERT(this->isUnmappable() || !this->sharedContext()->caps()->bufferMapsAreAsync());
SkASSERT(this->isProtected() == Protected::kNo);
```

```cpp
void asyncMap(GpuFinishedProc proc = nullptr, GpuFinishedContext ctx = nullptr)
```

**功能**：启动异步映射操作

**参数**：
- `proc`：映射完成回调函数
- `ctx`：回调上下文数据

**前提条件**：
- 后端支持异步映射（`bufferMapsAreAsync() == true`）
- 缓冲区不是受保护内存

**使用场景**：
- 大缓冲区映射（减少阻塞）
- 与 GPU 执行重叠（隐藏延迟）

```cpp
void unmap()
```

**功能**：取消映射缓冲区

**行为**：
- 调用后端的 `onUnmap()` 实现
- 将 `fMapPtr` 设置为 `nullptr`
- 如果有待完成的异步映射，取消该操作

**前提条件**：
- 缓冲区当前已映射或有待完成的异步映射

### 3. 资源类型

```cpp
const char* getResourceType() const override
```
返回资源类型字符串 `"Buffer"`，用于调试和日志。

## 内部实现细节

### 构造函数

```cpp
Buffer(const SharedContext* sharedContext,
       size_t size,
       Protected isProtected,
       std::string_view label,
       bool reusableRequiresPurgeable = false,
       bool requiresPrepareForReturnToCache = false)
```

**参数说明**：
- `sharedContext`：共享上下文（提供能力查询）
- `size`：缓冲区大小
- `isProtected`：是否为受保护内存
- `label`：调试标签
- `reusableRequiresPurgeable`：可复用缓冲区是否需要标记为可清除
- `requiresPrepareForReturnToCache`：返回缓存前是否需要准备操作

**初始化**：
- 调用基类 `Resource` 构造函数
- 设置 `fSize` 和 `fIsProtected`
- `fMapPtr` 初始化为 `nullptr`

### 纯虚函数接口

子类必须实现以下虚函数：

```cpp
virtual void onMap() = 0
```
后端特定的同步映射实现，应将映射结果存储到 `fMapPtr`。

```cpp
virtual void onUnmap() = 0
```
后端特定的取消映射实现。

```cpp
virtual void onAsyncMap(GpuFinishedProc, GpuFinishedContext)
```
后端特定的异步映射实现（默认实现会触发断言，表示不支持异步映射）。

### 默认异步映射实现

```cpp
void Buffer::onAsyncMap(GpuFinishedProc, GpuFinishedContext) {
    SkASSERT(!this->sharedContext()->caps()->bufferMapsAreAsync());
    SK_ABORT("Async buffer mapping not supported");
}
```

如果后端的 `bufferMapsAreAsync()` 返回 `false`，调用 `asyncMap()` 会触发中止。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `Resource` | 基类，提供资源生命周期管理 |
| `SharedContext` | 提供能力查询（如 `bufferMapsAreAsync()`） |
| `Caps` | 查询缓冲区映射能力 |
| `GpuTypes` | 定义 `GpuFinishedProc` 等回调类型 |

### 被依赖的模块

| 模块 | 依赖原因 |
|------|----------|
| `BufferManager` | 分配和管理 `Buffer` 对象 |
| `CommandBuffer` | 绑定缓冲区到渲染/计算管线 |
| `UploadBufferManager` | 使用传输缓冲区上传数据 |
| `DrawBufferManager` | 管理顶点/索引/Uniform 缓冲区 |

## 设计模式与设计决策

### 1. 模板方法模式

基类定义映射流程，子类实现具体细节：
```cpp
// 基类定义流程
void* Buffer::map() {
    if (!this->isMapped()) {
        this->onMap();  // 调用子类实现
    }
    return fMapPtr;
}

// 子类实现具体后端
void VulkanBuffer::onMap() override {
    vkMapMemory(..., &fMapPtr);
}
```

### 2. 延迟初始化

`fMapPtr` 初始化为 `nullptr`，仅在首次映射时分配：
- 节省不需要映射的缓冲区的资源
- 支持多次映射/取消映射的生命周期

### 3. 保护内存隔离

受保护内存缓冲区不可映射：
```cpp
SkASSERT(this->isProtected() == Protected::kNo);
```

**理由**：
- DRM 内容保护要求数据不可被 CPU 访问
- 防止意外的数据泄露

### 4. 同步与异步映射分离

提供两个独立接口：
- `map()`：阻塞等待，适用于小缓冲区
- `asyncMap()`：非阻塞，适用于大缓冲区或需要重叠的场景

**权衡**：
- 增加了 API 复杂度
- 提供了性能优化的灵活性

### 5. 能力查询驱动

通过 `Caps` 查询确定映射策略：
```cpp
if (!this->sharedContext()->caps()->bufferMapsAreAsync())
```

- 避免硬编码后端差异
- 支持未来新后端扩展

## 性能考量

### 1. 映射状态缓存

```cpp
if (!this->isMapped()) {
    this->onMap();
}
return fMapPtr;
```

避免重复映射调用，直接返回已映射指针。

### 2. 异步映射优化

对于支持异步映射的后端（如 Vulkan、D3D12）：
- 减少 CPU 等待时间
- 允许 GPU 工作与映射操作重叠
- 提高帧率稳定性

### 3. 受保护内存的零开销

保护检查在编译时优化为 no-op（Release 构建）：
```cpp
SkASSERT(this->isProtected() == Protected::kNo);
```

### 4. 虚函数开销

映射操作使用虚函数，有轻微开销，但：
- 映射操作相对不频繁（每帧几次到几十次）
- 映射本身涉及系统调用，虚函数开销可忽略
- 简化了跨后端代码

### 5. 缓冲区复用

继承自 `Resource` 的缓存机制：
- 减少缓冲区分配次数
- 降低内存碎片
- 提高稳态性能

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/Resource.h` | 基类 | 资源生命周期管理 |
| `src/gpu/graphite/BufferManager.h` | 使用者 | 缓冲区分配和管理 |
| `src/gpu/graphite/vk/VulkanBuffer.h` | 子类 | Vulkan 实现 |
| `src/gpu/graphite/mtl/MtlBuffer.h` | 子类 | Metal 实现 |
| `src/gpu/graphite/dawn/DawnBuffer.h` | 子类 | Dawn 实现 |
| `src/gpu/graphite/Caps.h` | 能力查询 | 映射能力查询 |
| `src/gpu/graphite/SharedContext.h` | 上下文 | 共享上下文 |
| `src/gpu/graphite/CommandBuffer.h` | 使用者 | 绑定缓冲区 |
| `include/gpu/GpuTypes.h` | 类型定义 | 回调函数类型 |
