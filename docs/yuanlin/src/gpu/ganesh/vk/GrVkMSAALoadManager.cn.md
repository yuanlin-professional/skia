# GrVkMSAALoadManager

> 源文件
> - src/gpu/ganesh/vk/GrVkMSAALoadManager.h
> - src/gpu/ganesh/vk/GrVkMSAALoadManager.cpp

## 概述

`GrVkMSAALoadManager` 是 Skia 图形库中专门处理 MSAA(多重采样抗锯齿)附件加载操作的管理器类。当使用可丢弃的 MSAA 附件时,该类负责从解析附件(resolve attachment)将数据加载回 MSAA 附件,这是一种节省带宽的优化策略。

该管理器通过自定义的 Vulkan 着色器管线实现 MSAA 加载功能,使用输入附件(input attachment)从解析附件读取数据,并通过全屏四边形绘制的方式将数据写入 MSAA 附件。这种机制允许在多个渲染通道之间高效地保持 MSAA 数据的连续性,同时避免不必要的内存带宽消耗。

## 架构位置

```
Skia 渲染架构
├── GrVkGpu
│   └── GrVkMSAALoadManager ← 当前类
│       ├── VkShaderModule (顶点着色器)
│       ├── VkShaderModule (片段着色器)
│       └── VkPipelineLayout (管线布局)
```

`GrVkMSAALoadManager` 是 `GrVkGpu` 的成员对象,在需要从解析附件加载到 MSAA 附件时被调用。它独立管理自己的着色器模块和管线布局,与渲染通道系统协作完成 MSAA 加载操作。

