# SkSLToBackend

> 源文件: src/gpu/SkSLToBackend.h, src/gpu/SkSLToBackend.cpp

## 概述

`SkSLToBackend` 是 Skia GPU 层中 SkSL(Skia Shading Language)编译器的包装器,负责将 SkSL 代码编译成特定后端的着色器代码(如 GLSL、Metal、SPIR-V 等)。该模块提供了统一的接口,集成了错误处理、调试日志和代码美化功能,简化了着色器编译流程。

该函数是 Skia GPU 渲染管线中的关键组件,连接了高层的 SkSL 代码和底层的图形 API,确保着色器能够正确编译并在目标平台上执行。

## 架构位置

`SkSLToBackend` 位于 GPU 层的着色器编译基础设施:

- 命名空间: `skgpu`
- 模块位置: `src/gpu/`
- 依赖层级: SkSL 编译器层与 GPU 后端层之间的桥梁
- 服务对象: Ganesh 和 Graphite 渲染器、PipelineBuilder、着色器缓存

该模块是着色器编译的统一入口点,被所有需要编译 SkSL 的上层模块使用。

## 主要类与结构体

本模块仅提供函数,不定义类或结构体。涉及的外部类型包括:

### 外部类型(SkSL 命名空间)

| 类型 | 说明 |
|------|------|
| `SkSL::ShaderCaps` | 着色器能力描述,定义目标后端的限制 |
| `SkSL::Program` | 编译后的 SkSL 程序 |
| `SkSL::ProgramKind` | 程序类型(顶点、片段等) |
| `SkSL::ProgramSettings` | 编译器设置 |
| `SkSL::ProgramInterface` | 程序接口信息(uniform、varying 等) |
| `SkSL::NativeShader` | 后端原生着色器代码(文本或二进制) |

### 外部类型(skgpu 命名空间)

| 类型 | 说明 |
|------|------|
| `ShaderErrorHandler` | 错误处理回调接口 |

## 公共 API 函数

### SkSLToBackend 函数

```cpp
namespace skgpu {

bool SkSLToBackend(
    const SkSL::ShaderCaps* caps,
    bool (*toBackend)(SkSL::Program&, const SkSL::ShaderCaps*, SkSL::NativeShader*),
    const char* backendLabel,
    const std::string& sksl,
    SkSL::ProgramKind programKind,
    const SkSL::ProgramSettings& settings,
    SkSL::NativeShader* output,
    SkSL::ProgramInterface* outInterface,
    ShaderErrorHandler* errorHandler
);

}  // namespace skgpu
```

**参数说明**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `caps` | `const SkSL::ShaderCaps*` | 目标后端的能力描述 |
| `toBackend` | 函数指针 | 后端特定的代码生成函数 |
| `backendLabel` | `const char*` | 后端名称(用于日志),如 "GLSL"、"Metal" |
| `sksl` | `const std::string&` | 输入的 SkSL 源代码 |
| `programKind` | `SkSL::ProgramKind` | 程序类型(顶点、片段、计算等) |
| `settings` | `const SkSL::ProgramSettings&` | 编译器设置 |
| `output` | `SkSL::NativeShader*` | 输出参数,接收生成的后端代码 |
| `outInterface` | `SkSL::ProgramInterface*` | 可选输出,接收程序接口信息 |
| `errorHandler` | `ShaderErrorHandler*` | 错误处理回调 |

**返回值**:
- `true`: 编译成功
- `false`: 编译失败(错误通过 `errorHandler` 报告)

## 内部实现细节

### 编译流程

```cpp
bool SkSLToBackend(...) {
    // 1. 代码美化(仅 Debug 模式)
#ifdef SK_DEBUG
    std::string src = SkShaderUtils::PrettyPrint(sksl);
#else
    const std::string& src = sksl;
#endif

    // 2. 创建 SkSL 编译器并编译
    SkSL::Compiler compiler;
    std::unique_ptr<SkSL::Program> program = compiler.convertProgram(
        programKind, src, settings
    );

    // 3. 编译失败处理
    if (!program || !(*toBackend)(*program, caps, output)) {
        errorHandler->compileError(
            src.c_str(),
            compiler.errorText().c_str(),
            /*shaderWasCached=*/false
        );
        return false;
    }

    // 4. 调试输出(条件编译控制)
    if (kPrintSkSL || kSkSLPostCompilation || printBackendSL) {
        SkShaderUtils::PrintShaderBanner(programKind);
        // ... 打印 SkSL 和后端代码 ...
    }

    // 5. 导出程序接口信息
    if (outInterface) {
        *outInterface = program->fInterface;
    }

    return true;
}
```

### 调试输出控制

模块使用多个编译时开关控制调试输出:

```cpp
#if defined(SK_PRINT_SKSL_SHADERS)
    const bool kPrintSkSL = true;
#else
    const bool kPrintSkSL = false;
#endif

const bool kSkSLPostCompilation = false;  // 手动启用

#if defined(SK_PRINT_NATIVE_SHADERS)
    const bool printBackendSL = (backendLabel != nullptr);
#else
    const bool printBackendSL = false;
#endif
```

