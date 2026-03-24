# GrGLOpsRenderPass

> 源文件
> - src/gpu/ganesh/gl/GrGLOpsRenderPass.h
> - src/gpu/ganesh/gl/GrGLOpsRenderPass.cpp

## 概述

`GrGLOpsRenderPass` 是 Skia 图形库中 Ganesh OpenGL 后端的渲染通道实现类。它继承自 `GrOpsRenderPass`，负责将图形操作命令直接转换为 OpenGL 调用。与传统的命令缓冲不同，该类采用即时执行模式，所有绘制命令都会立即发送到 GPU 执行，不进行缓冲或延迟处理。

该类的主要职责是管理一个渲染通道的生命周期，包括设置渲染目标、绑定管线状态、处理各种绘制调用（索引绘制、实例化绘制、间接绘制等）以及执行清除操作。它作为 Skia 高级图形操作和底层 OpenGL API 之间的桥梁，将抽象的渲染操作转换为具体的 GL 函数调用。

## 架构位置

```
GrOpsRenderPass (基类)
    ├── GrGLOpsRenderPass (GL后端实现)
    └── 其他后端实现 (Vulkan, Metal等)

渲染流程:
GrOpFlushState -> GrOpsRenderPass -> GrGLOpsRenderPass -> GrGLGpu -> OpenGL Driver
```

`GrGLOpsRenderPass` 位于 Ganesh 图形栈的 OpenGL 后端层，处于高层渲染操作（`GrOpsRenderPass`）和底层 GPU 接口（`GrGLGpu`）之间。它是 OpenGL 渲染路径的核心组件，负责协调和执行所有 GL 绘制命令。

## 主要类与结构体

### GrGLOpsRenderPass

