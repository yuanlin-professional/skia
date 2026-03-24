# tools/skslc - SkSL 着色器编译器工具

## 概述

`tools/skslc` 目录包含了 Skia 的 SkSL（Skia Shading Language）编译器命令行工具。SkSL 是 Skia 自定义的着色器语言，语法类似于 GLSL，但增加了 Skia 特有的功能和优化。`skslc` 工具负责将 SkSL 源代码编译并转换为多种目标着色器语言和中间表示。

`skslc` 支持丰富的输入格式和输出目标。输入方面，支持多种程序类型：顶点着色器（`.vert`）、片段着色器（`.frag`/`.sksl`）、网格顶点着色器（`.mvert`）、网格片段着色器（`.mfrag`）、计算着色器（`.compute`）、运行时混合器（`.rtb`）、运行时颜色过滤器（`.rtcf`）和运行时着色器（`.rts`/`.privrts`）。

输出方面，`skslc` 可以生成：GLSL 代码（`.glsl`）、SPIR-V 二进制（`.spirv`）和反汇编（`.asm.*`）、Metal Shading Language 代码（`.metal`）、HLSL 代码（`.hlsl`）、WGSL 代码（`.wgsl`）、SkSL Raster Pipeline 汇编（`.skrp`）以及管线阶段（Pipeline Stage）中间表示（`.stage`）。

该工具还支持通过 `/*#pragma settings*/` 注释在着色器源代码中嵌入编译选项，包括各种 `ShaderCaps` 配置（模拟不同 GPU 能力）和编译器设置（如 `NoInline`、`NoOptimize`、`ForceHighPrecision` 等）。此功能主要用于测试编译器在不同 GPU 能力约束下的代码生成行为。

`skslc` 支持两种调用模式：单文件模式（`skslc <input> <output> <flags>`）和工作列表模式（`skslc <worklist>`），后者允许批量处理多个着色器文件。

## 目录结构

```
tools/skslc/
├── BUILD.bazel            # Bazel 构建配置
├── Makefile               # Make 构建配置
├── compile_sksl.bzl       # Bazel SkSL 编译规则
├── Main.cpp               # 编译器主程序入口
├── ProcessWorklist.h      # 工作列表处理声明
└── ProcessWorklist.cpp    # 工作列表处理实现
```

## 关键类与函数

### main 函数（Main.cpp）
- 解析命令行参数，确定输入/输出路径和编译标志
- 两种调用模式：
  - 单文件: `skslc <input> <output> [--settings|--nosettings]`
  - 工作列表: `skslc <worklist>`

### process_command 函数
- 根据输入文件扩展名确定 `ProgramKind`（程序类型）
- 根据输出文件扩展名选择代码生成器：
  - `.glsl` -> `SkSL::ToGLSL()` - GLSL 代码生成
  - `.spirv` -> `SkSL::ToSPIRV()` - SPIR-V 二进制生成
  - `.asm.*` -> SPIR-V 反汇编
  - `.metal` -> `SkSL::ToMetal()` - Metal Shading Language 生成
  - `.hlsl` -> `SkSL::ToHLSL()` - HLSL 代码生成
  - `.wgsl` -> `SkSL::ToWGSL()` - WGSL 代码生成
  - `.skrp` -> `SkSL::MakeRasterPipelineProgram()` - Raster Pipeline 生成
  - `.stage` -> `SkSL::PipelineStage::ConvertProgram()` - 管线阶段生成

### detect_shader_settings 函数
- 解析源代码中的 `/*#pragma settings*/` 注释
- 支持多种 ShaderCaps 配置，如：
  - `AddAndTrueToLoopCondition`、`RewriteDoWhileLoops` - 控制流变换
  - `UsesPrecisionModifiers`、`Version110` - GLSL 版本控制
  - `FramebufferFetchSupport`、`DualSourceBlending` - GPU 特性模拟
- 支持编译器设置：`NoInline`、`NoOptimize`、`ForceHighPrecision`、`DebugTrace` 等

### ShaderCapsTestFactory
- 提供多种预配置的 `ShaderCaps` 对象
- 模拟不同 GPU 驱动的能力和限制
- 用于测试编译器的代码生成变换和兼容性处理

### ProcessWorklist
- **签名**: `ResultCode ProcessWorklist(const char* worklistPath, const std::function<ResultCode(SkSpan<std::string>)>&)`
- 从工作列表文件读取多组参数，逐组调用处理函数
- 空行分隔不同的参数组

### ResultCode 枚举
- `kSuccess` (0) - 编译成功
- `kCompileError` (1) - 编译错误
- `kInputError` (2) - 输入错误
- `kOutputError` (3) - 输出错误
- `kConfigurationError` (4) - 配置错误

## 依赖关系

- **编译器核心**: `src/sksl/SkSLCompiler.h`（SkSL 编译器）
- **代码生成器**: `src/sksl/codegen/` 下的所有代码生成器（GLSL、SPIRV、Metal、HLSL、WGSL、RasterPipeline、PipelineStage）
- **SPIR-V 工具**: `spirv-tools/libspirv.hpp`（SPIR-V 验证和反汇编）
- **IR 层**: `src/sksl/ir/`（SkSL 中间表示）
- **共享工具**: `tools/skslc/ProcessWorklist.h`（与 sksl-minify 共享）

## 输入输出格式对照表

| 输入扩展名 | 程序类型 | 说明 |
|-----------|----------|------|
| `.vert` | `kVertex` | 顶点着色器 |
| `.frag` / `.sksl` | `kFragment` | 片段着色器 |
| `.mvert` | `kMeshVertex` | 网格顶点着色器 |
| `.mfrag` | `kMeshFragment` | 网格片段着色器 |
| `.compute` | `kCompute` | 计算着色器 |
| `.rtb` | `kRuntimeBlender` | 运行时混合器 |
| `.rtcf` | `kRuntimeColorFilter` | 运行时颜色过滤器 |
| `.rts` | `kRuntimeShader` | 运行时着色器 |
| `.privrts` | `kPrivateRuntimeShader` | 私有运行时着色器 |

| 输出扩展名 | 目标格式 | 代码生成器 |
|-----------|----------|-----------|
| `.glsl` | GLSL | `SkSL::ToGLSL()` |
| `.spirv` | SPIR-V 二进制 | `SkSL::ToSPIRV()` |
| `.asm.*` | SPIR-V 反汇编 | SPIR-V Tools |
| `.metal` | Metal Shading Language | `SkSL::ToMetal()` |
| `.hlsl` | HLSL | `SkSL::ToHLSL()` |
| `.wgsl` | WGSL (WebGPU) | `SkSL::ToWGSL()` |
| `.skrp` | Raster Pipeline | `MakeRasterPipelineProgram()` |
| `.stage` | Pipeline Stage | `PipelineStage::ConvertProgram()` |

## 使用示例

```bash
# 编译 SkSL 片段着色器为 GLSL
skslc input.frag output.glsl --settings

# 编译 SkSL 为 SPIR-V 二进制
skslc input.vert output.spirv

# 编译 SkSL 为 Metal Shading Language
skslc input.frag output.metal

# 使用工作列表批量处理
skslc worklist.txt
```

## 相关文档与参考

- `src/sksl/SkSLCompiler.h` - SkSL 编译器核心
- `src/sksl/codegen/` - 各目标语言的代码生成器
- `tools/sksl-minify/` - SkSL 最小化工具（共享 ProcessWorklist）
- `tools/sksltrace/` - SkSL 调试追踪工具
- `resources/sksl/` - SkSL 测试用例
