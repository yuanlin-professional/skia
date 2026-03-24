# SkSL Analysis - 着色器语言静态分析通道

## 概述

`src/sksl/analysis` 目录包含了 SkSL（Skia Shading Language）编译器的**静态分析**基础设施与具体分析通道。SkSL 是 Skia 图形库所使用的着色器语言，其语法与 GLSL 类似，但增加了对 Skia 渲染管线的特定支持。静态分析是编译器在不实际执行程序的情况下，对程序中间表示（IR）进行检查和信息提取的过程。

本目录提供了两类核心功能：第一，通用的 IR 遍历基础设施（`ProgramVisitor` 和 `ProgramUsage`），它们是所有分析和变换通道的基石；第二，一系列具体的分析通道，用于验证程序正确性、提取优化信息以及执行语义检查。这些分析通道直接服务于 SkSL 编译器的各个阶段，包括前端类型检查、中间优化以及后端代码生成。

所有分析函数均为只读操作——它们检查 IR 树但不修改它。分析结果通常以布尔值或信息结构体的形式返回，供编译器的后续阶段使用。这些分析函数的公共接口统一声明在 `src/sksl/SkSLAnalysis.h` 的 `Analysis` 命名空间中，而具体实现则分散在本目录的各个 `.cpp` 文件中。

分析通道覆盖了广泛的语义检查场景，包括但不限于：控制流分析（函数是否总能返回值）、循环结构验证（循环能否安全展开）、表达式属性判定（是否为编译时常量、是否有副作用）、程序使用情况统计（变量和函数的引用计数），以及用于函数特化的参数匹配分析。这些分析在保障 SkSL 程序正确性与生成高效目标代码方面发挥着不可替代的作用。

## 架构图

