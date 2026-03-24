# GrOpsRenderPass

> 源文件: src/gpu/ganesh/GrOpsRenderPass.h, src/gpu/ganesh/GrOpsRenderPass.cpp

## 概述

`GrOpsRenderPass` 是 Ganesh GPU 后端中用于执行一系列渲染命令（绘制、清除、丢弃）的核心抽象类。所有命令都针对同一渲染目标，这些命令可能立即执行（如 OpenGL），也可能被缓冲以便稍后执行（如 Vulkan）。

主要功能包括：
- **管线绑定**：配置渲染管线状态（着色器、混合、光栅化等）
- **动态状态设置**：剪裁矩形、纹理绑定、缓冲区绑定
- **绘制调用**：支持多种绘制模式（索引、实例化、间接绘制）
- **清除操作**：颜色和模板缓冲区清除
- **上传操作**：绘制过程中的纹理数据上传

该类是后端无关的接口，具体实现由 GL、Vulkan、Metal 等后端提供。

## 架构位置

`GrOpsRenderPass` 位于 Ganesh 渲染执行层的中心：

```
GrOpsTask (渲染任务)
    ↓
GrOpFlushState (刷新状态)
    ↓
GrOpsRenderPass (渲染通道) ← 本模块
    ↓
    ├── GrGLOpsRenderPass (OpenGL 实现)
    ├── GrVkOpsRenderPass (Vulkan 实现)
    └── GrMtlOpsRenderPass (Metal 实现)
```

在绘制流程中的位置：

```
GrDrawOp → prepare() → execute(GrOpsRenderPass*)
                            ↓
                       draw commands
                            ↓
                       GPU hardware
```

## 主要类与结构体

### GrOpsRenderPass

渲染通道抽象基类，定义跨平台的渲染命令接口。

**继承关系**:
- 基类：无
- 派生类：`GrGLOpsRenderPass`, `GrVkOpsRenderPass`, `GrMtlOpsRenderPass`, `GrD3DOpsRenderPass`

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fOrigin` | `GrSurfaceOrigin` | 渲染目标的原点位置 |
| `fRenderTarget` | `GrRenderTarget*` | 当前渲染目标 |
| `fActiveIndexBuffer` | `sk_sp<const GrBuffer>` | 当前绑定的索引缓冲区 |
| `fActiveVertexBuffer` | `sk_sp<const GrBuffer>` | 当前绑定的顶点缓冲区 |
| `fActiveInstanceBuffer` | `sk_sp<const GrBuffer>` | 当前绑定的实例缓冲区 |
| `fDrawPipelineStatus` | `DrawPipelineStatus` | 管线配置状态 |
| `fXferBarrierType` | `GrXferBarrierType` | 传输屏障类型 |

### LoadAndStoreInfo

渲染通道的加载和存储操作配置。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLoadOp` | `GrLoadOp` | 加载操作（清除/加载/丢弃） |
| `fStoreOp` | `GrStoreOp` | 存储操作（存储/丢弃） |
| `fClearColor` | `std::array<float, 4>` | 清除颜色 RGBA |

### StencilLoadAndStoreInfo

模板缓冲区的加载和存储配置（清除值始终为 0）。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fLoadOp` | `GrLoadOp` | 加载操作 |
| `fStoreOp` | `GrStoreOp` | 存储操作 |

### DrawPipelineStatus 枚举

```cpp
enum class DrawPipelineStatus {
    kOk = 0,               // 管线正常配置
    kNotConfigured,        // 管线未配置
    kFailedToBind          // 管线绑定失败
};
```

## 公共 API 函数

### 生命周期管理

#### begin()

```cpp
void begin();
```

开始记录渲染命令，初始化内部状态。

#### end()

```cpp
void end();
```

结束记录，提交渲染通道供执行。

### 管线配置

#### bindPipeline()

```cpp
void bindPipeline(const GrProgramInfo&, const SkRect& drawBounds);
```

绑定渲染管线：
- 验证管线配置的有效性
- 检查顶点属性数量限制
- 设置传输屏障类型
- 配置动态状态标志

**验证内容**：
- 原点匹配检查
- 实例化支持检查
- 保守光栅化支持检查
- 线框模式支持检查
- 双面模板引用一致性检查

### 动态状态

#### setScissorRect()

```cpp
void setScissorRect(const SkIRect&);
```

设置剪裁矩形（仅当管线启用剪裁测试时需要）。

#### bindTextures()

```cpp
void bindTextures(const GrGeometryProcessor&,
                  const GrSurfaceProxy* const geomProcTextures[],
                  const GrPipeline&);
```

绑定几何处理器和片段处理器的纹理：
- 验证纹理格式匹配
- 检查 mipmap 状态
- 如果硬件支持，可能只更新几何处理器纹理

#### bindBuffers()

```cpp
void bindBuffers(sk_sp<const GrBuffer> indexBuffer,
                 sk_sp<const GrBuffer> instanceBuffer,
                 sk_sp<const GrBuffer> vertexBuffer,
                 GrPrimitiveRestart = GrPrimitiveRestart::kNo);