**继承关系:**
- 继承自: `GrOpsRenderPass`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fGpu` | `GrGLGpu* const` | 指向 GL GPU 对象的常量指针 |
| `fUseMultisampleFBO` | `bool` | 是否使用多重采样帧缓冲对象 |
| `fContentBounds` | `SkIRect` | 内容边界矩形 |
| `fColorLoadAndStoreInfo` | `LoadAndStoreInfo` | 颜色缓冲的加载和存储信息 |
| `fStencilLoadAndStoreInfo` | `StencilLoadAndStoreInfo` | 模板缓冲的加载和存储信息 |
| `fPrimitiveType` | `GrPrimitiveType` | 当前图元类型 |
| `fAttribArrayState` | `GrGLAttribArrayState*` | 顶点属性数组状态 |
| `fIndexPointer` | `const uint16_t*` | 索引数据指针 |
| `fDidBindVertexBuffer` | `bool` (DEBUG) | 调试标记，顶点缓冲是否已绑定 |
| `fDidBindInstanceBuffer` | `bool` (DEBUG) | 调试标记，实例缓冲是否已绑定 |

## 公共 API 函数

### 构造与初始化
- `GrGLOpsRenderPass(GrGLGpu* gpu)` - 构造函数，接收 GPU 对象指针
- `void set(...)` - 设置渲染目标和渲染通道参数
- `void reset()` - 重置渲染目标引用

### 生命周期管理
- `void onBegin()` - 渲染通道开始时调用
- `void onEnd()` - 渲染通道结束时调用

### 管线绑定
- `bool onBindPipeline(...)` - 绑定图形管线状态
- `void onSetScissorRect(...)` - 设置裁剪矩形
- `bool onBindTextures(...)` - 绑定纹理资源
- `void onBindBuffers(...)` - 绑定顶点、实例和索引缓冲

### 绘制命令
- `void onDraw(int vertexCount, int baseVertex)` - 简单顶点绘制
- `void onDrawIndexed(...)` - 索引绘制
- `void onDrawInstanced(...)` - 实例化绘制
- `void onDrawIndexedInstanced(...)` - 索引实例化绘制
- `void onDrawIndirect(...)` - 间接绘制
- `void onDrawIndexedIndirect(...)` - 索引间接绘制

### 清除操作
- `void onClear(...)` - 清除颜色缓冲
- `void onClearStencilClip(...)` - 清除模板裁剪

### 其他
- `void inlineUpload(...)` - 内联纹理上传

## 内部实现细节

### DMSAA (Dynamic MSAA) 支持

该类实现了对动态多重采样抗锯齿的特殊处理。DMSAA 允许在单采样纹理和多采样渲染缓冲之间动态切换：

```cpp
void GrGLOpsRenderPass::onBegin() {
    if (fUseMultisampleFBO &&
        fColorLoadAndStoreInfo.fLoadOp == GrLoadOp::kLoad &&
        glRT->hasDynamicMSAAAttachment()) {
        // 从单采样FBO加载到DMSAA附件
        if (fGpu->glCaps().canResolveSingleToMSAA()) {
            fGpu->resolveRenderFBOs(..., kSingleToMSAA);
        } else {
            fGpu->drawSingleIntoMSAAFBO(...);
        }
    }
}
```

### 缓冲绑定策略

由于不同平台的 OpenGL 驱动存在差异和 bug，该类实现了灵活的缓冲绑定策略：

1. **baseVertex/baseInstance 支持检测**: 对于不支持这些扩展的平台，延迟绑定缓冲并手动调整偏移量
2. **驱动 bug 规避**: 针对 `drawArraysBaseVertexIsBroken` 问题，在绘制时重新绑定顶点缓冲

### 多绘制调用优化

对于 ANGLE 和 WebGL 平台，由于不支持 `glMultiDrawElementsIndirect`，实现了替代方案：

```cpp
void GrGLOpsRenderPass::multiDrawArraysANGLEOrWebGL(...) {
    constexpr static int kMaxDrawCountPerBatch = 128;
    // 批量处理绘制命令
    while (drawCount) {
        int countInBatch = std::min(drawCount, kMaxDrawCountPerBatch);
        GL_CALL(MultiDrawArraysInstancedBaseInstance(...));
    }
}
```

### 实例化绘制的崩溃规避

某些驱动在处理大量实例时会崩溃，代码通过分批绘制来规避：

```cpp
int maxInstances = fGpu->glCaps().maxInstancesPerDrawWithoutCrashing(instanceCount);
for (int i = 0; i < instanceCount; i += maxInstances) {
    int instanceCountForDraw = std::min(instanceCount - i, maxInstances);
    // 分批绘制
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrGLGpu` | 底层 OpenGL GPU 接口 |
| `GrGLProgram` | 管线程序管理 |
| `GrGLVertexArray` | 顶点数组对象管理 |
| `GrGLRenderTarget` | 渲染目标抽象 |
| `GrGLCaps` | OpenGL 能力查询 |
| `GrBuffer` | 缓冲对象抽象 |
| `GrProgramInfo` | 程序信息容器 |
| `GrPipeline` | 图形管线状态 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|---------|
| `GrOpFlushState` | 通过该类执行渲染操作 |
| `GrRenderTargetProxy` | 使用该类作为渲染目标的具体实现 |

## 设计模式与设计决策

### 1. 即时执行模式 (Pass-Through Pattern)

该类采用即时执行模式，所有命令直接转发给 GPU，不进行缓冲：

```cpp
// 直接传递给 GPU 执行
void onDraw(int vertexCount, int baseVertex) override {
    GrGLenum glPrimType = fGpu->prepareToDraw(fPrimitiveType);
    GL_CALL(DrawArrays(glPrimType, baseVertex, vertexCount));
    fGpu->didDrawTo(fRenderTarget);
}
```

**设计理由**: OpenGL 本身已经有命令缓冲机制，在应用层再次缓冲会增加复杂性和开销。

### 2. 平台差异抽象

通过 `GrGLCaps` 查询能力并采用不同代码路径：

```cpp
if (fGpu->glCaps().baseVertexBaseInstanceSupport()) {
    GL_CALL(DrawElementsInstancedBaseVertexBaseInstance(...));
} else {
    // 手动调整缓冲绑定
    this->bindVertexBuffer(fActiveVertexBuffer.get(), baseVertex);
    GL_CALL(DrawElementsInstanced(...));
}
```

### 3. 资源绑定生命周期管理

使用 `sk_sp` 智能指针管理活动缓冲，确保资源在绘制过程中不会被释放：

```cpp
fActiveVertexBuffer = std::move(vertexBuffer);
fActiveIndexBuffer = std::move(indexBuffer);
fActiveInstanceBuffer = std::move(instanceBuffer);
```

## 性能考量

### 1. 状态变化最小化

通过缓存状态（如 `fAttribArrayState`）避免不必要的 GL 状态切换。

### 2. 批处理策略

- 对于间接绘制，尽可能使用 `glMultiDrawArraysIndirect` 减少调用次数
- 对于大量实例，自动分批以避免驱动崩溃

### 3. 内存访问优化

区分 CPU 缓冲和 GPU 缓冲：
```cpp
if (indexBuffer->isCpuBuffer()) {
    auto* cpuIndexBuffer = static_cast<const GrCpuBuffer*>(indexBuffer.get());
    fIndexPointer = reinterpret_cast<const uint16_t*>(cpuIndexBuffer->data());
} else {
    fIndexPointer = nullptr; // GPU 端缓冲
}
```

### 4. DMSAA 分辨率优化

根据设备能力选择最优的分辨率策略：
```cpp
GrNativeRect dmsaaLoadStoreBounds() const {
    if (fGpu->glCaps().framebufferResolvesMustBeFullSize()) {
        return GrNativeRect::MakeRelativeTo(..., fRenderTarget->dimensions());
    } else {
        return GrNativeRect::MakeRelativeTo(..., fContentBounds);
    }
}
```

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/GrOpsRenderPass.h` | 基类 | 定义渲染通道抽象接口 |
| `src/gpu/ganesh/gl/GrGLGpu.h` | 依赖 | OpenGL GPU 实现 |
| `src/gpu/ganesh/gl/GrGLProgram.h` | 依赖 | GL 程序对象 |
| `src/gpu/ganesh/gl/GrGLRenderTarget.h` | 依赖 | GL 渲染目标 |
| `src/gpu/ganesh/gl/GrGLVertexArray.h` | 依赖 | 顶点数组对象 |
| `src/gpu/ganesh/GrOpFlushState.h` | 使用者 | 刷新状态管理 |
| `src/gpu/ganesh/GrDrawIndirectCommand.h` | 依赖 | 间接绘制命令结构 |
