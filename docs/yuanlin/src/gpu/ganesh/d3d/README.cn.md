# src/gpu/ganesh/d3d - Skia Ganesh Direct3D 12 后端实现

## 概述

本目录包含 Skia 图形库 Ganesh GPU 渲染引擎的 **Direct3D 12 (D3D12)** 后端完整实现。Ganesh 是 Skia 的 GPU 加速渲染框架，通过抽象层支持多种图形 API（OpenGL、Vulkan、Metal、Direct3D），而本目录正是 Direct3D 12 的具体实现。整个目录共约 54 个源文件（含头文件和实现文件），由 Google 于 2020 年开发并持续维护。

Direct3D 12 是微软提供的低级图形 API，仅在 Windows 平台上可用。与 Direct3D 11 相比，D3D12 将更多的资源管理职责下放到应用程序层，包括内存分配、资源屏障（Resource Barrier）、描述符堆（Descriptor Heap）管理以及命令列表（Command List）调度。因此本后端的代码量较大、结构复杂，需要显式管理这些底层资源。

本后端的核心架构遵循 Ganesh 的后端抽象模式：`GrD3DGpu` 作为核心入口继承自 `GrGpu`，`GrD3DCaps` 继承自 `GrCaps` 用于能力查询，`GrD3DOpsRenderPass` 继承自 `GrOpsRenderPass` 用于渲染通道操作。着色器编译流水线通过 SkSL 转换为 HLSL，再由 D3D 编译器编译为字节码。资源管理方面，本后端集成了 AMD 的 D3D12 Memory Allocator（D3D12MA）库来进行高效的 GPU 内存管理。

本后端的着色器处理路径为：SkSL -> HLSL -> D3D Bytecode。其中 SkSL 到 HLSL 的转换复用了 SPIRV 中间层的 Uniform 和 Varying 处理器（`GrSPIRVUniformHandler`、`GrSPIRVVaryingHandler`），随后通过 `SkSL::ToHLSL` 生成最终的 HLSL 代码，再调用 D3DCompile 编译为 GPU 可执行的着色器字节码。

## 架构图

```
                        ┌─────────────────────────────────────┐
                        │         GrDirectContext             │
                        │   (通过 GrDirectContexts::MakeD3D   │
                        │    创建 D3D12 上下文)                │
                        └──────────────┬──────────────────────┘
                                       │
                        ┌──────────────▼──────────────────────┐
                        │           GrD3DGpu                  │
                        │  (核心 GPU 接口，继承 GrGpu)         │
                        │  - ID3D12Device                     │
                        │  - ID3D12CommandQueue                │
                        │  - GrD3DMemoryAllocator             │
                        │  - ID3D12Fence                      │
                        └──┬──────┬──────┬──────┬─────────────┘
                           │      │      │      │
            ┌──────────────▼┐  ┌──▼──────┴┐  ┌──▼────────────────┐
            │ GrD3DCaps     │  │ GrD3D    │  │ GrD3DResource     │
            │ (能力查询)     │  │ Command  │  │ Provider          │
            │ - 格式支持     │  │ List     │  │ (资源提供者)       │
            │ - MSAA支持    │  │ (命令列表)│  │ - PipelineState   │
            │ - 模板格式     │  │          │  │   Cache           │
            └───────────────┘  └──────────┘  │ - RootSignature   │
                                             │ - DescriptorTable │
                                             │   Cache           │
                                             └────┬──────────────┘
                                                  │
                    ┌─────────────┬───────────────┼───────────────┐
                    │             │               │               │
          ┌─────────▼──┐  ┌──────▼────┐  ┌───────▼───┐  ┌───────▼──────────┐
          │ GrD3D      │  │ GrD3D     │  │ GrD3D     │  │ GrD3DDescriptor  │
          │ Pipeline   │  │ RootSig   │  │ Command   │  │ 管理子系统        │
          │ State      │  │ nature    │  │ Signature │  │ - CpuDescriptor  │
          │ Builder    │  │           │  │           │  │   Manager        │
          │ (SkSL→HLSL)│  └───────────┘  └───────────┘  │ - Descriptor     │
          └────────────┘                                 │   TableManager   │
                                                         └──────────────────┘
           ┌──────────────────────────────────────────────────────────┐
           │                  资源类层次结构                            │
           │                                                          │
           │  GrD3DTextureResource (纹理资源基类)                      │
           │    ├── GrD3DTexture (纹理)                                │
           │    │     └── GrD3DTextureRenderTarget (纹理+渲染目标)      │
           │    ├── GrD3DRenderTarget (渲染目标)                       │
           │    │     └── GrD3DTextureRenderTarget (钻石继承)           │
           │    └── GrD3DAttachment (模板/深度附件)                     │
           │                                                          │
           │  GrD3DBuffer (GPU 缓冲区)                                 │
           │  GrD3DSemaphore (GPU 同步信号量)                           │
           └──────────────────────────────────────────────────────────┘
```

