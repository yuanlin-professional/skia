# VulkanGraphiteUtils -- Vulkan 后端工具函数与宏

> 源文件:
> - `src/gpu/graphite/vk/VulkanGraphiteUtils.h`
> - `src/gpu/graphite/vk/VulkanGraphiteUtils.cpp`

## 概述

VulkanGraphiteUtils 是 Skia Graphite Vulkan 后端的核心工具模块,提供了 Vulkan API 调用的辅助宏、Shader 模块创建、描述符集布局生成、纹理格式转换以及渲染通道兼容性处理等功能。该模块是 Vulkan 后端其他组件（如管线、命令缓冲区、资源提供者等）的基础依赖。

## 架构位置

该模块位于 Graphite Vulkan 后端的底层工具层:

```
Context (上层接口)
  -> VulkanSharedContext (共享上下文)
    -> VulkanGraphiteUtils (工具函数/宏)  <-- 本模块
      -> VulkanInterface (Vulkan 函数指针接口)
```

它是一个纯工具模块,不包含类实例,仅导出自由函数和宏,被 Vulkan 后端几乎所有其他组件所依赖。

## 主要类与结构体

本模块不定义类,主要包含以下内容:

### 宏定义

| 宏名称 | 功能 |
|--------|------|
| `VULKAN_CALL(IFACE, X)` | 调用 Vulkan 接口函数,支持可选的调试日志输出 |
| `VULKAN_LOG_IF_NOT_SUCCESS(SHARED_CONTEXT, RESULT, X, ...)` | 在设备未丢失时记录 Vulkan 调用失败 |
| `VULKAN_CALL_RESULT(SHARED_CONTEXT, RESULT, X)` | 调用 Vulkan 函数并检查结果,触发设备丢失检查 |
| `VULKAN_CALL_ERRCHECK(SHARED_CONTEXT, X)` | 与 `VULKAN_CALL_RESULT` 相同但自动声明结果变量 |
| `VULKAN_CALL_RESULT_NOCHECK(IFACE, RESULT, X)` | 调用 Vulkan 函数但不检查错误 |

### BackendTextures 命名空间

提供对 `BackendTexture` 中 Vulkan 特定数据的访问:
- `GetVkImage` -- 获取底层 VkImage
- `GetVkImageLayout` -- 获取当前图像布局
- `GetVkQueueFamilyIndex` -- 获取队列族索引
- `GetMemoryAlloc` -- 获取内存分配信息
- `SetMutableState` / `GetMutableState` -- 管理可变纹理状态

## 公共 API 函数

### Shader 模块创建

```cpp
VkShaderModule CreateVulkanShaderModule(const VulkanSharedContext*,
                                        const SkSL::NativeShader& spirv,
                                        VkShaderStageFlagBits);
```
将 SPIR-V 字节码编译为 `VkShaderModule`。失败时返回 `VK_NULL_HANDLE`。

### 描述符集布局

```cpp
VkDescriptorType DsTypeEnumToVkDs(DescriptorType);
void DescriptorDataToVkDescSetLayout(const VulkanSharedContext*,
                                     const SkSpan<DescriptorData>&,
                                     VkDescriptorSetLayout*);
```
- `DsTypeEnumToVkDs`: 将 Graphite 描述符类型枚举映射到 Vulkan 描述符类型。
- `DescriptorDataToVkDescSetLayout`: 根据描述符数据数组创建 `VkDescriptorSetLayout`,支持空布局作为占位符。

### 纹理格式转换

```cpp
TextureFormat VkFormatToTextureFormat(VkFormat);
VkFormat TextureFormatToVkFormat(TextureFormat);
VkImageAspectFlags GetVkImageAspectFlags(TextureFormat);
```
使用 `VK_FORMAT_MAPPING` 宏表实现双向映射,覆盖颜色、深度、模板和压缩格式共 30+ 种。外部格式 (`kExternal`) 映射到 `VK_FORMAT_UNDEFINED`,需要调用方额外处理。

### 管线阶段标志转换

```cpp
VkShaderStageFlags PipelineStageFlagsToVkShaderStageFlags(SkEnumBitMask<PipelineStageFlags>);
constexpr VkSampleCountFlagBits SampleCountToVkSampleCount(SampleCount);
```

