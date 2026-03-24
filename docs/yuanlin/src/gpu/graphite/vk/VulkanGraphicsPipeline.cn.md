# VulkanGraphicsPipeline -- Vulkan 图形管线

> 源文件:
> - `src/gpu/graphite/vk/VulkanGraphicsPipeline.h`
> - `src/gpu/graphite/vk/VulkanGraphicsPipeline.cpp`

## 概述

VulkanGraphicsPipeline 是 Skia Graphite Vulkan 后端的图形管线实现,负责将着色器编译、管线布局、顶点输入、深度模板、混合等状态组装为完整的 `VkPipeline` 对象。它继承自 `GraphicsPipeline` 基类,支持常规渲染管线和 MSAA 加载专用管线的创建,并实现了 Vulkan 动态状态优化以减少管线切换开销。

## 架构位置

```
GraphicsPipeline (抽象基类)
  -> VulkanGraphicsPipeline (Vulkan 具体实现)  <-- 本模块
       -> VulkanProgramInfo (着色器模块和管线布局持有者)
       -> VulkanRenderPass (兼容渲染通道)
       -> VulkanSampler (不可变采样器)
```

在 Graphite 的管线创建流程中,`VulkanSharedContext::createGraphicsPipeline()` 委托给 `VulkanGraphicsPipeline::Make()`。

## 主要类与结构体

### VulkanProgramInfo

持有 Vulkan 着色器模块和管线布局的生命周期管理类:

```cpp
class VulkanProgramInfo {
    VkShaderModule fVS, fFS;
    VkPipelineLayout fLayout;
};
```
- 析构时自动销毁 `VkShaderModule` 和 `VkPipelineLayout`
- 支持通过 `releaseLayout()` 转移管线布局所有权
- 每个字段只能设置一次（set-once 语义）

### VulkanGraphicsPipeline

核心管线类,关键常量和成员:

| 常量 | 值 | 用途 |
|------|-----|------|
| `kCombinedUniformIndex` | 0 | 合并 uniform 缓冲区绑定索引 |
| `kGradientBufferIndex` | 1 | 渐变存储缓冲区绑定索引 |
| `kDstAsInputDescSetIndex` | 0 | 目标作为输入附件的描述符集索引 |
| `kUniformBufferDescSetIndex` | 1 | Uniform 缓冲区描述符集索引 |
| `kTextureBindDescSetIndex` | 2 | 纹理/采样器描述符集索引 |
| `kLoadMsaaFromResolveInputDescSetIndex` | 3 | MSAA 加载输入附件描述符集索引 |
| `kMaxNumDescSets` | 4 | 最大描述符集数量 |
| `kStaticDataBufferIndex` | 0 | 静态顶点数据缓冲区索引 |
| `kAppendDataBufferIndex` | 1 | 追加顶点/实例数据缓冲区索引 |

## 公共 API 函数

### Make -- 创建常规图形管线

```cpp
static sk_sp<VulkanGraphicsPipeline> Make(
    VulkanSharedContext*, const RuntimeEffectDictionary*,
    const UniqueKey&, const GraphicsPipelineDesc&,
    const RenderPassDesc&, SkEnumBitMask<PipelineCreationFlags>, uint32_t compilationID);
```
完整的管线创建流程:
1. 使用 `ShaderInfo` 生成 SkSL 顶点和片段着色器
2. 编译 SkSL 到 SPIR-V（可选 SPIR-V 转换如多重采样输入加载）
3. 创建 `VkShaderModule`
4. 收集不可变采样器
5. 构建管线布局（4 个描述符集 + push constant）
6. 调用 `MakePipeline` 创建最终的 `VkPipeline`

### CreateLoadMSAAProgram / MakeLoadMSAAPipeline -- MSAA 加载管线

```cpp
static std::unique_ptr<VulkanProgramInfo> CreateLoadMSAAProgram(const VulkanSharedContext*);
static sk_sp<VulkanGraphicsPipeline> MakeLoadMSAAPipeline(
    VulkanSharedContext*, const VulkanProgramInfo&, const RenderPassDesc&);
```
分离程序创建和管线创建,允许复用同一程序创建不同渲染通道的 MSAA 加载管线。Load MSAA 管线使用全屏三角形条带从 resolve 附件加载数据到 MSAA 附件。

### updateDynamicState -- 动态状态更新

```cpp
void updateDynamicState(const VulkanSharedContext*,
                        VkCommandBuffer, const VulkanGraphicsPipeline* previous) const;
```
在管线绑定后,计算与前一个管线的动态状态差异,仅更新变化的部分。

## 内部实现细节

### 顶点输入状态

模板函数 `get_vertex_input_state` 统一处理两种 Vulkan 顶点输入描述:
- V1: `VkVertexInputBindingDescription` / `VkVertexInputAttributeDescription`（静态管线状态）
- V2: `VkVertexInputBindingDescription2EXT` / `VkVertexInputAttributeDescription2EXT`（动态顶点输入状态）

通过使用默认描述符初始化和模板参数,避免代码重复。

### 管线布局构建