## 文件分类索引

### 1. 核心实现 — GPU/Caps/Context

| 文件 | 说明 |
|------|------|
| GrD3DGpu.h / GrD3DGpu.cpp | D3D12 GPU 接口实现（核心入口，75K+ 行） |
| GrD3DCaps.h / GrD3DCaps.cpp | D3D12 能力查询与格式支持 |
| GrD3DDirectContext.cpp | DirectContext D3D12 创建入口 |

### 2. 能力/工具 — Utilities

| 文件 | 说明 |
|------|------|
| GrD3DUtil.h / GrD3DUtil.cpp | 工具函数与格式映射 |
| GrD3DTypesPriv.h / GrD3DTypesPriv.cpp | 私有类型定义 |
| GrD3DTypesMinimal.cpp | 类型最小化实现 |

### 3. 命令/渲染 — Command List/RenderPass

| 文件 | 说明 |
|------|------|
| GrD3DCommandList.h / GrD3DCommandList.cpp | 命令列表封装（Direct/Copy） |
| GrD3DCommandSignature.h / GrD3DCommandSignature.cpp | 间接绘制命令签名 |
| GrD3DOpsRenderPass.h / GrD3DOpsRenderPass.cpp | 渲染通道操作实现 |

### 4. 管线管理 — Pipeline

| 文件 | 说明 |
|------|------|
| GrD3DPipeline.h | PSO（管线状态对象）封装 |
| GrD3DPipelineState.h / GrD3DPipelineState.cpp | 完整管线状态（含 Uniform 绑定） |
| GrD3DPipelineStateBuilder.h / GrD3DPipelineStateBuilder.cpp | 管线状态构建器（SkSL→HLSL 编译） |
| GrD3DPipelineStateDataManager.h / GrD3DPipelineStateDataManager.cpp | Uniform 数据管理器 |
| GrD3DRootSignature.h / GrD3DRootSignature.cpp | 根签名定义 |

### 5. 描述符管理 — Descriptor Management

| 文件 | 说明 |
|------|------|
| GrD3DDescriptorHeap.h / GrD3DDescriptorHeap.cpp | 描述符堆基类 |
| GrD3DCpuDescriptorManager.h / GrD3DCpuDescriptorManager.cpp | CPU 端描述符管理器 |
| GrD3DDescriptorTableManager.h / GrD3DDescriptorTableManager.cpp | GPU 可见描述符表管理器 |

### 6. 资源/纹理 — Texture/Buffer/Attachment

| 文件 | 说明 |
|------|------|
| GrD3DTextureResource.h / GrD3DTextureResource.cpp | 纹理资源基类 |
| GrD3DTexture.h / GrD3DTexture.cpp | 纹理实现 |
| GrD3DRenderTarget.h / GrD3DRenderTarget.cpp | 渲染目标实现 |
| GrD3DTextureRenderTarget.h / GrD3DTextureRenderTarget.cpp | 纹理 + 渲染目标复合对象 |
| GrD3DAttachment.h / GrD3DAttachment.cpp | 模板/深度附件 |
| GrD3DBuffer.h / GrD3DBuffer.cpp | GPU 缓冲区实现 |

### 7. 资源管理 — Resource Provider

| 文件 | 说明 |
|------|------|
| GrD3DResourceProvider.h / GrD3DResourceProvider.cpp | 资源提供者（管线状态缓存、描述符管理） |
| GrD3DResourceState.h | 资源状态原子追踪 |

### 8. 内存管理 — Memory Allocator

