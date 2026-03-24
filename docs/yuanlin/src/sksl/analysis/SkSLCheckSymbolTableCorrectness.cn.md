# SkSLCheckSymbolTableCorrectness — 符号表正确性检查

> 源文件：[`src/sksl/analysis/SkSLCheckSymbolTableCorrectness.cpp`](../../src/sksl/analysis/SkSLCheckSymbolTableCorrectness.cpp)

## 概述

SkSLCheckSymbolTableCorrectness.cpp 实现了对 SkSL 程序符号表的正确性验证。它遍历程序中的所有变量声明，检查每个变量是否正确地出现在其所属的符号表作用域中。这是一个调试辅助分析，用于检测编译器自身的内部错误。

该文件 86 行，包含一个诊断性分析函数。

## 架构位置

```
SkSL 编译器
  └── 分析（Analysis）模块
        └── 正确性验证
              └── CheckSymbolTableCorrectness（本文件）
                    ├── 遍历程序 IR
                    └── 验证变量与符号表的对应关系
```

此分析用于编译器自身的正确性检查，确保编译器在处理作用域和符号表时没有引入 bug。

## 主要类与结构体

### `SymbolTableCorrectnessVisitor`（局部类）

```cpp
class SymbolTableCorrectnessVisitor : public ProgramVisitor {
public:
    SymbolTableCorrectnessVisitor(const Context& c, SymbolTable* sym);
    bool visitStatement(const Statement& stmt) override;
    bool visitExpression(const Expression&) override;
private:
    const Context& fContext;
    std::vector<SymbolTable*> fSymbolTableStack;
};
```

- `fContext`：编译上下文，用于报告错误
- `fSymbolTableStack`：符号表栈，跟踪当前作用域链

## 公共 API 函数

```cpp
void Analysis::CheckSymbolTableCorrectness(const Program& program);
```
- 检查程序中所有变量声明是否正确地存在于其对应的符号表中
- 遍历 `program.fOwnedElements` 中的所有程序元素
- 如果发现不正确的作用域，通过 `ErrorReporter` 报告内部错误

## 内部实现细节

### 符号表栈管理

```cpp
Analysis::SymbolTableStackBuilder symbolTableStackBuilder(&stmt, &fSymbolTableStack);
```

使用 `SymbolTableStackBuilder` RAII 对象自动管理符号表栈的推入和弹出。每当遇到引入新作用域的语句时，栈顶被更新为该作用域的符号表。

### 变量声明验证

对于每个 `VarDeclaration` 语句，检查过程如下：

1. 获取栈顶符号表（当前作用域）
2. 遍历该符号表的所有符号
3. 进行精确的指针比较（`symbol == vardecl.var()`）
4. 如果变量不在当前符号表中，报告内部错误

### 为什么不使用 SymbolTable::find()

注释明确说明不使用 `SymbolTable::find()`，原因是：
- `find()` 按名称查找，可能匹配到不同作用域中同名的其他变量
- `find()` 会沿符号表树向上查找，但我们只想检查一个特定的符号表
- 需要精确的指针比较来验证变量是否在预期的符号表中

### 表达式跳过

```cpp
bool visitExpression(const Expression&) override {
    return false;
}
```

只关注语句级别的变量声明，不需要分析表达式。

## 依赖关系

- `include/core/SkTypes.h` — `SkASSERT` 等宏
- `src/core/SkTHash.h` — 哈希表（符号表使用）
- `src/sksl/SkSLAnalysis.h` — 分析函数声明
- `src/sksl/SkSLContext.h` — 编译上下文
- `src/sksl/SkSLErrorReporter.h` — 错误报告器
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/ir/SkSLProgram.h` — 程序 IR
- `src/sksl/ir/SkSLSymbolTable.h` — 符号表
- `src/sksl/ir/SkSLVarDeclarations.h` — 变量声明
- `src/sksl/ir/SkSLVariable.h` — 变量

## 设计模式与设计决策

- **访问者模式**：使用 `ProgramVisitor` 遍历 IR 树，在 `visitStatement` 中对变量声明做检查。
- **防御性编程**：这是编译器对自身内部状态的断言检查，用于尽早发现作用域处理中的 bug。
- **RAII 栈管理**：通过 `SymbolTableStackBuilder` 自动管理符号表栈，确保在异常或提前返回时栈的正确性。
- **精确指针比较**：避免名称查找的歧义性，确保验证的精确性。

## 性能考量

1. **调试/诊断用途**：此分析主要在调试构建或验证流程中使用，不应在生产环境的关键路径上调用。
2. **符号表遍历**：对每个变量声明需要遍历整个符号表，时间复杂度为 O(S)，S 为符号表大小。总体复杂度为 O(V * S)，V 为变量声明数量。
3. **表达式跳过**：通过跳过表达式减少不必要的遍历。

## 相关文件

- `src/sksl/SkSLAnalysis.h` — 分析函数声明
- `src/sksl/ir/SkSLSymbolTable.h` — 符号表实现
- `src/sksl/ir/SkSLVariable.h` — 变量类型
- `src/sksl/ir/SkSLVarDeclarations.h` — 变量声明
- `src/sksl/SkSLContext.h` — 编译上下文
