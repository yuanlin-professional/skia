# SkSLMetalCodeGenerator

> 源文件: src/sksl/codegen/SkSLMetalCodeGenerator.h, src/sksl/codegen/SkSLMetalCodeGenerator.cpp

## 概述

`SkSLMetalCodeGenerator` 是 Skia 图形库中负责将 SkSL（Skia Shading Language）程序转换为 Metal Shading Language（MSL）代码的核心代码生成器。Metal 是 Apple 公司为 iOS、macOS、tvOS 等平台设计的现代图形和计算 API，MSL 是其配套的着色器语言。

该代码生成器实现了从 SkSL 中间表示（IR）到 Metal 着色器代码的完整转换流程，包括类型映射、表达式转换、语句生成、函数处理、全局变量管理等功能。它是 Skia 在 Apple 平台上实现高性能图形渲染的关键组件之一。

代码生成器采用了访问者模式遍历 SkSL IR 树，逐节点生成对应的 Metal 代码。它需要处理 SkSL 和 MSL 之间的语法差异、类型系统差异以及各种平台特定的限制和优化。

## 架构位置

在 Skia 的着色器编译架构中，`SkSLMetalCodeGenerator` 位于代码生成层，是多个后端代码生成器之一：

```
SkSL 源代码 → SkSL 编译器 → SkSL IR → [代码生成器]
                                        ├─ GLSLCodeGenerator
                                        ├─ MetalCodeGenerator ← 当前模块
                                        ├─ SPIRVCodeGenerator
                                        ├─ HLSLCodeGenerator
                                        └─ RasterPipelineCodeGenerator
```

该模块与其他编译流程组件的关系：

**输入依赖：**
- `SkSL::Program`：SkSL 程序的 IR 表示
- `SkSL::Context`：编译上下文，包含类型系统和错误报告器
- `ShaderCaps`：目标平台的着色器能力和限制

**输出接口：**
- `OutputStream`：生成的 Metal 代码输出流
- `NativeShader`：统一的原生着色器结构

**协作模块：**
- `SkSLCodeGenerator`：基类，提供通用代码生成框架
- `SkSLCodeGenTypes`：类型系统映射辅助工具
- 各种 SkSL IR 节点类型：表达式、语句、类型等

## 主要类与结构体

### MetalCodeGenerator

主要的代码生成器类，继承自 `CodeGenerator`：

```cpp
class MetalCodeGenerator : public CodeGenerator {
public:
    MetalCodeGenerator(const Context* context,
                       const ShaderCaps* caps,
                       const Program* program,
                       OutputStream* out,
                       PrettyPrint pp);

    bool generateCode() override;

protected:
    // 类型转换
    std::string typeName(const Type& type);
    void writeType(const Type& type);

    // 表达式生成
    void writeExpression(const Expression& expr, Precedence parentPrecedence);
    void writeBinaryExpression(const BinaryExpression& b, Precedence parentPrecedence);
    void writeFunctionCall(const FunctionCall& c);

    // 语句生成
    void writeStatement(const Statement& s);
    void writeBlock(const Block& b);
    void writeIfStatement(const IfStatement& stmt);
    void writeForStatement(const ForStatement& f);

    // 函数处理
    void writeFunction(const FunctionDefinition& f);
    bool writeFunctionDeclaration(const FunctionDeclaration& f);

    // 全局变量和结构体
    void writeStructDefinition(const StructDefinition& s);
    void writeGlobalStruct();
    void writeUniformStruct();
    void writeInputStruct();
    void writeOutputStruct();
};
```

**核心成员变量：**

```cpp
// 保留字集合，避免命名冲突
skia_private::THashSet<std::string_view> fReservedWords;

// 接口块名称映射
skia_private::THashMap<const Type*, std::string> fInterfaceBlockNameMap;

// 函数需求标志
skia_private::THashMap<const FunctionDeclaration*, Requirements> fRequirements;

// 辅助函数集合
skia_private::THashSet<std::string> fHelpers;

// 输出格式控制
const char* fLineEnding;
int fIndentation = 0;
bool fAtLineStart = false;
PrettyPrint fPrettyPrint;
```