```
+-----------------------------------------------------------------------------------+
|                           SkSL 编译器分析子系统                                      |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +---------------------------+        +------------------------------------+      |
|  |   SkSLAnalysis.h          |        |   TProgramVisitor<T> (模板基类)      |      |
|  |   (公共 API 声明)          |        |   - visitExpression()              |      |
|  |   namespace Analysis      |------->|   - visitStatement()               |      |
|  +---------------------------+        |   - visitProgramElement()          |      |
|                                       +----------------+-------------------+      |
|                                                        |                          |
|                                  +---------------------+---------------------+    |
|                                  |                                           |    |
|                    +-------------v-----------+             +-----------------v-+  |
|                    | ProgramVisitor           |             | ProgramUsage      |  |
|                    | (只读遍历, const IR)      |             | (使用情况统计)     |  |
|                    | - visit(Program&)        |             | - fVariableCounts |  |
|                    +-------------+------------+             | - fCallCounts     |  |
|                                  |                          | - fStructCounts   |  |
|                 +----------------+----------------+         +---------+---------+  |
|                 |                |                 |                   |            |
|    +------------v--+ +---------v-------+ +-------v--------+         |            |
|    | 正确性检查      | | 表达式属性分析    | | 控制流分析       |         |            |
|    |                | |                  | |                |         |            |
|    | CheckProgram   | | IsConstant       | | CanExitWithout | <-------+            |
|    |  Structure     | |  Expression      | |  ReturningValue|                      |
|    | CheckSymbol    | | IsTrivial        | | GetReturnCompl |                      |
|    |  TableCorrect  | |  Expression      | |  exity         |                      |
|    | Finalization   | | HasSideEffects   | | GetLoopUnroll  |                      |
|    |  Checks        | | IsSameExpression | |  Info          |                      |
|    |                | |  Tree            | | SwitchCase     |                      |
|    |                | | IsDynamically    | |  ContainsExit  |                      |
|    |                | |  Uniform         | | GetLoopControl |                      |
|    |                | | ReturnsInput     | |  FlowInfo      |                      |
|    |                | |  Alpha           | |                |                      |
|    +----------------+ +------------------+ +----------------+                      |
|                                                                                   |
|    +--------------------------------------------------+                           |
|    | 函数特化分析 (Specialization)                       |                           |
|    | - FindFunctionsToSpecialize()                     |                           |
|    | - FindSpecializationIndexForCall()                |                           |
|    | - FindSpecializedParametersForFunction()          |                           |
|    | - GetParameterMappingsForFunction()               |                           |
|    +--------------------------------------------------+                           |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## 目录结构

```
src/sksl/analysis/
|-- BUILD.bazel                              # Bazel 构建规则
|-- SkSLProgramVisitor.h                     # IR 遍历基类模板 TProgramVisitor
|-- SkSLProgramUsage.h                       # 程序使用情况统计类声明
|-- SkSLProgramUsage.cpp                     # 程序使用情况统计实现
|-- SkSLNoOpErrorReporter.h                  # 静默错误报告器
|-- SkSLSpecialization.h                     # 函数特化分析声明
|-- SkSLSpecialization.cpp                   # 函数特化分析实现
|-- SkSLSymbolTableStackBuilder.cpp          # 符号表栈管理工具
|-- SkSLCanExitWithoutReturningValue.cpp     # 函数返回路径完整性检查
|-- SkSLCheckProgramStructure.cpp            # 程序结构检查 (递归/调用深度)
|-- SkSLCheckSymbolTableCorrectness.cpp      # 符号表正确性验证
|-- SkSLFinalizationChecks.cpp               # 最终化阶段检查
|-- SkSLGetLoopControlFlowInfo.cpp           # 循环控制流信息获取
|-- SkSLGetLoopUnrollInfo.cpp                # 循环展开信息提取
|-- SkSLGetReturnComplexity.cpp              # 函数返回复杂度分析
|-- SkSLHasSideEffects.cpp                   # 表达式副作用检测
|-- SkSLIsConstantExpression.cpp             # 常量表达式判定
|-- SkSLIsDynamicallyUniformExpression.cpp   # 动态一致性表达式判定
|-- SkSLIsSameExpressionTree.cpp             # 表达式树等价性判定
|-- SkSLIsTrivialExpression.cpp              # 平凡表达式判定
|-- SkSLReturnsInputAlpha.cpp                # 输入 Alpha 通道保持检查
|-- SkSLSwitchCaseContainsExit.cpp           # switch-case 退出语句检测
```

## 关键类与函数

### TProgramVisitor<T> (SkSLProgramVisitor.h)

这是 SkSL 分析子系统中最核心的基类模板。它实现了对 IR 树的深度优先遍历，支持三种粒度的访问回调：

- `visitExpression()` -- 访问表达式节点
- `visitStatement()` -- 访问语句节点
- `visitProgramElement()` -- 访问程序顶层元素

模板参数 `T` 控制访问的是 `const` IR（只读分析）还是可变 IR（可修改的变换）。访问函数返回 `bool`：当返回 `true` 时，递归立即终止并向上传播 `true`，这为"搜索特定模式后立即停止"提供了便捷的短路机制。

```cpp
template <typename T>
class TProgramVisitor {
protected:
    virtual bool visitExpression(typename T::Expression& expression);
    virtual bool visitStatement(typename T::Statement& statement);
    virtual bool visitProgramElement(typename T::ProgramElement& programElement);
};
```

### ProgramVisitor (SkSLProgramVisitor.h)

`TProgramVisitor<ProgramVisitorTypes>` 的具体实例化，使用 `const` 类型参数，因此所有通过 `ProgramVisitor` 进行的遍历都是只读的。这是本目录中绝大多数分析通道的基类。

### ProgramUsage (SkSLProgramUsage.h / .cpp)

程序使用情况的"侧车"数据结构（side-car class），独立于 IR 树存储，跟踪以下三类引用计数：

- `fVariableCounts` -- 变量的存在、读取和写入计数（`VariableCounts: fVarExists, fRead, fWrite`）
- `fCallCounts` -- 函数调用次数
- `fStructCounts` -- 结构体类型使用次数

`ProgramUsage` 是死代码消除、常量传播等优化的基础数据。其 `isDead()` 方法通过检查读写计数来判断变量是否可安全删除。它支持增量更新——当 IR 节点被添加或删除时，可通过 `add()`/`remove()` 方法精确地调整引用计数，无需重新扫描整个程序。

```cpp
class ProgramUsage {
public:
    struct VariableCounts { int fVarExists, fRead, fWrite; };
    VariableCounts get(const Variable&) const;
    bool isDead(const Variable&) const;
    int get(const FunctionDeclaration&) const;
    void add(const Expression* / Statement* / ProgramElement&);
    void remove(const Expression* / Statement* / ProgramElement&);
};
```

### Analysis::GetUsage() (SkSLProgramUsage.cpp)

工厂函数，为整个 `Program` 或 `Module` 构建 `ProgramUsage` 对象。内部使用 `ProgramUsageVisitor`（继承自 `ProgramVisitor`）以增量方式（delta = +1）遍历所有 IR 元素，统计变量引用、函数调用和结构体使用。

### Analysis::CanExitWithoutReturningValue() (SkSLCanExitWithoutReturningValue.cpp)

检查非 `void` 函数是否可能在某条执行路径上不返回值。内部 `ReturnsOnAllPathsVisitor` 对 if/for/do/switch 等控制流结构进行路径分析，跟踪 `fFoundReturn`、`fFoundBreak` 和 `fFoundContinue` 三个状态。对于 if 语句，要求 `true` 和 `false` 两个分支都有返回才认为函数必定返回。

### Analysis::CheckProgramStructure() (SkSLCheckProgramStructure.cpp)

检测程序中的递归调用和过深的函数调用链。使用 `FunctionState`（`kVisiting` / `kVisited`）状态机进行DFS，当发现 `kVisiting` 状态的函数被再次访问时，即报告循环调用错误。调用深度上限为 50 层（`kProgramStackDepthLimit`）。

### Analysis::GetLoopUnrollInfo() (SkSLGetLoopUnrollInfo.cpp)

验证 `for` 循环是否满足 OpenGL ES 2.0 规范（附录 A，第 4 节）的严格循环格式要求，并提取循环展开信息（起始值、终止条件、步长、迭代次数）。循环终止上限为 100,000 次迭代（`kLoopTerminationLimit`）。该函数还会对 `!=` 条件的浮点循环进行安全重写，将其转换为 `<` 或 `>` 以避免舍入误差导致的无限循环。

### Analysis::HasSideEffects() (SkSLHasSideEffects.cpp)

判断表达式是否产生副作用。以下情况被视为有副作用：非 `pure` 函数调用、赋值操作符（`=`、`+=` 等）、自增自减操作符（`++`、`--`）。该分析结果被死代码消除通道用于决定是否可以安全地删除表达式语句。

### Analysis::IsConstantExpression() (SkSLIsConstantExpression.cpp)

判断表达式是否为 GLSL 1.0 第 5.10 节定义的常量表达式。此文件还包含 `ES2IndexingVisitor`，用于验证 ES2 环境下数组索引必须为"常量索引表达式"（constant-index-expression）的规则。

### Analysis::DoFinalizationChecks() (SkSLFinalizationChecks.cpp)

在编译最终阶段执行一系列验证：检查全局变量大小限制（`kVariableSlotLimit`）、验证 binding 布局的唯一性、确保 `out` 参数被赋值、检验 compute shader 的 workgroup local size 设定，以及检测无效的表达式引用。

### 函数特化分析 (SkSLSpecialization.h / .cpp)

一个相对复杂的分析子系统，用于支持 SkSL 的函数特化优化。`FindFunctionsToSpecialize()` 从 `main()` 开始遍历调用图，识别需要根据 uniform 参数进行特化的函数调用。核心数据结构包括：

- `SpecializationMap` -- 从函数声明映射到其所有特化版本
- `SpecializedCallMap` -- 从调用点映射到特化索引
- `SpecializedParameters` -- 特化参数到全局 uniform 表达式的映射

## 依赖关系

```
SkSLAnalysis.h (公共接口)
    |
    +-- analysis/SkSLProgramVisitor.h (遍历基础设施)
    +-- analysis/SkSLProgramUsage.h/.cpp (使用情况统计)
    +-- analysis/SkSLNoOpErrorReporter.h (静默错误处理)
    +-- analysis/SkSLSpecialization.h/.cpp (特化分析)
    |
    +-- ir/SkSLExpression.h (表达式 IR 节点)
    +-- ir/SkSLStatement.h (语句 IR 节点)
    +-- ir/SkSLProgramElement.h (顶层 IR 元素)
    +-- ir/SkSLVariable.h, SkSLFunctionDeclaration.h, ...
    |
    +-- SkSLContext.h (编译上下文)
    +-- SkSLErrorReporter.h (错误报告)
    +-- SkSLConstantFolder.h (常量折叠)
    +-- core/SkTHash.h (哈希表容器)
