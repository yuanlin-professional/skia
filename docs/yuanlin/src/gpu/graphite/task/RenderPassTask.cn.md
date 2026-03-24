# RenderPassTask

> 源文件
> - src/gpu/graphite/task/RenderPassTask.h
> - src/gpu/graphite/task/RenderPassTask.cpp

## 概述

`RenderPassTask` 是 Graphite 渲染管线中负责执行实际绘制操作的核心任务类型。它将一个或多个 `DrawPass` 对象转换为单个渲染通道（render pass），在此通道内完成所有绘制命令的录制和执行。该任务管理颜色附件、深度/模板附件、MSAA 解析附件等资源，并处理加载/存储操作、清空、目标纹理读取等复杂渲染配置。

渲染通道任务支持 MSAA（多重采样抗锯齿）渲染、目标读取（用于混合操作）、可丢弃附件池化、重放平移和裁剪、优化的 MSAA 纹理尺寸分配。它是绘制命令从高层 API 转换为 GPU 可执行指令的最后一环，直接操作 `CommandBuffer` 创建后端特定的渲染通道。

## 架构位置

`RenderPassTask` 在任务系统中是实际渲染执行者：

- **上层输入**: `DrawContext` 生成 `DrawPass` 列表，封装绘制几何和状态
- **渲染配置**: 通过 `RenderPassDesc` 描述符指定附件配置、加载/存储操作、采样数
- **资源管理**: 从 `Context` 获取可丢弃的 MSAA 和深度/模板附件，实例化目标纹理代理
- **命令录制**: 调用 `CommandBuffer::addRenderPass()` 创建后端渲染通道并录制绘制命令
- **重放支持**: 处理 `ReplayTargetData` 进行平移和裁剪，支持离屏渲染到多个目标

它是任务图中的叶子节点或接近叶子的节点，通常由 `DrawTask` 作为子任务包含。

## 主要类与结构体

### RenderPassTask 类

**类型别名**:
```cpp
using DrawPassList = skia_private::STArray<1, std::unique_ptr<DrawPass>>;
```
绘制通道列表，小数组优化（栈上分配 1 个元素）。

**成员变量**:
- `DrawPassList fDrawPasses`: 绘制通道列表（当前实现限制为 1 个）
- `RenderPassDesc fRenderPassDesc`: 渲染通道描述符（附件配置）
- `sk_sp<TextureProxy> fTarget`: 目标纹理代理（最终渲染结果）
- `sk_sp<TextureProxy> fDstCopy`: 目标拷贝纹理（用于混合时的目标读取）
- `SkIRect fDstReadBounds`: 目标读取区域边界

**核心方法**:
```cpp
static sk_sp<RenderPassTask> Make(DrawPassList passes,
                                  const RenderPassDesc& desc,
                                  sk_sp<TextureProxy> target,
                                  sk_sp<TextureProxy> dstCopy,
                                  SkIRect dstReadBounds)
```
创建渲染通道任务，执行详尽的参数验证：
- 目标纹理必须有效
- 解析附件必须与目标兼容（格式、维度）
- 颜色附件采样数必须匹配或使用 MSAA-render-to-single-sampled 扩展
- 深度/模板附件必须匹配渲染通道采样数
- 目标拷贝纹理必须足够大以覆盖读取边界

```cpp
Status prepareResources(ResourceProvider*, ScratchResourceManager*,
                       sk_sp<const RuntimeEffectDictionary>) override
```
准备渲染通道所需资源：
1. 实例化目标纹理（区分临时和非临时纹理）
2. 准备绘制通道资源（管线、缓冲区等）
3. 通知临时资源管理器消费已准备的资源

```cpp
Status addCommands(Context*, CommandBuffer*, ReplayTargetData) override
```
录制渲染通道命令：
1. 分配或获取 MSAA 颜色附件（如需）
2. 分配或获取深度/模板附件（如需）
3. 计算 MSAA 尺寸和解析偏移（优化分配）
4. 应用重放平移和裁剪（如绘制到重放目标）
5. 调用 `CommandBuffer::addRenderPass()` 录制渲染通道

```cpp
bool visitPipelines(const std::function<bool(const GraphicsPipeline*)>& visitor) override
```
遍历所有绘制通道使用的图形管线。

```cpp
bool visitProxies(const std::function<bool(const TextureProxy*)>& visitor,
                 bool readsOnly) override
```
遍历纹理代理：采样纹理、目标拷贝纹理（只读）、目标纹理（写入）。

## 公共 API 函数

### 工厂方法

`Make()` 方法创建任务实例，执行大量断言验证：

**解析附件验证**:
- 格式必须匹配目标纹理
- 采样数必须为 1（单采样）
- 不能是深度/模板格式
- 颜色附件必须多采样（>1）
- 颜色和解析附件格式必须一致

**颜色附件验证**:
- 无解析时：必须与目标纹理兼容
- 采样数必须匹配或使用 MSAA-RTS 扩展（附件单采样，通道多采样）

**深度/模板附件验证**:
- 格式必须为深度或模板类型
- 采样数必须匹配渲染通道

### 资源准备

`prepareResources()` 分两阶段处理：

