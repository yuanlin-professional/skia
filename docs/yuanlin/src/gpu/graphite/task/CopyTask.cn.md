# CopyTask

> 源文件
> - src/gpu/graphite/task/CopyTask.h
> - src/gpu/graphite/task/CopyTask.cpp

## 概述

`CopyTask` 文件定义了三种 GPU 拷贝任务类型，用于在不同类型的 GPU 资源间传输数据。这些任务类型包括：`CopyBufferToBufferTask`（缓冲区到缓冲区）、`CopyTextureToBufferTask`（纹理到缓冲区）和 `CopyTextureToTextureTask`（纹理到纹理）。所有任务都继承自 `Task` 基类，提供统一的资源准备和命令录制接口。

拷贝任务在 Graphite 管线中用于多种场景：纹理回读（读取 GPU 纹理到 CPU 可访问内存）、纹理 mipmap 生成辅助、临时纹理内容转移、绘制结果混合（通过目标纹理拷贝实现）。所有拷贝操作都是异步的 GPU 命令，不会阻塞 CPU 执行。

## 架构位置

拷贝任务在任务系统中承担数据传输职责：

- **缓冲区到缓冲区**: 用于数据重组、间接绘制参数构建、计算着色器输出处理
- **纹理到缓冲区**: 用于纹理回读（`readPixels`）、截图、调试验证
- **纹理到纹理**: 用于 mipmap 链构建、混合操作准备、纹理内容复制

这些任务通常作为其他任务的前置或后置步骤，不单独使用。它们与 `UploadTask`、`RenderPassTask`、`ComputeTask` 协同工作，构成完整的数据流转管线。

## 主要类与结构体

### CopyBufferToBufferTask

从源缓冲区拷贝数据到目标缓冲区。

**成员变量**:
- `const Buffer* fSrcBuffer`: 源缓冲区（非拥有指针，由 `UploadBufferManager` 管理）
- `size_t fSrcOffset`: 源偏移（字节）
- `sk_sp<Buffer> fDstBuffer`: 目标缓冲区（智能指针）
- `size_t fDstOffset`: 目标偏移（字节）
- `size_t fSize`: 拷贝大小（字节）

**工厂方法**:
```cpp
static sk_sp<CopyBufferToBufferTask> Make(const Buffer* srcBuffer, size_t srcOffset,
                                          sk_sp<Buffer> dstBuffer, size_t dstOffset, size_t size)
```
创建缓冲区到缓冲区拷贝任务，断言验证偏移和大小在缓冲区范围内。

### CopyTextureToBufferTask

从纹理拷贝像素数据到缓冲区（回读操作）。

**成员变量**:
- `sk_sp<TextureProxy> fTextureProxy`: 源纹理代理
- `SkIRect fSrcRect`: 源纹理区域
- `sk_sp<Buffer> fBuffer`: 目标缓冲区
- `size_t fBufferOffset`: 缓冲区偏移
- `size_t fBufferRowBytes`: 每行字节数（对齐后）

**工厂方法**:
```cpp
static sk_sp<CopyTextureToBufferTask> Make(sk_sp<TextureProxy> textureProxy, SkIRect srcRect,
                                           sk_sp<Buffer> buffer, size_t bufferOffset,
                                           size_t bufferRowBytes)
```
创建纹理到缓冲区拷贝任务，空纹理代理返回 nullptr。

**访问者接口**:
```cpp
bool visitProxies(...) override
```
访问源纹理代理（只读访问）。

### CopyTextureToTextureTask

从源纹理拷贝区域到目标纹理（必须相同格式）。

**成员变量**:
- `sk_sp<TextureProxy> fSrcProxy`: 源纹理代理
- `SkIRect fSrcRect`: 源区域
- `sk_sp<TextureProxy> fDstProxy`: 目标纹理代理
- `SkIPoint fDstPoint`: 目标起始点
- `int fDstLevel`: 目标 mipmap 层级

**工厂方法**:
```cpp
static sk_sp<CopyTextureToTextureTask> Make(sk_sp<TextureProxy> srcProxy, SkIRect srcRect,
                                            sk_sp<TextureProxy> dstProxy, SkIPoint dstPoint,
                                            int dstLevel = 0)
```
创建纹理到纹理拷贝任务，验证格式一致性（不同格式记录错误日志并返回 nullptr）。

**访问者接口**:
```cpp
bool visitProxies(...) override
```
访问源纹理代理（只读）和目标纹理代理（写入，仅当 `readsOnly=false` 时）。

## 公共 API 函数