| 文件 | 说明 |
|------|------|
| GrD3DAMDMemoryAllocator.h / GrD3DAMDMemoryAllocator.cpp | AMD D3D12MA 内存分配器 |

### 9. 同步 — Synchronization

| 文件 | 说明 |
|------|------|
| GrD3DSemaphore.h / GrD3DSemaphore.cpp | Fence 信号量封装 |

### 10. 后端表面 — Backend Surface

| 文件 | 说明 |
|------|------|
| GrD3DBackendSurface.cpp / GrD3DBackendSurfacePriv.h | 后端表面信息 |
| GrD3DBackendSemaphore.cpp | 后端信号量 |

## 关键类与函数

### 1. GrD3DGpu（文件：GrD3DGpu.h / GrD3DGpu.cpp）

**职责**：D3D12 后端的核心入口类，继承自 `GrGpu`，封装了 `ID3D12Device` 和 `ID3D12CommandQueue`，负责所有 GPU 操作的协调与调度。

**关键成员**：
- `fDevice`（`gr_cp<ID3D12Device>`）：D3D12 设备对象
- `fQueue`（`gr_cp<ID3D12CommandQueue>`）：命令队列
- `fMemoryAllocator`（`sk_sp<GrD3DMemoryAllocator>`）：内存分配器
- `fResourceProvider`（`GrD3DResourceProvider`）：资源提供者
- `fCurrentDirectCommandList`：当前活动的命令列表
- `fFence` / `fCurrentFenceValue`：GPU 围栏同步
- `fOutstandingCommandLists`：已提交但尚未完成的命令列表队列
- `fStagingBufferManager`：暂存缓冲区管理
- `fConstantsRingBuffer`：常量数据环形缓冲区

**关键方法**：
| 方法 | 描述 |
|------|------|
| `Make()` | 静态工厂方法，创建 GrD3DGpu 实例 |
| `onCreateTexture()` | 创建纹理资源 |
| `onReadPixels()` / `onWritePixels()` | 像素读写操作 |
| `onCopySurface()` | 表面复制 |
| `submit()` | 提交渲染通道 |
| `submitDirectCommandList()` | 提交命令列表到 GPU |
| `addResourceBarriers()` | 添加资源状态转换屏障 |
| `checkForFinishedCommandLists()` | 检查已完成的命令列表并回收 |
| `waitForQueueCompletion()` | 等待命令队列全部执行完毕 |
| `onGetOpsRenderPass()` | 获取渲染通道对象 |
| `makeStencilAttachment()` | 创建模板缓冲附件 |

### 2. GrD3DCaps（文件：GrD3DCaps.h / GrD3DCaps.cpp）

**职责**：查询和存储 D3D12 后端的硬件能力信息，继承自 `GrCaps`。包括格式支持、MSAA 采样数、模板格式等。

**关键方法**：
| 方法 | 描述 |
|------|------|
| `isFormatTexturable()` | 查询格式是否可用作纹理采样 |
| `isFormatRenderable()` | 查询格式是否可用作渲染目标 |
| `isFormatUnorderedAccessible()` | 查询格式是否支持 UAV |
| `getRenderTargetSampleCount()` | 获取支持的 MSAA 采样数 |
| `preferredStencilFormat()` | 获取首选模板格式 |
| `canCopyTexture()` / `canCopyAsResolve()` | 判断复制能力 |
| `getFormatFromColorType()` | 颜色类型到 DXGI 格式的映射 |
| `makeDesc()` | 生成管线程序描述 |

**内部结构**：
- `FormatInfo`：每种 DXGI 格式的能力信息（可采样、可渲染、MSAA、UAV）
- `ColorTypeInfo`：颜色类型与格式的映射关系及读写 Swizzle
- `D3DVendor` 枚举：识别 AMD、NVIDIA、Intel、ARM、Qualcomm 等 GPU 厂商

### 3. GrD3DCommandList（文件：GrD3DCommandList.h / GrD3DCommandList.cpp）

**职责**：封装 `ID3D12GraphicsCommandList`，管理 GPU 命令的录制与提交。提供资源追踪机制确保命令执行期间引用的资源不被释放。

**类层次**：
- `GrD3DCommandList`（基类）：通用命令列表功能
  - `GrD3DDirectCommandList`：直接命令列表，支持绘制、计算等完整功能
  - `GrD3DCopyCommandList`：仅支持复制操作的命令列表

