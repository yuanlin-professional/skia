# DawnCommandBuffer

> 源文件
> - src/gpu/graphite/dawn/DawnCommandBuffer.h
> - src/gpu/graphite/dawn/DawnCommandBuffer.cpp

## 概述

`DawnCommandBuffer` 是 Skia Graphite 中 Dawn 后端的命令缓冲区实现类,继承自 `CommandBuffer` 基类。该类负责将 Graphite 的高层渲染和计算命令编码为 Dawn 的 GPU 命令,管理渲染通道、计算通道、资源绑定、绘制调用和数据传输操作。它是 Graphite 渲染管线的核心执行组件,将抽象的图形 API 调用转换为 WebGPU 特定的命令序列。

核心职责包括:编码渲染通道(支持 MSAA、resolve、load/store 模拟)、编码计算通道(dispatch 调度)、管理图形和计算管线状态、绑定统一缓冲区和纹理采样器、执行各种绘制命令(draw、drawIndexed、drawInstanced、drawIndirect 等)、处理缓冲区和纹理拷贝操作、支持 GPU 统计查询(时间戳)。

## 架构位置

`DawnCommandBuffer` 位于 Skia Graphite 的 Dawn 后端命令编码层:

```
skgpu::graphite
├── CommandBuffer (基类 - 跨后端命令缓冲区抽象)
├── DrawPass (绘制通道)
├── DispatchGroup (计算调度组)
└── dawn/
    ├── DawnCommandBuffer (Dawn 命令缓冲区)
    ├── DawnSharedContext (Dawn 上下文)
    ├── DawnResourceProvider (资源提供者)
    ├── DawnGraphicsPipeline (图形管线)
    ├── DawnComputePipeline (计算管线)
    └── DawnQueueManager (队列管理器)
```

`DawnCommandBuffer` 接收 `DrawPass` 和 `DispatchGroup`,通过 `DawnResourceProvider` 获取资源,使用 `DawnGraphicsPipeline` 和 `DawnComputePipeline`,最终生成的 `wgpu::CommandBuffer` 提交给 `DawnQueueManager`。

## 主要类与结构体

### DawnCommandBuffer 类

```cpp
class DawnCommandBuffer final : public CommandBuffer {
public:
    static std::unique_ptr<DawnCommandBuffer> Make(const DawnSharedContext*,
                                                   DawnResourceProvider*);

    // 完成编码并返回 Dawn 命令缓冲区
    wgpu::CommandBuffer finishEncoding();

    // GPU 统计查询
    bool startStatsQuery(GpuStatsFlags) override;
    void endStatsQuery(GpuStatsFlags) override;
    std::optional<GpuStats> gpuStats() override;

private:
    // 渲染通道管理
    bool beginRenderPass(const RenderPassDesc&,
                        const SkIPoint& resolveOffset,
                        const Texture* colorTexture,
                        const Texture* resolveTexture,
                        const Texture* depthStencilTexture);
    bool endRenderPass();
    bool addDrawPass(DrawPass*);

    // Load/Resolve 模拟
    bool emulateLoadMSAAFromResolveAndBeginRenderPassEncoder(...);
    bool doBlitWithDraw(const wgpu::RenderPassEncoder&,
                       const RenderPassDesc&,
                       const wgpu::TextureView& srcTextureView,
                       SampleCount srcSampleCount,
                       const SkIPoint& srcOffset,
                       const SkIRect& dstBounds);

    // 管线和资源绑定
    bool bindGraphicsPipeline(const GraphicsPipeline*);
    void bindUniformBuffer(const BindBufferInfo&, UniformSlot);
    void bindTextureAndSamplers(const DrawPass&,
                               const DrawPassCommands::BindTexturesAndSamplers&);
    void bindIndexBuffer(const Buffer*, size_t offset);
    void bindIndirectBuffer(const Buffer*, size_t offset);

    // 绘制命令
    void draw(PrimitiveType, unsigned baseVertex, unsigned vertexCount);
    void drawIndexed(PrimitiveType, unsigned baseIndex, unsigned indexCount,
                     unsigned baseVertex);
    void drawInstanced(PrimitiveType, unsigned baseVertex, unsigned vertexCount,
                      unsigned baseInstance, unsigned instanceCount);
    void drawIndexedInstanced(...);
    void drawIndirect(PrimitiveType);
    void drawIndexedIndirect(PrimitiveType);

    // 计算通道管理
    void beginComputePass();
    void endComputePass();
    void bindComputePipeline(const ComputePipeline*);
    void dispatchWorkgroups(const WorkgroupSize&);
    void dispatchWorkgroupsIndirect(const Buffer*, size_t offset);

    wgpu::CommandEncoder fCommandEncoder;            // Dawn 命令编码器
    wgpu::RenderPassEncoder fActiveRenderPassEncoder; // 活动渲染通道编码器
    wgpu::ComputePassEncoder fActiveComputePassEncoder; // 活动计算通道编码器

    std::array<BindBufferInfo, kNumUniformBuffers> fBoundUniforms; // 绑定的统一缓冲区
    bool fBoundUniformBuffersDirty = false;

    // Load/Resolve 模拟信息
    struct ResolveStepEmulationInfo {
        const DawnTexture* fMSAATexture;
        const DawnTexture* fResolveTexture;
        SkIPoint fMSAAAOffset;
        SkIRect fResolveArea;
    };
    std::optional<ResolveStepEmulationInfo> fResolveStepEmulationInfo;

    // GPU 时间戳查询
    wgpu::QuerySet fTimestampQuerySet;
    sk_sp<DawnBuffer> fTimestampQueryBuffer;
    sk_sp<DawnBuffer> fTimestampQueryXferBuffer;
    bool fWroteFirstPassTimestamps = false;
    bool fHasStatsQuery = false;

    const DawnGraphicsPipeline* fActiveGraphicsPipeline = nullptr;
    const DawnComputePipeline* fActiveComputePipeline = nullptr;
    const DawnSharedContext* fSharedContext;
    DawnResourceProvider* fResourceProvider;
};
```

