# SkSLPipelineStageCodeGenerator

> 源文件: src/sksl/codegen/SkSLPipelineStageCodeGenerator.h, src/sksl/codegen/SkSLPipelineStageCodeGenerator.cpp

## 概述

`SkSLPipelineStageCodeGenerator` 是 Skia 图形库中用于将 SkSL 程序转换为片段处理器（Fragment Processor）和其他流水线阶段代码的专用代码生成器。与其他后端生成器（如 Metal、GLSL、HLSL）不同，Pipeline Stage 代码生成器不是生成完整的独立着色器程序，而是生成可以嵌入到 Skia 渲染流水线中的代码片段。

该模块的主要用途是支持 Skia 的动态效果系统，允许用户定义的着色器、颜色滤镜和混合器被编译并集成到 Skia 的渲染流水线中。生成的代码需要与宿主环境（通常是 C++ 代码）进行交互，因此代码生成器提供了一套回调接口（`Callbacks`），允许调用者自定义变量声明、函数定义、子效果采样等行为。

该生成器还支持函数特化（specialization）机制，可以针对特定参数值生成优化的函数变体，特别是当子效果（child effects）作为参数传递时。

## 架构位置

在 Skia 的着色器编译架构中，`SkSLPipelineStageCodeGenerator` 位于代码生成层，但与其他后端生成器有所不同：

```
SkSL 源代码 → SkSL 编译器 → SkSL IR → [代码生成器]
                                        ├─ Metal/GLSL/HLSL/SPIR-V (完整着色器)
                                        └─ PipelineStageCodeGenerator (代码片段) ← 当前模块
                                                    ↓
                                        嵌入到 Skia 渲染流水线
                                                    ↓
                                        GrFragmentProcessor/GrBlender/等
```

**上游依赖：**
- `SkSL::Program`：输入的 SkSL 程序 IR
- `SkSL::Context`：编译上下文和类型系统
- `Analysis::SpecializationInfo`：函数特化分析结果

**下游使用者：**
- `GrFragmentProcessor`：片段处理器
- `GrColorFilter`：颜色滤镜
- `GrBlender`：混合器
- 其他 Skia 效果组件

**协作模块：**
- `SkSL::Analysis`：提供特化分析工具
- 各种 SkSL IR 节点类型

## 主要类与结构体

### PipelineStage::Callbacks

回调接口，允许调用者自定义代码生成行为：

```cpp
class Callbacks {
public:
    virtual ~Callbacks() = default;

    // 获取主函数名称
    virtual std::string getMainName() { return "main"; }

    // 获取重整后的名称（名称修饰，避免冲突）
    virtual std::string getMangledName(const char* name) { return name; }

    // 定义函数
    virtual void defineFunction(const char* declaration, const char* body, bool isMain) = 0;

    // 声明函数
    virtual void declareFunction(const char* declaration) = 0;

    // 定义结构体
    virtual void defineStruct(const char* definition) = 0;

    // 声明全局变量
    virtual void declareGlobal(const char* declaration) = 0;

    // 声明 uniform 变量
    virtual std::string declareUniform(const VarDeclaration*) = 0;

    // 采样子效果
    virtual std::string sampleShader(int index, std::string coords) = 0;
    virtual std::string sampleColorFilter(int index, std::string color) = 0;
    virtual std::string sampleBlender(int index, std::string src, std::string dst) = 0;

    // 颜色空间转换
    virtual std::string toLinearSrgb(std::string color) = 0;
    virtual std::string fromLinearSrgb(std::string color) = 0;
};
```

这个接口是 Pipeline Stage 代码生成器的核心抽象，它将代码生成的具体细节委托给调用者。

### PipelineStageCodeGenerator

内部代码生成器类，不直接暴露给外部：