**关键方法（GrD3DDirectCommandList）**：
| 方法 | 描述 |
|------|------|
| `setPipelineState()` | 设置管线状态对象 |
| `setGraphicsRootSignature()` | 设置图形根签名 |
| `setVertexBuffers()` / `setIndexBuffer()` | 绑定顶点/索引缓冲 |
| `drawInstanced()` | 实例化绘制 |
| `drawIndexedInstanced()` | 索引实例化绘制 |
| `executeIndirect()` | 间接绘制 |
| `dispatch()` | 计算着色器分派 |
| `clearRenderTargetView()` | 清除渲染目标 |
| `resourceBarrier()` | 资源状态转换 |
| `setDescriptorHeaps()` | 设置描述符堆 |

**资源追踪**：
- `fTrackedResources`：追踪 `GrManagedResource` 引用
- `fTrackedRecycledResources`：追踪 `GrRecycledResource` 引用
- `fTrackedGpuBuffers`：追踪 GPU 缓冲区引用
- `fFinishedCallbacks`：命令执行完成后的回调

### 4. GrD3DResourceProvider（文件：GrD3DResourceProvider.h / GrD3DResourceProvider.cpp）

**职责**：D3D12 资源的工厂和缓存管理中心。负责创建、缓存和回收各类 D3D12 资源对象。

**关键方法**：
| 方法 | 描述 |
|------|------|
| `findOrCreateDirectCommandList()` | 获取或创建命令列表 |
| `findOrCreateRootSignature()` | 获取或创建根签名 |
| `findOrCreateCompatiblePipelineState()` | 获取或创建兼容管线状态 |
| `findOrCreateMipmapPipeline()` | 获取 Mipmap 生成计算管线 |
| `createRenderTargetView()` | 创建 RTV 描述符 |
| `createDepthStencilView()` | 创建 DSV 描述符 |
| `createShaderResourceView()` | 创建 SRV 描述符 |
| `createUnorderedAccessView()` | 创建 UAV 描述符 |
| `findOrCreateShaderViewTable()` | 创建着色器视图描述符表 |
| `findOrCreateSamplerTable()` | 创建采样器描述符表 |
| `uploadConstantData()` | 上传常量数据 |

**内部缓存**：
- `PipelineStateCache`：基于 LRU 缓存的管线状态缓存
- `DescriptorTableCache`：描述符表缓存，避免重复创建

### 5. GrD3DPipelineStateBuilder（文件：GrD3DPipelineStateBuilder.h / GrD3DPipelineStateBuilder.cpp）

**职责**：构建完整的 D3D12 管线状态对象（PSO）。将 SkSL 着色器转译为 HLSL，编译为 D3D 字节码，组装渲染管线的全部配置。

**关键方法**：
| 方法 | 描述 |
|------|------|
| `MakePipelineState()` | 静态方法，创建完整管线状态 |
| `MakeComputePipeline()` | 创建计算管线 |
| `compileD3DProgram()` | 编译 SkSL 为 HLSL 并进一步编译为 D3D 字节码 |
| `finalize()` | 最终组装 PSO |

**着色器编译链**：
```
SkSL 源码 → GrSPIRVUniformHandler/VaryingHandler 处理
         → SkSL::ToHLSL 转换为 HLSL 代码
         → D3DCompile 编译为字节码
         → 嵌入 ID3D12PipelineState 对象
```

### 6. GrD3DTextureResource（文件：GrD3DTextureResource.h / GrD3DTextureResource.cpp）

**职责**：所有 D3D12 纹理资源的基类，封装 `ID3D12Resource` 和资源状态管理。

**关键方法**：
| 方法 | 描述 |
|------|------|
| `setResourceState()` | 通过 GPU 屏障转换资源状态 |
| `prepareForPresent()` | 将资源切换到呈现状态 |
| `InitTextureResourceInfo()` | 初始化纹理资源信息 |
| `CreateMSAA()` | 创建 MSAA 纹理资源 |

### 7. GrD3DTexture / GrD3DRenderTarget / GrD3DTextureRenderTarget

