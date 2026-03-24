# SkSL Transform - 着色器语言 IR 变换通道

## 概述

`src/sksl/transform` 目录包含了 SkSL（Skia Shading Language）编译器的 **IR 变换通道**（Transformation Passes）。与 `analysis/` 目录中的只读分析不同，本目录中的代码会**主动修改** SkSL 程序的中间表示（IR），以实现代码优化、符号简化和内建元素声明等功能。

SkSL 变换通道在编译管线中处于分析通道之后、后端代码生成之前的关键位置。它们接收经过语义分析的 IR 树和 `ProgramUsage` 统计数据，执行各种优化和规范化操作，输出更精简、更高效的 IR 树。变换通道大致可以分为三类：**死代码消除**（移除未使用的变量、函数和不可达代码）、**代码简化**（常量替换、符号重命名、语法糖转换）以及**内建元素管理**（将模块中的内建函数、结构体和变量声明注入程序）。

所有变换函数的公共接口统一声明在 `SkSLTransform.h` 的 `Transform` 命名空间中。与 `analysis/` 目录的 `ProgramVisitor`（只读遍历）相对应，本目录定义了 `ProgramWriter`（可写遍历），它继承自相同的 `TProgramVisitor` 模板基类，但使用非 `const` 类型参数，使得 IR 节点可以在遍历过程中被就地替换或修改。

变换通道的设计遵循了一个重要原则：所有对 IR 的修改都必须同步更新 `ProgramUsage` 引用计数。当一个 IR 节点被移除时，必须调用 `ProgramUsage::remove()` 减少相关引用计数；当替换节点被插入时，必须调用 `ProgramUsage::add()` 增加新的引用计数。这种增量更新策略避免了在每个变换通道后重新扫描整个程序，是 SkSL 编译器高效性的关键保障。

大部分变换通道同时提供针对 `Program`（最终编译产物）和 `Module`（可复用的库模块）两个版本的重载函数。Module 版本主要用于模块预编译阶段的体积优化，而 Program 版本则用于最终程序的编译优化。

## 架构图

