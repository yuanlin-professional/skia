# GrVkPipelineState

> 源文件
> - src/gpu/ganesh/vk/GrVkPipelineState.h
> - src/gpu/ganesh/vk/GrVkPipelineState.cpp

## 概述

`GrVkPipelineState` 是 Skia Ganesh Vulkan 后端中封装完整管线状态的核心类。它不仅持有 Vulkan 管线对象（`GrVkPipeline`），还负责管理与绘制相关的所有资源，包括 uniform 数据、描述符集、采样器、以及处理器实现。该类是绘制操作中最关键的状态容器，协调着 GPU 资源的设置、绑定和生命周期管理。

主要职责包括：
- 持有和管理 `GrVkPipeline` 对象
- 管理 uniform 数据的设置和上传
- 管理纹理采样器和描述符集的绑定
- 处理输入附件（用于 subpass）
- 维护渲染目标状态（尺寸、原点、RT 调整）
- 协调几何处理器、片段处理器和传输处理器的实现

该类是绘制调用与 GPU 资源之间的桥梁，确保所有必要的状态在绘制前正确设置。

## 架构位置

`GrVkPipelineState` 在 Vulkan 渲染管线中的位置：

```
Skia Ganesh 渲染流程
  └─ Vulkan 后端
      ├─ GrVkGpu (设备管理)
      ├─ GrVkOpsRenderPass (渲染通道执行)
      │   └─ 绑定和使用 GrVkPipelineState
      ├─ GrVkPipelineStateCache (管线状态缓存)
      │   └─ 创建和缓存 GrVkPipelineState
      └─ GrVkPipelineState (完整管线状态) ← 当前类
          ├─ GrVkPipeline (Vulkan 管线对象)
          ├─ GrVkPipelineStateDataManager (uniform 管理)
          └─ 处理器实现 (GP, XP, FP)
```

该类是渲染管线的最终执行单元，聚合了所有绘制所需的状态和资源。

## 主要类与结构体

### 核心类

| 类名 | 说明 |
|------|------|
| `GrVkPipelineState` | 完整的 Vulkan 管线状态封装 |

### 内部结构体

**RenderTargetState**
```cpp
struct RenderTargetState {
    SkISize         fRenderTargetSize;     // 渲染目标尺寸
    GrSurfaceOrigin fRenderTargetOrigin;   // 表面原点（顶部或底部）

    void invalidate();  // 标记为无效，强制下次更新
};
```

用于追踪渲染目标状态，避免重复设置 RT 调整 uniform。

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fPipeline` | `sk_sp<const GrVkPipeline>` | Vulkan 管线对象 |
| `fSamplerDSHandle` | `GrVkDescriptorSetManager::Handle` | 采样器描述符集句柄 |
| `fImmutableSamplers` | `STArray<4, const GrVkSampler*>` | 不可变采样器数组 |
| `fRenderTargetState` | `RenderTargetState` | 当前渲染目标状态 |
| `fBuiltinUniformHandles` | `GrGLSLBuiltinUniformHandles` | 内置 uniform 句柄（RT 调整等） |
| `fGPImpl` | `unique_ptr<GrGeometryProcessor::ProgramImpl>` | 几何处理器实现 |
| `fXPImpl` | `unique_ptr<GrXferProcessor::ProgramImpl>` | 传输处理器实现 |
| `fFPImpls` | `vector<unique_ptr<GrFragmentProcessor::ProgramImpl>>` | 片段处理器实现数组 |
| `fDataManager` | `GrVkPipelineStateDataManager` | Uniform 数据管理器 |
| `fNumSamplers` | `int` | 采样器总数 |

## 公共 API 函数

### 构造与析构

```cpp
GrVkPipelineState(
    GrVkGpu* gpu,
    sk_sp<const GrVkPipeline> pipeline,
    const GrVkDescriptorSetManager::Handle& samplerDSHandle,
    const GrGLSLBuiltinUniformHandles& builtinUniformHandles,
    const UniformInfoArray& uniforms,
    uint32_t uniformSize,
    bool usePushConstants,
    const UniformInfoArray& samplers,
    unique_ptr<GrGeometryProcessor::ProgramImpl> gpImpl,
    unique_ptr<GrXferProcessor::ProgramImpl> xpImpl,
    vector<unique_ptr<GrFragmentProcessor::ProgramImpl>> fpImpls);
```
构造函数接受所有必要的组件，使用移动语义转移所有权。

```cpp
~GrVkPipelineState();
```
析构时断言所有 GPU 资源已释放（通过 `freeGPUResources` 显式释放）。

### Uniform 设置与绑定

```cpp
bool setAndBindUniforms(
    GrVkGpu* gpu,
    SkISize colorAttachmentDimensions,
    const GrProgramInfo& programInfo,
    GrVkCommandBuffer* commandBuffer);
