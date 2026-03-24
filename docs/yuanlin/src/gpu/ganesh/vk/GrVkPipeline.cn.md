# GrVkPipeline

> 源文件
> - src/gpu/ganesh/vk/GrVkPipeline.h
> - src/gpu/ganesh/vk/GrVkPipeline.cpp

## 概述

`GrVkPipeline` 是 Skia Ganesh 渲染引擎中用于封装 Vulkan 图形管线（Graphics Pipeline）的核心类。它继承自 `GrVkManagedResource`，负责管理 Vulkan 管线对象的创建、配置和生命周期。该类提供了两个静态工厂方法来创建管线实例，并封装了动态状态设置（如视口、裁剪矩形和混合常量）的功能。

Vulkan 管线对象是一个复杂的状态集合，包含顶点输入、图元装配、光栅化、多重采样、深度/模板测试、颜色混合等所有渲染阶段的配置。`GrVkPipeline` 通过多个辅助函数简化了管线创建过程，将 Skia 的高层次渲染状态转换为 Vulkan 的底层 API 调用。

## 架构位置

`GrVkPipeline` 位于 Skia 图形栈的 GPU 后端层次中：

```
Skia 图形引擎
  └─ Ganesh GPU 后端
      └─ Vulkan 后端实现
          ├─ GrVkGpu (设备管理)
          ├─ GrVkCommandBuffer (命令缓冲)
          ├─ GrVkPipeline (管线封装) ← 当前类
          ├─ GrVkRenderPass (渲染通道)
          └─ GrVkResourceProvider (资源提供)
```

该类作为 Vulkan 管线状态的抽象层，连接了 Ganesh 的平台无关接口和 Vulkan 的特定实现。

## 主要类与结构体

### 核心类继承关系

| 类名 | 父类 | 说明 |
|------|------|------|
| `GrVkPipeline` | `GrVkManagedResource` | Vulkan 管线封装，管理 VkPipeline 和 VkPipelineLayout |
| `GrVkManagedResource` | `GrManagedResource` | Vulkan 资源管理基类 |
| `GrManagedResource` | `SkRefCnt` | Ganesh 资源引用计数基类 |

### 关键成员变量

| 成员变量 | 类型 | 说明 |
|----------|------|------|
| `fPipeline` | `VkPipeline` | Vulkan 管线句柄 |
| `fPipelineLayout` | `VkPipelineLayout` | 管线布局句柄（描述符集和推送常量的布局） |
| `fGpu` | `const GrVkGpu*` | 关联的 Vulkan GPU 设备（继承自基类） |

## 公共 API 函数

### 管线创建

```cpp
static sk_sp<GrVkPipeline> Make(
    GrVkGpu* gpu,
    const GrGeometryProcessor::AttributeSet& vertexAttribs,
    const GrGeometryProcessor::AttributeSet& instanceAttribs,
    GrPrimitiveType primitiveType,
    GrSurfaceOrigin origin,
    const GrStencilSettings& stencilSettings,
    int numSamples,
    bool isHWAntialiasState,
    const skgpu::BlendInfo& blendInfo,
    bool isWireframe,
    bool useConservativeRaster,
    uint32_t subpass,
    VkPipelineShaderStageCreateInfo* shaderStageInfo,
    int shaderStageCount,
    VkRenderPass compatibleRenderPass,
    VkPipelineLayout layout,
    bool ownsLayout,
    VkPipelineCache cache);
```
详细创建管线的方法，接受所有必要的状态参数。

```cpp
static sk_sp<GrVkPipeline> Make(
    GrVkGpu* gpu,
    const GrProgramInfo& programInfo,
    VkPipelineShaderStageCreateInfo* shaderStageInfo,
    int shaderStageCount,
    VkRenderPass compatibleRenderPass,
    VkPipelineLayout layout,
    VkPipelineCache cache,
    uint32_t subpass);
```
从 `GrProgramInfo` 对象创建管线的便捷方法，内部调用第一个 `Make` 方法。

### 访问器

```cpp
VkPipeline pipeline() const
```
返回 Vulkan 管线句柄。

```cpp
VkPipelineLayout layout() const
```
返回管线布局句柄，断言布局非空。

### 动态状态设置

```cpp
static void SetDynamicScissorRectState(
    GrVkGpu* gpu,
    GrVkCommandBuffer* cmdBuffer,
    SkISize colorAttachmentDimensions,
    GrSurfaceOrigin origin,
    const SkIRect& scissorRect);
```
设置动态裁剪矩形，处理不同表面原点的坐标转换。

```cpp
static void SetDynamicViewportState(
    GrVkGpu* gpu,
    GrVkCommandBuffer* cmdBuffer,
    SkISize colorAttachmentDimensions);
```
设置动态视口状态，视口覆盖整个渲染目标。

```cpp
static void SetDynamicBlendConstantState(
    GrVkGpu* gpu,
    GrVkCommandBuffer* cmdBuffer,
    const skgpu::Swizzle& writeSwizzle,
    const GrXferProcessor& xferProcessor);
```
设置动态混合常量，应用颜色混洗。

## 内部实现细节

### 管线状态配置

管线创建过程涉及多个辅助函数，每个函数负责配置管线的特定部分：

**顶点输入配置** (`setup_vertex_input_state`)：
- 将 Skia 的顶点属性类型（`GrVertexAttribType`）映射为 Vulkan 格式（`VkFormat`）
- 配置顶点绑定和实例绑定
- 设置属性描述（位置、绑定、格式、偏移）

