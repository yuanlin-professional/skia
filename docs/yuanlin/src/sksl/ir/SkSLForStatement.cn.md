# SkSLForStatement

> 源文件: src/sksl/ir/SkSLForStatement.h, src/sksl/ir/SkSLForStatement.cpp

## 概述

`ForStatement` 是 SkSL IR 中表示 `for` 循环语句的节点类，同时也用于表示 `while` 循环（通过省略初始化器和迭代表达式）。该类继承自 `Statement`，负责处理循环结构的语义验证、循环展开分析以及针对不同目标平台的特殊处理。

作为 SkSL 编译器中重要的控制流节点，`ForStatement` 不仅要管理循环的四个组成部分（初始化、测试、迭代、循环体），还需要处理符号表作用域、ES2 兼容性约束（强制循环可展开）、以及多变量声明初始化器的特殊重写逻辑。该类包含循环展开信息 `LoopUnrollInfo`，支持编译器在 ES2 严格模式下进行循环展开验证，并提供优化机会。

## 架构位置

`ForStatement` 位于 Skia 图形库的 SkSL 着色器语言编译器的中间表示（IR）层：

- **模块位置**: `src/sksl/ir/` - SkSL 中间表示节点定义目录
- **继承关系**: `ForStatement` → `Statement` → `IRNode`
- **编译流程**: Parser → AST → IR（ForStatement） → 优化/展开 → 代码生成
- **依赖层次**:
  - 向上依赖: `Context`、`SymbolTable`、`Analysis`
  - 向下被用于: 代码生成器、循环优化器、ES2 合规性检查器
  - 平级关系: 与 `IfStatement`、`DoStatement`、`Block` 等语句节点并列

## 主要类与结构体

### LoopUnrollInfo 结构体
```cpp
struct LoopUnrollInfo {
    const Variable* fIndex;   // 循环索引变量
    double fStart;            // 起始值
    double fDelta;            // 每次迭代的增量
    int fCount;               // 迭代次数
};
```
存储循环展开所需的元信息：
- 仅在循环可展开时非空
- 用于 ES2 严格模式下的合规性验证
- 支持编译器优化（如零迭代循环消除）

### ForStatement 类
```cpp
class ForStatement final : public Statement {
public:
    inline static constexpr Kind kIRNodeKind = Kind::kFor;

private:
    ForLoopPositions fForLoopPositions;           // 各部分的源码位置信息
    std::unique_ptr<SymbolTable> fSymbolTable;    // 循环作用域符号表
    std::unique_ptr<Statement> fInitializer;      // 初始化语句（可为空）
    std::unique_ptr<Expression> fTest;            // 循环条件（可为空）
    std::unique_ptr<Expression> fNext;            // 迭代表达式（可为空）
    std::unique_ptr<Statement> fStatement;        // 循环体
    std::unique_ptr<LoopUnrollInfo> fUnrollInfo;  // 展开信息（ES3+可为空）
};
```

核心职责：
- 管理循环的四个组成部分和作用域
- 存储位置信息以支持精确的错误报告
- 保存循环展开分析结果

## 公共 API 函数

### 静态构造函数

#### Convert
```cpp
static std::unique_ptr<Statement> Convert(
    const Context& context,
    Position pos,
    ForLoopPositions forLoopPositions,
    std::unique_ptr<Statement> initializer,
    std::unique_ptr<Expression> test,
    std::unique_ptr<Expression> next,
    std::unique_ptr<Statement> statement,
    std::unique_ptr<SymbolTable> symbolTable);
```
将 `for` 循环转换为 IR 节点：
- 验证初始化器类型（简单语句、变量声明或变量声明块）
- 将测试表达式强制转换为 `bool` 类型
- 检查迭代表达式是否完整（不能是类型引用或函数引用）
- 在 ES2 严格模式下强制循环可展开，否则仅作优化提示
- 处理多变量声明初始化器（提升到外层作用域）
- 检测循环体中的非作用域变量声明错误

#### ConvertWhile
```cpp
static std::unique_ptr<Statement> ConvertWhile(
    const Context& context,
    Position pos,
    std::unique_ptr<Expression> test,
    std::unique_ptr<Statement> statement);
```
将 `while` 循环转换为 `ForStatement`：
- ES2 严格模式下禁止 `while` 循环
- 内部调用 `Convert`，传入空的初始化器、迭代表达式和符号表

#### Make
```cpp
static std::unique_ptr<Statement> Make(
    const Context& context,
    Position pos,
    ForLoopPositions positions,
    std::unique_ptr<Statement> initializer,
    std::unique_ptr<Expression> test,
    std::unique_ptr<Expression> next,
    std::unique_ptr<Statement> statement,
    std::unique_ptr<LoopUnrollInfo> unrollInfo,
    std::unique_ptr<SymbolTable> symbolTable);
```
直接创建 `ForStatement`（通过断言验证）：
- 验证所有组件的有效性
- 优化零迭代循环和空循环体为 `Nop`
- 假设类型已正确强制转换

### 访问器函数

