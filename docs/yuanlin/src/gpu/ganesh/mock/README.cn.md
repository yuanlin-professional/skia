# mock - Mock GPU 后端（测试用模拟后端）

## 概述

`src/gpu/ganesh/mock` 目录实现了 Skia Ganesh GPU 后端的 Mock（模拟）实现。Mock 后端是一个完整但不执行实际 GPU 操作的后端，主要用于单元测试、性能基准测试和无 GPU 环境下的功能验证。它提供了与真实 GPU 后端（如 OpenGL、Vulkan、Metal、Direct3D）相同的接口契约，但所有实际的渲染操作都被替换为空操作或简单的成功返回。

Mock 后端的设计哲学是"行为兼容但无副作用"。`GrMockGpu` 类继承自 `GrGpu`，实现了所有必需的虚函数接口，包括纹理创建、缓冲区管理、渲染通道操作和资源生命周期管理。读写像素操作直接返回成功，表面复制操作不执行实际数据传输，但所有返回值和状态变化都与真实后端保持一致。这使得上层的 Ganesh 渲染逻辑可以在 Mock 后端上运行完整的代码路径。

`GrMockCaps` 类模拟了 GPU 的能力查询系统。通过 `GrMockOptions` 配置结构，测试代码可以精确控制 Mock GPU 支持哪些格式、渲染能力和硬件特性。例如，可以设置最大纹理尺寸、是否支持 MSAA、是否支持 mipmap 以及各种颜色格式的可纹理化和可渲染性。这种可配置性使得测试可以覆盖各种硬件能力组合的边界情况。

Mock 后端还提供了 `GrMockOpTarget`，一个模拟的 `GrMeshDrawTarget` 实现，用于对绘制操作（如细分操作）进行单元测试。它使用预分配的 CPU 内存缓冲区代替 GPU 缓冲区映射，允许测试代码在绘制操作完成后检查写入的顶点数据。此外，`GrMockRenderTask` 和 `GrMockSurfaceProxy` 提供了渲染任务和表面代理的测试桩。

## 架构图

```
+---------------------------------------------------------------+
|                     测试框架 / 单元测试                         |
|  GrMockOptions 配置 --> GrDirectContext::MakeMock()            |
+---------------------------------------------------------------+
                              |
                              v
+---------------------------------------------------------------+
|                GrMockGpu (模拟 GPU 设备)                       |
|  继承自 GrGpu，实现所有虚函数                                   |
+---------------------------------------------------------------+
     |           |           |           |           |
     v           v           v           v           v
+--------+ +--------+ +----------+ +----------+ +----------+
|GrMock  | |GrMock  | |GrMock    | |GrMock    | |GrMock    |
|Caps    | |Texture | |Render    | |Buffer    | |Attachment|
|        | |        | |Target    | |          | |          |
|模拟GPU | |模拟纹理| |模拟渲染  | |模拟缓冲区| |模拟附件  |
|能力查询| |资源    | |目标      | |          | |(模板)    |
+--------+ +--------+ +----------+ +----------+ +----------+
                              |
                              v
+---------------------------------------------------------------+
|          GrMockOpsRenderPass (模拟渲染通道)                     |
|  - 所有绘制调用计数但不执行                                     |
|  - 标记渲染目标为脏（触发 mipmap 重生成标记）                    |
+---------------------------------------------------------------+

辅助测试类:
+-------------------+ +---------------------+ +--------------------+
| GrMockOpTarget    | | GrMockRenderTask     | | GrMockSurfaceProxy |
| (模拟绘制目标)     | | (模拟渲染任务)       | | (模拟表面代理)      |
| - CPU 内存缓冲区  | | - 依赖关系追踪       | | - 最小化代理桩     |
| - 顶点/间接数据   | | - 代理使用追踪       | |                    |
+-------------------+ +---------------------+ +--------------------+

后端格式系统:
+---------------------------------------------------------------+
| GrMockBackendSurface.cpp                                       |
|  GrMockBackendFormatData / GrMockBackendTextureData /          |
|  GrMockBackendRenderTargetData                                 |
|  - 将 GrColorType/CompressionType 包装为 GrBackendFormat      |
|  - 提供 Mock 特有的纹理和渲染目标后端数据                       |
+---------------------------------------------------------------+
```

