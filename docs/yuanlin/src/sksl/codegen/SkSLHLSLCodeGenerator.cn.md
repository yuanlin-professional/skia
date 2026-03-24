# SkSLHLSLCodeGenerator

> 源文件: src/sksl/codegen/SkSLHLSLCodeGenerator.h, src/sksl/codegen/SkSLHLSLCodeGenerator.cpp

## 概述

`SkSLHLSLCodeGenerator` 是 Skia 图形库中用于将 SkSL（Skia Shading Language）程序转换为 HLSL（High-Level Shading Language）代码的代码生成器。HLSL 是 Microsoft DirectX 的着色器语言，主要用于 Windows 平台的图形渲染。

该模块的核心功能是将 SkSL 中间表示（IR）转换为可在 DirectX 图形 API 上运行的 HLSL 代码。实现策略是先将 SkSL 编译为 SPIR-V 中间格式，然后再通过 SPIR-V 到 HLSL 的转换器生成最终的 HLSL 代码。这种两步转换的设计简化了代码生成逻辑，充分利用了现有的 SPIR-V 生态系统工具。

此代码生成器支持可选的 SPIR-V 验证功能，允许在转换过程中验证生成的 SPIR-V 代码的正确性，从而提高代码质量和可靠性。

## 架构位置

在 Skia 的着色器编译架构中，`SkSLHLSLCodeGenerator` 位于代码生成层（codegen layer），属于后端代码生成器之一。其在编译流水线中的位置如下：

```
SkSL 源代码 → SkSL 编译器 → SkSL IR → [各种代码生成器]
                                        ├─ GLSLCodeGenerator
                                        ├─ MetalCodeGenerator
                                        ├─ SPIRVCodeGenerator
                                        ├─ HLSLCodeGenerator ← 当前模块
                                        └─ 其他后端
```

该模块依赖于：
- `SkSLSPIRVCodeGenerator`：用于生成 SPIR-V 中间代码
- `SkSLSPIRVtoHLSL`：执行 SPIR-V 到 HLSL 的转换
- `SkSLProgram`：输入的 SkSL 程序 IR 表示
- `ShaderCaps`：描述目标平台的着色器能力

该模块被上层模块（如 `SkSLToBackend`）调用，作为统一着色器编译接口的一部分。

## 主要类与结构体

### ValidateSPIRVProc

```cpp
using ValidateSPIRVProc = bool (*)(ErrorReporter&, SkSpan<const uint32_t>);
```

这是一个函数指针类型，用于定义 SPIR-V 验证回调函数的签名。验证函数接收错误报告器和 SPIR-V 字节码，返回验证是否成功。

### ToHLSL 函数重载

模块提供了三个 `ToHLSL` 函数重载，支持不同的输出方式：

#### 版本 1：输出到流

```cpp
bool ToHLSL(Program& program,
            const ShaderCaps* caps,
            OutputStream& out,
            ValidateSPIRVProc = nullptr);
```

将 SkSL 程序转换为 HLSL 代码并写入输出流。

**参数说明：**
- `program`：输入的 SkSL 程序
- `caps`：目标平台的着色器能力描述
- `out`：输出流对象
- `ValidateSPIRVProc`：可选的 SPIR-V 验证回调函数

**返回值：** 转换是否成功

#### 版本 2：输出到字符串

```cpp
bool ToHLSL(Program& program,
            const ShaderCaps* caps,
            std::string* out,
            ValidateSPIRVProc);
```

将 SkSL 程序转换为 HLSL 代码并存储在字符串中。这是实际执行转换逻辑的核心版本。

#### 版本 3：输出到 NativeShader

```cpp
inline bool ToHLSL(Program& program,
                   const ShaderCaps* caps,
                   NativeShader* out);
```

这是一个内联便捷函数，将结果存储到 `NativeShader` 结构体的文本字段中。此版本专门为 `SkSLToBackend` 统一接口设计。

## 公共 API 函数

### ToHLSL (流版本)

将 SkSL 程序编译为 HLSL 并输出到流：

```cpp
bool ToHLSL(Program& program,
            const ShaderCaps* caps,
            OutputStream& out,
            ValidateSPIRVProc validateSPIRV) {
    TRACE_EVENT0("skia.shaders", "SkSL::ToHLSL");
    std::string hlsl;
    if (!ToHLSL(program, caps, &hlsl, validateSPIRV)) {
        return false;
    }
    out.writeString(hlsl);
    return true;
}
```

这个版本内部调用字符串版本，然后将结果写入流，实现了代码复用。

### ToHLSL (字符串版本)

实际执行转换的核心函数：

```cpp
bool ToHLSL(Program& program,
            const ShaderCaps* caps,
            std::string* out,
            ValidateSPIRVProc validateSPIRV) {
    std::vector<uint32_t> spirv;
    if (!ToSPIRV(program, caps, &spirv, validateSPIRV)) {
        return false;
    }
    SPIRVtoHLSL(spirv, out);
    return true;
}
```

**实现步骤：**
1. 创建 SPIR-V 字节码容器
2. 调用 `ToSPIRV` 将 SkSL 程序编译为 SPIR-V，并可选地验证
3. 调用 `SPIRVtoHLSL` 将 SPIR-V 转换为 HLSL 代码
4. 返回转换结果

