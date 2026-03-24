# AsyncReadTypes

> 源文件:
> - `src/gpu/AsyncReadTypes.h`

## 概述

`AsyncReadTypes.h` 定义了 Skia GPU 层中用于异步像素读取的核心模板类型。当客户端请求从 GPU 表面异步读取像素数据时，数据通过映射的 GPU 缓冲区传递给客户端。此头文件提供了管理这些映射缓冲区生命周期的 `TClientMappedBufferManager` 以及封装异步读取结果的 `TAsyncReadResult`，确保跨线程的缓冲区映射/取消映射操作安全进行。

## 架构位置

```
Skia GPU 层
  └── 异步读取子系统
        ├── TClientMappedBufferManager<T, IDType> (映射缓冲区生命周期管理)
        ├── TAsyncReadResult<T, IDType, TransferResultType> (异步读取结果封装)
        └── SkMessageBus (跨线程消息传递机制)
```

这些模板类被 Ganesh (`GrGpu`) 和 Graphite 后端实例化使用。

## 主要类与结构体

### `TClientMappedBufferManager<T, IDType>`
管理交给客户端的映射缓冲区的生命周期：
- **T**：缓冲区类型（如 `GrGpuBuffer`）。
- **IDType**：所有者标识类型，用于消息路由。
- 使用 `SkMessageBus` 接收缓冲区已完成使用的消息。
- 维护 `fClientHeldBuffers`（`std::forward_list<sk_sp<T>>`）追踪当前交给客户端的缓冲区。

#### `BufferFinishedMessage`
- 内部消息类型，客户端完成缓冲区使用后发送。
- 包含 `fBuffer`（缓冲区引用）和 `fIntendedRecipient`（目标接收者 ID）。
- 支持移动语义，移动后将原消息的接收者标记为无效。

### `TAsyncReadResult<T, IDType, TransferResultType>`
- 继承自 `SkImage::AsyncReadResult`，封装异步读取的像素数据。
- 支持多平面数据（如 YUV 格式），每个平面可以是映射缓冲区或 CPU 端数据。
- 析构时自动通过消息总线通知缓冲区管理器释放映射缓冲区。

#### `Plane`（内部类）
- 表示异步读取结果中的一个数据平面。
- 可以持有映射缓冲区（`fMappedBuffer`，零拷贝）或 CPU 数据（`fData`，像素转换后的副本）。
- `releaseMappedBuffer()` 通过消息总线发送释放通知。

## 公共 API 函数

### TClientMappedBufferManager
- **`TClientMappedBufferManager(IDType ownerID)`**：构造函数，使用所有者 ID 初始化消息收件箱。
- **`ownerID()`**：返回所有者的唯一标识，用于初始化消息的接收者字段。
- **`insert(sk_sp<T> b)`**：注册一个即将交给客户端的映射缓冲区。
- **`process()`**：轮询消息总线，处理所有已返回的缓冲区（调用 `unmap()`）。
- **`abandon()`**：通知管理器上下文已被放弃，清空缓冲区列表，不再执行取消映射。

### TAsyncReadResult
- **`count()`**：返回数据平面数量。
- **`data(int i)`**：返回第 i 个平面的数据指针。
- **`rowBytes(int i)`**：返回第 i 个平面每行的字节数。
- **`addTransferResult(...)`**：添加一个传输结果。如果有像素转换器，执行转换并存为 CPU 数据；否则直接保持映射缓冲区引用（零拷贝）。
- **`addCpuPlane(sk_sp<SkData>, size_t rowBytes)`**：直接添加 CPU 端数据平面。

## 内部实现细节

### 跨线程安全模型
1. 所有者线程调用 `insert()` 注册缓冲区，然后将结果传递给客户端。
2. 客户端在任意线程完成数据读取后，`TAsyncReadResult` 析构时通过 `SkMessageBus` 发送 `BufferFinishedMessage`。
3. 所有者线程周期性调用 `process()` 接收消息并调用 `unmap()`。
4. 消息总线确保跨线程通信的安全性。

### 缓冲区双重持有
- 管理器（`fClientHeldBuffers`）和客户端（通过 `TAsyncReadResult`）同时持有缓冲区的 `sk_sp` 引用。
- 客户端释放时发送消息，管理器收到后从列表中移除并取消映射。
- 如果管理器先于客户端销毁，析构函数会直接取消映射所有未返回的缓冲区。

### 零拷贝 vs 转换路径
- **零拷贝路径**：无需像素转换时，客户端直接访问映射缓冲区的数据，避免额外的内存分配和复制。
- **转换路径**：需要像素转换时（如颜色空间或格式转换），分配新的 `SkData`，执行转换后立即取消映射缓冲区。

## 依赖关系

- **Skia 核心**: `SkData`、`SkImage::AsyncReadResult`、`SkRefCnt`
- **消息系统**: `SkMessageBus`
- **容器**: `SkTArray`（STArray）、`std::forward_list`

## 设计模式与设计决策

1. **模板泛型设计**：通过模板参数 T（缓冲区类型）、IDType（标识类型）和 TransferResultType（传输结果类型）实现对不同后端的适配。
2. **消息总线模式**：使用 `SkMessageBus` 实现所有者和客户端之间的松耦合跨线程通信。
3. **RAII 资源管理**：`TAsyncReadResult` 析构时自动发送释放消息；`TClientMappedBufferManager` 析构时自动清理未返回的缓冲区。
4. **零拷贝优化**：尽可能避免数据复制，让客户端直接读取 GPU 映射的内存。
5. **前向链表**：使用 `std::forward_list` 存储客户端持有的缓冲区，适合频繁的首部插入和遍历删除操作。

## 性能考量

- **零拷贝传输**：当不需要像素转换时，客户端直接读取映射缓冲区内存，避免额外的内存分配和复制。
- **轮询机制**：`process()` 采用非阻塞轮询，不会阻塞所有者线程。
- **STArray 优化**：消息接收使用 `STArray<4, ...>` 预分配栈空间，避免少量消息时的堆分配。
- **延迟取消映射**：缓冲区在客户端完成使用后才取消映射，最大化映射窗口。

## 相关文件

- `src/core/SkMessageBus.h` - 跨线程消息总线
- `include/core/SkImage.h` - AsyncReadResult 基类定义
- `include/core/SkData.h` - CPU 端数据容器
- `src/gpu/ganesh/GrGpu.h` - Ganesh 后端的实例化使用
