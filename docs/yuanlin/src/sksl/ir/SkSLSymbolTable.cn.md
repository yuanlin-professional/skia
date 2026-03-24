# SkSL SymbolTable (符号表)

> 源文件:
> - `src/sksl/ir/SkSLSymbolTable.h`
> - `src/sksl/ir/SkSLSymbolTable.cpp`

## 概述

`SymbolTable` 是 SkSL 编译器中的核心数据结构，负责将标识符（identifier）映射到对应的符号（Symbol）。它支持嵌套作用域（通过父符号表链），管理符号的所有权，并提供符号的查找、插入、删除和重命名等操作。符号表在 SkSL 程序的编译过程中用于解析变量名、函数名和类型名。

## 架构位置

`SymbolTable` 位于 SkSL 编译器的 IR（中间表示）层。它是编译器前端的关键组件，在解析（parsing）和语义分析（semantic analysis）阶段被广泛使用。符号表通过父子链关系实现作用域嵌套，内建符号表（builtin symbol table）包含所有预定义的类型和函数，而用户代码的符号表则在此基础上叠加。

```
SkSL Compiler Pipeline:
  Source Code -> Parser -> IR (含 SymbolTable) -> Analysis -> CodeGen
                              ^
                              |
                         SymbolTable 在此处构建和查询
```

## 主要类与结构体

### `SymbolTable`