```cpp
ForLoopPositions forLoopPositions() const;               // 获取位置信息
std::unique_ptr<Statement>& initializer();               // 获取初始化器（可修改）
const std::unique_ptr<Statement>& initializer() const;   // 获取初始化器（只读）
std::unique_ptr<Expression>& test();                     // 获取测试表达式（可修改）
const std::unique_ptr<Expression>& test() const;         // 获取测试表达式（只读）
std::unique_ptr<Expression>& next();                     // 获取迭代表达式（可修改）
const std::unique_ptr<Expression>& next() const;         // 获取迭代表达式（只读）
std::unique_ptr<Statement>& statement();                 // 获取循环体（可修改）
const std::unique_ptr<Statement>& statement() const;     // 获取循环体（只读）
SymbolTable* symbols() const;                            // 获取符号表
const LoopUnrollInfo* unrollInfo() const;                // 获取展开信息（ES3+可能为空）
```

### 工具函数

#### description
```cpp
std::string description() const override;
```
生成循环的字符串表示，格式为 `for (init; test; next) body`。

## 内部实现细节

### 初始化器验证

实现两个辅助函数判断初始化器类型：

#### is_simple_initializer
```cpp
static bool is_simple_initializer(const Statement* stmt)
```
判断是否为简单初始化器：
- 空指针（无初始化）
- 空语句（`isEmpty()`）
- 单个变量声明（`VarDeclaration`）
- 表达式语句（`ExpressionStatement`）

#### is_vardecl_block_initializer
```cpp
static bool is_vardecl_block_initializer(const Statement* stmt)
```
判断是否为变量声明块：
- 必须是非作用域 `Block`
- 所有子语句都是 `VarDeclaration`
- 用于检测 `for (int i = 0, j = 1; ...)` 形式

### 符号提升机制

`hoist_vardecl_symbols_into_outer_scope` 函数处理多变量声明初始化器：

```cpp
static void hoist_vardecl_symbols_into_outer_scope(
    const Context& context,
    const Block& initBlock,
    SymbolTable* innerSymbols,
    SymbolTable* hoistedSymbols)
```

使用 `SymbolHoister` 访问者遍历初始化器块：
- 将所有变量符号从内层符号表移动到外层
- 转移符号所有权
- 支持后续将初始化器块提升到循环外

**原因**: 某些后端（如 Metal）不支持同一声明语句中的不同数组大小，因为数组大小是类型的一部分。

### 转换流程

`Convert` 函数的处理步骤：

1. **初始化器验证**：
   - 检查是简单初始化器还是变量声明块
   - 其他形式报告错误

2. **测试表达式处理**：
   - 强制转换为 `bool` 类型
   - 失败则返回 `nullptr`

3. **迭代表达式验证**：
   - 检查是否为完整表达式（`isIncomplete`）
   - 类型不重要，但必须是有效表达式

4. **循环展开分析**：
   - ES2 严格模式：必须可展开，失败则报错
   - ES3+：尽力分析，失败不影响编译

5. **循环体验证**：
   - 检测非作用域变量声明（如 `for (...) int x;`）
   - 这在大多数后端中是非法的

6. **多变量初始化器处理**：
   - 创建新的外层符号表
   - 提升变量符号
   - 将初始化器块和 `for` 循环包装在 `Block` 中
   - 等价于：
     ```glsl
     {
         int i = 0, j = 1;
         for (; test; next) body
     }
     ```

7. **创建节点**：
   - 调用 `Make` 创建最终的 `ForStatement`

### 优化机制

`Make` 函数中的优化：

```cpp
if (unrollInfo) {
    if (unrollInfo->fCount <= 0 || statement->isEmpty()) {
        return Nop::Make();
    }
}
```

消除无用循环：
- 零迭代循环（`for (int i = 0; i < 0; ++i)`）
- 空循环体且可展开

### while 循环处理

`ConvertWhile` 通过将 `while` 重写为 `for` 实现：
```cpp
while (test) body  →  for (; test;) body
```
- 初始化器: `nullptr`
- 迭代表达式: `nullptr`
- 符号表: `nullptr`（无需额外作用域）

### 描述生成

`description` 函数生成人类可读的循环表示：
```cpp
for (init; test; next) body
```
- 省略的部分保留分号
- 递归调用子节点的 `description`

## 依赖关系

### 头文件依赖

**核心依赖**：
- `SkSLStatement.h` - 语句基类
- `SkSLExpression.h` - 表达式基类
- `SkSLSymbolTable.h` - 符号表管理

**功能依赖**：
- `SkSLContext.h` - 编译上下文
- `SkSLAnalysis.h` - 循环分析（展开信息、变量声明检测）
- `SkSLProgramSettings.h` - ES2 严格模式配置
- `analysis/SkSLProgramVisitor.h` - AST 遍历框架

**关联节点**：
- `SkSLBlock.h` - 块语句（符号提升时使用）
- `SkSLVarDeclarations.h` - 变量声明
- `SkSLExpressionStatement.h` - 表达式语句
- `SkSLNop.h` - 空操作（优化结果）

### 运行时依赖

