# MtlCommandBuffer -- Metal 命令缓冲区

> 源文件:
> - `src/gpu/graphite/mtl/MtlCommandBuffer.h`
> - `src/gpu/graphite/mtl/MtlCommandBuffer.mm`

## 概述

MtlCommandBuffer 是 Graphite Metal 后端的命令缓冲区实现,负责录制渲染、计算和数据传输命令。它管理 Metal 编码器（渲染、计算、Blit）的生命周期,确保同一时刻只有一个编码器处于活跃状态,并将 Graphite 抽象的绘制命令转换为具体的 Metal API 调用。

## 架构位置

```
CommandBuffer (抽象基类)
  -> MtlCommandBuffer  <-- 本模块
       -> MtlRenderCommandEncoder (渲染编码器)
       -> MtlComputeCommandEncoder (计算编码器)
       -> MtlBlitCommandEncoder (Blit 编码器)
       -> id<MTLCommandBuffer> (Metal 命令缓冲区)
```

## 主要类与结构体

### MtlCommandBuffer

```cpp
class MtlCommandBuffer final : public CommandBuffer {
    sk_cfp<id<MTLCommandBuffer>> fCommandBuffer;
    sk_sp<MtlRenderCommandEncoder> fActiveRenderCommandEncoder;
    sk_sp<MtlComputeCommandEncoder> fActiveComputeCommandEncoder;
    sk_sp<MtlBlitCommandEncoder> fActiveBlitCommandEncoder;
    id<MTLBuffer> fCurrentIndexBuffer;
    id<MTLBuffer> fCurrentIndirectBuffer;
    id<MTLCommandQueue> fQueue;
    const MtlSharedContext* fSharedContext;
    MtlResourceProvider* fResourceProvider;
    bool fDrawIsOffscreen;
};
```

## 公共 API 函数

### Make -- 工厂方法
```cpp
static std::unique_ptr<MtlCommandBuffer> Make(id<MTLCommandQueue>, const MtlSharedContext*, MtlResourceProvider*);
```

### 状态查询与同步
```cpp
bool isFinished();            // 检查命令是否完成或出错
void waitUntilFinished();     // 阻塞等待完成
bool commit();                // 提交到队列
bool setNewCommandBufferResources() override;  // 创建新的 MTL 命令缓冲区
```

### 信号量
```cpp
void addWaitSemaphores(size_t, const BackendSemaphore*) override;
void addSignalSemaphores(size_t, const BackendSemaphore*) override;
```
使用 `MTLEvent` 实现（macOS 10.14+ / iOS 12+）。

## 内部实现细节

### 编码器管理

**互斥规则**: 渲染、计算和 Blit 编码器互斥,开始新类型编码器前必须结束当前编码器:
- `beginRenderPass()` 结束 Blit 编码器
- `beginComputePass()` 结束 Blit 编码器
- `getBlitCommandEncoder()` 按需创建或复用

Blit 编码器可跨多个操作复用以减少创建开销。

### 渲染通道处理

`beginRenderPass()` 配置 `MTLRenderPassDescriptor`:
1. 设置颜色附件（纹理、清除颜色、加载/存储操作）
2. 配置 resolve 附件（多重采样解析 -> `MTLStoreActionMultisampleResolve`）
3. 设置深度/模板附件
4. MSAA 加载：使用专用管线从 resolve 纹理绘制到 MSAA 附件

### DrawPass 命令分发

`addDrawPass()` 遍历 DrawPass 的命令列表,支持:
- 管线绑定、混合常量设置
- Uniform/顶点/索引/间接缓冲区绑定
- 纹理和采样器绑定（Metal 不使用不可变采样器）
- 裁剪和绘制命令（draw, drawIndexed, drawInstanced, drawIndirect 等）
- 离屏绘制跳过优化（`fDrawIsOffscreen`）

### 管线绑定

```cpp
void bindGraphicsPipeline(const GraphicsPipeline*);
```
同时设置渲染管线状态、深度模板状态和模板引用值。还处理 `DstReadStrategy::kTextureCopy` 时的目标纹理绑定。

### Uniform 绑定

将 Uniform 缓冲区同时绑定到顶点和片段阶段,通过 `UniformSlot` 映射到 Metal 缓冲区索引。内置 Uniform 使用 `setVertexBytes`/`setFragmentBytes` 内联传递。

### 数据传输操作

使用 Blit 编码器实现:
- `onCopyBufferToBuffer` -- 缓冲区间复制
- `onCopyTextureToBuffer` / `onCopyBufferToTexture` -- 纹理与缓冲区间传输
- `onCopyTextureToTexture` -- 纹理间复制
- `onSynchronizeBufferToCpu` -- 仅 macOS Managed 存储模式需要同步
- `onClearBuffer` -- 填充零

### 命令缓冲区创建

```cpp
bool createNewMTLCommandBuffer();
```
使用 `commandBufferWithUnretainedReferences`（或新 API 的 `MTLCommandBufferDescriptor`）创建,设置 `retainedReferences=NO` 以让 Graphite 自行管理资源引用。

## 依赖关系

- `CommandBuffer` -- 基类
- `MtlRenderCommandEncoder` / `MtlComputeCommandEncoder` / `MtlBlitCommandEncoder` -- Metal 编码器封装
- `MtlGraphicsPipeline` / `MtlComputePipeline` -- 管线对象
- `MtlTexture` / `MtlBuffer` / `MtlSampler` -- Metal 资源
- `MtlSharedContext` / `MtlResourceProvider` -- 上下文和资源管理

## 设计模式与设计决策

1. **编码器互斥**: Metal 要求同一时刻只有一个编码器活跃,通过 assert 和显式结束确保此约束。
2. **非保留引用**: 使用 `commandBufferWithUnretainedReferences` 让 Graphite 的资源追踪系统管理引用,避免 Metal 运行时重复保留。
3. **离屏绘制跳过**: 通过 `fDrawIsOffscreen` 标志在 DrawPass 处理中跳过完全离屏的绘制命令,保留状态变更命令。
4. **Blit 编码器复用**: 与渲染和计算编码器每次创建不同,Blit 编码器在多次操作间复用。

## 性能考量

- `@autoreleasepool` 包裹命令缓冲区创建,确保临时 ObjC 对象及时释放。
- Blit 宽度限制 32767 像素防止 Metal 溢出。
- macOS 上仅 Managed 存储模式缓冲区需要显式同步;iOS 的 Shared 模式无需同步。
- 调试信息（标签、调试组）仅在 `SK_ENABLE_MTL_DEBUG_INFO` 下启用。
- 渐变数据在 DrawPass 开始前预绑定,避免每次绘制重复绑定。

## 相关文件

- `src/gpu/graphite/CommandBuffer.h` -- 命令缓冲区基类
- `src/gpu/graphite/mtl/MtlRenderCommandEncoder.h` -- 渲染编码器
- `src/gpu/graphite/mtl/MtlBlitCommandEncoder.h` -- Blit 编码器
- `src/gpu/graphite/mtl/MtlComputeCommandEncoder.h` -- 计算编码器
- `src/gpu/graphite/DrawPass.h` -- 绘制通道