## 公共 API 函数

### 创建和编码完成

```cpp
static std::unique_ptr<DawnCommandBuffer> Make(const DawnSharedContext*,
                                               DawnResourceProvider*)
```
静态工厂方法创建命令缓冲区,初始化 Dawn 命令编码器。

```cpp
wgpu::CommandBuffer finishEncoding()
```
完成命令编码并返回最终的 `wgpu::CommandBuffer`,之后命令缓冲区进入不可用状态,需要重置后才能复用。

### GPU 统计查询

```cpp
bool startStatsQuery(GpuStatsFlags)
```
开始 GPU 统计查询,创建时间戳查询集和查询缓冲区。在命令缓冲区开始处写入起始时间戳(原生 Dawn)或在第一个渲染/计算通道写入(WebGPU)。

```cpp
void endStatsQuery(GpuStatsFlags)
```
结束统计查询,写入结束时间戳并解析查询结果到缓冲区。若设备不支持缓冲区映射,需要额外的传输缓冲区拷贝。

```cpp
std::optional<GpuStats> gpuStats()
```
获取 GPU 统计结果,包括执行时间(纳秒)。若查询缓冲区未映射或结果无效则返回空。

## 内部实现细节

### 渲染通道编码

`beginRenderPass()` 方法是核心的渲染通道创建逻辑,包含复杂的扩展处理:

1. **颜色附件配置**:
   - 设置清除颜色、load/store 操作
   - 配置 resolve 目标(MSAA -> Single Sample)
   - 处理 Load Resolve Texture 扩展(ExpandResolveTexture LoadOp)
   - 处理 Partial Load Resolve(部分区域 resolve)

2. **深度模板附件配置**:
   - 分别配置 depth 和 stencil 的 load/store 操作
   - 设置清除值

3. **MSAA Render To Single Sampled**:
   - 当渲染通道是 MSAA 但颜色附件是单采样时,启用 MSRTSS 扩展
   - 需要设置 `DawnRenderPassSampleCount` 链式结构体

4. **Render Pass Render Area**:
   - 设置渲染区域以优化 tile-based GPU
   - 仅在支持扩展时启用

5. **时间戳写入**(WebGPU 模式):
   - 在渲染通道开始和结束时写入时间戳
   - 第一个通道写入开始时间戳,所有通道覆盖结束时间戳

### Load/Resolve 模拟机制

当设备不支持 Load Resolve Texture 或 Partial Load Resolve 时,通过 `emulateLoadMSAAFromResolveAndBeginRenderPassEncoder()` 模拟:

```cpp
bool emulateLoadMSAAFromResolveAndBeginRenderPassEncoder(...)
```