### 渲染通道工具函数

```cpp
bool RenderPassDescWillLoadMSAAFromResolve(const RenderPassDesc&);
bool RenderPassDescWillImplicitlyLoadMSAA(const RenderPassDesc&);
RenderPassDesc MakePipelineCompatibleRenderPass(const RenderPassDesc&);
```
- `RenderPassDescWillLoadMSAAFromResolve`: 判断是否需要从 resolve 附件加载 MSAA 数据。
- `RenderPassDescWillImplicitlyLoadMSAA`: 判断是否使用 `VK_EXT_multisampled_render_to_single_sampled` 扩展隐式加载。
- `MakePipelineCompatibleRenderPass`: 将加载/存储操作调整为通用值,使渲染通道保持管线兼容。

## 内部实现细节

### 格式映射表
使用 X-Macro 模式 (`VK_FORMAT_MAPPING`) 定义所有支持的格式映射。宏 `M(TextureFormat, VkFormat)` 在正向和反向两个 switch 语句中展开,确保映射表的一致性。

### MSAA 处理逻辑
Graphite 在渲染通道结束时始终将多重采样数据解析到单采样颜色附件。当下一个渲染通道需要加载单采样数据时:
1. 如果支持 `VK_EXT_multisampled_render_to_single_sampled`,驱动/硬件自动完成
2. 否则 Graphite 通过额外的绘制调用手动加载

### Context 工厂

```cpp
namespace ContextFactory {
std::unique_ptr<Context> MakeVulkan(const VulkanBackendContext&, const ContextOptions&);
}
```
创建 Vulkan Graphite 上下文的入口点,依次创建 `VulkanSharedContext` 和 `VulkanQueueManager`。

## 依赖关系

### 上游依赖
- `include/gpu/vk/VulkanTypes.h` -- Vulkan 类型定义
- `src/gpu/vk/VulkanInterface.h` -- Vulkan 函数指针封装
- `src/gpu/graphite/DescriptorData.h` -- 描述符数据定义
- `src/gpu/graphite/TextureFormat.h` -- 纹理格式枚举
- `src/gpu/graphite/RenderPassDesc.h` -- 渲染通道描述

### 下游被依赖
被 Vulkan 后端几乎所有文件使用,包括:
- `VulkanGraphicsPipeline` -- 管线创建
- `VulkanCommandBuffer` -- 命令录制
- `VulkanDescriptorSet` -- 描述符集分配
- `VulkanTexture` -- 纹理管理
- `VulkanSampler` -- 采样器

## 设计模式与设计决策

1. **X-Macro 模式**: 格式映射表通过宏参数化,一份定义生成正向和反向查找,避免维护两份独立映射的不一致风险。

2. **调试宏可切换**: `VULKAN_DEBUG_LOG` 默认关闭,取消注释即可开启 Vulkan 调用日志或 tracing,无需修改业务代码。

3. **设备丢失分层处理**: `VULKAN_CALL_RESULT` 先记录日志(仅在设备未丢失时),再调用 `checkVkResult` 更新设备状态,确保不会重复报告已丢失设备的错误。

4. **管线兼容渲染通道**: `MakePipelineCompatibleRenderPass` 选择最常见的加载/存储操作组合,最大化管线缓存命中率。

## 性能考量

- 格式转换函数使用 `switch` 语句,编译器通常优化为跳转表,O(1) 查找。
- `SampleCountToVkSampleCount` 声明为 `constexpr`,编译期计算。
- 宏在非调试模式下零开销,条件编译避免运行时分支。
- `DescriptorDataToVkDescSetLayout` 使用栈上的 `STArray` 避免堆分配。

## 相关文件

- `src/gpu/graphite/vk/VulkanSharedContext.h` -- Vulkan 共享上下文
- `src/gpu/graphite/vk/VulkanGraphicsPipeline.h` -- 图形管线
- `src/gpu/graphite/vk/VulkanSampler.h` -- 采样器实现
- `src/gpu/graphite/vk/VulkanRenderPass.h` -- 渲染通道
- `src/gpu/graphite/TextureFormat.h` -- 跨后端纹理格式定义
- `include/gpu/vk/VulkanBackendContext.h` -- Vulkan 后端上下文