**目标纹理实例化**:
```cpp
if (scratchManager->pendingReadCount(fTarget.get()) == 0) {
    instantiated = TextureProxy::InstantiateIfNotLazy(resourceProvider, fTarget.get());
} else {
    instantiated = TextureProxy::InstantiateIfNotLazy(scratchManager, fTarget.get());
}
```
- 无待读计数：使用资源提供者分配常规非共享资源（特殊情况：`flushTrackedDevices()` 捕获的临时设备）
- 有待读计数：通过临时资源管理器分配可共享临时资源

**绘制通道准备**:
```cpp
drawPass->prepareResources(resourceProvider, runtimeDict, fRenderPassDesc)
```
准备管线、缓冲区、绑定资源等。

**资源消费通知**:
```cpp
scratchManager->notifyResourcesConsumed()
```
回收待返还的临时纹理（因为渲染通道将采样这些纹理，内容不再需要保留）。

### 命令录制

`addCommands()` 执行复杂的附件分配和命令录制：

**重放参数处理**:
```cpp
if (fTarget->texture() == replayData.fTarget) {
    replayTranslation = replayData.fTranslation;
    replayClip = replayData.fClip;
}
```
仅当绘制到最终重放目标时应用平移和裁剪。

**MSAA 颜色附件分配**:
```cpp
std::tie(msaaSize, resolveOffset) = get_msaa_size_and_resolve_offset(...);
colorAttachment = resourceProvider->findOrCreateShareableTexture(
        msaaSize, colorInfo, "DiscardableMSAAAttachment");
```
- 计算优化的 MSAA 尺寸（如果支持不同解析附件尺寸）
- 从共享池获取可丢弃附件（跨渲染通道复用）
- 计算解析偏移（MSAA 纹理较小时）

**深度/模板附件分配**:
```cpp
depthStencilAttachment = resourceProvider->findOrCreateShareableTexture(
        dimensions, dsInfo, "DepthStencilAttachment");
```
从共享池获取可丢弃深度/模板附件。

**裁剪检查**:
```cpp
if (!commandBuffer->setReplayTranslationAndClip(
        replayTranslation - resolveOffset, replayClip, renderTargetBounds)) {
    return Status::kSuccess; // 完全裁剪，跳过渲染通道
}
```
应用平移和裁剪，如果无交集则跳过整个渲染通道。

**渲染通道录制**:
```cpp
commandBuffer->addRenderPass(fRenderPassDesc,
                             colorAttachment,
                             resolveAttachment,
                             depthStencilAttachment,
                             fDstCopy->texture(),
                             fDstReadBounds,
                             resolveOffset,
                             fTarget->dimensions(),
                             fDrawPasses)
```
创建后端渲染通道并录制所有绘制通道命令。

## 内部实现细节

### get_msaa_size_and_resolve_offset 辅助函数

计算优化的 MSAA 纹理尺寸和解析偏移：

**优化策略**:
- 如果支持不同解析附件尺寸 AND 加载操作不是清空 AND 绘制边界有效且与目标相交
- 则使用近似尺寸（`GetApproxSize()`）分配刚好容纳绘制边界的 MSAA 纹理
- 记录解析偏移（绘制边界左上角到目标纹理的偏移）

**无优化情况**:
- 不支持特性或需要清空操作：分配完整目标尺寸的近似尺寸
- 解析偏移为 (0, 0)

**近似尺寸**:
`GetApproxSize()` 返回略大于请求尺寸的尺寸（如 POT 对齐），以提高纹理池化复用率。

### 可丢弃附件池化

MSAA 和深度/模板附件标记为 `Discardable::kYes`：
- 渲染通道结束后内容不需要保留
- 可被后续渲染通道复用
- 通过 `findOrCreateShareableTexture()` 从共享池获取
- 池中纹理按尺寸和格式查找，尺寸近似匹配即可复用

### 解析偏移处理

当 MSAA 纹理小于目标纹理时：
- 绘制通道边界平移 `-resolveOffset`，使左上角对齐 MSAA 纹理 (0, 0)
- 解析操作将 MSAA 纹理 (0, 0) 开始的区域解析到目标纹理的 `resolveOffset` 位置
- 重放平移也需减去 `resolveOffset`：`replayTranslation - resolveOffset`

### 临时资源消费通知

`notifyResourcesConsumed()` 在 `prepareResources()` 结束时调用：
- 触发临时资源管理器回收待返还的纹理
- 这些纹理在渲染通道中被采样，完成采样后内容不再需要
- 回收使其可被后续任务复用，提高内存效率

### 重放目标判断

```cpp
if (fTarget->texture() == replayData.fTarget)
```
检查目标纹理是否为重放目标：
- 是：应用平移和裁剪，支持多次重放到不同位置
- 否：不应用重放参数，渲染到独立纹理

## 依赖关系

### 直接依赖

**核心类型**:
- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/DrawPass.h`: 绘制通道封装
- `src/gpu/graphite/RenderPassDesc.h`: 渲染通道描述符
- `src/gpu/graphite/TextureProxy.h`: 纹理代理

**资源管理**:
- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理器
- `src/gpu/graphite/Texture.h`: 纹理对象
- `src/gpu/graphite/Caps.h`: 能力查询

**命令系统**:
- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/Context.h`: 全局上下文
- `src/gpu/graphite/GraphicsPipeline.h`: 图形管线

