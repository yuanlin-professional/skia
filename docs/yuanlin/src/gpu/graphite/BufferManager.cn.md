# BufferManager (缓冲区管理器)

> 源文件：[src/gpu/graphite/BufferManager.h](../../../../src/gpu/graphite/BufferManager.h)、[src/gpu/graphite/BufferManager.cpp](../../../../src/gpu/graphite/BufferManager.cpp)

## 概述

`BufferManager.h` 定义了三个核心的缓冲区管理类：`BufferSubAllocator`、`DrawBufferManager` 和 `StaticBufferManager`。这些类共同负责管理 Graphite 中所有动态和静态 GPU 缓冲区的分配、子分配、映射和生命周期管理。

- **`BufferSubAllocator`**：RAII 风格的缓冲区子分配器，在大缓冲区内进行细粒度的子范围分配。
- **`DrawBufferManager`**：管理每帧动态数据（顶点、索引、uniform、storage 缓冲区）的上传，自动处理映射或传输缓冲区拷贝。
- **`StaticBufferManager`**：一次性上传静态数据（如细分索引缓冲区），生命周期与 Context 一致。

## 架构位置

缓冲区管理器位于资源分配和绘制记录之间：

- **上游**：`DrawPass`、`RenderStep`、计算着色器等请求缓冲区空间。
- **下游**：通过 `ResourceProvider` 获取底层 GPU 缓冲区，通过 `Recording` 转移给 `CommandBuffer`。
- **协作**：`UploadBufferManager` 处理映射不可用时的传输缓冲区拷贝。

## 主要类与结构体

### `BufferSubAllocator`
RAII 子分配器，支持在大缓冲区内进行多次子分配。

**核心成员：**
- `fBuffer`：底层 GPU 缓冲区。
- `fMappedPtr`：映射的 CPU 地址（可为 null，表示仅 GPU 使用）。
- `fOffset / fStride / fRemaining`：当前分配位置和剩余容量。

**关键方法：**
- `getMappedSubrange(count, stride, align)`：分配可映射的子范围。
- `getSubrange(count, stride, align)`：分配仅 GPU 使用的子范围。
- `appendMappedWithStride(count)`：追加与前一次分配连续的映射范围。
- `reset()`：归还缓冲区到管理器的复用池。
- `resetForNewBinding()`：重置对齐以适应新的绑定点。

### `DrawBufferManager`
管理所有动态缓冲区分配。

**核心成员：**
- `fCurrentBuffers`：8 种缓冲区类型的 `BufferState` 数组。
- `fUsedBuffers`：已使用的缓冲区列表（转移给 Recording）。
- `fClearList`：需要清零的缓冲区区域列表。

**缓冲区类型（8 种）：**
0. 顶点缓冲区
1. 索引缓冲区
2. Uniform 缓冲区
3. Storage 缓冲区（可映射）
4. GPU 专用 Storage 缓冲区
5. 顶点 Storage 缓冲区
6. 索引 Storage 缓冲区
7. 间接 Storage 缓冲区

**关键方法：**
- `getMappedVertexBuffer / getMappedIndexBuffer / getMappedUniformBuffer / getMappedStorageBuffer`：获取可映射的各类缓冲区。
- `getStorage / getVertexStorage / getIndexStorage / getIndirectStorage`：获取 GPU 专用缓冲区。
- `getScratchStorage(size)`：获取可复用的 scratch 存储缓冲区。
- `transferToRecording(Recording*) -> bool`：最终化并转移所有缓冲区到 Recording。

### `DrawBufferManager::Options`
配置选项：顶点/索引/Storage 缓冲区的最小和最大大小。

### `StaticBufferManager`
一次性静态数据上传。

**关键方法：**
- `getVertexWriter(count, stride, binding)`：获取静态顶点数据写入器。
- `getIndexWriter(size, binding)`：获取静态索引数据写入器。
- `finalize(Context*, QueueManager*, GlobalCache*) -> FinishResult`：压缩、私有化静态数据并记录 GPU 拷贝任务。

## 内部实现细节

### BufferSubAllocator 的对齐策略
- 第一次子分配或 `resetForNewBinding()` 后：对齐到 stride、绑定对齐和额外对齐的 LCM。
- 后续子分配：仅对齐到 stride 和额外对齐，避免不必要的空洞。

### 缓冲区大小增长
`DrawBufferManager` 使用指数增长策略（`fLastBufferSize`），缓冲区大小在 `minBlockSize` 和 `maxBlockSize` 之间翻倍增长，摊销大型 Recording 的分配次数。

### Scratch 缓冲区机制
- `getScratchStorage` 返回的 `BufferSubAllocator` 归还时，整个缓冲区可被后续请求完全复用。
- 使用 `fUnavailableScratchBuffers` 集合跟踪已分发的 scratch 缓冲区，避免同一 Recording 内的冲突。

### 映射失败处理
如果任何缓冲区映射失败，`fMappingFailed` 标记为 true，后续的 `transferToRecording` 返回 false，整个 Recording 快照失败。

## 依赖关系

- `ResourceProvider`：底层缓冲区创建。
- `Buffer`：GPU 缓冲区对象。
- `Caps`：对齐需求和能力查询。
- `UploadBufferManager`：传输缓冲区管理（用于不支持直接映射的后端）。
- `Recording`：最终的缓冲区所有权接收者。

## 设计模式与设计决策

1. **RAII 子分配器**：`BufferSubAllocator` 在析构时自动归还缓冲区，防止泄漏。
2. **统一的缓冲区状态管理**：8 种缓冲区类型使用相同的 `BufferState` 结构和分配逻辑。
3. **延迟绑定静态数据**：`StaticBufferManager` 使用后写入模式，最终化时才确定 GPU 私有缓冲区的绑定信息。
4. **自动传输缓冲区回退**：当直接映射不可用时，自动使用传输缓冲区进行 CPU -> GPU 数据传输。

## 性能考量

- 缓冲区子分配避免了每次绘制创建独立缓冲区的开销。
- 指数增长策略减少了大型场景中的分配次数。
- Scratch 缓冲区复用最小化 Recording 内的内存使用。
- 对齐优化减少了缓冲区内的空洞。

## 相关文件

- `src/gpu/graphite/Buffer.h/.cpp`：GPU 缓冲区。
- `src/gpu/graphite/ResourceProvider.h/.cpp`：资源提供者。
- `src/gpu/graphite/UploadBufferManager.h/.cpp`：上传缓冲区管理。
- `src/gpu/graphite/ResourceTypes.h`：BufferType、AccessPattern 等。
- `src/gpu/BufferWriter.h`：缓冲区写入器。