**模拟步骤**:
1. 创建不包含 resolve 目标的渲染通道(MSAA 附件 store 而非 discard)
2. 若需要 load resolve,使用 `doBlitWithDraw()` 将 resolve 纹理 blit 到 MSAA 附件
3. 开始正常渲染
4. 在 `endRenderPass()` 中,创建中间渲染通道将 MSAA 纹理 blit 回 resolve 纹理

**Blit 实现**:
```cpp
bool doBlitWithDraw(...)
```
使用全屏三角形绘制实现纹理拷贝,支持 MSAA 源纹理的 resolve。从 `DawnResourceProvider` 获取预编译的 blit 管线。

### 绘制命令编码

`addDrawPass()` 方法遍历 `DrawPass` 的命令列表并编码:

```cpp
for (auto [type, cmdPtr] : drawPass->commands()) {
    switch (type) {
        case DrawPassCommands::Type::kBindGraphicsPipeline: ...
        case DrawPassCommands::Type::kBindUniformBuffer: ...
        case DrawPassCommands::Type::kBindTexturesAndSamplers: ...
        case DrawPassCommands::Type::kDraw: ...
        case DrawPassCommands::Type::kDrawIndexed: ...
        case DrawPassCommands::Type::kDrawInstanced: ...
        case DrawPassCommands::Type::kDrawIndirect: ...
        // ... 更多命令类型
    }
}
```

关键命令:
- **BindGraphicsPipeline**: 切换图形管线,标记统一缓冲区为脏
- **BindUniformBuffer**: 绑定统一缓冲区到指定槽位
- **BindTexturesAndSamplers**: 创建绑定组并绑定纹理和采样器
- **SetScissor**: 设置裁剪矩形
- **Draw 系列**: 各种绘制调用(直接、索引、实例化、间接)

### 统一缓冲区管理

```cpp
void syncUniformBuffers()
```
在绘制前同步统一缓冲区,若 `fBoundUniformBuffersDirty` 为 true,则创建新的绑定组并调用 `SetBindGroup()`。

统一缓冲区槽位:
- **Slot 0**: Intrinsic uniforms(视口、裁剪等)
- **Slot 1**: Render step uniforms
- **Slot 2**: Paint uniforms
- **Slot 3**: Gradient buffer

Dawn 支持两种 intrinsic uniform 传递方式:
1. **Uniform Buffer Object** (UBO): 通用方式,在渲染通道前更新
2. **Push Constants**: 原生 Dawn 支持,在渲染通道内更新,延迟更低

### 计算通道编码

```cpp
bool onAddComputePass(DispatchGroupSpan groups)
```
编码计算通道,遍历 DispatchGroup 并为每个 dispatch 绑定管线、资源和调度:

```cpp
for (const auto& dispatch : group->dispatches()) {
    this->bindComputePipeline(group->getPipeline(dispatch.fPipelineIndex));
    this->bindDispatchResources(*group, dispatch);
    if (/* direct dispatch */) {
        this->dispatchWorkgroups(*globalSize);
    } else {
        this->dispatchWorkgroupsIndirect(indirect.fBuffer, indirect.fOffset);
    }
}
```

## 依赖关系

### 对外依赖

| 依赖类/模块 | 用途 | 依赖类型 |
|------------|------|---------|
| `CommandBuffer` | Graphite 命令缓冲区基类 | 继承 |
| `wgpu::CommandEncoder` | Dawn 命令编码器 | 强依赖 |
| `wgpu::RenderPassEncoder` | Dawn 渲染通道编码器 | 强依赖 |
| `wgpu::ComputePassEncoder` | Dawn 计算通道编码器 | 强依赖 |
| `DawnSharedContext` | Dawn 上下文和设备 | 强依赖 |
| `DawnResourceProvider` | 资源创建和管理 | 强依赖 |
| `DawnGraphicsPipeline` | 图形管线状态 | 强依赖 |
| `DawnComputePipeline` | 计算管线状态 | 强依赖 |
| `DrawPass` | 绘制通道命令列表 | 输入 |
| `DispatchGroup` | 计算调度组 | 输入 |

### 被依赖关系

- **DawnQueueManager**: 提交命令缓冲区到 GPU 队列
- **Graphite Recording**: 创建和管理命令缓冲区生命周期

## 设计模式与设计决策

### 命令模式

`DawnCommandBuffer` 实现命令模式,将渲染操作封装为命令序列:
- 命令延迟执行(编码时不立即执行)
- 支持批处理和优化
- 命令可序列化和回放