```
设置所有 uniform 数据并绑定 uniform 描述符集。依次调用各处理器的 `setData` 方法，然后上传 uniform 数据到 GPU。

### 纹理设置与绑定

```cpp
bool setAndBindTextures(
    GrVkGpu* gpu,
    const GrGeometryProcessor& geomProc,
    const GrPipeline& pipeline,
    const GrSurfaceProxy* const geomProcTextures[],
    GrVkCommandBuffer* commandBuffer);
```
设置所有纹理采样器并绑定采样器描述符集。必须在 `setAndBindUniforms` 之后调用。

### 输入附件绑定

```cpp
bool setAndBindInputAttachment(
    GrVkGpu* gpu,
    gr_rp<const GrVkDescriptorSet> inputDescSet,
    GrVkCommandBuffer* commandBuffer);
```
绑定输入附件描述符集（用于 subpass 读取前一个 subpass 的输出）。

### 管线绑定

```cpp
void bindPipeline(const GrVkGpu* gpu, GrVkCommandBuffer* commandBuffer);
```
将管线对象绑定到命令缓冲区。

### 资源释放

```cpp
void freeGPUResources(GrVkGpu* gpu);
```
释放所有 GPU 资源，包括管线对象、uniform buffer、不可变采样器等。

## 内部实现细节

### Uniform 设置流程

`setAndBindUniforms` 方法实现了完整的 uniform 设置流程：

1. **设置渲染目标状态**：计算 RT 调整向量和翻转向量
2. **调用处理器 setData**：
   - 几何处理器：`fGPImpl->setData()`
   - 片段处理器：遍历 FP 树调用 `setData()`
   - 传输处理器：`fXPImpl->setData()`
3. **设置目标纹理 uniform**：如果使用目标纹理读取
4. **上传 uniform 数据**：通过 `fDataManager.uploadUniforms()`
5. **绑定 uniform 描述符集**：如果使用 uniform buffer

关键代码：
```cpp
fGPImpl->setData(fDataManager, *gpu->caps()->shaderCaps(), programInfo.geomProc());

for (int i = 0; i < programInfo.pipeline().numFragmentProcessors(); ++i) {
    const auto& fp = programInfo.pipeline().getFragmentProcessor(i);
    fp.visitWithImpls([&](const GrFragmentProcessor& fp,
                          GrFragmentProcessor::ProgramImpl& impl) {
        impl.setData(fDataManager, fp);
    }, *fFPImpls[i]);
}
```

### 纹理绑定优化

`setAndBindTextures` 实现了多项优化：

**单纹理缓存**：
当只有一个采样器时，尝试从纹理对象的缓存中获取描述符集：
```cpp
if (fNumSamplers == 1) {
    const GrVkDescriptorSet* descriptorSet = texture->cachedSingleDescSet(samplerState);
    if (descriptorSet) {
        // 直接使用缓存的描述符集，避免更新
        commandBuffer->bindDescriptorSets(...);
        return true;
    }
}
```

**描述符集更新**：
对于多纹理或缓存未命中的情况，更新描述符集：
```cpp
for (int i = 0; i < fNumSamplers; ++i) {
    // 获取纹理视图和采样器
    const GrVkImageView* textureView = texAttachment->textureView();
    const GrVkSampler* sampler = ...; // 不可变或动态创建

    // 填充描述符信息
    VkDescriptorImageInfo imageInfo;
    imageInfo.sampler = fImmutableSamplers[i] ? VK_NULL_HANDLE : sampler->sampler();
    imageInfo.imageView = textureView->imageView();
    imageInfo.imageLayout = VK_IMAGE_LAYOUT_SHADER_READ_ONLY_OPTIMAL;

    // 更新描述符集
    VkWriteDescriptorSet writeInfo = {...};
    UpdateDescriptorSets(gpu->device(), 1, &writeInfo, 0, nullptr);
}
```

**不可变采样器支持**：
对于 YCbCr 转换等场景，使用不可变采样器（在创建描述符集布局时指定）：
```cpp
if (fImmutableSamplers[i]) {
    sampler = fImmutableSamplers[i];
    imageInfo.sampler = VK_NULL_HANDLE;  // 不可变采样器无需在更新时指定
}
```

### 渲染目标状态管理

`setRenderTargetState` 方法处理坐标系统转换：

**RT 调整向量**（RTAdjustment）：
将 Skia 设备坐标转换为 Vulkan 归一化设备坐标（NDC）：
```cpp
std::array<float, 4> v = SkSL::Compiler::GetRTAdjustVector(
    colorAttachmentDimensions, flip);
fDataManager.set4fv(fBuiltinUniformHandles.fRTAdjustmentUni, 1, v.data());
```

**RT 翻转向量**（RTFlip）：
处理不同表面原点的坐标翻转：
```cpp
bool flip = (origin == kBottomLeft_GrSurfaceOrigin);
std::array<float, 2> d = SkSL::Compiler::GetRTFlipVector(
    colorAttachmentDimensions.height(), flip);