```
+-----------------------------------------------------------------------------------+
|                           SkSL 编译器变换子系统                                      |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +---------------------------+        +------------------------------------+      |
|  |   SkSLTransform.h         |        |   TProgramVisitor<T> (来自 analysis)|      |
|  |   (公共 API 声明)          |        +----------------+-------------------+      |
|  |   namespace Transform     |                         |                          |
|  +---------------------------+           +-------------v--------------+            |
|                                          | ProgramWriter              |            |
|                                          | (可写遍历, 非const IR)      |            |
|                                          | - visitExpressionPtr()     |            |
|                                          | - visitStatementPtr()      |            |
|                                          +-------------+--------------+            |
|                                                        |                          |
|         +----------------------------------------------+-----+                    |
|         |                    |                    |           |                    |
|  +------v--------+  +-------v---------+  +-------v-------+  |                    |
|  | 死代码消除      |  | 代码简化         |  | 内建元素管理   |  |                    |
|  |               |  |                  |  |               |  |                    |
|  | EliminateDead |  | AddConstToVar    |  | FindAndDeclare|  |                    |
|  |  Functions    |  |  Modifiers       |  |  BuiltinFuncs |  |                    |
|  | EliminateDead |  | RenamePrivate    |  | FindAndDeclare|  |                    |
|  |  LocalVars    |  |  Symbols         |  |  BuiltinStructs  |                    |
|  | EliminateDead |  | ReplaceConst     |  | FindAndDeclare|  |                    |
|  |  GlobalVars   |  |  VarsWithLiterals|  |  BuiltinVars  |  |                    |
|  | EliminateUn   |  | ReplaceSplat     |  +---------------+  |                    |
|  |  reachableCode|  |  CastsWithSwizzle|                     |                    |
|  | EliminateEmpty|  | RewriteIndexed   |  +------------------v-------+            |
|  |  Statements   |  |  Swizzle         |  | Switch 变量提升            |            |
|  | EliminateUn   |  +------------------+  | HoistSwitchVarDeclarations|            |
|  |  necessaryBra |                        |  AtTopLevel               |            |
|  |  ces          |                        +---------------------------+            |
|  +---------------+                                                                |
|                                                                                   |
|  +--------------------------------------------------+                             |
|  |   ProgramUsage (来自 analysis/)                    |                             |
|  |   - 所有变换通道通过 add()/remove() 增量更新         |                             |
|  +--------------------------------------------------+                             |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

## 目录结构

```
src/sksl/transform/
|-- BUILD.bazel                                   # Bazel 构建规则
|-- SkSLTransform.h                               # 所有变换函数的公共 API 声明
|-- SkSLTransform.cpp                             # IWYU 占位文件 (仅包含头文件)
|-- SkSLProgramWriter.h                           # 可写 IR 遍历器基类
|
|-- [死代码消除]
|-- SkSLEliminateDeadFunctions.cpp                # 删除未被调用的函数定义
|-- SkSLEliminateDeadLocalVariables.cpp           # 删除未读取的局部变量
|-- SkSLEliminateDeadGlobalVariables.cpp          # 删除未使用的全局变量
|-- SkSLEliminateUnreachableCode.cpp              # 删除 return/break 后的不可达语句
|-- SkSLEliminateEmptyStatements.cpp              # 删除空语句 (Nop)
|-- SkSLEliminateUnnecessaryBraces.cpp            # 简化单语句花括号块
|
|-- [代码简化与优化]
|-- SkSLAddConstToVarModifiers.cpp                # 为只写一次的变量添加 const 修饰
|-- SkSLReplaceConstVarsWithLiterals.cpp          # 将 const 变量替换为字面量值
|-- SkSLReplaceSplatCastsWithSwizzles.cpp         # 将 float4(x) 替换为 x.xxxx
|-- SkSLRewriteIndexedSwizzle.cpp                 # 重写索引化的 swizzle 表达式
|-- SkSLRenamePrivateSymbols.cpp                  # 重命名私有符号以缩减代码体积
|
|-- [内建元素管理]
|-- SkSLFindAndDeclareBuiltinFunctions.cpp        # 将引用的内建函数注入程序
|-- SkSLFindAndDeclareBuiltinStructs.cpp          # 将引用的内建结构体注入程序
|-- SkSLFindAndDeclareBuiltinVariables.cpp        # 将引用的内建变量注入程序
|
|-- [Switch 语句变换]
|-- SkSLHoistSwitchVarDeclarationsAtTopLevel.cpp  # 提升 switch-case 顶层变量声明
```

## 关键类与函数

### ProgramWriter (SkSLProgramWriter.h)

`TProgramVisitor<ProgramWriterTypes>` 的具体实例化，是所有可修改 IR 的变换通道的基类。与只读的 `ProgramVisitor` 相比，`ProgramWriter` 使用非 `const` 类型参数，并且暴露了对 `std::unique_ptr` 的直接访问：

```cpp
class ProgramWriter : public TProgramVisitor<ProgramWriterTypes> {
public:
    bool visitExpressionPtr(std::unique_ptr<Expression>& e) override;
    bool visitStatementPtr(std::unique_ptr<Statement>& s) override;
};
```

子类可以重写 `visitExpressionPtr()` 和 `visitStatementPtr()` 来直接修改 `unique_ptr`，从而实现 IR 节点的就地替换。例如，死变量消除通道通过 `stmt = Nop::Make()` 将变量声明替换为空操作。

### Transform::EliminateDeadFunctions() (SkSLEliminateDeadFunctions.cpp)

移除程序中未被调用的函数定义。通过 `ProgramUsage::get(FunctionDeclaration&)` 获取函数的调用计数，将调用次数为零且非 `main()` 的函数从 `fOwnedElements` 和 `fSharedElements` 中移除。使用 `std::remove_if` 配合自定义谓词 `dead_function_predicate()` 进行高效的就地过滤。

```cpp
static bool dead_function_predicate(const ProgramElement* element, ProgramUsage* usage) {
    if (!element->is<FunctionDefinition>()) return false;
    const FunctionDefinition& fn = element->as<FunctionDefinition>();
    if (fn.declaration().isMain() || usage->get(fn.declaration()) > 0) return false;
    usage->remove(*element);  // 在删除前更新引用计数
    return true;
}
```

### Transform::EliminateDeadLocalVariables() (SkSLEliminateDeadLocalVariables.cpp)

删除从未被读取的局部变量及其赋值语句。这是一个多层优化过程：

1. 首先扫描 `ProgramUsage::fVariableCounts`，快速判断程序中是否存在可消除的死变量
2. 使用 `DeadLocalVariableEliminator`（继承自 `ProgramWriter`）遍历函数体
3. 将死变量的声明替换为其初始值表达式语句（保留副作用）或 `Nop`
4. 将对死变量的赋值 `deadVar = expr` 替换为 `expr` 本身
5. 如果替换后的表达式语句无副作用（通过 `Analysis::HasSideEffects()` 判断），则进一步替换为 `Nop`

该通道还能处理嵌套赋值链，如 `a = b = 123`，当 `a` 和 `b` 都是死变量时，可以完全消除整条语句。

### Transform::EliminateDeadGlobalVariables() (SkSLEliminateDeadGlobalVariables.cpp)

删除未使用的全局变量。支持 `onlyPrivateGlobals` 参数，当设置为 `true` 时仅删除以 `$` 前缀开头的私有全局变量。使用 `ProgramUsage::isDead()` 判断变量是否已死——该方法会排除 `in`/`out`/`uniform` 修饰的变量以及 opaque 类型（采样器、原子变量等）。

### Transform::EliminateUnreachableCode() (SkSLEliminateUnreachableCode.cpp)

消除 `return`、`break`、`continue`、`discard` 语句之后的不可达代码。`UnreachableCodeEliminator` 维护两个布尔栈：

- `fFoundFunctionExit` -- 跟踪函数级别的退出（return/discard）
- `fFoundBlockExit` -- 跟踪块级别的退出（break/continue）

对于 if 语句，仅当两个分支都包含退出时才向外传播退出状态。对于 switch 语句，需要所有 case（包含 default）都有返回才能传播函数退出。

### Transform::RenamePrivateSymbols() (SkSLRenamePrivateSymbols.cpp)

将私有函数和局部变量重命名为短名称，以减小生成代码的体积。`SymbolRenamer` 首先尝试单字母名称（a-z, A-Z），失败后尝试双字母组合。对于函数名，在非 RuntimeEffect 模式下会添加 `$` 前缀以避免与用户代码冲突。重命名完成后，所有函数的 `$export` 标志会被清除。

```cpp
static std::string FindShortNameForSymbol(const Symbol* sym,
                                          const SymbolTable* symbolTable,
                                          const std::string& namePrefix) {
    // 依次尝试 a-z, A-Z, 然后 aa-ZZ (共 52 + 2704 = 2756 种组合)
    for (std::string_view letter : kLetters) {
        std::string name = namePrefix + std::string(letter);
        if (symbolTable->find(name) == nullptr) return name;
    }
    // ...
}
```

### Transform::ReplaceConstVarsWithLiterals() (SkSLReplaceConstVarsWithLiterals.cpp)

将 `const` 变量的引用替换为其字面量值。该通道包含一个代码体积分析：仅当替换后的总代码体积不增大时才执行替换。具体计算公式为：

- 旧体积 = `strlen("const type varname=initialvalue;")` + `引用次数 * strlen("varname")`
- 新体积 = `引用次数 * strlen("initialvalue")`

### Transform::AddConstToVarModifiers() (SkSLAddConstToVarModifiers.cpp)

检查变量是否可以安全地添加 `const` 修饰符。条件是：变量尚未标记为 `const`、初始值是编译时常量（`Analysis::IsCompileTimeConstant()`）、且变量仅被写入一次。添加 `const` 后，该变量可被内联器（inliner）进行常量折叠。

### Transform::EliminateUnnecessaryBraces() (SkSLEliminateUnnecessaryBraces.cpp)

简化模块 IR 中的冗余花括号。分两个阶段执行：

1. **UnnecessaryBraceEliminator**：将 if/for/do 语句体中仅含单条语句的花括号块替换为该语句本身
2. **RequiredBraceWriter**：修复第一阶段可能引入的 "dangling else" 歧义——当外层 if 有 else 分支、内层 if 无 else 分支时，必须为内层 if 添加花括号以消除歧义

### Transform::RewriteIndexedSwizzle() (SkSLRewriteIndexedSwizzle.cpp)

将形如 `myVec.zyx[i]` 的索引化 swizzle 重写为 `myVec[vec3(2, 1, 0)[i]]`。这与 glslang 的处理方式一致，将 swizzle 组件转换为常量向量的索引查找。

### Transform::ReplaceSplatCastsWithSwizzles() (SkSLReplaceSplatCastsWithSwizzles.cpp)

将 splat 构造器（如 `float4(myFloat)`）替换为 swizzle 表达式（如 `myFloat.xxxx`）。swizzle 形式在文本表示上更紧凑，且在加载时会被优化回 splat 构造器。仅对非字面量参数或高精度浮点字面量执行此替换。

### Transform::FindAndDeclareBuiltinFunctions() (SkSLFindAndDeclareBuiltinFunctions.cpp)

将程序引用的内建函数从模块中复制到程序的 `fSharedElements` 列表。该过程是迭代的：添加一个内建函数可能引入对其他内建函数的引用，因此使用循环不断发现新依赖，直到不再有新的函数引用为止。还会处理 `dFdy` 内建函数对 RTFlip uniform 输入的依赖。

### Transform::FindAndDeclareBuiltinVariables() (SkSLFindAndDeclareBuiltinVariables.cpp)

扫描程序中使用的内建变量（如 `sk_FragColor`、`sk_FragCoord`、`sk_Clockwise`），并将它们的声明元素添加到程序中。同时设置程序接口标志：

- `sk_FragCoord` / `sk_Clockwise` --> 设置 `fRTFlipUniform`（RT 翻转 uniform）
- `sk_LastFragColor` --> 设置 `fUseLastFragColor`
- `sk_SecondaryFragColor` --> 设置 `fOutputSecondaryColor`

### Transform::HoistSwitchVarDeclarationsAtTopLevel() (SkSLHoistSwitchVarDeclarationsAtTopLevel.cpp)

将 switch-case 顶层的变量声明提升到外围作用域。这是为了解决 ES2 和 WGSL 等目标语言中 switch 语句重写时的作用域问题。变量声明被移到一个新创建的外围 Block 中，原来的声明位置被替换为赋值语句（有初始值时）或 Nop（无初始值时）。

## 依赖关系

```
SkSLTransform.h (公共接口)
    |
    +-- transform/SkSLProgramWriter.h
    |       |
    |       +-- analysis/SkSLProgramVisitor.h (遍历基类，const 和非 const 两种)
    |
    +-- analysis/SkSLProgramUsage.h (引用计数，所有变换都通过 add/remove 更新)
    +-- SkSLAnalysis.h (分析函数，如 HasSideEffects, IsCompileTimeConstant)
    +-- SkSLConstantFolder.h (常量折叠工具，用于 ReplaceConstVarsWithLiterals)
    |
    +-- ir/SkSLExpression.h, SkSLStatement.h, SkSLProgramElement.h (IR 节点)
    +-- ir/SkSLNop.h (空操作节点，用于替换被删除的语句)
    +-- ir/SkSLVariable.h, SkSLFunctionDeclaration.h, ...
    +-- ir/SkSLSymbolTable.h (符号表操作，用于 RenamePrivateSymbols)
    |
    +-- SkSLContext.h (编译上下文)
    +-- SkSLModule.h (模块结构，用于模块级变换)
    +-- SkSLProgramSettings.h (编译设置，控制是否启用特定变换)