### 状态机模式

命令缓冲区维护复杂的状态机:
- **Idle**: 初始状态或重置后
- **Recording**: 命令编码中
- **InRenderPass**: 渲染通道活动
- **InComputePass**: 计算通道活动
- **Encoded**: 编码完成,等待提交

状态转换由 `fActiveRenderPassEncoder` 和 `fActiveComputePassEncoder` 的有效性决定。

### 适配器模式

`DawnCommandBuffer` 作为适配器,将 Graphite 的高层 API 适配到 Dawn 的低层 API:
- `RenderPassDesc` → `wgpu::RenderPassDescriptor`
- `GraphicsPipeline` → `wgpu::RenderPipeline`
- `BindBufferInfo` → `wgpu::BindGroup`
- `TextureProxy` → `wgpu::TextureView`

### 脏标记模式

使用 `fBoundUniformBuffersDirty` 标记统一缓冲区状态:
- 管线切换时标记为脏
- 绘制前检查并同步
- 减少不必要的绑定组创建

### 资源生命周期管理

通过 `trackResource()` 方法跟踪命令缓冲区使用的资源:
- 防止资源在命令执行前被释放
- 支持资源缓存和复用
- 确保引用计数正确

## 性能考量

### 渲染通道合并

Graphite 在上层已进行渲染通道合并优化,`DawnCommandBuffer` 按接收的 `DrawPass` 列表创建最少数量的渲染通道。

### 绑定组缓存

`DawnResourceProvider` 缓存绑定组,`DawnCommandBuffer` 仅在状态变化时创建新绑定组:
```cpp
if (fBoundUniformBuffersDirty) {
    syncUniformBuffers();
}
```

### 推送常量优化

在支持推送常量的平台上,intrinsic uniforms 通过推送常量传递,避免缓冲区更新和绑定开销:
```cpp
if (usePushConstant) {
    updateIntrinsicUniformsAsPushConstant(uniformData);
}
```

推送常量的优势:
- 无需缓冲区分配
- 零拷贝,直接写入命令缓冲区
- 更低的带宽占用

### Load/Resolve 模拟的权衡

模拟模式虽然增加渲染通道数量,但提高 MSAA 纹理复用:
- 在不支持 transient attachments 的设备上,MSAA 纹理必须存储
- 通过复用 MSAA 纹理减少内存占用
- 对于大分辨率渲染目标,内存节省显著超过通道切换开销

### 时间戳查询优化

WebGPU 模式下使用渲染/计算通道时间戳:
```cpp
wgpuTimestampWrites.beginningOfPassWriteIndex = 0; // 第一个通道
wgpuTimestampWrites.endOfPassWriteIndex = 1;       // 每个通道覆盖
```
仅需 2 个查询槽位,最小化查询开销。

### 间接绘制优化

支持间接绘制减少 CPU-GPU 同步:
```cpp
void drawIndirect(PrimitiveType);
void drawIndexedIndirect(PrimitiveType);
void dispatchWorkgroupsIndirect(const Buffer*, size_t);
```
绘制参数由 GPU 计算,避免回读到 CPU。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/graphite/CommandBuffer.h` | 基类定义 | Graphite 命令缓冲区抽象 |
| `src/gpu/graphite/DrawPass.h` | 输入 | 绘制通道命令列表 |
| `src/gpu/graphite/compute/DispatchGroup.h` | 输入 | 计算调度组 |
| `src/gpu/graphite/dawn/DawnSharedContext.h` | 协作类 | Dawn 上下文和设备 |
| `src/gpu/graphite/dawn/DawnResourceProvider.h` | 协作类 | 资源创建和缓存 |
| `src/gpu/graphite/dawn/DawnGraphicsPipeline.h` | 使用者 | 图形管线状态 |
| `src/gpu/graphite/dawn/DawnComputePipeline.h` | 使用者 | 计算管线状态 |
| `src/gpu/graphite/dawn/DawnQueueManager.h` | 使用者 | 队列提交 |
| `src/gpu/graphite/dawn/DawnBuffer.h` | 资源类 | Dawn 缓冲区 |
| `src/gpu/graphite/dawn/DawnTexture.h` | 资源类 | Dawn 纹理 |
| `src/gpu/graphite/dawn/DawnSampler.h` | 资源类 | Dawn 采样器 |
| `webgpu/webgpu_cpp.h` | 外部依赖 | WebGPU C++ API |