## 文件分类索引

### 1. 核心实现 — GPU/Caps

| 文件 | 说明 |
|------|------|
| GrMockGpu.h / GrMockGpu.cpp | Mock GPU 设备（继承 GrGpu，所有操作为空实现） |
| GrMockCaps.h / GrMockCaps.cpp | Mock GPU 能力查询（通过 GrMockOptions 配置） |

### 2. 渲染 — RenderPass

| 文件 | 说明 |
|------|------|
| GrMockOpsRenderPass.h | Mock 渲染操作通道（计数但不执行绘制） |

### 3. 资源/代理 — Texture/Buffer/Proxy

| 文件 | 说明 |
|------|------|
| GrMockTexture.h | Mock 纹理/渲染目标/纹理渲染目标 |
| GrMockBuffer.h | Mock GPU 缓冲区 |
| GrMockAttachment.h | Mock 模板附件 |
| GrMockSurfaceProxy.h | Mock 表面代理（最小化测试桩） |
| GrMockRenderTask.h | Mock 渲染任务（依赖关系追踪） |

### 4. 互操作/后端 — Backend Surface/Types

| 文件 | 说明 |
|------|------|
| GrMockBackendSurface.cpp | Mock 后端表面格式实现 |
| GrMockTypes.cpp | Mock 类型工具函数 |
| GrMockTypesPriv.h | Mock 私有类型（GrMockTextureSpec） |

### 5. 测试操作目标 — Op Target

| 文件 | 说明 |
|------|------|
| GrMockOpTarget.h | Mock 绘制操作目标（CPU 内存缓冲区替代 GPU 缓冲区） |

## 关键类与函数

### GrMockGpu
Mock GPU 设备类，继承自 `GrGpu`。是整个 Mock 后端的入口点。

- `Make(const GrMockOptions*, const GrContextOptions&, GrDirectContext*)` - 静态工厂方法，创建 Mock GPU 实例
- `onCreateTexture(...)` - 创建 `GrMockTexture` 或 `GrMockTextureRenderTarget`，支持 mipmap 状态和保护内容
- `onCreateCompressedTexture(...)` - 创建压缩格式的 Mock 纹理
- `onWrapBackendTexture(...)` / `onWrapRenderableBackendTexture(...)` / `onWrapBackendRenderTarget(...)` - 包装外部后端资源为 Mock 资源
- `onCreateBuffer(...)` - 创建 `GrMockBuffer` 实例
- `onGetOpsRenderPass(...)` - 返回 `GrMockOpsRenderPass` 实例
- `submit(GrOpsRenderPass*)` - 累积绘制计数到统计信息，然后删除渲染通道
- `onReadPixels()` / `onWritePixels()` / `onCopySurface()` 等 - 直接返回 `true`，不执行实际操作
- `onCreateBackendTexture(...)` / `deleteBackendTexture(...)` - 管理外部纹理 ID 的创建和清理
- `NextInternalTextureID()` / `NextExternalTextureID()` / `NextInternalRenderTargetID()` / `NextExternalRenderTargetID()` - 使用 `std::atomic` 生成唯一 ID，内部/外部使用不同的 ID 空间便于调试
- `fMockOptions` - 存储 Mock 配置选项，控制纹理分配失败模拟等行为

### GrMockCaps
Mock GPU 能力查询类，继承自 `GrCaps`。通过 `GrMockOptions` 精确配置所有 GPU 能力。