```cpp
class PipelineStageCodeGenerator {
public:
    PipelineStageCodeGenerator(const Program& program,
                               const char* sampleCoords,
                               const char* inputColor,
                               const char* destColor,
                               Callbacks* callbacks);

    void generateCode();

private:
    // 表达式和语句生成
    void writeExpression(const Expression& expr, Precedence parentPrecedence);
    void writeStatement(const Statement& s);

    // 特殊表达式处理
    void writeChildCall(const ChildCall& c);
    void writeFunctionCall(const FunctionCall& c);
    void writeVariableReference(const VariableReference& ref);

    // 函数处理
    void writeFunction(const FunctionDefinition& f);
    std::string functionName(const FunctionDeclaration& decl,
                             Analysis::SpecializationIndex specIndex);

    // 全局元素处理
    void writeGlobalVarDeclaration(const GlobalVarDeclaration& g);
    void writeStructDefinition(const StructDefinition& s);

    // 特化支持
    void forEachSpecialization(const FunctionDeclaration& decl, const std::function<void()>& fn);

    // 成员变量
    const Program& fProgram;
    const char* fSampleCoords;      // 采样坐标替换字符串
    const char* fInputColor;        // 输入颜色替换字符串
    const char* fDestColor;         // 目标颜色替换字符串
    Callbacks* fCallbacks;

    // 特化信息
    Analysis::SpecializationInfo fSpecializationInfo;
    Analysis::SpecializationIndex fActiveSpecializationIndex;
    const Analysis::SpecializedParameters* fActiveSpecialization;

    // 名称映射
    THashMap<const Variable*, std::string> fVariableNames;
    THashMap<const Type*, std::string> fStructNames;
    THashMap<Analysis::SpecializedFunctionKey, std::string,
             Analysis::SpecializedFunctionKey::Hash> fFunctionNames;

    StringStream* fBuffer;
    bool fCastReturnsToHalf;
    const FunctionDeclaration* fCurrentFunction;
};
```

## 公共 API 函数

### ConvertProgram

主要的公共接口函数：

```cpp
void ConvertProgram(const Program& program,
                    const char* sampleCoords,
                    const char* inputColor,
                    const char* destColor,
                    Callbacks* callbacks);
```

**参数说明：**

- `program`：要转换的 SkSL 程序
- `sampleCoords`：用于替换 `sk_FragCoord` 或坐标参数的字符串（如 `"_coords"`）
- `inputColor`：用于替换输入颜色内建变量的字符串（如 `"_inColor"`）
- `destColor`：用于替换目标颜色内建变量的字符串（如 `"_dstColor"`，用于混合器）
- `callbacks`：回调接口实现，用于自定义代码生成行为

**工作流程：**

1. 创建 `PipelineStageCodeGenerator` 实例
2. 调用 `generateCode()` 遍历 SkSL IR
3. 通过回调接口生成代码片段
4. 调用者收集生成的代码并嵌入到宿主环境

## 内部实现细节

### 内建变量替换

Pipeline Stage 代码生成器的一个关键功能是替换 SkSL 的内建变量：

```cpp
void PipelineStageCodeGenerator::writeVariableReference(const VariableReference& ref) {
    const Variable* var = ref.variable();

    // 替换主函数的坐标参数
    if (fCurrentFunction && var == fCurrentFunction->getMainCoordsParameter()) {
        this->write(fSampleCoords);
        return;
    }

    // 替换输入颜色参数
    if (fCurrentFunction && var == fCurrentFunction->getMainInputColorParameter()) {
        this->write(fInputColor);
        return;
    }

    // 替换目标颜色参数
    if (fCurrentFunction && var == fCurrentFunction->getMainDestColorParameter()) {
        this->write(fDestColor);
        return;
    }

    // 使用映射的名称或原始名称
    std::string* name = fVariableNames.find(var);
    this->write(name ? *name : var->name());
}
```

这使得生成的代码可以使用调用者指定的变量名，而不是 SkSL 的内建变量名。

### 子效果调用处理

子效果（child effects）的调用需要特殊处理：