`setup_pipeline_layout` 函数创建 4 个描述符集布局:
1. 目标输入附件（始终存在,用于 dst-as-input 功能）
2. Uniform/存储缓冲区（根据 caps 选择 UBO 或 SSBO 动态偏移）
3. 纹理/采样器（支持不可变采样器如 YCbCr）
4. MSAA 加载输入附件（非 MSAA 加载时为占位空布局）

不使用的描述符集仍创建空的占位布局,因为 `VK_NULL_HANDLE` 作为 `VkDescriptorSetLayout` 仅在启用 `graphicsPipelineLibrary` 特性时有效。

### 管线创建与缓存

`create_graphics_pipeline` 支持 `VK_EXT_pipeline_creation_cache_control`:
1. 首先尝试设置 `FAIL_ON_PIPELINE_COMPILE_REQUIRED` 标志,检查缓存命中
2. 缓存未命中时移除该标志重新创建
3. 通过 tracing 事件区分缓存命中和编译

### 着色器管线库

`create_shaders_pipeline` 使用 `VK_EXT_graphics_pipeline_library` 将管线拆分为:
- 着色器子集（预光栅化 + 片段着色器）
- 接口子集（顶点输入 + 片段输出）

这允许在不同混合/顶点配置间共享编译好的着色器,且使驱动能在完整管线中优化混合代码。

### 动态状态管理

当 `useBasicDynamicState()` 为真时,以下状态作为动态状态:
- 视口、裁剪、混合常量（始终动态）
- 深度测试/写入使能、深度比较操作
- 模板测试使能、模板操作、比较掩码、写入掩码、引用值
- 图元拓扑、面剔除、前面方向等

当 `useVertexInputDynamicState()` 为真时,顶点输入描述也通过 `VK_EXT_vertex_input_dynamic_state` 设为动态。

`updateDynamicState` 方法通过对比前一个管线的状态,仅发出变化的 Vulkan 命令。

## 依赖关系

### 上游依赖
- `GraphicsPipeline` -- 抽象基类
- `VulkanGraphiteUtils` -- Vulkan 调用宏和工具函数
- `VulkanSharedContext` / `VulkanCaps` -- 设备能力查询
- `VulkanRenderPass` -- 兼容渲染通道
- `VulkanSampler` -- 不可变采样器
- `ShaderInfo` -- SkSL 着色器生成
- `SkSLToBackend` -- SkSL 到 SPIR-V 编译
- `VulkanSpirvTransforms` -- SPIR-V 后处理变换

### 下游被依赖
- `VulkanCommandBuffer` -- 绑定管线和设置动态状态
- `VulkanResourceProvider` -- 管线缓存管理

## 设计模式与设计决策

1. **所有权分离**: `VulkanProgramInfo` 持有着色器模块和管线布局的临时所有权,通过 `releaseLayout()` 在成功创建管线后将布局所有权转移给管线对象,失败时自动清理。

2. **占位描述符集布局**: 即使某些描述符集不使用,也创建空的 `VkDescriptorSetLayout` 作为占位,确保绑定索引的正确性且不依赖 `graphicsPipelineLibrary` 特性。

3. **分层管线创建**: MSAA 加载管线将程序创建 (`CreateLoadMSAAProgram`) 和管线创建 (`MakeLoadMSAAPipeline`) 分离,允许同一程序复用于不同渲染通道描述。

4. **差异化动态状态更新**: 管线缓存前一个管线的状态,仅发出差异命令。虽然不是最优方案（理想情况下前端应直接计算差异），但在当前架构下有效减少了冗余状态设置。

5. **管线库优化**: 对于支持 `VK_EXT_graphics_pipeline_library` 的设备,将着色器编译与接口配置解耦,允许更细粒度的管线复用。

## 性能考量

- **管线缓存**: 利用 `VkPipelineCache` 和 `VK_EXT_pipeline_creation_cache_control` 跳过已缓存管线的重复编译。
- **动态状态**: 最多 22 种动态状态减少管线变体数量,显著降低管线创建和切换开销。
- **着色器管线库**: 将着色器编译（耗时操作）与接口配置（快速操作）分离,使管线变体生成成本更低。
- **差异化状态更新**: 通过与前一个管线比较,跳过未变化的动态状态设置命令。
- **STArray 栈分配**: 顶点属性和描述符布局使用栈上的小数组优化,避免频繁堆分配。
- **编译事件追踪**: 通过 `TRACE_EVENT` 精确标记缓存命中和编译事件,便于性能分析。

## 相关文件

- `src/gpu/graphite/vk/VulkanGraphiteUtils.h` -- Vulkan 工具宏和函数
- `src/gpu/graphite/vk/VulkanRenderPass.h` -- 渲染通道管理
- `src/gpu/graphite/vk/VulkanResourceProvider.h` -- 资源提供者
- `src/gpu/graphite/vk/VulkanCommandBuffer.h` -- 命令缓冲区
- `src/gpu/graphite/vk/VulkanCaps.h` -- Vulkan 能力查询
- `src/gpu/graphite/vk/VulkanSpirvTransforms.h` -- SPIR-V 变换
- `src/gpu/graphite/ShaderInfo.h` -- 着色器信息生成
- `src/gpu/graphite/GraphicsPipeline.h` -- 管线基类
