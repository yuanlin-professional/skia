# FuzzSKSL2Metal.cpp - SkSL 到 Metal 着色器转换模糊测试

> 源文件: `fuzz/oss_fuzz/FuzzSKSL2Metal.cpp`

## 概述

本文件实现了一个针对 Skia 的 SkSL（Skia Shading Language）到 Apple Metal 着色语言转换管线的模糊测试（fuzz test）。它是 OSS-Fuzz 持续模糊测试基础设施的一部分，用于自动发现 SkSL 编译器和 Metal 代码生成器中的崩溃、内存错误和未定义行为。测试将随机生成的字节数据作为 SkSL 片段着色器源码，尝试编译并转换为 Metal 着色器。

## 架构位置

该文件位于 `fuzz/oss_fuzz/` 目录下，属于 Skia 的安全测试层。它通过 Google 的 OSS-Fuzz 服务持续运行，覆盖 SkSL 编译器前端（解析、类型检查、IR 生成）和 Metal 后端代码生成器的完整路径。在 Skia 的 GPU 渲染管线中，SkSL 到 Metal 的转换是 Apple 平台（iOS/macOS）上 GPU 着色器部署的关键环节。

## 主要类与结构体

本文件不定义新的类或结构体，使用的关键类型包括：

- **`SkSL::Compiler`**: SkSL 编译器核心，负责解析和编译着色器源码
- **`SkSL::ProgramSettings`**: 编译配置，控制编译器行为
- **`SkSL::Program`**: 编译后的着色器程序中间表示
- **`SkSL::NativeShader`**: Metal 着色器输出容器
- **`SkSL::ShaderCapsFactory`**: 着色器能力工厂，提供默认的 GPU 能力配置

## 公共 API 函数

- **`FuzzSKSL2Metal(const uint8_t *data, size_t size)`**: 核心模糊测试函数，接受原始字节数据，尝试将其作为 SkSL 源码编译并转换为 Metal 着色器。成功返回 `true`，任何阶段失败返回 `false`
- **`LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)`**: LibFuzzer 标准入口点（仅在 `SK_BUILD_FOR_LIBFUZZER` 定义时编译），限制输入大小不超过 3000 字节

## 内部实现细节

### 测试流程

1. 创建 `SkSL::Compiler` 实例和默认 `ProgramSettings`
2. 将输入字节重新解释为字符串，作为 `kFragment` 类型的着色器源码
3. 调用 `compiler.convertProgram()` 编译 SkSL 程序
4. 如果编译成功，调用 `SkSL::ToMetal()` 生成 Metal 代码
5. 使用 `ShaderCapsFactory::Default()` 提供默认的 GPU 能力描述

### 输入限制

LibFuzzer 模式下，输入大小限制为 3000 字节。这是因为过大的输入会导致编译器花费过多时间在解析和优化上，降低模糊测试的效率。

## 依赖关系

- **`src/gpu/ganesh/GrShaderCaps.h`**: GPU 着色器能力描述
- **`src/sksl/SkSLCompiler.h`**: SkSL 编译器
- **`src/sksl/SkSLProgramKind.h`**: 程序类型枚举
- **`src/sksl/SkSLProgramSettings.h`**: 编译设置
- **`src/sksl/codegen/SkSLMetalCodeGenerator.h`**: Metal 代码生成器
- **`src/sksl/codegen/SkSLNativeShader.h`**: 原生着色器输出
- **`src/sksl/ir/SkSLProgram.h`**: 程序 IR
- **`fuzz/Fuzz.h`**: 模糊测试基础设施

## 设计模式与设计决策

- **最小化测试目标**: 仅测试编译和代码生成路径，不涉及实际 GPU 执行，隔离了驱动层的复杂性
- **输入大小限制**: 3000 字节上限确保模糊测试能快速迭代大量用例
- **双模式编译**: 支持 LibFuzzer（`LLVMFuzzerTestOneInput`）和 Skia 内部模糊测试框架两种入口
- **默认能力配置**: 使用 `ShaderCapsFactory::Default()` 而非特定 GPU 配置，确保覆盖通用代码路径

## 性能考量

- 3000 字节的输入限制是模糊测试效率和覆盖率之间的折衷
- 每次测试创建新的编译器实例，避免状态泄漏但增加了初始化开销
- Metal 代码生成是纯 CPU 操作，不依赖 GPU 硬件
- `ShaderCapsFactory::Default()` 返回的能力配置在所有测试中共享，避免重复构建
- 编译器的前端解析阶段对输入大小敏感，3000 字节上限确保解析在合理时间内完成
- 输入字节到字符串的转换（`reinterpret_cast<const char*>`）是零拷贝操作

### 已发现的典型问题类型

通过此模糊测试历史上发现的问题类型包括：
- 编译器在处理畸形 SkSL 输入时的断言失败
- Metal 代码生成器在特定 IR 结构下的未处理分支
- 类型检查器在边界条件下的内存访问越界

## 相关文件

- `fuzz/oss_fuzz/FuzzSKSL2GLSL.cpp` - SkSL 到 GLSL 的对应模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2SPIRV.cpp` - SkSL 到 SPIR-V 的对应模糊测试
- `fuzz/oss_fuzz/FuzzSKSL2WGSL.cpp` - SkSL 到 WGSL 的对应模糊测试
- `src/sksl/codegen/SkSLMetalCodeGenerator.cpp` - Metal 代码生成器实现
- `src/sksl/SkSLCompiler.cpp` - SkSL 编译器实现
