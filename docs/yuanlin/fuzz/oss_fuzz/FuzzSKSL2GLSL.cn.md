# FuzzSKSL2GLSL.cpp - SkSL 到 GLSL 着色器转换模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzSKSL2GLSL.cpp`

## 概述

本文件实现了针对 SkSL 到 GLSL（OpenGL Shading Language）转换管线的模糊测试。GLSL 是 OpenGL 和 OpenGL ES 使用的着色器语言。该测试将随机字节数据作为 SkSL 片段着色器源码进行编译并转换为 GLSL，用于发现编译器前端和 GLSL 代码生成后端中的安全漏洞。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，是 SkSL 编译器模糊测试系列的组成部分。GLSL 后端是 Skia 最广泛使用的着色器输出格式，覆盖了 OpenGL 和 OpenGL ES 平台（Android、Linux、Windows 的 OpenGL 模式等），因此该模糊测试对 Skia 的安全性具有重要意义。

## 主要类与结构体

- **`SkSL::Compiler`**: SkSL 编译器核心
- **`SkSL::ProgramSettings`**: 默认编译设置（无需额外配置）
- **`SkSL::Program`**: 编译后的程序 IR
- **`SkSL::NativeShader`**: GLSL 代码输出容器

## 公共 API 函数

- **`FuzzSKSL2GLSL(const uint8_t *data, size_t size)`**: 核心模糊测试函数，将字节数据编译为 SkSL 并转换为 GLSL
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 入口点，输入限制 3000 字节

## 内部实现细节

### 测试流程

与 Metal 和 WGSL 模糊测试结构相同：
1. 创建编译器实例和默认设置
2. 将输入编译为 `kFragment` 着色器程序
3. 调用 `SkSL::ToGLSL()` 生成 GLSL 代码

### 与 SPIR-V 版本的区别

GLSL 版本不需要配置 RT-flip 参数，因为 OpenGL 的坐标系统翻转是在 GLSL 代码中直接处理的，而非通过外部 uniform。

## 依赖关系

- **`src/sksl/codegen/SkSLGLSLCodeGenerator.h`**: GLSL 代码生成器
- **`src/gpu/ganesh/GrShaderCaps.h`**: 着色器能力描述
- **`src/sksl/SkSLCompiler.h`**: SkSL 编译器
- **`fuzz/Fuzz.h`**: 模糊测试基础设施

## 设计模式与设计决策

- **最简配置**: 使用默认 `ProgramSettings`，不需要额外的后端特定配置
- **统一测试结构**: 与 Metal、SPIR-V、WGSL 模糊测试保持一致的代码结构
- **相同的输入限制**: 3000 字节上限在所有 SkSL 模糊测试中保持一致

## 性能考量

- GLSL 代码生成是所有后端中最轻量的之一，因为输出是文本格式
- 3000 字节输入限制确保每次测试在毫秒级完成
- 默认的 ShaderCaps 覆盖了通用代码路径
- 字符串拼接是 GLSL 代码生成的主要操作，内存分配模式对性能有一定影响

### GLSL 后端的特殊性

GLSL 后端作为 Skia 最成熟的着色器输出格式，有以下特点：
- 代码最成熟稳定，历史 bug 最少
- 覆盖了最广泛的 GPU 硬件（从低端移动设备到高端桌面 GPU）
- 不同 GLSL 版本（ES 2.0、ES 3.0、桌面 3.30 等）的代码生成路径可能不同
- ShaderCapsFactory::Default() 通常对应一个合理的中端能力配置

### 与 Skia Ganesh 后端的关系

GLSL 代码生成器是 Skia Ganesh（OpenGL）GPU 后端的核心组件。Ganesh 在运行时将 SkSL 着色器编译为 GLSL 并提交给 OpenGL 驱动程序编译。

## 相关文件

- `fuzz/oss_fuzz/FuzzSKSL2Metal.cpp` - Metal 后端模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2SPIRV.cpp` - SPIR-V 后端模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2WGSL.cpp` - WGSL 后端模糊测试
- `src/sksl/codegen/SkSLGLSLCodeGenerator.cpp` - GLSL 代码生成器实现
- `src/sksl/SkSLCompiler.cpp` - SkSL 编译器核心实现
- `src/gpu/ganesh/GrShaderCaps.cpp` - GPU 着色器能力配置实现
- `src/gpu/ganesh/gl/` - Skia OpenGL 后端（GLSL 的主要使用者）
- `src/sksl/ir/SkSLProgram.h` - SkSL 程序中间表示
- `fuzz/oss_fuzz/FuzzSkRuntimeEffect.cpp` - 运行时效果模糊测试