```

绑定渲染所需的缓冲区，允许传入空指针。

### 绘制命令

#### draw()

```cpp
void draw(int vertexCount, int baseVertex);
```

绘制非索引几何体。

#### drawIndexed()

```cpp
void drawIndexed(int indexCount, int baseIndex,
                 uint16_t minIndexValue, uint16_t maxIndexValue,
                 int baseVertex);
```

使用索引缓冲区绘制几何体，提供索引范围优化。

#### drawInstanced()

```cpp
void drawInstanced(int instanceCount, int baseInstance,
                   int vertexCount, int baseVertex);
```

实例化绘制（需要硬件支持）。

#### drawIndexedInstanced()

```cpp
void drawIndexedInstanced(int indexCount, int baseIndex,
                          int instanceCount, int baseInstance,
                          int baseVertex);
```

索引实例化绘制。

#### drawIndirect() / drawIndexedIndirect()

```cpp
void drawIndirect(const GrBuffer* drawIndirectBuffer,
                  size_t bufferOffset, int drawCount);
void drawIndexedIndirect(const GrBuffer* drawIndirectBuffer,
                         size_t bufferOffset, int drawCount);
```

从缓冲区读取绘制参数进行间接绘制。如果硬件不支持，自动 polyfill 为循环调用实例化绘制。

#### drawIndexPattern()

```cpp
void drawIndexPattern(int patternIndexCount, int patternRepeatCount,
                      int maxPatternRepetitionsInIndexBuffer,
                      int patternVertexCount, int baseVertex);
```

绘制重复的索引模式，用于高效绘制重复几何体。

### 其他操作

#### clear()

```cpp
void clear(const GrScissorState& scissor, std::array<float, 4> color);
```

清除渲染目标（全部或剪裁区域）。

#### clearStencilClip()

```cpp
void clearStencilClip(const GrScissorState& scissor, bool insideStencilMask);
```

清除模板剪裁。

#### inlineUpload()

```cpp
virtual void inlineUpload(GrOpFlushState*, GrDeferredTextureUploadFn&) = 0;
```

在绘制过程中上传纹理数据（纯虚函数）。

#### executeDrawable()

```cpp
void executeDrawable(std::unique_ptr<SkDrawable::GpuDrawHandler>);
```

执行 SkDrawable 对象（用于嵌入原生绘制代码）。

## 内部实现细节

### 状态验证机制

使用 `prepareToDraw()` 在每次绘制前验证状态：

```cpp
bool GrOpsRenderPass::prepareToDraw() {
    if (DrawPipelineStatus::kOk != fDrawPipelineStatus) {
        this->gpu()->stats()->incNumFailedDraws();
        return false;
    }
    SkASSERT(DynamicStateStatus::kUninitialized != fScissorStatus);
    SkASSERT(DynamicStateStatus::kUninitialized != fTextureBindingStatus);

    if (kNone_GrXferBarrierType != fXferBarrierType) {
        this->gpu()->xferBarrier(fRenderTarget, fXferBarrierType);
    }
    return true;
}
```

### 间接绘制 Polyfill

当硬件不支持间接绘制时的回退实现：

```cpp
if (!this->gpu()->caps()->nativeDrawIndirectSupport()) {
    auto* cpuIndirectBuffer = static_cast<const GrCpuBuffer*>(drawIndirectBuffer);
    auto* cmds = reinterpret_cast<const GrDrawIndirectCommand*>(
            cpuIndirectBuffer->data() + bufferOffset);
    for (int i = 0; i < drawCount; ++i) {
        auto [vertexCount, instanceCount, baseVertex, baseInstance] = cmds[i];
        this->onDrawInstanced(instanceCount, baseInstance, vertexCount, baseVertex);
    }
    return;
}
```

这确保了 API 的一致性，即使在不支持的硬件上也能工作。

### 索引模式优化

`drawIndexPattern()` 实现分批绘制：

```cpp
void GrOpsRenderPass::drawIndexPattern(int patternIndexCount, int patternRepeatCount,
                                       int maxPatternRepetitionsInIndexBuffer,
                                       int patternVertexCount, int baseVertex) {
    int baseRepetition = 0;
    while (baseRepetition < patternRepeatCount) {
        int repeatCount = std::min(patternRepeatCount - baseRepetition,
                                   maxPatternRepetitionsInIndexBuffer);
        int drawIndexCount = repeatCount * patternIndexCount;
        int minIndexValue = 0;
        int maxIndexValue = patternVertexCount * repeatCount - 1;
        this->drawIndexed(drawIndexCount, 0, minIndexValue, maxIndexValue,
                          patternVertexCount * baseRepetition + baseVertex);
        baseRepetition += repeatCount;
    }
}
```

这允许使用有限大小的索引缓冲区绘制任意数量的重复。

### 调试状态追踪

在 DEBUG 模式下跟踪动态状态：

```cpp
#ifdef SK_DEBUG
enum class DynamicStateStatus {
    kDisabled,      // 功能未启用
    kUninitialized, // 需要但未设置
    kConfigured     // 已正确配置
};