## 主要类与结构体

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fVertShaderModule` | `VkShaderModule` | 顶点着色器模块 |
| `fFragShaderModule` | `VkShaderModule` | 片段着色器模块 |
| `fShaderStageInfo[2]` | `VkPipelineShaderStageCreateInfo` | 着色器阶段创建信息 |
| `fPipelineLayout` | `VkPipelineLayout` | 管线布局(所有 MSAA 加载管线共享) |

## 公共 API 函数

| 函数签名 | 功能说明 |
|---------|---------|
| `GrVkMSAALoadManager()` | 构造函数,初始化句柄为 NULL |
| `~GrVkMSAALoadManager()` | 析构函数 |
| `bool loadMSAAFromResolve(GrVkGpu*, GrVkCommandBuffer*, const GrVkRenderPass&, GrAttachment* dst, GrVkImage* src, const SkIRect&)` | 从解析附件加载数据到 MSAA 附件 |
| `void destroyResources(GrVkGpu*)` | 销毁 Vulkan 资源 |

## 内部实现细节

### 着色器程序创建

`createMSAALoadProgram()` 创建用于 MSAA 加载的着色器:

```cpp
bool GrVkMSAALoadManager::createMSAALoadProgram(GrVkGpu* gpu) {
    // 1. 顶点着色器: 生成全屏四边形
    std::string vertShaderText =
        "layout(vulkan, set=0, binding=0) uniform vertexUniformBuffer {"
            "half4 uPosXform;"  // 位置变换参数
        "};"
        "void main() {"
            // 使用顶点 ID 生成 4 个顶点(0,0), (1,0), (0,1), (1,1)
            "float2 position = float2(sk_VertexID >> 1, sk_VertexID & 1);"
            // 应用变换到 NDC 坐标
            "sk_Position.xy = position * uPosXform.xy + uPosXform.zw;"
            "sk_Position.zw = half2(0, 1);"
        "}";

    // 2. 片段着色器: 从输入附件读取
    std::string fragShaderText =
        "layout(vulkan, input_attachment_index=0, set=2, binding=0) "
        "subpassInput uInput;"
        "void main() {"
            "sk_FragColor = subpassLoad(uInput);"  // 从输入附件加载
        "}";

    // 3. 编译着色器模块
    if (!GrCompileVkShaderModule(gpu, vertShaderText,
                                 VK_SHADER_STAGE_VERTEX_BIT,
                                 &fVertShaderModule, ...)) {
        return false;
    }
    if (!GrCompileVkShaderModule(gpu, fragShaderText,
                                 VK_SHADER_STAGE_FRAGMENT_BIT,
                                 &fFragShaderModule, ...)) {
        return false;
    }

    // 4. 创建管线布局
    // 使用标准的 3 个描述符集:
    // - Set 0: Uniform Buffer (顶点变换参数)
    // - Set 1: Samplers (虽然不用,但需要占位)
    // - Set 2: Input Attachment (解析附件)
    VkDescriptorSetLayout dsLayout[3];
    dsLayout[0] = resourceProvider.getUniformDSLayout();
    dsLayout[1] = resourceProvider.getSamplerDSLayout(zeroSamplerHandle);
    dsLayout[2] = resourceProvider.getInputDSLayout();

    VkPipelineLayoutCreateInfo layoutCreateInfo = {
        .sType = VK_STRUCTURE_TYPE_PIPELINE_LAYOUT_CREATE_INFO,
        .setLayoutCount = 3,
        .pSetLayouts = dsLayout,
    };
    VK_CALL(CreatePipelineLayout(..., &fPipelineLayout));

    return true;
}
```

### MSAA 加载执行流程

```cpp
bool GrVkMSAALoadManager::loadMSAAFromResolve(
    GrVkGpu* gpu,
    GrVkCommandBuffer* commandBuffer,
    const GrVkRenderPass& renderPass,
    GrAttachment* dst,  // MSAA 附件
    GrVkImage* src,     // 解析附件
    const SkIRect& rect) {

    // 1. 懒创建着色器程序(首次调用时)
    if (fVertShaderModule == VK_NULL_HANDLE) {
        if (!createMSAALoadProgram(gpu)) {
            return false;
        }
    }

    // 2. 获取或创建管线
    sk_sp<const GrVkPipeline> pipeline =
        resourceProv.findOrCreateMSAALoadPipeline(
            renderPass,
            dst->numSamples(),
            fShaderStageInfo,
            fPipelineLayout);
    commandBuffer->bindPipeline(gpu, std::move(pipeline));

    // 3. 设置动态状态
    VkViewport viewport = {
        .x = 0.0f, .y = 0.0f,
        .width = dst->width(),
        .height = dst->height(),
        .minDepth = 0.0f, .maxDepth = 1.0f
    };
    commandBuffer->setViewport(gpu, 0, 1, &viewport);

    VkRect2D scissor = {
        .offset = {0, 0},
        .extent = {dst->width(), dst->height()}
    };
    commandBuffer->setScissor(gpu, 0, 1, &scissor);

    // 4. 计算顶点变换参数(NDC 坐标)
    int dw = dst->width();
    int dh = dst->height();
    float dx0 = 2.f * rect.fLeft / dw - 1.f;
    float dx1 = 2.f * (rect.fLeft + rect.width()) / dw - 1.f;
    float dy0 = 2.f * rect.fTop / dh - 1.f;
    float dy1 = 2.f * (rect.fTop + rect.height()) / dh - 1.f;

    // uPosXform = (scaleX, scaleY, translateX, translateY)
    float uniData[] = {dx1 - dx0, dy1 - dy0, dx0, dy0};

    // 5. 创建并绑定 uniform buffer
    sk_sp<GrGpuBuffer> uniformBuffer =
        resourceProvider->createBuffer(
            uniData, sizeof(uniData),
            GrGpuBufferType::kUniform,
            kDynamic_GrAccessPattern);
    GrVkBuffer* vkUniformBuffer = static_cast<GrVkBuffer*>(uniformBuffer.get());
    commandBuffer->bindDescriptorSets(
        gpu, fPipelineLayout,
        GrVkUniformHandler::kUniformBufferDescSet,
        /*setCount=*/1,
        vkUniformBuffer->uniformDescriptorSet(), ...);
    commandBuffer->addGrBuffer(std::move(uniformBuffer));

    // 6. 绑定输入附件描述符集
    gr_rp<const GrVkDescriptorSet> inputDS =
        src->inputDescSetForMSAALoad(gpu);
    commandBuffer->bindDescriptorSets(
        gpu, fPipelineLayout,
        GrVkUniformHandler::kInputDescSet, /*setCount=*/1,
        inputDS->descriptorSet(), ...);
    commandBuffer->addRecycledResource(std::move(inputDS));

    // 7. 绘制全屏四边形(4 个顶点)
    commandBuffer->draw(gpu, 4, 1, 0, 0);

    return true;
}
```

### 资源销毁

```cpp
void GrVkMSAALoadManager::destroyResources(GrVkGpu* gpu) {
    if (fVertShaderModule != VK_NULL_HANDLE) {
        GR_VK_CALL(gpu->vkInterface(),
                   DestroyShaderModule(gpu->device(), fVertShaderModule, nullptr));
        fVertShaderModule = VK_NULL_HANDLE;
    }
    if (fFragShaderModule != VK_NULL_HANDLE) {
        GR_VK_CALL(gpu->vkInterface(),
                   DestroyShaderModule(gpu->device(), fFragShaderModule, nullptr));
        fFragShaderModule = VK_NULL_HANDLE;
    }
    if (fPipelineLayout != VK_NULL_HANDLE) {
        GR_VK_CALL(gpu->vkInterface(),
                   DestroyPipelineLayout(gpu->device(), fPipelineLayout, nullptr));
        fPipelineLayout = VK_NULL_HANDLE;
    }
}
```

## 依赖关系

### 依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrVkGpu` | GPU 对象,提供设备句柄和资源提供者 |
| `GrVkCommandBuffer` | 命令缓冲区,记录绘制命令 |
| `GrVkRenderPass` | 渲染通道,提供子通道信息 |
| `GrAttachment` | 目标 MSAA 附件 |
| `GrVkImage` | 源解析附件,提供输入附件描述符集 |
| `GrVkResourceProvider` | 资源提供者,获取管线和描述符布局 |
| `GrVkPipeline` | Vulkan 管线对象 |
| `GrVkBuffer` | Uniform buffer |
| `GrVkDescriptorSet` | 描述符集 |
| `GrCompileVkShaderModule` | 着色器编译工具 |