```

### 与 analysis/ 的关系

`transform/` 目录是 `analysis/` 目录最主要的消费者。关键的依赖关系包括：

| 变换通道 | 依赖的分析功能 |
|---------|--------------|
| `EliminateDeadFunctions` | `ProgramUsage::get(FunctionDeclaration&)` |
| `EliminateDeadLocalVariables` | `ProgramUsage::fVariableCounts`, `Analysis::HasSideEffects()` |
| `EliminateDeadGlobalVariables` | `ProgramUsage::isDead()` |
| `AddConstToVarModifiers` | `Analysis::IsCompileTimeConstant()`, `ProgramUsage::get(Variable&)` |
| `ReplaceConstVarsWithLiterals` | `ConstantFolder::GetConstantValue()` |
| `RenamePrivateSymbols` | `Analysis::SymbolTableStackBuilder` |
| `HoistSwitchVarDeclarations` | `Analysis::IsConstantExpression()` |

## 设计模式分析

### 可写访问者模式 (Mutable Visitor Pattern)

`ProgramWriter` 是对经典访问者模式的扩展。与只读的 `ProgramVisitor` 不同，`ProgramWriter` 通过暴露 `std::unique_ptr<Expression>&` 和 `std::unique_ptr<Statement>&` 引用，允许子类在遍历过程中**就地替换** IR 节点。这种设计使得 IR 变换可以在单次遍历中完成，无需额外的"查找-记录-替换"步骤。

```cpp
// 典型的节点替换模式
bool visitStatementPtr(std::unique_ptr<Statement>& stmt) override {
    if (should_eliminate(stmt)) {
        fUsage->remove(stmt.get());    // 1. 更新引用计数（移除旧节点）
        stmt = Nop::Make();            // 2. 就地替换为新节点
        // 注意：如果新节点不是 Nop，还需要 fUsage->add(stmt.get())
        return false;
    }
    return INHERITED::visitStatementPtr(stmt);
}
```

### 策略模式 (Strategy Pattern)

变换通道的启用与否由 `ProgramSettings` 中的配置标志控制：

- `fRemoveDeadFunctions` -- 控制 `EliminateDeadFunctions`
- `fRemoveDeadVariables` -- 控制 `EliminateDeadLocalVariables` 和 `EliminateDeadGlobalVariables`

这使得编译管线可以根据目标平台或编译模式灵活地启用或禁用特定的变换。

### 谓词过滤模式 (Predicate Filter Pattern)

死代码消除通道广泛使用 `std::remove_if` 配合自定义谓词函数进行容器元素的过滤。谓词函数不仅判断元素是否应被移除，还负责在返回 `true` 之前更新 `ProgramUsage`。这种"判断与清理一体化"的设计简洁高效。

### 双遍历模式 (Two-Pass Pattern)

`EliminateUnnecessaryBraces` 采用了双遍历策略：第一遍（`UnnecessaryBraceEliminator`）积极地移除花括号，第二遍（`RequiredBraceWriter`）修复因过度移除导致的 "dangling else" 问题。这种"先做再修"的模式比单遍中同时处理两个目标更简单清晰。

### 增量更新契约 (Incremental Update Contract)

本目录中最重要的设计约束：**所有 IR 修改必须同步更新 ProgramUsage**。这不是一个可选的优化，而是一个正确性要求——后续的变换通道依赖 `ProgramUsage` 中的引用计数来做出决策。违反此契约会导致死代码未被清除（计数偏高）或仍在使用的代码被误删（计数偏低）。

## 数据流

```
+------------------+     +---------------------+     +---------------------+
| SkSL IR 树        |     | ProgramUsage        |     | ProgramSettings     |
| (经过语义分析)     |     | (来自 Analysis)      |     | (编译配置)           |
+--------+---------+     +---------+-----------+     +---------+-----------+
         |                         |                           |
         v                         v                           v
