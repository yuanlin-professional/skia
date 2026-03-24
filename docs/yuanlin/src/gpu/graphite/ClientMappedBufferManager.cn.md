# ClientMappedBufferManager (客户端映射缓冲区管理器)

> 源文件：[src/gpu/graphite/ClientMappedBufferManager.h](../../../../src/gpu/graphite/ClientMappedBufferManager.h)、[src/gpu/graphite/ClientMappedBufferManager.cpp](../../../../src/gpu/graphite/ClientMappedBufferManager.cpp)

## 概述

`ClientMappedBufferManager` 管理客户端映射的 GPU 缓冲区的生命周期，主要用于异步像素读取（readPixels）操作。当 GPU 完成数据传输后，需要通知客户端数据已就绪并安全地解除缓冲区映射。该管理器通过消息总线（SkMessageBus）机制接收缓冲区完成消息，确保缓冲区在正确的 Context 上被处理。

`ClientMappedBufferManager` 是通用模板 `TClientMappedBufferManager` 的 Graphite 特化版本，使用 `Buffer` 作为缓冲区类型，`Context::ContextID` 作为接收者标识。

## 架构位置

`ClientMappedBufferManager` 位于 GPU 到 CPU 数据传输的异步回调系统中：

- **上游**：GPU 命令完成回调（finish proc）发送 `BufferFinishedMessage`。
- **下游**：`Context` 在处理消息时回调客户端的 readPixels 完成函数。
- **通信机制**：通过 `SkMessageBus` 进行跨线程消息传递。

## 主要类与结构体

### `ClientMappedBufferManager`
继承自 `skgpu::TClientMappedBufferManager<Buffer, Context::ContextID>`。构造函数接受 `Context::ContextID` 作为消息接收者标识。

## 公共 API 函数

### `SkShouldPostMessageToBus`
```cpp
bool SkShouldPostMessageToBus(const BufferFinishedMessage&, Context::ContextID potentialRecipient);
```
消息总线路由函数。通过比较消息的 `fIntendedRecipient` 和潜在接收者的 ContextID，确定消息是否应投递到指定的 Context。

## 内部实现细节

- `.cpp` 文件使用 `DECLARE_SKMESSAGEBUS_MESSAGE` 宏注册消息类型到 SkMessageBus 系统。
- 消息路由是简单的 ID 比较，确保缓冲区完成消息只投递给发起请求的 Context。
- `false` 模板参数表示消息不允许广播（仅发送到匹配的接收者）。

## 依赖关系

### 上游依赖
- `skgpu::TClientMappedBufferManager`：通用模板基类（定义在 `src/gpu/AsyncReadTypes.h`）。
- `Buffer`：Graphite 缓冲区类型。
- `Context::ContextID`：Context 的唯一标识。
- `SkMessageBus`：跨线程消息传递系统。

### 下游使用者
- `Context`：持有管理器实例，处理缓冲区完成消息。
- GPU 命令缓冲区完成回调：发送 `BufferFinishedMessage`。

## 设计模式与设计决策

1. **消息总线模式**：使用 SkMessageBus 解耦 GPU 完成回调和客户端通知，支持跨线程安全通信。

2. **ID 路由**：使用 ContextID 确保消息投递到正确的 Context，支持多 Context 环境。

3. **类型别名包装**：使用独立类（而非 typedef）以支持前向声明。

## 性能考量

- 消息路由是 O(1) 的 ID 比较，开销极小。
- 缓冲区映射和解映射的实际成本由底层 GPU API 决定，管理器本身仅负责生命周期协调。

## 相关文件

- `src/gpu/AsyncReadTypes.h`：`TClientMappedBufferManager` 模板定义。
- `src/gpu/graphite/Buffer.h/.cpp`：Graphite 缓冲区类型。
- `include/gpu/graphite/Context.h`：Context 和 ContextID。
- `src/core/SkMessageBus.h`：消息总线系统。