核心符号表类，提供标识符到 `Symbol` 的映射。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fParent` | `SymbolTable*` | 父符号表指针，用于实现作用域链 |
| `fOwnedSymbols` | `vector<unique_ptr<Symbol>>` | 该符号表拥有所有权的符号集合 |
| `fBuiltin` | `bool` | 标识是否为内建符号表 |
| `fAtModuleBoundary` | `bool` | 标识父表是否属于不同的模块 |
| `fOwnedStrings` | `forward_list<string>` | 拥有所有权的字符串存储 |
| `fSymbols` | `THashMap<SymbolKey, Symbol*>` | 名称到符号的哈希映射 |

### `SymbolKey`（私有内部结构体）

用于在哈希表中查找符号的键值结构。包含 `fName`（字符串视图）和 `fHash`（32 位哈希值），通过 `SkChecksum::Hash32` 计算哈希。

## 公共 API 函数

### 构造与作用域管理

- **`SymbolTable(bool builtin)`** -- 创建一个没有父表的根符号表。
- **`SymbolTable(SymbolTable* parent, bool builtin)`** -- 创建一个带父表的嵌套符号表。
- **`insertNewParent()`** -- 在当前符号表和其父表之间插入一个新的空符号表，返回新表的 `unique_ptr`。

### 符号查找

- **`find(string_view name)`** -- 按名称查找符号，沿作用域链向上递归查找，返回 `const Symbol*`。
- **`findBuiltinSymbol(string_view name)`** -- 仅在内建符号表中查找符号。
- **`findMutable(string_view name)`** -- 查找并返回可变的符号指针（慎用，修改符号会影响整个程序）。
- **`instantiateSymbolRef(context, name, pos)`** -- 查找符号并创建对应的表达式引用（VariableReference、TypeReference、FunctionReference 或 FieldAccess）。

### 符号添加与注入

- **`addWithoutOwnership(context, symbol)`** -- 添加符号但不转移所有权，重复定义时报错。
- **`addWithoutOwnershipOrDie(symbol)`** -- 添加符号但不转移所有权，重复定义时 abort。
- **`add<T>(context, unique_ptr<T>)`** -- 添加符号并转移所有权，重复定义时报错。
- **`addOrDie<T>(unique_ptr<T>)`** -- 添加符号并转移所有权，重复定义时 abort。
- **`injectWithoutOwnership(symbol)`** -- 强制插入符号（覆盖同名符号），不转移所有权。
- **`inject<T>(unique_ptr<T>)`** -- 强制插入符号并转移所有权。

### 符号管理

- **`renameSymbol(context, symbol, newName)`** -- 为符号分配新名称，旧名称仍保留在符号表中。对于函数声明，会重命名整个重载链。
- **`removeSymbol(symbol)`** -- 从符号表中移除符号，如果符号表拥有该符号的所有权，则返回该符号。
- **`moveSymbolTo(otherTable, sym, context)`** -- 将符号从当前表移动到另一个表，连同所有权一起转移。
- **`takeOwnershipOfSymbol<T>(unique_ptr<T>)`** -- 接管符号的所有权但不将其添加到查找表中。

### 类型与辅助函数

- **`addArrayDimension(context, type, arraySize)`** -- 创建数组类型（如 `float[5]`）并缓存到符号表中。
- **`isType(name)`** -- 检查名称是否引用类型。
- **`isBuiltinType(name)`** -- 检查名称是否引用内建类型。
- **`wouldShadowSymbolsFrom(other)`** -- 检查当前表与另一表是否存在名称冲突。
- **`foreach(fn)`** -- 遍历当前表中的所有符号（不含父表）。
- **`takeOwnershipOfString(str)`** -- 接管字符串所有权，返回稳定的字符串指针。
- **`markModuleBoundary()`** -- 标记当前符号表的父表属于不同模块。

## 内部实现细节

### 符号查找机制

`lookup()` 方法通过 `SymbolKey`（包含名称和预计算的哈希值）在 `fSymbols` 哈希映射中查找。如果当前表未找到，则递归查找父表。`MakeSymbolKey` 静态方法使用 `SkChecksum::Hash32` 计算名称的哈希值。

### 函数重载链

当添加一个 `FunctionDeclaration` 符号时，如果已存在同名函数，系统会将已有函数设置为新函数的 `nextOverload`，从而形成重载链。这允许同名但参数不同的函数共存。

### 模块边界检查

当 `fAtModuleBoundary` 为 true 时，`addWithoutOwnership()` 会额外检查父表中是否已存在同名符号。如果存在，则视为重复定义并拒绝添加。这防止了用户代码意外覆盖模块中的符号。

### 数组类型缓存

`addArrayDimension()` 会尝试将内建类型的数组类型提升到模块边界处的符号表，以便在不同作用域间复用同一数组类型。如果符号表中已存在同名数组类型，则直接复用。

### 字符串所有权管理

`fOwnedStrings` 使用 `forward_list<string>` 存储字符串。由于链表节点的地址稳定性，返回的字符串指针在整个程序生命周期内有效。

## 依赖关系

**内部依赖：**
- `SkSLSymbol` -- 符号基类
- `SkSLType` -- 类型系统
- `SkSLFunctionDeclaration` -- 函数声明（用于重载链管理）
- `SkSLExpression` -- 表达式基类（用于 `instantiateSymbolRef`）
- `SkSLContext` -- 编译器上下文（含错误报告器和配置）
- `SkSLErrorReporter` -- 错误报告器
- `SkChecksum` -- 哈希计算
- `SkTHash` -- 哈希映射实现

**外部依赖：**
- 标准库：`<forward_list>`, `<memory>`, `<string>`, `<string_view>`, `<vector>`

## 设计模式与设计决策

1. **作用域链模式**：通过 `fParent` 指针形成链式结构，实现了经典的嵌套作用域查找。查找时从当前作用域开始，沿父表链逐级向上搜索。

2. **所有权分离**：符号表支持两种模式 -- 拥有所有权（`add`）和不拥有所有权（`addWithoutOwnership`）。这允许内建符号在多个程序间共享，而用户符号由各自的符号表管理。

3. **注入 vs 添加**：`inject` 系列方法允许强制覆盖已有符号，而 `add` 系列方法在符号已存在时报错。这提供了灵活性，同时在正常使用中维护了安全性。

4. **模板化 API**：`add<T>`、`inject<T>` 等方法使用模板，返回具体类型的指针，避免了调用者的类型转换。

5. **模块边界隔离**：`fAtModuleBoundary` 标志确保模块间的符号不会意外冲突，维护了编译单元之间的独立性。

## 性能考量

- **哈希查找**：使用预计算哈希的 `THashMap` 实现 O(1) 平均查找时间。`SymbolKey` 在创建时即计算哈希值，避免重复计算。
- **作用域链长度**：符号查找最坏情况需要遍历整个父表链，查找深度与作用域嵌套层级成正比。
- **字符串存储**：使用 `forward_list` 提供 O(1) 的插入和稳定的指针，但牺牲了缓存局部性。
- **阴影检测优化**：`wouldShadowSymbolsFrom` 始终迭代较小的哈希表以最小化比较次数。
- **数组类型复用**：将内建数组类型提升到模块边界，减少重复创建相同的数组类型。

## 相关文件

- `src/sksl/ir/SkSLSymbol.h` -- Symbol 基类定义
- `src/sksl/ir/SkSLType.h` -- 类型系统
- `src/sksl/ir/SkSLFunctionDeclaration.h` -- 函数声明和重载管理
- `src/sksl/SkSLContext.h` -- 编译器上下文
- `src/sksl/SkSLErrorReporter.h` -- 错误报告接口
- `src/core/SkChecksum.h` -- 哈希算法
- `src/core/SkTHash.h` -- 哈希容器实现