**GrD3DTexture**（文件：GrD3DTexture.h / .cpp）：
- 继承 `GrTexture` 和 `GrD3DTextureResource`
- 管理 Shader Resource View（SRV）
- 支持 `MakeNewTexture()`、`MakeWrappedTexture()`、`MakeAliasingTexture()`

**GrD3DRenderTarget**（文件：GrD3DRenderTarget.h / .cpp）：
- 继承 `GrRenderTarget` 和 `GrD3DTextureResource`
- 管理 Render Target View（RTV）和可选的 MSAA 资源
- 通过 `fMSAATextureResource` 支持多重采样

**GrD3DTextureRenderTarget**（文件：GrD3DTextureRenderTarget.h / .cpp）：
- 同时继承 `GrD3DTexture` 和 `GrD3DRenderTarget`（钻石继承）
- 表示既可采样又可作为渲染目标的纹理
- 使用 C++ 虚继承解决 `GrD3DTextureResource` 的重复继承问题

### 8. 描述符管理子系统

**GrD3DDescriptorHeap**（文件：GrD3DDescriptorHeap.h / .cpp）：
- 描述符堆的基本封装，管理 CPU/GPU 句柄
- 提供 `CPUHandle` 和 `GPUHandle` 结构体用于描述符寻址

**GrD3DCpuDescriptorManager**（文件：GrD3DCpuDescriptorManager.h / .cpp）：
- 管理 CPU 端不可见的描述符（用于创建视图时的暂存）
- 内部使用 `HeapPool` 和 `SkBitSet` 实现空闲描述符的分配与回收
- 支持四种描述符池：RTV、DSV、ShaderView（CBV/SRV/UAV）、Sampler

**GrD3DDescriptorTableManager**（文件：GrD3DDescriptorTableManager.h / .cpp）：
- 管理 GPU 可见的着色器描述符表
- 使用 `GrRecycledResource` 机制实现堆的自动回收
- 内部 `Heap` 类采用线性分配策略，用完后整体回收

### 9. 其他关键类

**GrD3DBuffer**（文件：GrD3DBuffer.h / .cpp）：
- GPU 缓冲区实现，支持顶点、索引、Uniform、传输等类型
- 支持 Map/Unmap 操作用于 CPU-GPU 数据传输

**GrD3DRootSignature**（文件：GrD3DRootSignature.h / .cpp）：
- 定义着色器参数布局（根签名）
- 包含三个参数槽：ConstantBufferView、ShaderViewDescriptorTable、SamplerDescriptorTable

**GrD3DSemaphore**（文件：GrD3DSemaphore.h / .cpp）：
- 基于 `ID3D12Fence` 的 GPU 同步信号量
- 支持跨命令队列和跨进程同步

**GrD3DAMDMemoryAllocator**（文件：GrD3DAMDMemoryAllocator.h / .cpp）：
- 集成 AMD D3D12 Memory Allocator 库（D3D12MA）
- 提供高效的 GPU 内存子分配和碎片管理

**GrD3DOpsRenderPass**（文件：GrD3DOpsRenderPass.h / .cpp）：
- 渲染通道实现，处理实际的绘制、清除、模板操作
- 管理当前管线状态、裁剪矩形、混合因子等渲染状态

## 依赖关系

### 上游依赖（本目录依赖的模块）

| 模块路径 | 说明 |
|----------|------|
| `src/gpu/ganesh/GrGpu.h` | GPU 抽象基类 |
| `src/gpu/ganesh/GrCaps.h` | 能力查询基类 |
| `src/gpu/ganesh/GrOpsRenderPass.h` | 渲染通道基类 |
| `src/gpu/ganesh/GrTexture.h` | 纹理基类 |
| `src/gpu/ganesh/GrRenderTarget.h` | 渲染目标基类 |
| `src/gpu/ganesh/GrGpuBuffer.h` | GPU 缓冲区基类 |
| `src/gpu/ganesh/GrAttachment.h` | 附件基类 |
| `src/gpu/ganesh/GrManagedResource.h` | 托管资源基类 |
| `src/gpu/ganesh/GrSemaphore.h` | 信号量基类 |
| `src/gpu/ganesh/GrStagingBufferManager.h` | 暂存缓冲管理 |
| `src/gpu/ganesh/GrRingBuffer.h` | 环形缓冲区 |
| `src/gpu/ganesh/GrUniformDataManager.h` | Uniform 数据管理基类 |
| `src/gpu/ganesh/GrSPIRVUniformHandler.h` | SPIRV Uniform 处理器 |
| `src/gpu/ganesh/GrSPIRVVaryingHandler.h` | SPIRV Varying 处理器 |
| `src/gpu/ganesh/glsl/GrGLSLProgramBuilder.h` | 着色器程序构建器基类 |
| `src/sksl/codegen/SkSLHLSLCodeGenerator.h` | SkSL 到 HLSL 代码生成器 |
| `include/gpu/ganesh/d3d/GrD3DTypes.h` | D3D 公共类型定义 |
| `include/gpu/ganesh/d3d/GrD3DBackendSurface.h` | D3D 后端表面公共接口 |