### 使用场景

- **常规绘制**: `DrawContext` 生成 `DrawPass` 并创建渲染通道任务
- **MSAA 渲染**: 多采样抗锯齿渲染并解析到目标纹理
- **混合操作**: 使用目标拷贝纹理读取目标内容
- **离屏渲染**: 渲染到临时纹理用于后续处理

## 设计模式与设计决策

### 可丢弃附件设计

MSAA 和深度/模板附件标记为可丢弃：
- **内存效率**: 跨渲染通道复用附件，减少峰值内存
- **性能优化**: 避免每个渲染通道分配/释放纹理
- **后端优化**: 可丢弃标记允许后端优化内存模式（如 Transient）

### 优化的 MSAA 尺寸

支持小于目标尺寸的 MSAA 纹理：
- **内存节省**: 仅分配刚好容纳绘制内容的 MSAA 纹理
- **复用率提升**: 更多渲染通道使用相似尺寸的附件，池化效率更高
- **解析开销减少**: 更小的 MSAA 纹理意味着更少的解析数据传输

### 单 DrawPass 限制

当前实现 `SkASSERT(fDrawPasses.size() == 1)`：
- **简化实现**: 一对一映射简化资源管理和命令录制
- **未来扩展**: 注释提到支持子通道（subpasses），多个 DrawPass 可合并到单个渲染通道
- **后端能力**: 某些后端（Vulkan）支持子通道，可优化内存带宽

### 延迟附件分配

在 `addCommands()` 而非 `prepareResources()` 中分配 MSAA 和深度/模板附件：
- **实时池化**: 从 Context 的可丢弃附件池获取，确保最新可用状态
- **尺寸优化**: 基于绘制边界动态计算 MSAA 尺寸
- **避免浪费**: 不为可能被裁剪掉的渲染通道预分配

### 临时设备特殊处理

无待读计数的临时纹理使用常规分配：
- **背景**: `Recorder::flushTrackedDevices()` 可能提前捕获未完成的临时设备
- **问题**: 实际读取在另一个 Recording 中，不应作为临时资源共享
- **解决**: 检测待读计数，无读取时分配非共享资源

## 性能考量

### 可丢弃附件复用

- 减少纹理分配/释放次数，降低驱动开销
- 提高缓存命中率，GPU 可能复用 TLB 条目
- 减少峰值内存占用

### 优化 MSAA 尺寸分配

- 小 MSAA 纹理节省显存带宽和存储
- 更高的池化命中率（更多渲染通道共享相似尺寸）
- 减少解析操作的数据传输量

### 重放裁剪优化

- 完全裁剪的渲染通道跳过录制，节省 CPU 和 GPU 时间
- 部分裁剪减少绘制区域，降低片段着色器负载

### 临时资源回收

- `notifyResourcesConsumed()` 及时回收纹理
- 后续任务可立即复用，减少并发内存占用
- 避免延迟回收导致的内存峰值

### 单渲染通道批处理

- 所有绘制在单个渲染通道内完成，减少加载/存储操作
- GPU 可保持附件在片上内存（tile-based 架构）
- 减少命令缓冲区开销（一次渲染通道设置）

## 相关文件

### 任务系统

- `src/gpu/graphite/task/Task.h`: 任务基类
- `src/gpu/graphite/task/DrawTask.h`: 绘制任务容器
- `src/gpu/graphite/task/TaskList.h`: 任务列表
- `src/gpu/graphite/task/UploadTask.h`: 上传任务
- `src/gpu/graphite/task/CopyTask.h`: 拷贝任务

### 绘制系统

- `src/gpu/graphite/DrawPass.h`: 绘制通道封装
- `src/gpu/graphite/DrawContext.h`: 绘制上下文
- `src/gpu/graphite/GraphicsPipeline.h`: 图形管线

### 渲染配置

- `src/gpu/graphite/RenderPassDesc.h`: 渲染通道描述符
- `src/gpu/graphite/AttachmentTypes.h`: 附件类型定义
- `src/gpu/graphite/TextureInfo.h`: 纹理信息

### 资源管理

- `src/gpu/graphite/ResourceProvider.h`: 资源提供者
- `src/gpu/graphite/ScratchResourceManager.h`: 临时资源管理器
- `src/gpu/graphite/Texture.h`: 纹理对象
- `src/gpu/graphite/TextureProxy.h`: 纹理代理

### 命令系统

- `src/gpu/graphite/CommandBuffer.h`: 命令缓冲区
- `src/gpu/graphite/Context.h`: 全局上下文
- `src/gpu/graphite/Caps.h`: 能力查询

### 后端实现

- `src/gpu/graphite/vk/VulkanCommandBuffer.h`: Vulkan 渲染通道
- `src/gpu/graphite/mtl/MtlCommandBuffer.h`: Metal 渲染通道
- `src/gpu/graphite/dawn/DawnCommandBuffer.h`: Dawn 渲染通道
