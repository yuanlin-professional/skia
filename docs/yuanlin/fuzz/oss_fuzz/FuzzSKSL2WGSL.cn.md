# FuzzSKSL2WGSL.cpp - SkSL 到 WGSL 着色器转换模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzSKSL2WGSL.cpp`

## 概述

本文件实现了针对 SkSL 到 WGSL（WebGPU Shading Language）转换管线的模糊测试。WGSL 是 WebGPU API 使用的着色器语言，是下一代 Web 图形标准的核心组件。该测试将随机字节数据作为 SkSL 片段着色器源码，尝试编译并生成 WGSL 代码，用于发现 WGSL 代码生成器中的安全问题。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，是 SkSL 编译器后端模糊测试系列之一。WGSL 后端支持 Skia 的 Dawn/WebGPU 渲染管线，对于浏览器中的 GPU 加速渲染安全性至关重要，特别是在 Chrome 中使用 Skia Graphite 后端时。

## 主要类与结构体

- **`SkSL::Compiler`**: SkSL 编译器核心
- **`SkSL::ProgramSettings`**: 默认编译设置
- **`SkSL::Program`**: 编译后的程序 IR
- **`SkSL::NativeShader`**: WGSL 代码输出容器

## 公共 API 函数

- **`FuzzSKSL2WGSL(const uint8_t *data, size_t size)`**: 核心模糊测试函数
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 3000 字节

## 内部实现细节

### 测试流程

与 GLSL 和 Metal 模糊测试结构相同：
1. 创建编译器和默认设置
2. 将输入编译为 `kFragment` 着色器
3. 调用 `SkSL::ToWGSL()` 生成 WGSL 代码

### 与其他后端的差异

WGSL 版本使用默认设置，不需要 SPIR-V 的 RT-flip 配置。WGSL 作为较新的着色器语言，其代码生成器可能包含更多待发现的问题。

## 依赖关系

- **`src/sksl/codegen/SkSLWGSLCodeGenerator.h`**: WGSL 代码生成器
- **`src/gpu/ganesh/GrShaderCaps.h`**: 着色器能力
- **`src/sksl/SkSLCompiler.h`**: SkSL 编译器
- **`fuzz/Fuzz.h`**: 模糊测试基础设施

## 设计模式与设计决策

- **统一测试结构**: 与其他 SkSL 后端模糊测试保持一致的代码模式
- **默认配置**: 使用默认 `ProgramSettings`，WGSL 后端不需要额外配置
- **3000 字节限制**: 与其他 SkSL 模糊测试统一的输入限制

## 性能考量

- WGSL 代码生成为纯文本输出，CPU 开销较小
- 3000 字节限制确保高效的模糊测试迭代
- 默认 ShaderCaps 覆盖通用代码路径
- WGSL 代码生成器是所有后端中最新的，可能存在更多的优化空间

### WGSL 后端的特殊性

WGSL 是 WebGPU 标准的一部分，具有以下特点：
- 语法设计更现代，与 Rust 风格类似
- 类型系统比 GLSL 更严格，代码生成器需要更多的类型标注
- 主要在 Chrome 浏览器的 Dawn（WebGPU 实现）中使用
- 支持 Skia Graphite 渲染后端（下一代 GPU 架构）

### 与 Skia Graphite 的关系

WGSL 代码生成器是 Skia Graphite（下一代 GPU 后端）在 Dawn/WebGPU 平台上的核心组件。Graphite 旨在替代 Ganesh，提供更好的多线程支持和更高效的 GPU 命令录制。

## 相关文件

- `fuzz/oss_fuzz/FuzzSKSL2Metal.cpp` - Metal 后端模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2SPIRV.cpp` - SPIR-V 后端模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2GLSL.cpp` - GLSL 后端模糊测试
- `src/sksl/codegen/SkSLWGSLCodeGenerator.cpp` - WGSL 代码生成器实现
- `src/sksl/SkSLCompiler.cpp` - SkSL 编译器核心实现
- `src/gpu/graphite/` - Skia Graphite 后端（WGSL 的主要使用者）
- `fuzz/oss_fuzz/FuzzSkRuntimeEffect.cpp` - 运行时效果模糊测试（使用完整编译+渲染管线）
- `src/sksl/ir/SkSLProgram.h` - SkSL 程序中间表示
- `src/sksl/SkSLProgramSettings.h` - SkSL 编译设置定义
