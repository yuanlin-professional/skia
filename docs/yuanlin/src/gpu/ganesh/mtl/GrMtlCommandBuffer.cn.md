# GrMtlCommandBuffer

> 源文件
> - src/gpu/ganesh/mtl/GrMtlCommandBuffer.h
> - src/gpu/ganesh/mtl/GrMtlCommandBuffer.mm

## 概述

`GrMtlCommandBuffer` 是 Skia 图形库中 Metal 后端的命令缓冲区封装类,继承自 `SkRefCnt`。它封装了 Metal 的 `id<MTLCommandBuffer>` 对象,负责管理 Blit 和渲染命令编码器的创建、复用、资源追踪以及命令提交。该类是 Metal 渲染管线中的核心组件,通过智能编码器复用机制优化渲染性能。

## 架构位置

```
Skia Graphics Library
└── src/gpu/ganesh/mtl/
    ├── GrMtlGpu              (Metal GPU管理器)
    ├── GrMtlCommandBuffer    (命令缓冲区) ← 当前类
    ├── GrMtlRenderCommandEncoder (渲染编码器)
    └── GrMtlOpsRenderPass    (渲染通道)
```

## 主要类与结构体

### GrMtlCommandBuffer

Metal 命令缓冲区管理类,负责编码器生命周期和资源追踪。

**继承关系:**
- 基类: `SkRefCnt`
- 派生类: 无(终端类)