### 下游使用（依赖本目录的模块）

| 模块 | 说明 |
|------|------|
| `include/gpu/ganesh/d3d/GrD3DDirectContext.h` | D3D 上下文创建的公共 API |
| Ganesh 渲染管线 | 通过 `GrGpu` 抽象接口调用本后端 |

### 外部依赖

| 依赖 | 说明 |
|------|------|
| Direct3D 12 API | `d3d12.h`、`dxgi1_4.h` 等 Windows SDK 头文件 |
| D3D Compiler | `d3dcompiler.h`，用于 HLSL 着色器编译 |
| D3D12 Memory Allocator (D3D12MA) | AMD 开源的 D3D12 内存分配库 |
| DXGI | 设备枚举与交换链管理 |
| IDXGraphicsAnalysis | PIX 图形调试工具接口（仅测试模式） |

## 设计模式分析

### 1. 工厂模式（Factory Pattern）

几乎所有核心类都使用静态 `Make()` 工厂方法创建实例，隐藏构造细节：
```cpp
// GrD3DGpu 的工厂方法
static std::unique_ptr<GrGpu> Make(const GrD3DBackendContext&, const GrContextOptions&, GrDirectContext*);

// GrD3DTexture 的多种工厂方法
static sk_sp<GrD3DTexture> MakeNewTexture(...);
static sk_sp<GrD3DTexture> MakeWrappedTexture(...);
static sk_sp<GrD3DTexture> MakeAliasingTexture(...);
```

### 2. 享元/缓存模式（Flyweight/Cache Pattern）

`GrD3DResourceProvider` 大量使用 `findOrCreate` 命名的方法，通过缓存避免重复创建：
```cpp
sk_sp<GrD3DRootSignature> findOrCreateRootSignature(int numTextureSamplers, int numUAVs);
GrD3DPipelineState* findOrCreateCompatiblePipelineState(GrD3DRenderTarget*, const GrProgramInfo&);
sk_sp<GrD3DDescriptorTable> findOrCreateShaderViewTable(...);
```
其中 `PipelineStateCache` 使用 `SkLRUCache` 实现 LRU 缓存策略。

### 3. 命令模式（Command Pattern）

`GrD3DCommandList` 封装了所有 GPU 命令的录制，支持延迟提交：
- 命令先被录制到命令列表中
- 通过 `submit()` 方法一次性提交到命令队列
- 提交后命令列表被放入 `fOutstandingCommandLists` 等待 GPU 执行完毕

### 4. 池化模式（Pool Pattern）

描述符管理使用了分层池化：
```
GrD3DCpuDescriptorManager
  └── HeapPool（每种类型一个）
        └── Heap（实际描述符堆 + SkBitSet 位图管理空闲槽位）
```

命令列表也使用池化回收：
```cpp
void recycleDirectCommandList(std::unique_ptr<GrD3DDirectCommandList>);
// 回收的命令列表存储在 fAvailableDirectCommandLists 中供复用
```

### 5. 模板方法模式（Template Method Pattern）

`GrD3DGpu` 通过重写 `GrGpu` 的虚函数实现 D3D12 特定逻辑：
```cpp
sk_sp<GrTexture> onCreateTexture(...) override;
bool onReadPixels(...) override;
bool onWritePixels(...) override;
GrOpsRenderPass* onGetOpsRenderPass(...) override;
bool onSubmitToGpu(const GrSubmitInfo&) override;
```