DynamicStateStatus fScissorStatus;
DynamicStateStatus fTextureBindingStatus;
bool fHasIndexBuffer;
DynamicStateStatus fInstanceBufferStatus;
DynamicStateStatus fVertexBufferStatus;
#endif
```

这有助于在开发过程中捕获状态配置错误。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrRenderTarget` | 渲染目标表示 |
| `GrBuffer` | 缓冲区对象 |
| `GrProgramInfo` | 程序配置信息 |
| `GrPipeline` | 渲染管线 |
| `GrGeometryProcessor` | 几何处理器 |
| `GrGpu` | GPU 抽象层 |
| `GrCaps` | 硬件能力查询 |
| `GrScissorState` | 剪裁状态 |
| `SkDrawable` | 可绘制对象 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrDrawOp` | 所有绘制操作通过此类执行 |
| `GrOpFlushState` | 管理渲染通道生命周期 |
| `GrOpsTask` | 使用渲染通道执行任务 |
| `GrGLGpu` / `GrVkGpu` / `GrMtlGpu` | 实现具体后端 |

## 设计模式与设计决策

### 命令模式

`GrOpsRenderPass` 实现命令模式：
- **命令接口**：draw(), clear() 等方法
- **接收者**：GPU 硬件
- **调用者**：GrDrawOp 对象
- **命令缓冲**：Vulkan/Metal 后端可以延迟执行

### 模板方法模式

基类提供算法框架，子类实现具体步骤：

```cpp
void GrOpsRenderPass::draw(...) {
    if (!this->prepareToDraw()) { return; }  // 基类逻辑
    this->onDraw(...);                        // 子类实现
}
```

### 策略模式

通过虚函数实现不同后端的绘制策略：
- GL：立即模式绘制
- Vulkan：命令缓冲记录
- Metal：渲染命令编码器

### NVI（Non-Virtual Interface）

公共接口是非虚的，实际实现是私有虚函数：

```cpp
public:
    void draw(int vertexCount, int baseVertex);  // 非虚
private:
    virtual void onDraw(int vertexCount, int baseVertex) = 0;  // 虚
```

**优点**：
- 基类控制调用时机和前置条件检查
- 子类只需关注核心逻辑
- 更好的封装性

## 性能考量

### 状态缓存

通过成员变量缓存当前绑定的缓冲区：
- 避免冗余的 GPU 状态切换
- 减少驱动开销
- 后端可以优化批处理

### 间接绘制优化

原生支持间接绘制时：
- **单次 GPU 调用**：批量执行多个绘制命令
- **CPU 开销降低**：减少 CPU-GPU 通信
- **并行度提高**：GPU 可以并行调度

Polyfill 实现虽然性能较低，但保证了功能可用性。

### 索引范围提示

`drawIndexed()` 接受 `minIndexValue` 和 `maxIndexValue`：
- **顶点缓存优化**：某些 GPU 可以预取特定范围的顶点
- **验证优化**：驱动可以跳过边界检查
- **内存带宽节省**：只访问必要的顶点数据

### 传输屏障管理

自动插入传输屏障：
```cpp
if (kNone_GrXferBarrierType != fXferBarrierType) {
    this->gpu()->xferBarrier(fRenderTarget, fXferBarrierType);
}
```

确保混合操作的正确性，同时避免不必要的同步。

### 批处理支持

`drawIndexPattern()` 允许高效绘制重复几何体：
- 减少绘制调用次数
- 更好的 GPU 利用率
- 降低 CPU 开销

## 相关文件

| 文件路径 | 关系 |
|---------|------|
| `src/gpu/ganesh/GrOpsTask.h` | 使用渲染通道执行任务 |
| `src/gpu/ganesh/GrOpFlushState.h` | 管理通道生命周期 |
| `src/gpu/ganesh/GrDrawOp.h` | 通过通道执行绘制 |
| `src/gpu/ganesh/GrProgramInfo.h` | 程序配置信息 |
| `src/gpu/ganesh/GrPipeline.h` | 渲染管线定义 |
| `src/gpu/ganesh/GrGpu.h` | GPU 抽象层 |
| `src/gpu/ganesh/gl/GrGLOpsRenderPass.h` | OpenGL 实现 |
| `src/gpu/ganesh/vk/GrVkOpsRenderPass.h` | Vulkan 实现 |
| `src/gpu/ganesh/mtl/GrMtlOpsRenderPass.h` | Metal 实现 |
| `src/gpu/ganesh/GrBuffer.h` | 缓冲区定义 |
| `src/gpu/ganesh/GrRenderTarget.h` | 渲染目标定义 |
