# skslc Main - SkSL 着色器编译器

> 源文件: `tools/skslc/Main.cpp`

## 概述

Main.cpp 是 SkSL（Skia Shading Language）离线编译器的主入口。它能将 SkSL 着色器程序编译为多种目标格式：GLSL、HLSL、Metal Shading Language、SPIR-V、WGSL 以及 Skia 内部的 Raster Pipeline 字节码。该工具是 Skia GPU 后端开发和测试的核心工具。

## 架构位置

位于 `tools/skslc/` 目录，是 Skia 构建系统中的独立编译器工具。被 Skia 的测试基础设施广泛使用来验证着色器编译的正确性。

## 主要类与结构体

### `ShaderCapsTestFactory`
继承自 `SkSL::ShaderCapsFactory`，提供多种模拟 GPU 着色器能力的静态工厂方法，如：
- `AddAndTrueToLoopCondition` - 模拟需要在循环条件中添加 `&& true` 的 GPU
- `CannotUseFractForNegativeValues` - 模拟 fract() 对负数不正确的 GPU
- 其他数十种特定 GPU 行为模拟

### `Adapter` (内部类)
将 `SkSL::OutputStream` 适配为 `SkWStream` 接口。

## 公共 API 函数

编译器通过命令行参数驱动，核心编译流程由 `SkSL::Compiler` 类提供。

## 内部实现细节

- 通过文件扩展名（.vert/.frag/.compute 等）确定着色器类型
- 通过输出后缀（.glsl/.metal/.spirv/.wgsl/.hlsl 等）确定目标代码生成器
- 支持 Shader Caps 文件名后缀来指定模拟的 GPU 能力
- SPIR-V 输出经过 spirv-tools 验证
- WGSL 输出经过 Tint 验证
- 支持 Pipeline Stage 代码生成（用于 Skia 内部着色器组合）
- 支持 Raster Pipeline 字节码生成（用于 CPU 软件渲染）

## 依赖关系

- `src/sksl/` - SkSL 编译器核心
- `spirv-tools/libspirv.hpp` - SPIR-V 验证
- 各种代码生成器：GLSL、HLSL、Metal、SPIR-V、WGSL、RasterPipeline

## 设计模式与设计决策

- **策略模式**: 根据输出格式选择不同的代码生成器
- **工厂模式**: `ShaderCapsTestFactory` 提供大量预设的 GPU 能力配置
- **适配器模式**: `Adapter` 类桥接 Skia 和 SkSL 的流接口

## 性能考量

- 作为离线工具，优先保证正确性而非编译速度
- 支持 worklist 批处理模式以减少进程启动开销

## 相关文件

- `src/sksl/SkSLCompiler.h` - SkSL 编译器核心
- `tools/skslc/ProcessWorklist.h` - 批处理支持