### 6. 引用计数与资源生命周期管理

采用多层引用计数确保 GPU 资源安全：
- `gr_cp<T>`：D3D12 COM 对象的智能指针
- `sk_sp<T>`：Skia 引用计数智能指针
- `GrManagedResource`：命令列表关联的托管资源，执行完毕后自动释放
- `GrRecycledResource`：可回收资源，释放后自动回到资源池

## 数据流

### 绘制操作数据流

```
应用层调用 SkCanvas API
        │
        ▼
Ganesh 渲染管线生成 GrOp 操作
        │
        ▼
GrD3DGpu::onGetOpsRenderPass()
  → 创建/复用 GrD3DOpsRenderPass
        │
        ▼
GrD3DOpsRenderPass::onBindPipeline()
  → GrD3DResourceProvider::findOrCreateCompatiblePipelineState()
    → GrD3DPipelineStateBuilder::MakePipelineState()  [缓存未命中时]
      → SkSL → HLSL → D3DCompile → ID3D12PipelineState
        │
        ▼
GrD3DOpsRenderPass::onBindTextures()
  → 创建 SRV/Sampler 描述符表
  → GrD3DDirectCommandList::setDescriptorHeaps()
  → GrD3DDirectCommandList::setGraphicsRootDescriptorTable()
        │
        ▼
GrD3DOpsRenderPass::onDrawInstanced() / onDrawIndexedInstanced()
  → GrD3DDirectCommandList::drawInstanced() / drawIndexedInstanced()
        │
        ▼
GrD3DGpu::submit()
  → GrD3DOpsRenderPass::submit()
        │
        ▼
GrD3DGpu::submitDirectCommandList()
  → fCurrentDirectCommandList->submit(fQueue)
  → fFence Signal
  → 命令列表入队 fOutstandingCommandLists
```

### 纹理上传数据流

```
GrD3DGpu::onWritePixels()
        │
        ▼
GrD3DGpu::uploadToTexture()
  → fStagingBufferManager 分配暂存缓冲
  → 将像素数据写入暂存缓冲
  → 设置资源屏障 (COPY_DEST)
  → GrD3DCommandList::copyBufferToTexture()
  → 恢复资源屏障 (SHADER_RESOURCE)
```

### 像素回读数据流

```
GrD3DGpu::onReadPixels()
        │
        ▼
  → 创建回读缓冲（D3D12_HEAP_TYPE_READBACK）
  → 设置资源屏障 (COPY_SOURCE)
  → GrD3DGpu::readOrTransferPixels()
    → GrD3DCommandList::copyTextureRegionToBuffer()
  → 提交命令列表并等待完成
  → Map 回读缓冲 → 复制到目标内存
```

## 平台特定说明

### 仅限 Windows 平台

本目录代码 **仅在 Windows 平台** 上编译和运行。核心依赖：
- **Windows SDK**：需要 Windows 10 SDK 或更高版本
- **Direct3D 12 Runtime**：需要 Windows 10（版本 1607 / Build 14393）或更高版本
- **D3D12 Feature Level**：要求至少 D3D_FEATURE_LEVEL_11_0

### 编译条件

代码中大量使用以下编译条件：
- `SK_BUILD_FOR_WIN`：Windows 平台编译标识
- `GPU_TEST_UTILS`：测试工具编译标识，启用 PIX 捕获、着色器缓存重置等调试功能
- `SK_DEBUG`：调试模式，启用管线状态缓存统计
- `SK_TRACE_MANAGED_RESOURCES`：启用资源追踪日志

### 钻石继承问题

`GrD3DTextureRenderTarget` 通过 C++ 虚继承同时继承 `GrD3DTexture` 和 `GrD3DRenderTarget`，在 Windows 平台上会触发 C4250 警告（通过 dominance 继承成员函数）。代码通过 `#pragma warning(push/pop)` 抑制该警告：
```cpp
#ifdef SK_BUILD_FOR_WIN
#pragma warning(push)
#pragma warning(disable: 4250)
#endif
```

### GPU 厂商适配