fDataManager.set2fv(fBuiltinUniformHandles.fRTFlipUni, 1, d.data());
```

Vulkan 的帧缓冲空间 (0, 0) 在左上角，与 Skia 设备坐标一致。当表面原点为 `kBottomLeft` 时需要翻转。

### 资源追踪

命令缓冲区追踪所有使用的资源，确保在命令执行期间资源不被释放：
```cpp
commandBuffer->addGrSurface(sk_ref_sp<const GrSurface>(texture));
commandBuffer->addResource(textureView);
commandBuffer->addResource(texAttachment->resource());
commandBuffer->addRecycledResource(descriptorSet);
commandBuffer->addGrBuffer(std::move(uniformBuffer));
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrVkPipeline` | 持有的 Vulkan 管线对象 |
| `GrVkPipelineStateDataManager` | 管理 uniform 数据 |
| `GrVkGpu` | Vulkan 设备和接口 |
| `GrVkCommandBuffer` | 命令记录和资源追踪 |
| `GrVkResourceProvider` | 获取采样器和描述符集 |
| `GrVkDescriptorSet` | 描述符集对象 |
| `GrVkSampler` | 采样器对象 |
| `GrVkTexture` | 纹理对象 |
| `GrGeometryProcessor::ProgramImpl` | 几何处理器实现 |
| `GrXferProcessor::ProgramImpl` | 传输处理器实现 |
| `GrFragmentProcessor::ProgramImpl` | 片段处理器实现 |
| `GrProgramInfo` | 程序渲染信息 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrVkPipelineStateCache` | 创建和缓存管线状态对象 |
| `GrVkOpsRenderPass` | 在绘制时绑定和使用管线状态 |

## 设计模式与设计决策

### 聚合模式
该类聚合了绘制所需的所有组件（管线、uniform、采样器、处理器），提供统一的接口进行设置和绑定。

### 资源所有权
使用智能指针管理资源生命周期：
- `sk_sp<const GrVkPipeline>`：共享所有权，支持缓存复用
- `unique_ptr`：独占所有权，用于处理器实现
- 不可变采样器使用原始指针 + 手动引用计数（待改进为 `sk_sp`）

### 两阶段设置
将 uniform 设置和纹理设置分为两个独立方法：
1. `setAndBindUniforms`：设置所有 uniform 数据
2. `setAndBindTextures`：设置所有纹理（必须在 uniform 之后）

这种设计明确了操作顺序，因为 uniform 设置会使纹理绑定失效。

### 缓存友好
- 追踪渲染目标状态，避免重复设置 RT uniform
- 单纹理情况下尝试使用缓存的描述符集
- 将更新后的单纹理描述符集缓存到纹理对象

### 访问者模式
使用 `visitWithImpls` 遍历片段处理器树，确保处理器和实现正确配对：
```cpp
fp.visitWithImpls([&](const GrFragmentProcessor& fp,
                      GrFragmentProcessor::ProgramImpl& impl) {
    impl.setData(fDataManager, fp);
}, *fFPImpls[i]);
```

## 性能考量

### 描述符集缓存
单纹理场景下的缓存可以避免频繁更新描述符集，这是 Vulkan 中相对昂贵的操作。

### 状态追踪
渲染目标状态追踪避免了不必要的 uniform 更新，减少 CPU 开销和数据传输。

### 资源批量绑定
一次性收集所有采样器绑定，然后批量更新描述符集，比逐个更新更高效。

### 不可变采样器优化
对于 YCbCr 转换等特殊采样器，使用不可变采样器可以让驱动进行更好的优化。

### 推送常量支持
对于小量 uniform 数据，使用推送常量避免了 uniform buffer 的创建和绑定开销。

### 自动资源追踪
通过命令缓冲区自动追踪资源引用，确保资源在使用期间不被释放，同时避免手动引用计数的复杂性。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/vk/GrVkPipeline.h` | 组件 | Vulkan 管线对象 |
| `src/gpu/ganesh/vk/GrVkPipelineStateDataManager.h` | 组件 | Uniform 数据管理 |
| `src/gpu/ganesh/vk/GrVkPipelineStateBuilder.h` | 创建者 | 构建管线状态对象 |
| `src/gpu/ganesh/vk/GrVkPipelineStateCache.h` | 使用者 | 缓存管线状态 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 依赖 | Vulkan GPU 设备 |
| `src/gpu/ganesh/vk/GrVkCommandBuffer.h` | 依赖 | 命令缓冲区 |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h` | 依赖 | 资源提供者 |
| `src/gpu/ganesh/vk/GrVkDescriptorSet.h` | 依赖 | 描述符集 |
| `src/gpu/ganesh/vk/GrVkSampler.h` | 依赖 | 采样器 |
| `src/gpu/ganesh/vk/GrVkTexture.h` | 依赖 | 纹理对象 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 依赖 | 几何处理器接口 |
| `src/gpu/ganesh/GrXferProcessor.h` | 依赖 | 传输处理器接口 |
| `src/gpu/ganesh/GrFragmentProcessor.h` | 依赖 | 片段处理器接口 |