### Requirements 枚举

定义了函数对各种资源的需求：

```cpp
using Requirements = int;
static constexpr Requirements kNo_Requirements          = 0;
static constexpr Requirements kInputs_Requirement       = 1 << 0;   // 输入变量
static constexpr Requirements kOutputs_Requirement      = 1 << 1;   // 输出变量
static constexpr Requirements kUniforms_Requirement     = 1 << 2;   // uniform 变量
static constexpr Requirements kGlobals_Requirement      = 1 << 3;   // 全局变量
static constexpr Requirements kFragCoord_Requirement    = 1 << 4;   // 片段坐标
static constexpr Requirements kSampleMaskIn_Requirement = 1 << 5;   // 采样掩码输入
static constexpr Requirements kVertexID_Requirement     = 1 << 6;   // 顶点 ID
static constexpr Requirements kInstanceID_Requirement   = 1 << 7;   // 实例 ID
static constexpr Requirements kThreadgroups_Requirement = 1 << 8;   // 线程组
```

### GlobalStructVisitor

访问者基类，用于遍历全局结构：

```cpp
class GlobalStructVisitor {
public:
    virtual ~GlobalStructVisitor() = default;
    virtual void visitInterfaceBlock(const InterfaceBlock& block, std::string_view blockName) {}
    virtual void visitTexture(const Type& type, std::string_view name) {}
    virtual void visitSampler(const Type& type, std::string_view name) {}
    virtual void visitConstantVariable(const VarDeclaration& decl) {}
    virtual void visitNonconstantVariable(const Variable& var, const Expression* value) {}
};
```

### ThreadgroupStructVisitor

用于遍历线程组共享变量的访问者：

```cpp
class ThreadgroupStructVisitor {
public:
    virtual ~ThreadgroupStructVisitor() = default;
    virtual void visitNonconstantVariable(const Variable& var) = 0;
};
```

### IndexSubstitutionData

用于处理索引表达式替换的数据结构：

```cpp
struct IndexSubstitutionData {
    IndexSubstitutionMap fMap;              // 表达式到临时变量的映射
    StringStream fMainStream;               // 主输出流
    StringStream fPrefixStream;             // 前缀输出流
    bool fCreateSubstitutes = true;         // 是否创建替换变量
};
```

这个结构用于解决 Metal 中函数调用时索引表达式可能被多次求值的问题，通过将索引表达式的结果存储在临时变量中来避免副作用。

## 公共 API 函数

### ToMetal 函数重载

模块提供了三个 `ToMetal` 函数重载：

#### 版本 1：带格式化输出

```cpp
bool ToMetal(Program& program,
             const ShaderCaps* caps,
             OutputStream& out,
             PrettyPrint prettyPrint);
```

生成格式化的 Metal 代码，包含适当的缩进和换行。

#### 版本 2：紧凑输出

```cpp
bool ToMetal(Program& program,
             const ShaderCaps* caps,
             OutputStream& out);
```

生成紧凑的 Metal 代码，减少文件大小。内部调用版本 1，传入 `PrettyPrint::kNo`。

#### 版本 3：输出到 NativeShader

```cpp
bool ToMetal(Program& program,
             const ShaderCaps* caps,
             NativeShader* out);
```

将结果存储到 `NativeShader` 结构，用于统一的着色器接口。

### generateCode

主要的代码生成入口点：

```cpp
bool MetalCodeGenerator::generateCode() {
    // 1. 写入头部 (#include, using 声明等)
    this->writeHeader();

    // 2. 写入结构体定义
    this->writeStructDefinitions();

    // 3. 写入全局变量
    this->writeGlobalStruct();
    this->writeUniformStruct();
    this->writeInputStruct();
    this->writeOutputStruct();

    // 4. 写入函数声明和定义
    for (const ProgramElement* e : fProgram.elements()) {
        this->writeProgramElement(*e);
    }

    return true;
}
```