**关键成员变量:**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fCmdBuffer` | `id<MTLCommandBuffer>` | Metal 命令缓冲区对象 |
| `fActiveBlitCommandEncoder` | `id<MTLBlitCommandEncoder>` | 当前活动的 Blit 编码器 |
| `fActiveRenderCommandEncoder` | `unique_ptr<GrMtlRenderCommandEncoder>` | 当前活动的渲染编码器 |
| `fPreviousRenderPassDescriptor` | `MTLRenderPassDescriptor*` | 上一次渲染通道描述符(用于复用判断) |
| `fTrackedResources` | `STArray<32, sk_sp<GrManagedResource>>` | 追踪的托管资源 |
| `fTrackedGrBuffers` | `STArray<32, sk_sp<GrBuffer>>` | 追踪的缓冲区 |
| `fTrackedGrSurfaces` | `STArray<16, gr_cb<GrSurface>>` | 追踪的表面 |
| `fFinishedCallbacks` | `TArray<sk_sp<RefCntedCallback>>` | 完成回调列表 |
| `fHasWork` | `bool` | 是否包含待执行的命令 |

## 公共 API 函数

### 工厂方法

```cpp
static sk_sp<GrMtlCommandBuffer> Make(id<MTLCommandQueue> queue);
```
从 Metal 命令队列创建命令缓冲区。

**版本适配:**
- **macOS 11.0+/iOS 14.0+:** 启用 `MTLCommandBufferErrorOptionEncoderExecutionStatus`
- **旧版本:** 使用基础 API

### 编码器获取方法

#### getBlitCommandEncoder
```cpp
id<MTLBlitCommandEncoder> getBlitCommandEncoder();
```
获取或创建 Blit 命令编码器,用于内存传输操作。

#### getRenderCommandEncoder(复用版)
```cpp
GrMtlRenderCommandEncoder* getRenderCommandEncoder(
    MTLRenderPassDescriptor* descriptor,
    const GrMtlPipelineState* pipelineState,
    GrMtlOpsRenderPass* opsRenderPass
);
```
尝试复用当前渲染编码器,如果配置兼容则避免重新创建。

#### getRenderCommandEncoder(新建版)
```cpp
GrMtlRenderCommandEncoder* getRenderCommandEncoder(
    MTLRenderPassDescriptor* descriptor,
    GrMtlOpsRenderPass* opsRenderPass
);
```
强制创建新的渲染命令编码器。

### 资源管理方法

```cpp
void addResource(const sk_sp<const GrManagedResource>& resource);
void addGrBuffer(sk_sp<const GrBuffer> buffer);
void addGrSurface(sk_sp<const GrSurface> surface);
```
添加资源到追踪列表,确保在命令执行期间资源不被释放。

### 同步与事件方法

```cpp
void encodeSignalEvent(sk_sp<GrMtlEvent>, uint64_t value);
void encodeWaitForEvent(sk_sp<GrMtlEvent>, uint64_t value);
```
编码事件信号和等待操作(macOS 10.14+/iOS 12.0+)。

### 提交与状态查询

```cpp
bool commit(bool waitUntilCompleted);
bool hasWork();
bool isCompleted();
void waitUntilCompleted();
void callFinishedCallbacks();
```

### 调试支持

```cpp
void pushDebugGroup(NSString* string);  // macOS 10.13+
void popDebugGroup();
```

## 内部实现细节

### 渲染编码器复用逻辑

`getRenderCommandEncoder` 通过 `compatible()` 函数判断是否可复用:

```cpp
static bool compatible(
    const MTLRenderPassAttachmentDescriptor* first,
    const MTLRenderPassAttachmentDescriptor* second,
    const GrMtlPipelineState* pipelineState
) {
    // 兼容条件:
    // 1. 渲染目标相同
    bool renderTargetsMatch = (first.texture == second.texture);

    // 2. 第一个的存储动作为 Store 或 DontCare
    bool storeActionsValid =
        first.storeAction == MTLStoreActionStore ||
        first.storeAction == MTLStoreActionDontCare;

    // 3. 第二个的加载动作为 Load 或 DontCare
    bool loadActionsValid =
        second.loadAction == MTLLoadActionLoad ||
        second.loadAction == MTLLoadActionDontCare;

    // 4. 第二个不会采样第一个的渲染目标
    bool secondDoesntSampleFirst =
        (!pipelineState || pipelineState->doesntSampleAttachment(first));

    // 5. 存储动作互相兼容
    bool secondStoreValid = /* 复杂的存储动作兼容性检查 */;

    return renderTargetsMatch && (nil == first.texture ||
        (storeActionsValid && loadActionsValid &&
         secondDoesntSampleFirst && secondStoreValid));
}
```

**复用优势:**
- 避免编码器创建开销
- 减少 GPU 状态切换
- 提高渲染吞吐量

### 编码器生命周期管理

```cpp
void GrMtlCommandBuffer::endAllEncoding() {
    if (fActiveRenderCommandEncoder) {
        fActiveRenderCommandEncoder->endEncoding();
        fActiveRenderCommandEncoder.reset();
        fPreviousRenderPassDescriptor = nil;
    }
    if (fActiveBlitCommandEncoder) {
        [fActiveBlitCommandEncoder endEncoding];
        fActiveBlitCommandEncoder = nil;
    }
}
```

在以下情况触发 `endAllEncoding`:
- 获取不同类型编码器时
- 编码事件信号/等待时
- 提交命令缓冲区前

### 命令提交流程

```cpp
bool GrMtlCommandBuffer::commit(bool waitUntilCompleted) {
    this->endAllEncoding();  // 1. 结束所有编码器

    if ([fCmdBuffer status] != MTLCommandBufferStatusNotEnqueued) {
        NSLog(@"Invalid state");
        return false;
    }

    [fCmdBuffer commit];  // 2. 提交到 GPU

    if (waitUntilCompleted) {
        this->waitUntilCompleted();  // 3. 可选同步等待
    }

    // 4. iOS 特殊处理: 确保命令被调度
    #if defined(SK_BUILD_FOR_IOS) && defined(SK_METAL_WAIT_UNTIL_SCHEDULED)
    else {
        [fCmdBuffer waitUntilScheduled];
    }
    #endif

    // 5. 检查执行状态
    if ([fCmdBuffer status] == MTLCommandBufferStatusError) {
        SkDebugf("Error submitting command buffer.\n");
        if (NSError* error = [fCmdBuffer error]) {
            NSLog(@"%@", error);
        }
    }

    return ([fCmdBuffer status] != MTLCommandBufferStatusError);
}
```

### 资源追踪机制

使用三个数组追踪不同类型的资源:

```cpp
STArray<32, sk_sp<const GrManagedResource>> fTrackedResources;  // 通用资源(当前禁用)
STArray<32, sk_sp<const GrBuffer>> fTrackedGrBuffers;           // 缓冲区
STArray<16, gr_cb<const GrSurface>> fTrackedGrSurfaces;         // 表面
```

**作用:**
- 延长资源生命周期至命令执行完成
- 防止资源在命令队列中时被释放
- 避免写后写冲突

### 事件编码(同步原语)

```cpp
void GrMtlCommandBuffer::encodeSignalEvent(sk_sp<GrMtlEvent> event,
                                           uint64_t eventValue) {
    SkASSERT(fCmdBuffer);
    this->endAllEncoding();  // 确保无活动编码器

    if (@available(macOS 10.14, iOS 12.0, tvOS 12.0, *)) {
        [fCmdBuffer encodeSignalEvent:event->mtlEvent() value:eventValue];
        this->addResource(std::move(event));
    }
    fHasWork = true;
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `Metal/Metal.h` | Metal API |
| `GrMtlRenderCommandEncoder` | 渲染编码器封装 |
| `GrMtlOpsRenderPass` | 渲染通道 |
| `GrMtlPipelineState` | 管线状态 |
| `GrMtlSemaphore` | 信号量/事件 |
| `GrManagedResource` | 托管资源基类 |
| `GrBuffer` | 缓冲区抽象 |
| `GrSurface` | 表面抽象 |

### 被依赖的模块

| 模块 | 使用场景 |
|-----|---------|
| `GrMtlGpu` | 持有和管理命令缓冲区 |
| `GrMtlOpsRenderPass` | 使用命令缓冲区编码渲染命令 |
| `GrMtlBuffer` | 通过 Blit 编码器传输数据 |
| `GrMtlTexture` | 上传纹理数据 |

## 设计模式与设计决策

### 延迟编码器创建
编码器仅在首次使用时创建,避免不必要的对象分配。

### 编码器复用策略
通过详细的兼容性检查尽可能复用渲染编码器,这是 Apple Metal Best Practices Guide 推荐的优化手段。

### 资源生命周期绑定
使用智能指针数组追踪资源,确保:
- 命令执行期间资源有效
- 命令完成后自动释放资源

### 分离式资源追踪
针对不同资源类型使用不同数组,便于:
- 类型安全管理
- 性能优化(小对象数组)
- 调试和分析

### 版本兼容性处理
通过 `@available` 宏在编译时检查 API 可用性,在运行时优雅降级。

## 性能考量

### 编码器复用收益
- **避免对象创建:** 编码器创建是昂贵操作(~100μs)
- **减少状态验证:** 复用编码器保留管线状态
- **降低驱动开销:** 减少 Metal 驱动的状态机转换

### 资源追踪开销
- **预分配数组:** `STArray<32>` 避免大部分动态分配
- **引用计数:** 使用 `sk_sp` 自动管理,无额外开销
- **批量释放:** 析构时一次性释放所有资源

### 批处理优化
- 单个命令缓冲区可包含多个渲染通道
- 延迟提交直到必要时刻
- 减少 CPU-GPU 同步点

### iOS 后台处理
```cpp
#if defined(SK_BUILD_FOR_IOS) && defined(SK_METAL_WAIT_UNTIL_SCHEDULED)
[fCmdBuffer waitUntilScheduled];
#endif
```
确保应用进入后台前命令已被调度,避免丢失渲染结果。

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/mtl/GrMtlGpu.h` | 管理者 | 创建和持有命令缓冲区 |
| `src/gpu/ganesh/mtl/GrMtlRenderCommandEncoder.h` | 组合 | 渲染编码器封装 |
| `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.h` | 使用者 | 使用命令缓冲区编码 |
| `src/gpu/ganesh/mtl/GrMtlPipelineState.h` | 协作 | 提供管线状态信息 |
| `src/gpu/ganesh/mtl/GrMtlSemaphore.h` | 同步 | 事件同步机制 |
| `src/gpu/ganesh/GrManagedResource.h` | 基础 | 资源管理基类 |
| `Metal/Metal.h` | API | Metal 框架 |