**调试输出内容**:
- **SkSL 源码**: 编译前的美化代码
- **SkSL 后编译**: 编译器优化后的 IR 描述
- **后端代码**: 生成的 GLSL/Metal/SPIR-V 代码

### 后端代码输出

根据 `NativeShader` 的类型分别处理:

```cpp
if (printBackendSL) {
    SkDebugf("%s:\n", backendLabel);
    if (output->isBinary()) {
        // 二进制输出(如 SPIR-V)转十六进制
        const std::string asHex = SkShaderUtils::SpirvAsHexStream(output->fBinary);
        SkShaderUtils::PrintLineByLine(asHex);
    } else {
        // 文本输出(如 GLSL/Metal)
        SkShaderUtils::PrintLineByLine(output->fText);
    }
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 | 头文件 |
|------|------|--------|
| SkSL::Compiler | SkSL 编译器核心 | `src/sksl/SkSLCompiler.h` |
| SkSL::NativeShader | 后端着色器代码容器 | `src/sksl/codegen/SkSLNativeShader.h` |
| SkSL::Program | 编译后的程序表示 | `src/sksl/ir/SkSLProgram.h` |
| ShaderErrorHandler | 错误处理接口 | `include/gpu/ShaderErrorHandler.h` |
| SkShaderUtils | 着色器工具(美化、打印) | `src/utils/SkShaderUtils.h` |
| SkDebug | 调试输出 | `include/private/base/SkDebug.h` |

### 被依赖的模块

| 模块 | 关系 | 说明 |
|------|------|------|
| GrGLProgram | 使用方 | Ganesh OpenGL 程序编译 |
| GrMtlProgram | 使用方 | Ganesh Metal 程序编译 |
| GrVkProgram | 使用方 | Ganesh Vulkan 程序编译 |
| graphite::PipelineBuilder | 使用方 | Graphite 管线构建 |
| GrGLSLProgramBuilder | 使用方 | GLSL 程序构建器 |

## 设计模式与设计决策

### 1. 外观模式(Facade Pattern)

`SkSLToBackend` 作为外观,隐藏了 SkSL 编译器的复杂性:
- 统一接口,简化调用
- 集成错误处理和日志
- 封装调试功能

### 2. 策略模式(Strategy Pattern)

通过函数指针 `toBackend` 实现后端特定代码生成:

```cpp
bool (*toBackend)(SkSL::Program&, const SkSL::ShaderCaps*, SkSL::NativeShader*)
```

不同后端提供不同的实现:
- GLSL: `ToGLSL`
- Metal: `ToMetal`
- SPIR-V: `ToSPIRV`

### 3. 依赖注入

错误处理通过 `ShaderErrorHandler` 接口注入:
- 调用方决定如何处理错误(日志、UI、断言等)
- 模块不依赖具体的错误处理实现

### 4. 条件编译优化

使用宏控制调试代码:
- Release 模式下,调试代码完全不编译
- 避免运行时开销

### 5. 分离关注点

模块职责明确:
- **不负责**: 缓存管理、代码生成算法
- **负责**: 编译流程协调、错误处理、调试输出

## 性能考量

### 1. Debug vs Release 差异

**Debug 模式**:
```cpp
std::string src = SkShaderUtils::PrettyPrint(sksl);  // 额外分配和格式化
```

**Release 模式**:
```cpp
const std::string& src = sksl;  // 直接引用,无拷贝
```

### 2. 编译器开销

SkSL 编译是 CPU 密集型操作:
- 语法分析
- 类型检查
- IR 生成
- 优化 Pass
- 后端代码生成

典型编译时间: 1-10ms(取决于着色器复杂度)

### 3. 缓存策略

模块本身不实现缓存,由上层调用方负责:
- 通常使用着色器键(ScratchKey/UniqueKey)
- 避免重复编译相同的着色器

### 4. 错误处理开销

错误处理仅在失败时触发:
- 成功路径无额外开销
- 失败时格式化错误信息的开销可接受

### 5. 调试输出影响

启用调试输出会显著影响性能:
- 字符串格式化
- 控制台 I/O
- **建议**: 仅在需要时启用特定的调试宏

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/sksl/SkSLCompiler.h` | 依赖 | SkSL 编译器核心 |
| `src/sksl/codegen/SkSLGLSLCodeGenerator.h` | 相关 | GLSL 代码生成 |
| `src/sksl/codegen/SkSLMetalCodeGenerator.h` | 相关 | Metal 代码生成 |
| `src/sksl/codegen/SkSLSPIRVCodeGenerator.h` | 相关 | SPIR-V 代码生成 |
| `src/gpu/ganesh/gl/GrGLProgram.cpp` | 使用方 | OpenGL 程序编译 |
| `src/gpu/ganesh/mtl/GrMtlPipelineState.mm` | 使用方 | Metal 管线状态 |
| `src/gpu/ganesh/vk/GrVkPipeline.cpp` | 使用方 | Vulkan 管线 |
| `src/gpu/graphite/ContextUtils.cpp` | 使用方 | Graphite 着色器编译 |
| `include/gpu/ShaderErrorHandler.h` | 依赖 | 错误处理接口 |
| `src/utils/SkShaderUtils.h` | 依赖 | 着色器工具函数 |