## 内部实现细节

### 类型映射

Metal 的类型系统与 SkSL 有所不同，代码生成器需要进行类型映射：

```cpp
std::string MetalCodeGenerator::typeName(const Type& raw) {
    const Type& type = raw.resolve().scalarTypeForLiteral();
    switch (type.typeKind()) {
        case Type::TypeKind::kVector:
            return this->typeName(type.componentType()) + std::to_string(type.columns());

        case Type::TypeKind::kMatrix:
            return this->typeName(type.componentType()) +
                   std::to_string(type.columns()) + "x" +
                   std::to_string(type.rows());

        case Type::TypeKind::kArray:
            if (type.isUnsizedArray()) {
                return String::printf("const device %s*", typeName.c_str());
            } else {
                return String::printf("array<%s, %d>", typeName.c_str(), type.columns());
            }

        case Type::TypeKind::kSampler:
            return "sampler2D";

        case Type::TypeKind::kTexture:
            return "texture2d<half>";

        case Type::TypeKind::kAtomic:
            return "atomic_uint";

        default:
            return std::string(type.name());
    }
}
```

**关键映射：**
- SkSL 向量 → Metal 向量（如 `float3`）
- SkSL 矩阵 → Metal 矩阵（如 `float3x3`）
- SkSL 数组 → Metal `array<T, N>` 或 `const device T*`
- SkSL 纹理 → Metal `texture2d<half>`
- SkSL 原子类型 → Metal `atomic_uint`

### 纹理和采样器处理

Metal 将纹理和采样器分离，而 SkSL 中它们是组合的。代码生成器需要为每个纹理变量生成两个 Metal 变量：

```cpp
// SkSL: uniform sampler2D myTexture;
// Metal:
texture2d<half> myTexture_Tex;
sampler myTexture_Smplr;
```

使用后缀 `_Tex` 和 `_Smplr` 来区分纹理和采样器。

### 保留字处理

Metal 有一些保留字与 SkSL 关键字冲突：

```cpp
fReservedWords = {"atan2", "rsqrt", "rint", "dfdx", "dfdy", "vertex", "fragment"};
```

代码生成器会检查变量名和函数名，避免使用这些保留字。

### 矩阵构造辅助函数

Metal 的矩阵构造语法与 SkSL 不同，需要生成辅助函数：

```cpp
void MetalCodeGenerator::assembleMatrixFromMatrix(const Type& sourceMatrix,
                                                   int columns,
                                                   int rows) {
    // 从一个矩阵提取元素构造另一个尺寸的矩阵
    // 例如：从 float4x4 构造 float3x3
}
```

### 运算符重载和辅助函数

Metal 不支持某些 SkSL 中的操作，需要生成辅助函数：

**矩阵相等比较：**
```cpp
void MetalCodeGenerator::writeMatrixEqualityHelpers(const Type& left, const Type& right) {
    // Metal 不支持矩阵直接比较，生成逐元素比较函数
    this->write("bool operator==(");
    this->writeType(left);
    this->write(" a, ");
    this->writeType(right);
    this->write(" b) { ... }");
}
```

**数组相等比较：**
```cpp
void MetalCodeGenerator::writeArrayEqualityHelpers(const Type& type) {
    // 生成数组比较函数
}
```

**矩阵除法：**
```cpp
void MetalCodeGenerator::writeMatrixDivisionHelpers(const Type& type) {
    // Metal 不直接支持矩阵除以标量，需要辅助函数
}
```

### 索引表达式替换

为了避免函数参数中的索引表达式被多次求值，代码生成器实现了索引替换机制：

```cpp
void MetalCodeGenerator::writeWithIndexSubstitution(const std::function<void()>& fn) {
    fIndexSubstitutionData = std::make_unique<IndexSubstitutionData>();
    fn();  // 生成代码，期间会收集需要替换的索引表达式

    // 写入临时变量声明
    this->write(fIndexSubstitutionData->fPrefixStream.str());
    // 写入主代码
    this->write(fIndexSubstitutionData->fMainStream.str());

    fIndexSubstitutionData.reset();
}
```