- **分析工具**:
  - `Analysis::GetLoopUnrollInfo` - 计算展开信息
  - `Analysis::DetectVarDeclarationWithoutScope` - 检测非法变量声明
- **类型系统**: 测试表达式的 `bool` 类型强制转换
- **符号表**: 符号提升、作用域管理

## 设计模式与设计决策

### 工厂模式

提供三个静态工厂方法：
- `Convert`: 处理 `for` 循环的完整验证和转换
- `ConvertWhile`: 专门处理 `while` 循环
- `Make`: 快速创建已验证的节点

设计原因：
- 分离转换逻辑和构造逻辑
- `Convert` 处理复杂的多变量初始化器重写
- `ConvertWhile` 提供统一的循环表示

### 访问者模式

`SymbolHoister` 使用 `ProgramVisitor` 遍历初始化器块：
```cpp
class SymbolHoister : public ProgramVisitor {
    bool visitStatement(const Statement& stmt) override {
        if (stmt.is<VarDeclaration>()) {
            // 提升符号
            return false;  // 停止遍历子节点
        }
        return ProgramVisitor::visitStatement(stmt);
    }
};
```

### 不可变优化

展开信息 `fUnrollInfo` 在创建后不可修改：
- 支持并发读取
- 避免优化过程中的状态不一致
- 符合函数式编程范式

### 懒惰删除

使用 `nullptr` 表示可选组件：
- 初始化器可为空（`while` 循环）
- 测试条件可为空（无限循环）
- 迭代表达式可为空（手动迭代）
- 符号表可为空（`while` 循环）

### 渐进式降级

循环展开行为取决于语言模式：
- **ES2 严格模式**: 必须可展开，否则编译失败
- **ES3+**: 尽力分析，不影响编译结果

设计原因：
- ES2 目标平台（如 OpenGL ES 2.0）不支持动态循环
- ES3+ 平台支持任意循环，但展开信息仍可用于优化

### 作用域提升策略

多变量初始化器的处理策略：
```cpp
// 输入
for (int i = 0, j = 1; test; next) body

// 转换为
{
    int i = 0;
    int j = 1;
    for (; test; next) body
}
```

设计原因：
- 保持语义等价（变量作用域不变）
- 适配后端限制（Metal 不支持复合声明）
- 简化循环节点结构

## 性能考量

### 内存布局

```cpp
ForLoopPositions fForLoopPositions;          // ~16 字节
std::unique_ptr<SymbolTable> fSymbolTable;   // 8 字节
std::unique_ptr<Statement> fInitializer;     // 8 字节
std::unique_ptr<Expression> fTest;           // 8 字节
std::unique_ptr<Expression> fNext;           // 8 字节
std::unique_ptr<Statement> fStatement;       // 8 字节
std::unique_ptr<LoopUnrollInfo> fUnrollInfo; // 8 字节
```
总大小：约 72 字节（加上 `Statement` 基类）

### 编译时优化

零迭代循环消除：
```cpp
for (int i = 0; i < 0; ++i) { /* ... */ }  →  Nop
```

空循环体消除：
```cpp
for (int i = 0; i < 10; ++i) {}  →  Nop (仅当可展开时)
```

### 展开分析性能

`GetLoopUnrollInfo` 仅在以下情况调用：
- ES2 严格模式（必须）
- ES3+ 模式且循环结构简单（可选）

避免对无法展开的复杂循环浪费分析时间。

### 符号提升的成本

符号提升仅在多变量初始化器时触发：
- 创建额外的 `Block` 节点
- 增加符号表层次
- 但避免了后端代码生成的复杂性

权衡：编译时成本 vs 后端兼容性

## 相关文件

### 同级 IR 节点
- `src/sksl/ir/SkSLDoStatement.h/cpp` - do-while 循环
- `src/sksl/ir/SkSLIfStatement.h/cpp` - 条件语句
- `src/sksl/ir/SkSLBlock.h/cpp` - 块语句
- `src/sksl/ir/SkSLBreakStatement.h` - break 语句
- `src/sksl/ir/SkSLContinueStatement.h` - continue 语句

### 依赖的核心组件
- `src/sksl/SkSLContext.h` - 编译上下文
- `src/sksl/SkSLAnalysis.h` - 循环分析工具
- `src/sksl/ir/SkSLSymbolTable.h/cpp` - 符号表
- `src/sksl/ir/SkSLType.h/cpp` - 类型系统
- `src/sksl/SkSLProgramSettings.h` - 编译器配置

### 相关的语句节点
- `src/sksl/ir/SkSLVarDeclarations.h/cpp` - 变量声明
- `src/sksl/ir/SkSLExpressionStatement.h/cpp` - 表达式语句
- `src/sksl/ir/SkSLNop.h` - 空操作

### 使用场景
- `src/sksl/SkSLCompiler.cpp` - 编译器主流程
- `src/sksl/codegen/` - 各种后端代码生成器
- `src/sksl/transform/SkSLLoopUnrolling.cpp` - 循环展开优化器
- `src/sksl/analysis/SkSLProgramVisitor.cpp` - 程序遍历器