- 构造函数设置所有硬件能力标志：`fMipmapSupport`、`fDrawInstancedSupport`、`fHalfFloatVertexAttributeSupport`、`fMapBufferFlags`、`fMaxTextureSize`、`fMaxWindowRectangles`、`fMaxRenderTargetSize`、`fMaxVertexAttributes`
- `GrShaderCaps` 配置：`fIntegerSupport`、`fFlatInterpolationSupport`、`fMaxFragmentSamplers`、`fShaderDerivativeSupport`、`fDualSourceBlendingSupport`、`fSampleMaskSupport`
- `isFormatTexturable(format, GrTextureType)` - 查询格式是否可纹理化，委托给 `GrMockOptions::ConfigOptions::fTexturable`
- `isFormatRenderable(format, sampleCount)` - 查询格式是否可渲染，检查 `Renderability` 枚举
- `maxRenderTargetSampleCount(GrColorType)` - 根据配置返回 0（不可渲染）、1（非 MSAA）或 `kMaxSampleCnt`（16，支持 MSAA）
- `getRenderTargetSampleCount(requestCount, GrColorType)` - 返回支持的采样数，向上取到最近的 2 的幂
- `resolveMaskFormat()` 由 `onGetDefaultBackendFormat()` 支持，将 `GrColorType` 映射为 Mock 后端格式
- `getTestingCombinations()` - 返回所有支持的格式/颜色类型组合列表，用于测试

### GrMockTexture / GrMockRenderTarget / GrMockTextureRenderTarget
Mock 纹理和渲染目标的层次结构。

- `GrMockTexture` - 继承自 `GrTexture`，存储 `GrMockTextureInfo`，支持 budgeted/wrapped 两种缓存模式
  - `getBackendTexture()` - 返回 `GrBackendTextures::MakeMock()` 构造的后端纹理
  - `backendFormat()` - 委托给 `fInfo.getBackendFormat()`
- `GrMockRenderTarget` - 继承自 `GrRenderTarget`，存储 `GrMockRenderTargetInfo`
  - `onGpuMemorySize()` - 计算模拟的 GPU 内存占用，考虑 MSAA 解析缓冲区
  - `canAttemptStencilAttachment()` / `completeStencilAttachment()` - 始终返回 `true`
- `GrMockTextureRenderTarget` - 多继承自 `GrMockTexture` 和 `GrMockRenderTarget`，表示可同时作为纹理和渲染目标的资源
  - 正确处理菱形继承问题，使用 `GrSurface` 作为虚基类
  - `asTexture()` / `asRenderTarget()` - 提供类型转换

### GrMockBuffer
Mock GPU 缓冲区，继承自 `GrGpuBuffer`。

- `onMap()` - 当 `mapBufferFlags` 非零时通过 `sk_malloc_throw` 分配 CPU 内存
- `onUnmap()` - 释放映射的内存
- `onClearToZero()` / `onUpdateData()` - 直接返回 `true`

### GrMockAttachment
Mock 模板附件，继承自 `GrAttachment`。

- 仅支持 `UsageFlags::kStencilAttachment` 用途
- `backendFormat()` - 返回 `GrBackendFormats::MakeMockStencilFormat()`

### GrMockOpsRenderPass
Mock 渲染操作通道，继承自 `GrOpsRenderPass`。

- 所有绘制方法（`onDraw`、`onDrawIndexed`、`onDrawInstanced`、`onDrawIndexedInstanced`、`onDrawIndirect`、`onDrawIndexedIndirect`）调用 `noopDraw()` 计数并标记渲染目标为脏
- `onBegin()` - 如果加载操作为 `kClear` 则标记目标为脏
- `onClear()` - 标记渲染目标为脏
- `numDraws()` - 返回总绘制调用次数，供 `GrMockGpu::submit()` 累积统计

### GrMockOpTarget
模拟的 `GrMeshDrawTarget` 实现，用于绘制操作的单元测试。

- 使用 6MB 静态顶点数据缓冲区（`fStaticVertexData[6 * 1024 * 1024]`）
- `makeVertexSpace()` / `makeVertexSpaceAtLeast()` - 返回预分配的 CPU 缓冲区指针
- `makeDrawIndirectSpace()` / `makeDrawIndexedIndirectSpace()` - 返回预分配的间接绘制数据缓冲区
- `peekStaticVertexData()` / `peekStaticIndirectData()` - 测试代码可以检查写入的数据
- 未实现的方法使用 `SK_ABORT` 宏标记，确保测试只使用预期的 API

### GrMockRenderTask
Mock 渲染任务，继承自 `GrRenderTask`。