### 函数参数传递

Metal 需要明确指定参数的传递方式（值传递、引用传递、设备内存等）：

```cpp
void MetalCodeGenerator::writeFunctionRequirementParams(const FunctionDeclaration& f,
                                                         const char*& separator) {
    Requirements reqs = this->requirements(f);

    if (reqs & kInputs_Requirement) {
        this->write(separator);
        this->write("Inputs _in");
        separator = ", ";
    }
    if (reqs & kOutputs_Requirement) {
        this->write(separator);
        this->write("thread Outputs* _out");
        separator = ", ";
    }
    if (reqs & kUniforms_Requirement) {
        this->write(separator);
        this->write("Uniforms _uniforms");
        separator = ", ";
    }
    // ... 其他需求
}
```

### 内建变量映射

SkSL 内建变量需要映射到 Metal 的对应变量：

```cpp
// SkSL: sk_FragCoord
// Metal: _in.position (在片段着色器中)

void MetalCodeGenerator::writeFragCoord() {
    this->write("_in.position");
}
```

### 控制流语句

Metal 的控制流语法与 SkSL 基本一致，但需要注意格式化：

```cpp
void MetalCodeGenerator::writeIfStatement(const IfStatement& stmt) {
    this->write("if (");
    this->writeExpression(*stmt.test(), Precedence::kExpression);
    this->write(") ");
    this->writeStatement(*stmt.ifTrue());
    if (stmt.ifFalse()) {
        this->write(" else ");
        this->writeStatement(*stmt.ifFalse());
    }
}
```

## 依赖关系

### 头文件依赖

**核心依赖：**
```cpp
#include "src/sksl/codegen/SkSLCodeGenerator.h"     // 基类
#include "src/sksl/codegen/SkSLCodeGenTypes.h"      // 类型系统工具
#include "src/sksl/ir/SkSLProgram.h"                // SkSL 程序 IR
#include "src/sksl/SkSLContext.h"                   // 编译上下文
```

**IR 节点类型：**
```cpp
#include "src/sksl/ir/SkSLBinaryExpression.h"
#include "src/sksl/ir/SkSLBlock.h"
#include "src/sksl/ir/SkSLConstructor.h"
#include "src/sksl/ir/SkSLFunctionDefinition.h"
#include "src/sksl/ir/SkSLVariableReference.h"
// ... 等等
```

**工具类：**
```cpp
#include "src/core/SkTHash.h"                       // 哈希表
#include "src/sksl/SkSLStringStream.h"              // 字符串流
#include "src/sksl/SkSLMemoryLayout.h"              // 内存布局计算
```

### 关键外部依赖

- **SkSL 分析工具**：`SkSL::Analysis` 命名空间的各种分析函数
- **字符串处理**：`SkSL::String` 工具类
- **追踪工具**：`SkTraceEvent` 宏用于性能分析

## 设计模式与设计决策

### 访问者模式

代码生成器使用访问者模式遍历 SkSL IR 树：

```cpp
void MetalCodeGenerator::writeExpression(const Expression& expr, Precedence parentPrecedence) {
    switch (expr.kind()) {
        case Expression::Kind::kBinary:
            this->writeBinaryExpression(expr.as<BinaryExpression>(), parentPrecedence);
            break;
        case Expression::Kind::kFunctionCall:
            this->writeFunctionCall(expr.as<FunctionCall>());
            break;
        // ... 其他表达式类型
    }
}
```

### 多遍生成策略

代码生成采用多遍策略：

1. **第一遍**：收集全局信息（结构体定义、全局变量、函数声明）
2. **第二遍**：生成函数实现和主入口点

这种策略确保了所有依赖在使用前都已经声明。

### 延迟代码生成

某些辅助函数（如矩阵操作、数组比较等）只在实际使用时才生成：

```cpp
if (!fHelpers.contains("matrix_compare")) {
    fHelpers.add("matrix_compare");
    this->writeMatrixEqualityHelpers(leftType, rightType);
}
```