```

本目录中的代码是**被依赖方**而非依赖方——`transform/` 目录下的 IR 变换通道大量使用本目录的分析结果。例如，`ProgramUsage::isDead()` 被死代码消除通道调用；`HasSideEffects()` 被死变量消除通道调用；`GetLoopUnrollInfo()` 被循环展开通道调用。

## 设计模式分析

### 访问者模式 (Visitor Pattern)

本目录的核心设计模式是**访问者模式**的模板化变体。`TProgramVisitor<T>` 是访问者基类，SkSL IR 节点（`Expression`、`Statement`、`ProgramElement`）构成了被访问的元素层次结构。与经典访问者模式不同的是，这里使用模板参数 `T` 来控制 `const` 限定，从而在编译时区分只读访问（`ProgramVisitor`）和可修改访问（`ProgramWriter`，定义在 `transform/` 目录中）。

### 内部类实现模式

几乎所有分析通道都采用了**匿名命名空间中的内部类**模式。每个分析函数内部定义一个继承自 `ProgramVisitor` 的私有类，重写所需的 `visit*()` 方法。这种模式有几个优点：

1. 将分析逻辑的状态（成员变量）与分析逻辑的行为（重写方法）封装在一起
2. 分析类对外不可见，保持了干净的公共 API
3. 每个分析函数是自包含的，易于理解和维护

```cpp
// 典型模式示例
bool Analysis::HasSideEffects(const Expression& expr) {
    class HasSideEffectsVisitor : public ProgramVisitor {
        bool visitExpression(const Expression& expr) override { /* ... */ }
    };
    HasSideEffectsVisitor visitor;
    return visitor.visitExpression(expr);
}
```

### 增量更新模式 (Delta Pattern)

`ProgramUsageVisitor` 采用了巧妙的 `delta` 参数设计：构造时传入 `+1` 表示"添加引用"，传入 `-1` 表示"移除引用"。同一个遍历逻辑可以同时服务于引用计数的增加和减少，避免了代码重复。

### 短路求值模式

`ProgramVisitor` 的 `visit*()` 方法返回 `bool`。当返回 `true` 时，遍历立即停止并向上传播。这为"查找型"分析（如 `HasSideEffects`、`IsConstantExpression`）提供了高效的提前终止能力。

## 数据流

```
                    SkSL 源代码
                        |
                        v
               +------------------+
               |  SkSL Parser     |
               +--------+---------+
                        |
                        v
               +------------------+
               |  SkSL IR 树       |  (ProgramElement -> Statement -> Expression)
               +--------+---------+
                        |
          +-------------+-------------+
          |                           |
          v                           v