**图元装配配置** (`setup_input_assembly_state`)：
- 将 `GrPrimitiveType` 转换为 `VkPrimitiveTopology`
- 支持三角形、三角带、点、线和线带

**深度模板配置** (`setup_depth_stencil_state`)：
- 转换 Skia 的模板设置为 Vulkan 的模板操作状态
- 处理单面和双面模板测试
- 根据表面原点调整正反面定义

**光栅化配置** (`setup_raster_state`)：
- 支持线框模式渲染
- 配置剔除模式和正面定义
- 不启用深度偏移

**多重采样配置** (`setup_multisample_state`)：
- 将采样数转换为 Vulkan 采样计数
- 禁用采样着色和 alpha-to-coverage

**颜色混合配置** (`setup_color_blend_state`)：
- 将 Skia 的混合系数和方程转换为 Vulkan 枚举
- 支持基础混合模式和高级混合扩展（EXT_blend_operation_advanced）
- 根据 `blendInfo.fWritesColor` 控制颜色写入掩码

**动态状态配置** (`setup_dynamic_state`)：
- 配置三个动态状态：视口、裁剪矩形、混合常量
- 允许在不重建管线的情况下修改这些状态

### 管线缓存支持

实现支持管线缓存优化：
- 首次尝试使用 `VK_PIPELINE_CREATE_FAIL_ON_PIPELINE_COMPILE_REQUIRED_BIT_EXT` 标志进行缓存查找
- 如果缓存未命中，移除该标志并进行完整编译
- 通过 `TRACE_EVENT` 标记区分缓存命中和未命中情况

### 内存泄漏抑制

在某些配置下（`SK_ENABLE_SCOPED_LSAN_SUPPRESSIONS`），使用 LSAN（LeakSanitizer）抑制器来处理 Vulkan 驱动的已知问题。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `GrVkGpu` | 获取 Vulkan 设备、能力和接口 |
| `GrVkCommandBuffer` | 设置动态渲染状态 |
| `GrGeometryProcessor` | 顶点和实例属性定义 |
| `GrProgramInfo` | 程序渲染状态信息 |
| `GrStencilSettings` | 模板测试配置 |
| `GrXferProcessor` | 混合模式信息 |
| `skgpu::BlendInfo` | 混合系数和方程 |
| `VulkanUtilsPriv` | Vulkan 工具函数 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| `GrVkPipelineState` | 持有 `GrVkPipeline` 实例 |
| `GrVkOpsRenderPass` | 调用动态状态设置方法 |
| `GrVkResourceProvider` | 通过管线缓存创建管线 |

## 设计模式与设计决策

### 工厂模式
使用静态 `Make` 方法而非公共构造函数，确保对象通过智能指针 `sk_sp` 正确管理。这种模式允许在创建失败时返回 `nullptr`，而不会留下部分构造的对象。

### 资源所有权管理
通过 `ownsLayout` 参数控制是否拥有 `VkPipelineLayout` 的所有权。当为 `false` 时，析构时不销毁布局对象，这在多个管线共享同一布局时很有用。

### 静态辅助函数
将管线状态配置逻辑分解为多个静态函数，提高代码可读性和可维护性。每个函数专注于配置 Vulkan 管线的特定部分。

### 动态状态优化
将视口、裁剪矩形和混合常量设为动态状态，避免因这些频繁变化的状态而重新创建管线，提高性能。

### 追踪和调试
使用 `TRACE_EVENT` 宏标记关键操作，便于性能分析和调试。在调试模式下提供 `dumpInfo` 方法输出管线信息。

## 性能考量

### 管线缓存
利用 Vulkan 的管线缓存机制减少重复编译开销。支持管线创建缓存控制扩展时，优先进行缓存查找，避免不必要的编译。

### 动态状态最小化
虽然动态状态允许运行时修改，但 Vulkan 规范限制了可用的动态状态类型。当前实现选择了最频繁变化的三个状态（视口、裁剪、混合常量）作为动态状态。

### 属性映射优化
`attrib_type_to_vkformat` 使用 `switch-case` 直接映射，编译器可以优化为跳转表或二分查找，确保快速转换。

### 栈分配优化
使用 `STArray`（栈分配的小型数组）存储顶点绑定和属性描述，避免堆分配开销。对于大多数几何体，这些数组足够小，可以完全在栈上分配。

### 保守光栅化支持
仅在硬件支持且需要时才启用保守光栅化，避免不必要的性能损失。该特性对某些图形效果（如精确覆盖检测）很重要。

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/gpu/ganesh/vk/GrVkManagedResource.h` | 父类 | 资源管理基类 |
| `src/gpu/ganesh/vk/GrVkGpu.h` | 依赖 | Vulkan GPU 设备封装 |
| `src/gpu/ganesh/vk/GrVkCommandBuffer.h` | 依赖 | 命令缓冲区接口 |
| `src/gpu/ganesh/vk/GrVkPipelineState.h` | 使用者 | 管线状态持有者 |
| `src/gpu/ganesh/vk/GrVkRenderPass.h` | 协作 | 渲染通道定义 |
| `src/gpu/ganesh/vk/GrVkCaps.h` | 依赖 | Vulkan 能力查询 |
| `src/gpu/ganesh/GrGeometryProcessor.h` | 依赖 | 几何处理器接口 |
| `src/gpu/ganesh/GrProgramInfo.h` | 依赖 | 程序信息封装 |
| `src/gpu/vk/VulkanUtilsPriv.h` | 依赖 | Vulkan 工具函数 |