- `addTarget()` / `addDependency()` / `addUsed()` - 手动设置任务的目标、依赖和使用的代理
- `onIsUsed()` - 遍历 `fUsed` 数组检查代理是否被使用
- `onExecute()` - 直接返回 `true`
- 构造时立即设置 `kDisowned_Flag`，因为 Mock 任务不受 DrawManager 管理

### GrMockSurfaceProxy
最小化的表面代理桩，继承自 `GrSurfaceProxy`。

- 创建 1x1 像素、RGBA_8888 格式、非预算、不使用分配器的代理
- `instantiate()` - 返回 `false`，不进行实际实例化
- `createSurface()` - 返回 `nullptr`

### GrMockBackendSurface.cpp 中的后端数据类
实现了 Mock 后端的格式系统。

- `GrMockBackendFormatData` - 包装 `GrColorType` 或 `SkTextureCompressionType` 或模板标志，三者互斥。实现 `bytesPerBlock()`、`stencilBits()`、`channelMask()` 等格式查询
- `GrMockBackendTextureData` - 存储 `GrMockTextureInfo`，实现 `isSameTexture()` 通过 ID 比较
- `GrMockBackendRenderTargetData` - 存储 `GrMockRenderTargetInfo`
- `GrBackendFormats::MakeMockColorType()` / `MakeMockCompressionType()` / `MakeMockStencilFormat()` - 创建各种 Mock 格式

## 依赖关系

### 上游依赖（本模块依赖的模块）
- `src/gpu/ganesh/` - Ganesh 核心（`GrGpu`、`GrCaps`、`GrTexture`、`GrRenderTarget`、`GrGpuBuffer`、`GrAttachment`、`GrOpsRenderPass`、`GrRenderTask`、`GrSurfaceProxy`、`GrMeshDrawTarget`）
- `include/gpu/ganesh/mock/` - Mock 公共头文件（`GrMockTypes.h`、`GrMockBackendSurface.h`）
- `src/gpu/ganesh/GrBackendSurfacePriv.h` - 后端表面私有 API，用于创建自定义后端格式
- `include/gpu/ganesh/GrDirectContext.h` - 直接上下文，`GrMockOpTarget` 持有其引用

### 下游依赖（依赖本模块的模块）
- Skia 单元测试框架广泛使用 `GrDirectContext::MakeMock()` 创建测试上下文
- 细分操作测试使用 `GrMockOpTarget` 验证顶点数据输出
- 渲染任务调度测试使用 `GrMockRenderTask` 验证依赖关系图
- 资源管理测试使用 `GrMockSurfaceProxy` 验证代理生命周期

## 设计模式分析

### 空对象模式（Null Object Pattern）
Mock 后端是空对象模式的典型应用。`GrMockGpu` 中的大量方法（如 `onReadPixels()`、`onWritePixels()`、`onCopySurface()`、`onTransferPixelsTo()` 等）直接返回成功，不执行任何实际操作。这使得上层代码无需特殊处理即可在无 GPU 环境中运行。

### 策略模式（Strategy Pattern）
`GrMockOptions` 和 `GrMockCaps` 构成策略模式。通过改变 `GrMockOptions` 中的配置（如 `fFailTextureAllocations`、各格式的 `Renderability`、`fMaxTextureSize` 等），同一个 Mock 后端可以模拟不同硬件的行为特征。

### 工厂方法模式（Factory Method Pattern）
- `GrMockGpu::Make()` 是工厂方法，根据 `GrMockOptions` 创建配置好的 Mock GPU
- `NextInternalTextureID()` 等静态方法使用原子计数器生成全局唯一 ID，内部和外部纹理使用不同的 ID 空间（正数/负数），便于调试时区分资源来源

### 组合模式（Composite Pattern）
`GrMockTextureRenderTarget` 通过多继承组合了 `GrMockTexture` 和 `GrMockRenderTarget` 的功能，使用 `GrSurface` 虚基类解决菱形继承问题。`asTexture()` 和 `asRenderTarget()` 方法提供了统一的类型转换接口。