+------------------------------------------------------------------------+
|                          变换管线入口                                     |
+------------------------------------------------------------------------+
         |
         |  [阶段 1: 内建元素注入]
         v
+-----------------------------------+
| FindAndDeclareBuiltinFunctions()  |  从模块复制被引用的内建函数
| FindAndDeclareBuiltinStructs()    |  从模块复制被引用的内建结构体
| FindAndDeclareBuiltinVariables()  |  扫描并声明 sk_FragColor 等内建变量
+-----------------------------------+
         |
         |  [阶段 2: 死代码消除循环]
         v
+-----------------------------------+
| EliminateDeadFunctions()          |  删除未调用的函数
| EliminateDeadGlobalVariables()    |  删除未使用的全局变量
| EliminateDeadLocalVariables()     |  删除未读取的局部变量
| EliminateUnreachableCode()        |  删除 return/break 后的不可达代码
+-----------------------------------+
         |
         |  [阶段 3: 代码简化 (主要用于模块)]
         v
+-----------------------------------+
| AddConstToVarModifiers()          |  为满足条件的变量添加 const
| ReplaceConstVarsWithLiterals()    |  const 变量内联为字面量
| RenamePrivateSymbols()            |  私有符号短名称替换
| EliminateEmptyStatements()        |  清除 Nop 语句
| EliminateUnnecessaryBraces()      |  简化单语句花括号
| ReplaceSplatCastsWithSwizzles()   |  float4(x) -> x.xxxx
+-----------------------------------+
         |
         |  [阶段 4: 目标特定变换]
         v