+------------------+      +-------------------------+
| Analysis::       |      | Analysis::GetUsage()    |
| CheckProgram     |      | (构建 ProgramUsage)      |
| Structure()      |      +------------+------------+
| (递归检测)        |                   |
+------------------+                   v
          |               +-------------------------+
          v               | ProgramUsage            |
+------------------+      | fVariableCounts:        |
| Analysis::       |      |   var -> {Exist,R,W}    |
| GetLoopUnroll    |      | fCallCounts:            |
| Info()           |      |   func -> callCount     |
| (循环展开分析)    |      | fStructCounts:          |
+------------------+      |   struct -> useCount    |
          |               +------------+------------+
          v                            |
+------------------+                   v
| Analysis::       |      +-------------------------+
| DoFinalization   |      | Transform 通道 (消费方)   |
| Checks()        |      | - EliminateDeadFunctions |
| (最终验证)       |      | - EliminateDeadVariables |
+------------------+      | - ReplaceConstVars...    |
                          +-------------------------+
                                       |
                                       v
                          +-------------------------+
                          | 优化后的 SkSL IR 树       |
                          +-------------------------+
                                       |
                                       v
                          +-------------------------+
                          | 后端代码生成              |
                          | (GLSL / Metal / SPIR-V)  |
                          +-------------------------+
```

分析通道的典型数据流如下：

1. **构建阶段**：`Analysis::GetUsage()` 遍历完整的 IR 树，构建初始的 `ProgramUsage` 引用计数表。
2. **验证阶段**：各种 `Check*` 和 `DoFinalizationChecks()` 函数验证程序正确性，将错误报告给 `ErrorReporter`。
3. **查询阶段**：优化通道（位于 `transform/` 目录）查询分析结果——例如，`ProgramUsage::isDead()` 判断变量是否可删除，`HasSideEffects()` 判断表达式是否可安全移除。
4. **增量更新**：当 `transform/` 目录中的变换通道修改 IR 时，通过 `ProgramUsage::add()/remove()` 增量更新引用计数，避免重新扫描整个程序。

## 相关文档与参考

- **SkSL 设计文档**：SkSL 语言规范和编译器架构，参见 `src/sksl/README.md`
- **公共 API 头文件**：`src/sksl/SkSLAnalysis.h` -- 所有分析函数的声明和文档注释
- **变换通道**：`src/sksl/transform/` -- 消费分析结果的 IR 变换通道
- **IR 节点定义**：`src/sksl/ir/` -- SkSL 中间表示的完整节点定义
- **函数特化设计文档**：go/sksl-function-specialization (Google 内部文档)
- **GLSL ES 1.0 规范**：附录 A 第 4 节定义了循环展开的严格规则，`GetLoopUnrollInfo()` 严格遵循此规范
- **SkSL 测试用例**：`resources/sksl/` -- 大量涵盖分析通道行为的测试文件，如 `SwitchWithEarlyReturn.sksl`