### 测试替身模式（Test Double Pattern）
整个 Mock 目录是测试替身模式的实现：
- `GrMockGpu` 是 Fake（具有简化行为的替代实现）
- `GrMockOpTarget` 是 Spy（记录交互以供后续验证）
- `GrMockRenderTask` 和 `GrMockSurfaceProxy` 是 Stub（返回预设值的最小实现）

## 数据流

```
1. Mock 上下文创建
   GrMockOptions 配置 --> GrMockGpu::Make()
       |
       +-- GrMockCaps 根据 options 初始化能力标志
       +-- GrShaderCaps 配置着色器能力
       +-- GrMockGpu 注册到 GrDirectContext
       |
       v
2. 资源创建流程 (以纹理为例)
   GrResourceProvider::createTexture()
       |
       v
   GrMockGpu::onCreateTexture()
       |
       +-- 检查 fMockOptions.fFailTextureAllocations (可模拟失败)
       +-- 生成 NextInternalTextureID() 唯一标识
       +-- 创建 GrMockTextureInfo(colorType, compression, id, protected)
       +-- 根据是否 Renderable 创建:
           +-- GrMockTexture (仅纹理)
           +-- GrMockTextureRenderTarget (纹理+渲染目标)
       +-- 注册到缓存 (budgeted/wrapped)
       |
       v
3. 渲染通道流程
   GrOpsTask 请求渲染通道
       |
       v
   GrMockGpu::onGetOpsRenderPass()
       |
       v
   new GrMockOpsRenderPass(gpu, rt, origin, colorInfo)
       |
       v
   Ops 在渲染通道上执行:
   - onBindPipeline() --> true
   - onBindTextures() --> true
   - onBindBuffers() --> no-op
   - onDraw/onDrawIndexed/onDrawInstanced... --> noopDraw()
     (计数 ++fNumDraws, 标记 RT 脏)
       |
       v
   GrMockGpu::submit(renderPass)
       |
       +-- 遍历 numDraws 累积 fStats.incNumDraws()
       +-- delete renderPass
       |
       v
4. 后端纹理 ID 管理
   创建: onCreateBackendTexture()
       +-- NextExternalTextureID() (负数空间)
       +-- fOutstandingTestingOnlyTextureIDs.add(id)

   验证: isTestingOnlyBackendTexture()
       +-- fOutstandingTestingOnlyTextureIDs.contains(id)

   删除: deleteBackendTexture()
       +-- fOutstandingTestingOnlyTextureIDs.remove(id)
       |
       v
5. 单元测试数据流 (GrMockOpTarget)
   创建 GrMockOpTarget(mockContext)
       +-- 分配 6MB 静态顶点缓冲区
       +-- 分配间接绘制缓冲区
       |
       v
   被测操作 (如 PathTessellator) 调用:
   - target->makeVertexSpace() --> 返回 fStaticVertexData 指针
   - 操作写入顶点数据
       |
       v
   测试代码验证:
   - target->peekStaticVertexData() 检查输出
```

## 相关文档与参考

- `include/gpu/ganesh/mock/GrMockTypes.h` - Mock 类型公共头文件（`GrMockOptions`、`GrMockTextureInfo`、`GrMockRenderTargetInfo`）
- `include/gpu/ganesh/mock/GrMockBackendSurface.h` - Mock 后端表面公共 API（`GrBackendFormats::MakeMockColorType()` 等）
- `src/gpu/ganesh/GrGpu.h` - GPU 设备抽象基类，定义了所有 Mock 需要实现的虚函数
- `src/gpu/ganesh/GrCaps.h` - GPU 能力查询基类
- `src/gpu/ganesh/GrMeshDrawTarget.h` - 网格绘制目标接口，`GrMockOpTarget` 的基类
- `src/gpu/ganesh/GrRenderTask.h` - 渲染任务基类，`GrMockRenderTask` 的基类
- `src/gpu/ganesh/GrSurfaceProxy.h` - 表面代理基类，`GrMockSurfaceProxy` 的基类
- `tests/` 目录下大量测试使用 `GrDirectContext::MakeMock()` 作为测试环境