`GrD3DCaps` 维护了 GPU 厂商枚举，用于针对特定厂商硬件的兼容性修复：
```cpp
enum D3DVendor {
    kAMD_D3DVendor       = 0x1002,
    kARM_D3DVendor       = 0x13B5,
    kImagination_D3DVendor = 0x1010,
    kIntel_D3DVendor     = 0x8086,
    kNVIDIA_D3DVendor    = 0x10DE,
    kQualcomm_D3DVendor  = 0x5143,
};
```
通过 `applyDriverCorrectnessWorkarounds()` 方法应用特定厂商的问题规避策略。

### 支持的 DXGI 格式

本后端支持以下 15 种 DXGI 纹理格式（`GrD3DCaps::kNumDxgiFormats = 15`）：

| DXGI 格式 | 每像素字节数 | 用途 |
|-----------|-------------|------|
| `DXGI_FORMAT_R8G8B8A8_UNORM` | 4 | 标准 RGBA |
| `DXGI_FORMAT_R8_UNORM` | 1 | 单通道 Alpha/灰度 |
| `DXGI_FORMAT_B8G8R8A8_UNORM` | 4 | BGRA（Windows 偏好） |
| `DXGI_FORMAT_B5G6R5_UNORM` | 2 | 16 位 RGB |
| `DXGI_FORMAT_R16G16B16A16_FLOAT` | 8 | HDR 半精度浮点 |
| `DXGI_FORMAT_R16_FLOAT` | 2 | 单通道半精度 |
| `DXGI_FORMAT_R8G8_UNORM` | 2 | 双通道 |
| `DXGI_FORMAT_R10G10B10A2_UNORM` | 4 | 10 位 HDR |
| `DXGI_FORMAT_B4G4R4A4_UNORM` | 2 | 16 位 BGRA |
| `DXGI_FORMAT_R8G8B8A8_UNORM_SRGB` | 4 | sRGB 色彩空间 |
| `DXGI_FORMAT_BC1_UNORM` | 8/block | 压缩纹理 |
| `DXGI_FORMAT_R16_UNORM` | 2 | 16 位单通道 |
| `DXGI_FORMAT_R16G16_UNORM` | 4 | 16 位双通道 |
| `DXGI_FORMAT_R16G16B16A16_UNORM` | 8 | 16 位 RGBA |
| `DXGI_FORMAT_R16G16_FLOAT` | 4 | 半精度双通道 |

模板格式另外支持：
- `DXGI_FORMAT_D24_UNORM_S8_UINT`（32 位，24 位深度 + 8 位模板）
- `DXGI_FORMAT_D32_FLOAT_S8X24_UINT`（64 位，32 位浮点深度 + 8 位模板）

### 根签名布局

每个渲染管线使用统一的三参数根签名：
```
ParamIndex 0: ConstantBufferView      → Uniform 常量缓冲区
ParamIndex 1: ShaderViewDescriptorTable → SRV/UAV 描述符表
ParamIndex 2: SamplerDescriptorTable   → 采样器描述符表
```

## 相关文档与参考

### Skia 项目内部参考
- `include/gpu/ganesh/d3d/` - D3D 后端的公共 API 头文件
- `src/gpu/ganesh/` - Ganesh 渲染引擎核心代码
- `src/gpu/ganesh/vk/` - Vulkan 后端实现（架构类似，可对比参考）
- `src/gpu/ganesh/mtl/` - Metal 后端实现
- `src/gpu/ganesh/gl/` - OpenGL 后端实现
- `src/sksl/` - SkSL 着色语言编译器
- `src/sksl/codegen/SkSLHLSLCodeGenerator.h` - HLSL 代码生成器

### 外部文档参考
- [Microsoft Direct3D 12 编程指南](https://docs.microsoft.com/en-us/windows/win32/direct3d12/directx-12-programming-guide)
- [D3D12 Resource Binding](https://docs.microsoft.com/en-us/windows/win32/direct3d12/resource-binding)
- [D3D12 Memory Management](https://docs.microsoft.com/en-us/windows/win32/direct3d12/memory-management)
- [AMD D3D12 Memory Allocator (D3D12MA)](https://gpuopen.com/d3d12-memory-allocator/)
- [HLSL 着色器编程](https://docs.microsoft.com/en-us/windows/win32/direct3dhlsl/dx-graphics-hlsl)
- [Skia GPU 文档](https://skia.org/docs/user/api/skcanvas_creation/#gpu)