```cpp
void PipelineStageCodeGenerator::writeChildCall(const ChildCall& c) {
    const Variable* child = &c.child();

    // 如果函数被特化，查找特化后的子效果
    if (fActiveSpecialization) {
        const Expression** specializedChild = fActiveSpecialization->find(child);
        if (specializedChild) {
            child = (*specializedChild)->as<VariableReference>().variable();
        }
    }

    // 找到子效果的索引
    int index = 0;
    for (const ProgramElement* p : fProgram.elements()) {
        if (p->is<GlobalVarDeclaration>()) {
            const GlobalVarDeclaration& global = p->as<GlobalVarDeclaration>();
            const VarDeclaration& decl = global.varDeclaration();
            if (decl.var() == child) {
                break;
            } else if (decl.var()->type().isEffectChild()) {
                ++index;
            }
        }
    }

    // 根据子效果类型调用相应的回调
    const ExpressionArray& arguments = c.arguments();
    switch (c.child().type().typeKind()) {
        case Type::TypeKind::kShader: {
            // 着色器需要坐标参数
            AutoOutputBuffer exprBuffer(this);
            this->writeExpression(*arguments[0], Precedence::kSequence);
            std::string sampleOutput = fCallbacks->sampleShader(index, exprBuffer.fBuffer.str());
            this->write(sampleOutput);
            break;
        }
        case Type::TypeKind::kColorFilter: {
            // 颜色滤镜需要颜色参数
            AutoOutputBuffer exprBuffer(this);
            this->writeExpression(*arguments[0], Precedence::kSequence);
            std::string sampleOutput = fCallbacks->sampleColorFilter(index, exprBuffer.fBuffer.str());
            this->write(sampleOutput);
            break;
        }
        case Type::TypeKind::kBlender: {
            // 混合器需要两个颜色参数
            AutoOutputBuffer exprBuffer1(this);
            this->writeExpression(*arguments[0], Precedence::kSequence);
            AutoOutputBuffer exprBuffer2(this);
            this->writeExpression(*arguments[1], Precedence::kSequence);
            std::string sampleOutput = fCallbacks->sampleBlender(
                index, exprBuffer1.fBuffer.str(), exprBuffer2.fBuffer.str());
            this->write(sampleOutput);
            break;
        }
    }
}
```

### 函数特化

函数特化允许为特定参数值生成优化的函数变体：

```cpp
void PipelineStageCodeGenerator::forEachSpecialization(
        const FunctionDeclaration& decl,
        const std::function<void()>& fn) {
    // 保存当前特化状态
    Analysis::SpecializationIndex prevSpecializationIndex = fActiveSpecializationIndex;
    const Analysis::SpecializedParameters* prevSpecialization = fActiveSpecialization;

    if (const Analysis::Specializations* specializations =
                fSpecializationInfo.fSpecializationMap.find(&decl)) {
        // 为每个特化版本调用回调
        for (fActiveSpecializationIndex = 0;
             fActiveSpecializationIndex < specializations->size();
             ++fActiveSpecializationIndex) {
            fActiveSpecialization = &specializations->at(fActiveSpecializationIndex);
            fn();
        }
    } else {
        // 函数没有特化，正常生成
        fActiveSpecializationIndex = Analysis::kUnspecialized;
        fActiveSpecialization = nullptr;
        fn();
    }

    // 恢复先前的特化状态
    fActiveSpecializationIndex = prevSpecializationIndex;
    fActiveSpecialization = prevSpecialization;
}
```

**特化的函数命名：**

```cpp
std::string PipelineStageCodeGenerator::functionName(
        const FunctionDeclaration& decl,
        Analysis::SpecializationIndex specIndex) {
    if (decl.isMain()) {
        return std::string(fCallbacks->getMainName());
    }

    if (decl.isIntrinsic() || decl.moduleType() == ModuleType::sksl_shared) {
        return std::string(decl.name());
    }

    // 为特化版本生成唯一名称
    std::string specializedName = std::string(decl.name());
    Analysis::GetParameterMappingsForFunction(
        decl, fSpecializationInfo, specIndex,
        [&](int, const Variable*, const Expression* expr) {
            specializedName += '_';
            specializedName += expr->description();
        });

    return fCallbacks->getMangledName(specializedName.c_str());
}
```

### 函数调用处理

函数调用需要考虑特化参数：