### CopyBufferToBufferTask 接口

```cpp
Status prepareResources(...) override
```
直接返回 `kSuccess`，无需准备额外资源（缓冲区应已分配）。

```cpp
Status addCommands(...) override
```
调用 `CommandBuffer::copyBufferToBuffer()` 录制拷贝命令，成功返回 `kSuccess`，失败返回 `kFail`。

### CopyTextureToBufferTask 接口

```cpp
Status prepareResources(...) override
```
验证源纹理已实例化或为延迟实例化类型，不主动实例化（假设前置任务已初始化纹理内容）。返回 `kSuccess`。

**注释说明**: 未来应参与临时资源回收机制（类似 `RenderPassTask`），当前实现绕过复用系统。

```cpp
Status addCommands(...) override
```
调用 `CommandBuffer::copyTextureToBuffer()` 录制回读命令。返回 `kSuccess` 或 `kFail`。

**注释说明**: 当前仅用于单次回读操作，未来可能默认返回 `kDiscard`。

### CopyTextureToTextureTask 接口

```cpp
Status prepareResources(...) override
```
实例化目标纹理代理（不实例化源纹理，假设前置任务已处理）。失败记录错误日志并返回 `kFail`。

**注释说明**:
- 当前存在特殊情况：临时设备的目标回读拷贝，源纹理由后续 `RenderPassTask` 实例化
- 未来应通过 `ScratchResourceManager` 实例化目标纹理并参与回收机制
- 未来应支持返回临时纹理（需要明确返回时机）

```cpp
Status addCommands(...) override
```
断言源纹理已实例化，调用 `CommandBuffer::copyTextureToTexture()` 录制拷贝命令。返回 `kSuccess` 或 `kFail`。

**注释说明**: 未来应支持指定拷贝是否可重复（如混合需要的目标回读 vs 一次性客户端拷贝请求）。

## 内部实现细节

### 缓冲区拷贝验证

`CopyBufferToBufferTask::Make()` 使用断言确保：
```cpp
SkASSERT(srcBuffer && dstBuffer);
SkASSERT(size <= srcBuffer->size() - srcOffset);
SkASSERT(size <= dstBuffer->size() - dstOffset);
```
验证缓冲区有效性和拷贝范围合法性。

### 格式兼容性检查

`CopyTextureToTextureTask::Make()` 验证纹理格式：
```cpp
TextureFormat srcFormat = TextureInfoPriv::ViewFormat(srcProxy->textureInfo());
TextureFormat dstFormat = TextureInfoPriv::ViewFormat(dstProxy->textureInfo());
if (srcFormat != dstFormat) {
    SKGPU_LOG_E("Unable to copy between textures of different formats...");
    return nullptr;
}
```
纹理到纹理拷贝不执行格式转换，不同格式必须拒绝。

### 源纹理实例化策略

纹理拷贝任务不主动实例化源纹理，基于以下假设：
- 源纹理内容应由前置任务初始化（`UploadTask`、`RenderPassTask` 等）
- 未实例化的源纹理意味着内容未定义，拷贝无意义
- 延迟实例化类型（lazy proxies）在命令录制时自动实例化

**特殊情况**: 临时设备的回读拷贝可能在源纹理实例化前创建任务，依赖后续任务实例化。

### 目标纹理实例化

`CopyTextureToTextureTask` 在 `prepareResources()` 中实例化目标：
```cpp
if (!TextureProxy::InstantiateIfNotLazy(resourceProvider, fDstProxy.get())) {
    SKGPU_LOG_E("Could not instantiate dst texture proxy...");
    return Status::kFail;
}
```
确保拷贝目标在命令录制前已分配。

### 调试转储

所有任务类型实现 `dump()` 方法（`SK_DUMP_TASKS` 宏启用时），输出任务类型、源和目标指针信息，用于任务图可视化调试。

## 依赖关系

### 直接依赖

**头文件**:
- `src/gpu/graphite/task/Task.h`: 任务基类
- `include/core/SkPoint.h`, `include/core/SkRect.h`: 几何类型
- `include/core/SkRefCnt.h`: 智能指针