## 内部实现细节

### 两步转换策略

HLSL 代码生成采用了间接转换策略：

```
SkSL → SPIR-V → HLSL
```

这种设计有以下优势：
1. **代码复用**：复用已有的 `SPIRVCodeGenerator`，减少重复开发
2. **标准化中间格式**：SPIR-V 是 Khronos 标准，有完善的工具链支持
3. **简化维护**：只需维护 SPIR-V 到 HLSL 的转换逻辑，而不是直接从 SkSL 生成 HLSL
4. **验证能力**：可以在中间阶段验证 SPIR-V 的正确性

### SPIR-V 验证

模块支持可选的 SPIR-V 验证步骤。验证函数通过 `ValidateSPIRVProc` 回调传入，允许外部调用者在转换过程中插入验证逻辑。这对于调试和确保生成代码的正确性非常有用。

### 错误处理

转换过程中的错误通过返回值传递。如果 SPIR-V 生成或 SPIR-V 到 HLSL 的转换失败，函数返回 `false`，具体错误信息会通过 `Program` 的 `ErrorReporter` 报告。

## 依赖关系

### 头文件依赖

```cpp
#include "include/core/SkSpan.h"           // 数组视图
#include "src/sksl/codegen/SkSLNativeShader.h"  // 原生着色器结构
#include "src/sksl/codegen/SkSLSPIRVCodeGenerator.h"  // SPIR-V 生成器
#include "src/sksl/codegen/SkSLSPIRVtoHLSL.h"  // SPIR-V 到 HLSL 转换器
#include "src/sksl/ir/SkSLProgram.h"       // SkSL 程序 IR
```

### 关键外部函数

- `ToSPIRV()`：将 SkSL 程序编译为 SPIR-V 字节码
- `SPIRVtoHLSL()`：将 SPIR-V 字节码转换为 HLSL 文本代码

### 运行时依赖

- `ShaderCaps`：用于查询目标平台的着色器能力和限制
- `ErrorReporter`：用于报告编译和转换过程中的错误

## 设计模式与设计决策

### 适配器模式

`ToHLSL` 函数充当了适配器角色，将 SPIR-V 生成器和 SPIR-V 到 HLSL 转换器组合起来，对外提供统一的 SkSL 到 HLSL 转换接口。

### 函数重载与便捷接口

模块提供了多个 `ToHLSL` 重载版本，满足不同的使用场景：
- 流输出版本：适合直接写入文件或网络流
- 字符串输出版本：适合需要进一步处理 HLSL 代码的场景
- `NativeShader` 版本：统一后端接口，简化上层调用

### 内联优化

`NativeShader` 版本使用 `inline` 关键字，允许编译器内联展开，减少函数调用开销。这在频繁调用的场景下可以提升性能。

### 跟踪与性能分析

代码使用 `TRACE_EVENT0` 宏进行性能跟踪：

```cpp
TRACE_EVENT0("skia.shaders", "SkSL::ToHLSL");
```

这允许开发者使用 Chromium 的跟踪工具分析 HLSL 代码生成的性能瓶颈。

## 性能考量

### 两步转换的开销

虽然 SkSL → SPIR-V → HLSL 的两步转换会引入额外的转换开销，但在实际应用中，这种开销是可以接受的，因为：

1. **一次性开销**：着色器编译通常在初始化时执行一次，不在渲染热路径上
2. **转换速度快**：SPIR-V 和 HLSL 都是结构化的中间格式，转换算法相对高效
3. **缓存策略**：生成的 HLSL 代码可以被缓存，避免重复编译

### 内存分配

转换过程中需要分配内存存储 SPIR-V 字节码和 HLSL 文本。对于大型着色器程序，这可能会产生明显的内存分配开销。实现使用了 `std::vector<uint32_t>` 和 `std::string`，利用了标准库的内存管理优化。

### 字符串操作

HLSL 代码以字符串形式生成，涉及大量的字符串拼接操作。使用 `std::string` 的自动内存管理可以简化实现，但在极端性能敏感的场景下，可以考虑使用预分配的字符串缓冲区优化。

## 相关文件

### 同目录代码生成器

- `SkSLGLSLCodeGenerator.h/cpp`：生成 GLSL 代码
- `SkSLMetalCodeGenerator.h/cpp`：生成 Metal 着色器语言代码
- `SkSLSPIRVCodeGenerator.h/cpp`：生成 SPIR-V 字节码
- `SkSLPipelineStageCodeGenerator.h/cpp`：生成流水线阶段代码
- `SkSLRasterPipelineCodeGenerator.h/cpp`：生成光栅管线代码

### 依赖的工具模块

- `SkSLSPIRVtoHLSL.h/cpp`：SPIR-V 到 HLSL 转换器
- `SkSLNativeShader.h`：原生着色器数据结构定义

### 上层调用者

- `SkSLCompiler.h/cpp`：SkSL 编译器主模块
- 各种着色器效果实现，通过统一接口调用 HLSL 代码生成

### 测试与验证

- `tests/SkSLTest.cpp`：SkSL 编译器单元测试
- `tests/sksl/`：包含各种 SkSL 测试用例，验证不同后端的代码生成正确性