```cpp
void PipelineStageCodeGenerator::writeFunctionCall(const FunctionCall& c) {
    const FunctionDeclaration& function = c.function();

    // 处理颜色空间转换内建函数
    if (function.intrinsicKind() == IntrinsicKind::k_toLinearSrgb_IntrinsicKind) {
        AutoOutputBuffer exprBuffer(this);
        this->writeExpression(*c.arguments()[0], Precedence::kSequence);
        this->write(fCallbacks->toLinearSrgb(exprBuffer.fBuffer.str()));
        return;
    }

    // 查找调用点的特化索引
    Analysis::SpecializationIndex callIndex =
        Analysis::FindSpecializationIndexForCall(c, fSpecializationInfo, fActiveSpecializationIndex);

    // 查找特化参数
    SkBitSet specializedParams =
        Analysis::FindSpecializedParametersForFunction(function, fSpecializationInfo);

    // 写入函数名
    this->write(this->functionName(function, callIndex));
    this->write("(");

    // 写入参数，跳过特化的参数
    auto separator = SkSL::String::Separator();
    for (int argIdx = 0; argIdx < c.arguments().size(); ++argIdx) {
        if (specializedParams.test(argIdx)) {
            continue;  // 跳过特化参数
        }
        this->write(separator());
        this->writeExpression(*c.arguments()[argIdx], Precedence::kSequence);
    }
    this->write(")");
}
```

### uniform 变量处理

uniform 变量的声明委托给回调接口：

```cpp
void PipelineStageCodeGenerator::writeGlobalVarDeclaration(const GlobalVarDeclaration& g) {
    const VarDeclaration& decl = g.varDeclaration();
    const Variable& var = *decl.var();

    if (var.isBuiltin() || var.type().isOpaque()) {
        // 不重新声明内建变量和不透明类型
    } else if (var.modifierFlags().isUniform()) {
        // 通过回调声明 uniform
        std::string uniformName = fCallbacks->declareUniform(&decl);
        fVariableNames.set(&var, std::move(uniformName));
    } else {
        // 通过回调声明全局变量
        std::string mangledName = fCallbacks->getMangledName(std::string(var.name()).c_str());
        std::string declaration = this->modifierString(var.modifierFlags()) +
                                  this->typedVariable(var.type(), mangledName);
        if (decl.value()) {
            AutoOutputBuffer outputToBuffer(this);
            this->writeExpression(*decl.value(), Precedence::kExpression);
            declaration += " = ";
            declaration += outputToBuffer.fBuffer.str();
        }
        declaration += ";\n";
        fCallbacks->declareGlobal(declaration.c_str());
        fVariableNames.set(&var, std::move(mangledName));
    }
}
```

### 返回值类型转换

主函数的返回值可能需要类型转换：

```cpp
void PipelineStageCodeGenerator::writeReturnStatement(const ReturnStatement& r) {
    this->write("return");
    if (r.expression()) {
        this->write(" ");
        if (fCastReturnsToHalf) {
            this->write("half4(");
        }
        this->writeExpression(*r.expression(), Precedence::kExpression);
        if (fCastReturnsToHalf) {
            this->write(")");
        }
    }
    this->write(";");
}
```

这确保即使用户的 SkSL 代码返回 `float4`，生成的代码也会转换为 `half4`（如果需要）。

### 两遍生成策略

代码生成采用两遍策略：

```cpp
void PipelineStageCodeGenerator::generateCode() {
    // 查找需要特化的函数
    Analysis::FindFunctionsToSpecialize(fProgram, &fSpecializationInfo, [](const Variable& param) {
        return param.type().isEffectChild();
    });

    // 第一遍：声明全局变量、结构体、函数原型
    for (const ProgramElement* e : fProgram.elements()) {
        this->writeProgramElementFirstPass(*e);
    }

    // 第二遍：定义函数
    for (const ProgramElement* e : fProgram.elements()) {
        this->writeProgramElementSecondPass(*e);
    }
}
```

这确保所有依赖在使用前都已经声明。

## 依赖关系

### 核心依赖

```cpp
#include "src/sksl/ir/SkSLProgram.h"            // SkSL 程序 IR
#include "src/sksl/analysis/SkSLSpecialization.h"  // 函数特化分析
#include "src/sksl/SkSLStringStream.h"          // 字符串流
```