+-----------------------------------+
| RewriteIndexedSwizzle()           |  v.zyx[i] -> v[vec3(2,1,0)[i]]
| HoistSwitchVarDeclarations        |  switch 变量提升 (ES2/WGSL 兼容)
|   AtTopLevel()                    |
+-----------------------------------+
         |
         v
+-----------------------------------+
| 优化后的 SkSL IR 树                |
| + 更新后的 ProgramUsage            |
+-----------------------------------+
         |
         v
+-----------------------------------+
| 后端代码生成                       |
| GLSL / Metal / SPIR-V / WGSL     |
+-----------------------------------+
```

### 变换的执行顺序

变换通道的执行顺序是经过精心设计的：

1. **内建元素注入**必须最先执行，因为后续的死代码消除需要知道哪些内建函数被引用
2. **死代码消除**在内建元素注入之后执行，可以移除未使用的内建函数定义
3. **代码简化**在死代码消除之后执行，因为移除死代码可能使更多变量变为 `const` 候选
4. **目标特定变换**最后执行，因为它们通常与特定后端的代码生成规则相关

### 模块预编译 vs 程序编译

许多变换通道提供了 `Module&` 和 `Program&` 两个版本的重载。模块预编译阶段会执行更激进的优化（如 `RenamePrivateSymbols`、`EliminateEmptyStatements`、`EliminateUnnecessaryBraces`、`ReplaceSplatCastsWithSwizzles`），因为模块会被长期驻留在内存中，缩减其 IR 体积有持久的收益。而程序编译阶段则主要执行死代码消除和内建元素注入。

## 相关文档与参考

- **分析子系统**：`src/sksl/analysis/` -- 提供 `ProgramVisitor`、`ProgramUsage` 等基础设施
- **公共 API 头文件**：`src/sksl/transform/SkSLTransform.h` -- 所有变换函数的声明和详细文档注释
- **SkSL IR 定义**：`src/sksl/ir/` -- 中间表示节点的完整定义（Expression, Statement, ProgramElement 等）
- **SkSL 编译器入口**：`src/sksl/SkSLCompiler.cpp` -- 调用各变换通道的编译管线主逻辑
- **程序设置**：`src/sksl/SkSLProgramSettings.h` -- 控制变换通道启用/禁用的配置项
- **常量折叠**：`src/sksl/SkSLConstantFolder.h` -- `ReplaceConstVarsWithLiterals` 所依赖的常量求值工具
- **测试用例**：`resources/sksl/` 和 `tests/sksl/` -- 覆盖各变换通道行为的测试文件
- **GLSL ES 1.0 规范**：部分变换（如 `HoistSwitchVarDeclarationsAtTopLevel`）是为了满足 ES2 规范的限制
- **WGSL 规范**：Switch 变量提升也服务于 WebGPU 的 WGSL 着色器语言的语法要求