这减少了生成代码的大小，避免了不必要的函数定义。

### 临时流缓冲

使用多个字符串流（`StringStream`）缓冲不同部分的代码：

```cpp
StringStream fExtraFunctions;           // 辅助函数
StringStream fExtraFunctionPrototypes;  // 辅助函数原型
```

这允许代码生成器在不同的顺序生成代码片段，最后按正确顺序组装。

### 优先级处理

表达式生成时需要考虑运算符优先级，避免生成不必要的括号：

```cpp
void MetalCodeGenerator::writeBinaryExpression(const BinaryExpression& b,
                                                Precedence parentPrecedence) {
    Precedence precedence = b.getOperator().getBinaryPrecedence();
    if (precedence >= parentPrecedence) {
        this->write("(");
    }
    this->writeExpression(*b.left(), precedence);
    this->write(b.getOperator().operatorName());
    this->writeExpression(*b.right(), precedence);
    if (precedence >= parentPrecedence) {
        this->write(")");
    }
}
```

## 性能考量

### 字符串构建优化

Metal 代码以文本形式生成，涉及大量字符串操作。代码生成器使用了以下优化策略：

1. **流式输出**：使用 `OutputStream` 而不是频繁的字符串拼接
2. **字符串流缓冲**：使用 `StringStream` 减少内存分配
3. **预分配**：对于已知大小的字符串，可以预分配内存

### 避免重复生成

使用 `fHelpers` 集合跟踪已生成的辅助函数，避免重复生成：

```cpp
if (!fHelpers.contains("my_helper")) {
    fHelpers.add("my_helper");
    generateHelperFunction();
}
```

### 格式化开销

`PrettyPrint` 模式会增加生成代码的大小和生成时间。在生产环境中，可以使用紧凑模式减少开销：

- **调试模式**：使用 `PrettyPrint::kYes`，生成易读的代码
- **发布模式**：使用 `PrettyPrint::kNo`，减少文件大小

### 追踪与性能分析

代码使用性能追踪宏：

```cpp
TRACE_EVENT0("skia.shaders", "SkSL::ToMetal");
```

这允许开发者使用 Chromium 的追踪工具识别性能瓶颈。

### 内存布局计算

`SkSLMemoryLayout` 工具类用于计算 uniform 缓冲区的内存布局，这是一个相对昂贵的操作，但在代码生成阶段只执行一次。

## 相关文件

### 同级代码生成器

- `SkSLGLSLCodeGenerator.h/cpp`：生成 GLSL 代码
- `SkSLHLSLCodeGenerator.h/cpp`：生成 HLSL 代码
- `SkSLSPIRVCodeGenerator.h/cpp`：生成 SPIR-V 字节码
- `SkSLPipelineStageCodeGenerator.h/cpp`：生成流水线阶段代码
- `SkSLRasterPipelineCodeGenerator.h/cpp`：生成光栅管线代码

### 依赖的核心模块

- `src/sksl/SkSLCompiler.h/cpp`：SkSL 编译器主入口
- `src/sksl/SkSLContext.h`：编译上下文和类型系统
- `src/sksl/ir/SkSLProgram.h`：SkSL 程序 IR
- `src/sksl/codegen/SkSLCodeGenerator.h`：代码生成器基类

### IR 节点定义

- `src/sksl/ir/SkSLExpression.h`：表达式基类
- `src/sksl/ir/SkSLStatement.h`：语句基类
- `src/sksl/ir/SkSLType.h`：类型系统
- `src/sksl/ir/SkSLVariable.h`：变量定义

### 工具类

- `src/sksl/SkSLStringStream.h`：字符串流
- `src/sksl/SkSLMemoryLayout.h`：内存布局计算
- `src/sksl/SkSLString.h`：字符串工具
- `src/core/SkTHash.h`：哈希表实现

### 测试文件

- `tests/SkSLMetalTest.cpp`：Metal 代码生成单元测试
- `tests/sksl/metal/`：Metal 代码生成测试用例目录