### 被依赖的模块

| 模块名称 | 依赖说明 |
|---------|---------|
| `GrVkGpu` | GrVkGpu 包含 GrVkMSAALoadManager 成员 |
| `GrVkOpsRenderPass` | 渲染通道在需要时调用 loadMSAAFromResolve |

## 设计模式与设计决策

### 1. 懒初始化模式 (Lazy Initialization)

着色器资源在首次使用时才创建:

```cpp
bool loadMSAAFromResolve(...) {
    if (fVertShaderModule == VK_NULL_HANDLE) {
        // 首次调用时创建
        if (!createMSAALoadProgram(gpu)) {
            return false;
        }
    }
    // 使用已创建的资源
    // ...
}
```

**优势**:
- 不使用 MSAA 加载功能时不占用资源
- 延迟创建减少初始化时间

### 2. 单例资源共享

所有 MSAA 加载操作共享同一组着色器模块和管线布局:

```cpp
// 类成员(共享)
VkShaderModule fVertShaderModule;
VkShaderModule fFragShaderModule;
VkPipelineLayout fPipelineLayout;
```

**优势**:
- 减少内存占用
- 避免重复编译着色器
- 管线缓存更有效

### 3. 输入附件优化

使用 Vulkan 输入附件(input attachment)而非常规纹理采样:

```cpp
// 着色器中使用 subpassInput
"layout(vulkan, input_attachment_index=0, set=2, binding=0) subpassInput uInput;"
"sk_FragColor = subpassLoad(uInput);"
```

**优势**:
- 在 tile-based GPU 上带宽更优
- 无需额外的图像布局转换
- 与渲染通道子通道配合更自然

