# VulkanSpirvTransforms

> 源文件: `src/gpu/graphite/vk/VulkanSpirvTransforms.h`, `src/gpu/graphite/vk/VulkanSpirvTransforms.cpp`

## 概述

`VulkanSpirvTransforms` 模块提供了 SPIR-V 字节码的后处理变换功能。它能够在单次遍历中对已编译的 SPIR-V 着色器应用多种变换。当前实现的主要变换是将输入附件（input attachment）的加载操作从单采样修改为多采样模式，使着色器能在 MSAA 渲染通道中正确读取输入附件。

该模块的设计可扩展以支持未来的额外 SPIR-V 变换需求。

## 架构位置

- **上层**: 被 Vulkan 着色器编译管线调用，在 SPIR-V 生成后、提交给驱动前执行
- **输入**: SkSL 编译器生成的原始 SPIR-V
- **输出**: 变换后的 SPIR-V，可直接用于 `VkShaderModule` 创建

## 主要类与结构体

### `SPIRVTransformOptions` 结构体

控制要应用的变换选项：
- `fMultisampleInputLoad`（bool）— 是否调整 SPIR-V 以支持多采样输入附件加载

### `SpirvMultisampleTransformer` 类（内部）

执行多采样输入附件变换的核心类，具体变换包括：
- 添加 `SampleRateShading` 能力声明
- 在入口点中追加 `SampleId` 内建变量
- 为 `SampleId` 变量添加装饰（RelaxedPrecision、Flat、BuiltIn SampleId）
- 将输入附件的 `OpTypeImage` 从单采样改为多采样
- 将 `OpImageRead` 操作添加 `Sample` 操作数

### `SpirvTransformer` 类（内部）

SPIR-V 遍历和变换的主控制器：
- 逐指令遍历 SPIR-V
- 根据当前位置（全局声明区 vs 函数区）分发到不同的变换处理
- 未变换的指令原样复制到输出

## 公共 API 函数

- **`TransformSPIRV(const NativeShader& spirv, const SPIRVTransformOptions& options)`** — 对 SPIR-V 字节码应用指定的变换，返回新的 NativeShader

## 内部实现细节

### SPIR-V 结构理解

变换器理解 SPIR-V 的模块布局：
- 前 5 个字（header）：魔数、版本、生成器、ID 上界、保留字
- 指令区：按顺序排列的能力声明、扩展、内存模型、入口点、装饰、类型/常量/全局变量、函数声明

### 多采样变换流程

1. **OpCapability**: 遇到 `InputAttachment` 能力时，追加 `SampleRateShading` 能力
2. **OpEntryPoint**: 将新的 `SampleId` 变量 ID 追加到接口变量列表
3. **OpDecorate**: 在装饰区首次访问时，为 `SampleId` 变量添加 3 条装饰指令
4. **OpTypePointer**: 遇到 `kIdTypePointerInputInt` 时，声明 `SampleId` 变量
5. **OpTypeImage**: 将子通道数据图像类型的 MS 位从 0 改为 1
6. **OpLoad**: 追踪输入附件变量的加载结果 ID
7. **OpImageRead**: 在输入附件的图像读取前添加 `OpLoad SampleId`，并为读取操作添加 `Sample` 操作数

### ID 管理

通过修改 SPIR-V header 中的 ID 上界（`kIDBoundIndex`）来分配新 ID，确保不与现有 ID 冲突。

## 依赖关系

- `SkSL::NativeShader` — SPIR-V 字节码容器
- `SkSL::spirv` — SkSL SPIR-V 代码生成中定义的固定 ID 常量
- `spirv.h` — SPIR-V 操作码和常量定义
- `SkSLSPIRVValidator`（调试模式）— SPIR-V 验证器

## 设计模式与设计决策

### 单遍变换

所有变换在一次 SPIR-V 遍历中完成，避免多次遍历的开销。变换器按指令类型分发处理，未被任何变换修改的指令直接复制。

### 可扩展性

虽然当前只有多采样变换，但架构设计为可添加更多变换器。`SPIRVTransformOptions` 结构体和 `SpirvTransformer` 的分发逻辑都支持新变换的加入。

### 假设条件

多采样变换假设 SkSL 编译器不会自行生成 `SampleId` 变量和 `SampleRateShading` 能力。这是一个合理的假设，因为多采样输入加载是 Vulkan 特有的后处理需求。

## 性能考量

- **预分配缓冲区**: 输出 SPIR-V 预分配为输入大小 + 64 字（为变换添加的指令预留空间）
- **单遍处理**: 避免多次遍历大型 SPIR-V blob
- **布尔追踪**: 使用 `vector<bool>` 追踪输入附件加载结果，空间和时间复杂度为 O(maxId)

## 相关文件

- `src/sksl/codegen/SkSLNativeShader.h` — NativeShader 类型定义
- `src/sksl/spirv.h` — SPIR-V 常量和操作码
- `src/sksl/codegen/SkSLCodeGenTypes.h` — SPIR-V 代码生成类型
- `src/gpu/graphite/vk/VulkanResourceProvider.cpp` — 调用 SPIR-V 变换的位置
