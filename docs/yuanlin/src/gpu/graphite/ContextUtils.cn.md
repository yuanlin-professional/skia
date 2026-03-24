# ContextUtils (上下文工具函数)

> 源文件：[src/gpu/graphite/ContextUtils.h](../../../../src/gpu/graphite/ContextUtils.h)、[src/gpu/graphite/ContextUtils.cpp](../../../../src/gpu/graphite/ContextUtils.cpp)

## 概述

`ContextUtils` 提供了一组 Graphite 渲染管线中使用的工具函数和常量定义，包括内置 uniform 声明、硬件混合能力检查、管线标签生成、计算着色器 SkSL 构建和采样器布局发射等功能。这些工具函数被着色器代码生成、管线编译和绘制通道处理等多个模块共享使用。

## 架构位置

`ContextUtils` 是横切多个子系统的工具层：

- 被 `DrawPass`、`ShaderInfo`、`PaintParams` 等模块引用。
- 提供的 `kIntrinsicUniforms` 是每个 Graphite 着色器程序都使用的内置 uniform。

## 主要类与结构体

本文件没有定义类，仅提供常量和自由函数。

### `kIntrinsicUniforms` (全局常量)
所有 Graphite 着色器程序共有的内置 uniform：
- `viewport` (float4)：视口参数（left, top, 2/width, 2/height），用于 NDC 变换。
- `dstReadBounds` (float4)：目标读取纹理的边界和逆尺寸，用于 dst 纹理坐标归一化。

## 公共 API 函数

### `CollectIntrinsicUniforms`
```cpp
void CollectIntrinsicUniforms(const Caps*, SkIRect viewport, SkIRect dstReadBounds, UniformManager*);
```
将内置 uniform 值写入 `UniformManager`。视口参数预计算为 2/width 和 2/height（因 NDC 范围 [-1,1]）。如果 NDC Y 轴朝上（非 Skia 默认），高度取反。

### `CanUseHardwareBlending`
```cpp
bool CanUseHardwareBlending(const Caps*, TextureFormat, SkBlendMode, Coverage);
```
判断是否可以使用硬件混合。返回 false 的场景：
- LCD 覆盖率搭配非 SrcOver 混合模式。
- `kPlus` 混合模式在不自动钳位的格式上（需要着色器混合以正确钳位）。
- 高级混合模式但硬件不支持。
- 需要双源混合但硬件不支持。

### `GetPipelineLabel`
```cpp
std::string GetPipelineLabel(const Caps*, const ShaderCodeDictionary*,
                              const RenderPassDesc&, const RenderStep*, UniquePaintParamsID);
```
生成管线的可读标签，格式为 `"RenderPassLabel + RenderStepName + ShaderLabel"`。用于调试和管线缓存识别。

### `BuildComputeSkSL`
```cpp
std::string BuildComputeSkSL(const Caps*, const ComputeStep*, BackendApi);
```
为计算步骤生成 SkSL 代码。处理不同资源类型的布局声明（uniform、storage、纹理等），考虑后端差异（如纹理索引是否与缓冲区共享范围）。

### `EmitSamplerLayout`
```cpp
std::string EmitSamplerLayout(const ResourceBindingRequirements&, int* binding);
```
生成采样器绑定的 SkSL 布局声明。根据后端需求选择：
- 分离纹理/采样器绑定（WebGPU/Dawn）：`layout(webgpu, set=N, sampler=M, texture=T)`。
- 组合绑定：`layout(set=N, binding=M)`。

## 内部实现细节

### 视口 Uniform 预计算
视口 uniform 的 width/height 存储为 `2/width` 和 `2/height`，因为顶点着色器需要将设备坐标归一化到 NDC [-1,1] 范围。这避免了 GPU 端的除法操作。

### Plus 混合模式的近似处理
`SkBlendMode::kPlus` 的精确结果是 `clamp(D+S, 0, 1)`，与覆盖率组合后无法用硬件混合表示。在自动钳位的格式上可以近似为 `min(D+f*S, 1)`，在不钳位的格式或有快速 dst 读取时使用着色器混合保证正确性。

### 计算着色器 SkSL 构建
`BuildComputeSkSL` 遍历 `ComputeStep` 的资源描述列表，为每种资源类型生成适当的 SkSL 布局声明和类型前缀。支持 uniform buffer、storage buffer、只读 storage buffer、写入/只读/采样纹理等。

## 依赖关系

- `Caps`：能力查询（NDC 方向、硬件混合支持等）。
- `ShaderCodeDictionary`：着色器 ID 到字符串转换。
- `RenderPassDesc / RenderStep`：管线标签组成。
- `ComputeStep`：计算着色器资源描述。
- `UniformManager`：uniform 数据写入。
- `ResourceBindingRequirements`：资源绑定需求。

## 设计模式与设计决策

1. **预计算优化**：将 GPU 常量在 CPU 端预计算，减少着色器指令。
2. **硬件混合回退逻辑集中化**：将混合能力判断逻辑集中在一个函数中，避免各处重复。
3. **后端抽象**：通过 `ResourceBindingRequirements` 和 `BackendApi` 参数化后端差异。

## 性能考量

- 内置 uniform 的预计算避免了每个顶点的除法。
- 硬件混合判断在管线创建时执行一次，后续绘制直接使用结果。

## 相关文件

- `src/gpu/graphite/Caps.h`：能力查询。
- `src/gpu/graphite/ShaderCodeDictionary.h`：着色器字典。
- `src/gpu/graphite/RenderPassDesc.h`：渲染通道描述。
- `src/gpu/graphite/Renderer.h`：渲染步骤。
- `src/gpu/graphite/UniformManager.h`：Uniform 管理。
- `src/gpu/graphite/compute/ComputeStep.h`：计算步骤。