**实现文件**:
- `src/gpu/graphite/Buffer.h`: 缓冲区对象
- `src/gpu/graphite/Texture.h`: 纹理对象
- `src/gpu/graphite/TextureProxy.h`: 纹理代理
- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/TextureInfoPriv.h`: 纹理信息私有接口
- `src/gpu/graphite/Log.h`: 日志工具

### 使用场景

- **回读操作**: `readPixels()` 使用 `CopyTextureToBufferTask`
- **截图/调试**: 纹理内容提取到 CPU 内存
- **混合操作**: `CopyTextureToTextureTask` 准备目标纹理用于混合
- **Mipmap 生成**: 拷贝纹理到不同 mipmap 层级
- **间接绘制**: `CopyBufferToBufferTask` 重组绘制参数

### 协作对象

- **CommandBuffer**: 录制实际的 GPU 拷贝命令
- **ResourceProvider**: 实例化纹理代理
- **UploadBufferManager**: 管理源缓冲区（针对 Buffer-to-Buffer）
- **TextureProxy**: 延迟纹理分配和实例化

## 设计模式与设计决策

### 类型分离设计

三种独立任务类型而非统一接口的原因：
- **类型安全**: 编译期区分不同拷贝类型，避免运行时类型错误
- **接口明确**: 每种类型暴露特定参数（如纹理拷贝有 mipmap 层级参数）
- **优化机会**: 后端可针对不同拷贝类型选择最优实现

### 非拥有源缓冲区指针

`CopyBufferToBufferTask` 对源缓冲区使用裸指针：
- **生命周期保证**: `UploadBufferManager` 确保缓冲区在录制完成前有效
- **避免循环引用**: 上传缓冲区由 `Recording` 持有，任务持有 `Recording`，裸指针打破循环
- **性能优化**: 减少引用计数开销

### 格式一致性要求

纹理到纹理拷贝要求相同格式：
- **硬件限制**: 大多数 GPU 的拷贝命令不支持格式转换
- **性能考虑**: 格式转换应使用渲染通道（可利用纹理采样和像素着色器）
- **明确语义**: 拷贝是位拷贝，转换是语义转换，分离职责

### 延迟源实例化

不主动实例化源纹理的设计：
- **假设前置**: 依赖任务图正确排序，源内容由前置任务准备
- **避免浪费**: 不为未定义内容分配资源
- **调试友好**: 断言失败清晰指出任务图错误

### 未来改进方向

代码注释指出多个改进点：
1. **临时资源参与**: 拷贝任务应参与 `ScratchResourceManager` 的复用机制
2. **可重复性标识**: 区分一次性拷贝和可重复拷贝
3. **丢弃策略**: 单次操作应返回 `kDiscard` 优化任务图
4. **作用域集成**: 将拷贝任务包装到 `DrawTask` 等作用域任务中

## 性能考量

### GPU 异步执行

所有拷贝都是 GPU 命令，异步执行不阻塞 CPU，允许 CPU 继续录制后续命令。

### DMA 引擎优化

现代 GPU 使用专用 DMA 引擎执行拷贝，与渲染引擎并行工作，不占用着色器资源。

### 缓存局部性

纹理拷贝可能利用 GPU 缓存层次，相邻像素访问受益于缓存行填充。

### 对齐要求

虽然任务本身不处理对齐，调用者需确保：
- 缓冲区偏移满足后端对齐要求（通常 4 或 16 字节）
- 纹理行字节数对齐到 GPU 缓存行（由 `Caps::getAlignedTextureDataRowBytes()` 计算）

### 避免格式转换

纹理到纹理拷贝的格式一致性要求避免昂贵的像素转换开销，纯位拷贝最高效。

### 回读瓶颈

纹理到缓冲区拷贝涉及 GPU 到 CPU 数据传输，是主要性能瓶颈：
- 需要同步点（等待 GPU 完成）
- 带宽受限于 PCIe 总线（独立显卡）或内存控制器（集成显卡）
- 应尽量避免频繁回读

## 相关文件

### 任务系统

- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/task/UploadTask.h`: 上传任务（CPU 到 GPU 传输）
- `src/gpu/graphite/task/RenderPassTask.h`: 渲染通道任务
- `src/gpu/graphite/task/DrawTask.h`: 绘制任务容器

### 资源类型

- `src/gpu/graphite/Buffer.h`: GPU 缓冲区对象
- `src/gpu/graphite/Texture.h`: GPU 纹理对象
- `src/gpu/graphite/TextureProxy.h`: 纹理代理（延迟分配）

### 命令系统

- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区接口
- `src/gpu/graphite/vk/VulkanCommandBuffer.h`: Vulkan 拷贝实现
- `src/gpu/graphite/mtl/MtlCommandBuffer.h`: Metal 拷贝实现
- `src/gpu/graphite/dawn/DawnCommandBuffer.h`: Dawn 拷贝实现

### 资源管理

- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理器
- `src/gpu/graphite/UploadBufferManager.h`: 上传缓冲区管理器
