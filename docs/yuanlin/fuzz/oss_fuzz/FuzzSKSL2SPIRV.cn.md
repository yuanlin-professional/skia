# FuzzSKSL2SPIRV.cpp - SkSL 到 SPIR-V 着色器转换模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzSKSL2SPIRV.cpp`

## 概述

本文件实现了针对 SkSL 到 SPIR-V（Standard Portable Intermediate Representation for Vulkan）转换管线的模糊测试。SPIR-V 是 Vulkan GPU API 使用的标准中间着色器格式。该测试将随机字节数据作为 SkSL 片段着色器源码，尝试编译并生成 SPIR-V 字节码，用于发现编译器和 SPIR-V 代码生成器中的安全问题。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，是 Skia SkSL 编译器后端模糊测试系列之一。SPIR-V 后端是 Skia Vulkan 渲染管线的关键组件，覆盖该路径对于确保 Vulkan 平台上的着色器安全性至关重要。

## 主要类与结构体

使用的关键类型与 Metal 模糊测试类似：
- **`SkSL::Compiler`**: SkSL 编译器核心
- **`SkSL::ProgramSettings`**: 编译配置，包含 SPIR-V 特有的 RT-flip 设置
- **`SkSL::Program`**: 编译后的程序 IR
- **`SkSL::NativeShader`**: SPIR-V 字节码输出容器

## 公共 API 函数

- **`FuzzSKSL2SPIRV(const uint8_t *data, size_t size)`**: 核心模糊测试函数
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 3000 字节

## 内部实现细节

### SPIR-V 特有配置

与其他 SkSL 模糊测试不同，SPIR-V 版本需要额外配置 RT-flip（渲染目标翻转）uniform 的位置：
- `settings.fRTFlipOffset = 16384`: 设置为较大的偏移值，避免与其他 uniform 冲突
- `settings.fRTFlipSet = 0`: 描述符集编号
- `settings.fRTFlipBinding = 0`: 绑定点编号

这些设置是必需的，因为 Vulkan 的坐标系统与 OpenGL 不同（Y 轴方向相反），编译器需要知道翻转 uniform 的位置。如果保留默认无效值，编译器会报告错误。

### 测试流程

1. 创建编译器和带 RT-flip 配置的设置
2. 将输入字节编译为 `kFragment` 类型的 SkSL 程序
3. 调用 `SkSL::ToSPIRV()` 生成 SPIR-V 字节码

## 依赖关系

- **`src/sksl/codegen/SkSLSPIRVCodeGenerator.h`**: SPIR-V 代码生成器
- **`src/gpu/ganesh/GrShaderCaps.h`**: GPU 着色器能力
- **`src/sksl/SkSLCompiler.h`**: SkSL 编译器
- **`fuzz/Fuzz.h`**: 模糊测试基础设施

## 设计模式与设计决策

- **RT-flip 配置**: 使用安全的大偏移值（16384）避免 uniform 冲突，简化模糊测试设置
- **与其他 SkSL 模糊测试的一致性**: 保持相同的输入限制（3000 字节）和测试结构
- **Vulkan 特定处理**: RT-flip 配置体现了 Vulkan 后端相对于 OpenGL/Metal 的额外复杂性

## 性能考量

- SPIR-V 代码生成是纯 CPU 操作，不需要 Vulkan 运行时
- 3000 字节输入限制与其他 SkSL 模糊测试一致
- RT-flip 的大偏移值不影响代码生成性能
- SPIR-V 输出是二进制格式（`NativeShader` 包含字节数组），生成过程涉及更多的数据结构操作
- 编译器的 IR 到 SPIR-V 转换阶段是该后端特有的性能热点

### SPIR-V 与其他后端的技术差异

SPIR-V 后端的独特之处在于：
- 需要处理 Vulkan 描述符集和绑定点布局
- RT-flip uniform 是 Vulkan 特有需求，用于处理 Y 轴翻转
- 输出是二进制中间表示而非文本，错误更难以调试
- SPIR-V 有严格的验证规则，代码生成器必须产生合规的字节码

## 相关文件

- `fuzz/oss_fuzz/FuzzSKSL2Metal.cpp` - Metal 后端模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2GLSL.cpp` - GLSL 后端模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2WGSL.cpp` - WGSL 后端模糊测试
- `src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp` - SPIR-V 代码生成器实现
- `src/sksl/SkSLCompiler.cpp` - SkSL 编译器核心实现
- `src/gpu/vk/` - Skia Vulkan 后端（SPIR-V 的主要使用者）
- `src/sksl/ir/SkSLProgram.h` - SkSL 程序中间表示