### IR 节点依赖

```cpp
#include "src/sksl/ir/SkSLBinaryExpression.h"
#include "src/sksl/ir/SkSLChildCall.h"
#include "src/sksl/ir/SkSLFunctionCall.h"
#include "src/sksl/ir/SkSLVarDeclarations.h"
#include "src/sksl/ir/SkSLVariableReference.h"
// ... 等等
```

### 工具类依赖

```cpp
#include "src/core/SkTHash.h"                   // 哈希表
#include "src/utils/SkBitSet.h"                 // 位集合
#include "src/sksl/SkSLString.h"                // 字符串工具
```

## 设计模式与设计决策

### 策略模式（通过回调接口）

`Callbacks` 接口实现了策略模式，允许调用者自定义代码生成策略。这使得同一个代码生成器可以为不同的目标环境生成代码：

- **片段处理器**：生成嵌入到 Ganesh 渲染器的代码
- **颜色滤镜**：生成颜色变换代码
- **混合器**：生成混合操作代码

### 模板方法模式

`generateCode()` 定义了代码生成的整体流程，但将具体步骤委托给虚函数和回调：

```cpp
void generateCode() {
    分析特化信息();
    第一遍生成();
    第二遍生成();
}
```

### 访问者模式

与其他代码生成器类似，使用访问者模式遍历 SkSL IR 树。

### 命名空间分离

使用 `PipelineStage` 命名空间将此代码生成器与其他后端分离：

```cpp
namespace SkSL {
namespace PipelineStage {
    void ConvertProgram(...);
    class Callbacks { ... };
}
}
```

### 输出缓冲

使用 `AutoOutputBuffer` RAII 辅助类临时切换输出流：

```cpp
struct AutoOutputBuffer {
    AutoOutputBuffer(PipelineStageCodeGenerator* generator) : fGenerator(generator) {
        fOldBuffer = fGenerator->fBuffer;
        fGenerator->fBuffer = &fBuffer;
    }
    ~AutoOutputBuffer() {
        fGenerator->fBuffer = fOldBuffer;
    }
    StringStream fBuffer;
};
```

这允许表达式被生成到临时缓冲区，然后以字符串形式传递给回调。

## 性能考量

### 特化的权衡

函数特化可以生成更优化的代码，但会增加代码生成时间和最终代码大小：

- **优势**：消除动态分支，减少参数传递开销
- **劣势**：增加代码大小，可能影响指令缓存效率

Skia 仅对传递子效果的函数进行特化，这是一个平衡的选择。

### 字符串操作

代码生成涉及大量字符串操作。使用 `StringStream` 和 `std::string` 简化了实现，但在性能敏感场景下可能成为瓶颈。

### 回调开销

通过回调接口生成代码会引入函数调用开销，但这在代码生成阶段（非渲染热路径）是可以接受的。

### 名称映射

使用哈希表（`THashMap`）存储变量和函数名称映射，提供 O(1) 的查找性能。

## 相关文件

### 同级代码生成器

- `SkSLMetalCodeGenerator.h/cpp`：生成 Metal 代码
- `SkSLGLSLCodeGenerator.h/cpp`：生成 GLSL 代码
- `SkSLSPIRVCodeGenerator.h/cpp`：生成 SPIR-V 字节码
- `SkSLRasterPipelineCodeGenerator.h/cpp`：生成光栅管线代码

### 依赖的分析工具

- `src/sksl/analysis/SkSLSpecialization.h/cpp`：函数特化分析

### 使用者

- `src/gpu/ganesh/GrFragmentProcessor.h/cpp`：片段处理器
- `src/gpu/ganesh/effects/`：各种 GPU 效果实现
- `src/effects/`：各种效果实现

### IR 定义

- `src/sksl/ir/SkSLProgram.h`：SkSL 程序
- `src/sksl/ir/SkSLChildCall.h`：子效果调用表达式
- `src/sksl/ir/SkSLVarDeclarations.h`：变量声明

### 测试

- `tests/SkSLPipelineStageTest.cpp`：Pipeline Stage 代码生成测试
- `tests/sksl/`：各种测试用例