### 4. 全屏四边形技巧

使用顶点 ID 程序化生成四边形,无需顶点缓冲区:

```cpp
// 根据 sk_VertexID 生成顶点位置
"float2 position = float2(sk_VertexID >> 1, sk_VertexID & 1);"
// sk_VertexID: 0 -> (0,0), 1 -> (1,0), 2 -> (0,1), 3 -> (1,1)
```

**优势**:
- 无需分配和管理顶点缓冲区
- 减少内存带宽消耗
- 代码更简洁

### 5. 参数化变换

通过 uniform buffer 传递变换参数,支持任意矩形区域加载:

```cpp
float uniData[] = {dx1 - dx0, dy1 - dy0, dx0, dy0};
// 顶点着色器应用变换:
// sk_Position.xy = position * uPosXform.xy + uPosXform.zw;
```

**优势**:
- 灵活支持部分加载
- 无需修改着色器代码
- 高效复用管线

## 性能考量

### 1. 懒创建策略

```cpp
if (fVertShaderModule == VK_NULL_HANDLE) {
    createMSAALoadProgram(gpu);
}
```

- **首次调用开销**: 第一次 MSAA 加载会触发着色器编译,有一定延迟
- **后续调用**: 着色器和管线布局已创建,直接复用

### 2. 管线缓存

```cpp
sk_sp<const GrVkPipeline> pipeline =
    resourceProv.findOrCreateMSAALoadPipeline(...);
```

`GrVkResourceProvider` 缓存已创建的管线:
- 相同参数(render pass, sample count)复用管线
- 避免重复创建 VkPipeline

### 3. 描述符集管理

```cpp
// 输入附件描述符集由 GrVkImage 缓存
gr_rp<const GrVkDescriptorSet> inputDS =
    src->inputDescSetForMSAALoad(gpu);
```

- 描述符集在 `GrVkImage` 中缓存(`fCachedMSAALoadInputDescSet`)
- 避免每次都创建新的描述符集

### 4. Uniform Buffer 动态创建

```cpp
sk_sp<GrGpuBuffer> uniformBuffer =
    resourceProvider->createBuffer(
        uniData, sizeof(uniData),
        GrGpuBufferType::kUniform,
        kDynamic_GrAccessPattern);
```

- 每次调用创建新的 uniform buffer
- 16 字节小缓冲区,开销可接受
- TODO 注释建议缓存 uniform buffer 以进一步优化

### 5. 子通道内完成

MSAA 加载在渲染通道的首个子通道完成:
- 不需要额外的渲染通道切换
- 在 tile-based GPU 上非常高效(数据保持在 tile memory)

### 6. 最小绘制开销

- 仅绘制 4 个顶点(1 个四边形)
- 无索引缓冲区,直接绘制
- 片段着色器仅做简单的输入附件读取

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `src/gpu/ganesh/vk/GrVkGpu.h/cpp` | 包含 GrVkMSAALoadManager 成员对象 |
| `src/gpu/ganesh/vk/GrVkOpsRenderPass.h/cpp` | 调用 loadMSAAFromResolve 执行加载 |
| `src/gpu/ganesh/vk/GrVkCommandBuffer.h/cpp` | 记录 MSAA 加载的绘制命令 |
| `src/gpu/ganesh/vk/GrVkRenderPass.h/cpp` | 提供渲染通道信息 |
| `src/gpu/ganesh/vk/GrVkImage.h/cpp` | 提供输入附件描述符集 |
| `src/gpu/ganesh/vk/GrVkResourceProvider.h/cpp` | 提供管线和描述符布局 |
| `src/gpu/ganesh/vk/GrVkPipeline.h/cpp` | MSAA 加载管线 |
| `src/gpu/ganesh/vk/GrVkUtil.h/cpp` | 着色器编译工具 |
| `src/gpu/ganesh/GrAttachment.h` | MSAA 附件基类 |
