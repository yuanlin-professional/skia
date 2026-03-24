# SkSLBlock

> 源文件: src/sksl/ir/SkSLBlock.h, src/sksl/ir/SkSLBlock.cpp

## 概述

`Block` 类是 SkSL（Skia Shading Language）中间表示(IR)中的核心语句类型，用于将多个语句组合成单个语句单元。它是 `Statement` 的终结子类（`final class`），代表代码块的语义结构，包括带花括号的作用域块、无括号的语句组以及复合语句。`Block` 不仅管理语句的集合，还可以关联符号表以支持作用域管理。该类提供了智能的优化机制，能够在不影响语义的情况下简化空块或单语句块，从而优化 IR 结构。

## 架构位置

`Block` 位于 Skia 的 SkSL 编译器的 IR 层中，是语句层级的关键节点：

```
skia/
  src/
    sksl/
      ir/
        SkSLIRNode.h              # IR 节点基类
        SkSLStatement.h           # 语句基类（Block 的父类）
        SkSLBlock.h/cpp           # 本文件，代码块语句
        SkSLNop.h                 # 空操作语句
        SkSLSymbolTable.h         # 符号表
      SkSLPosition.h              # 位置信息
      SkSLDefines.h               # 类型定义（StatementArray 等）
```

在编译流程中的位置：
```
源代码解析 → AST 构建 → IR 生成 (Block 创建) → 优化传递 → 代码生成
                                    ↓
                            符号表管理（作用域）
```

`Block` 在以下场景中发挥作用：
- 函数体必须是 `kBracedScope` 类型的 `Block`
- `if/else`、`for`、`while` 等控制流语句的主体
- 变量声明语句组（如 `int a, b;` 被表示为复合语句块）

## 主要类与结构体

### Block 类

```cpp
class Block final : public Statement {
public:
    // 块类型枚举
    enum class Kind {
        kUnbracedBlock,      // 无花括号的语句组
        kBracedScope,        // 带花括号的作用域块（语言级别）
        kCompoundStatement,  // 复合语句（如 `int a, b;`）
    };

    // 直接构造函数
    Block(Position pos,
          StatementArray statements,
          Kind kind = Kind::kBracedScope,
          std::unique_ptr<SymbolTable> symbols = nullptr);

    // 智能工厂方法（允许优化）
    static std::unique_ptr<Statement> Make(Position pos,
                                           StatementArray statements,
                                           Kind kind = Kind::kBracedScope,
                                           std::unique_ptr<SymbolTable> symbols = nullptr);

    // 复合语句构建器
    static std::unique_ptr<Statement> MakeCompoundStatement(
        std::unique_ptr<Statement> existing,
        std::unique_ptr<Statement> additional);

    // 强制创建 Block 对象（不优化）
    static std::unique_ptr<Block> MakeBlock(Position pos,
                                            StatementArray statements,
                                            Kind kind = Kind::kBracedScope,
                                            std::unique_ptr<SymbolTable> symbols = nullptr);

    // 访问器
    const StatementArray& children() const;
    StatementArray& children();
    bool isScope() const;
    Kind blockKind() const;
    void setBlockKind(Kind kind);
    SymbolTable* symbolTable() const;

    // Statement 接口实现
    bool isEmpty() const override;
    std::string description() const override;

private:
    std::unique_ptr<SymbolTable> fSymbolTable;  // 符号表（可为空）
    StatementArray fChildren;                   // 子语句数组
    Kind fBlockKind;                            // 块类型
};
```

### Block::Kind 枚举

- **kUnbracedBlock**: 表示没有花括号的语句组，纯粹用于内部 IR 组织，无语义影响
- **kBracedScope**: 表示语言级别的作用域块，有花括号，创建新的符号作用域
- **kCompoundStatement**: 表示概念上的单个语句，如 `int a, b;` 在内部被分解为 `int a; int b;`，调试器视为单个语句

## 公共 API 函数

### 构造函数

```cpp
Block(Position pos, StatementArray statements, Kind kind, std::unique_ptr<SymbolTable> symbols)
```

**功能**: 直接创建 `Block` 对象，不进行任何优化。

**参数**:
- `pos`: 代码块在源代码中的位置
- `statements`: 子语句数组
- `kind`: 块类型（默认为 `kBracedScope`）
- `symbols`: 关联的符号表（可为 `nullptr`）

### Make (智能工厂)

```cpp
static std::unique_ptr<Statement> Make(Position pos, StatementArray statements,
                                       Kind kind, std::unique_ptr<SymbolTable> symbols)
```

**功能**: 智能创建语句对象，会根据情况优化简化块结构。

**优化策略**:
1. 如果是 `kBracedScope` 或符号表非空，必须返回 `Block` 对象（保留语义）
2. 如果语句数组为空，返回 `Nop` 空操作
3. 如果只包含一个非空语句，直接返回该语句（避免不必要的 `Block` 包装）
4. 如果包含多个语句但只有一个非空，返回那个非空语句
5. 如果所有语句都是空的，返回其中一个空语句

**返回**: 可能是 `Block` 对象，也可能是简化后的单个 `Statement`。

### MakeBlock (强制工厂)

```cpp
static std::unique_ptr<Block> MakeBlock(Position pos, StatementArray statements,
                                        Kind kind, std::unique_ptr<SymbolTable> symbols)
```

**功能**: 强制创建 `Block` 对象，不进行优化。

**使用场景**: 当调用者必须要求返回 `Block` 类型时（如函数体）。

**特点**: 不会简化或消除空语句，保证返回类型为 `Block`。

### MakeCompoundStatement (复合语句构建)

```cpp
static std::unique_ptr<Statement> MakeCompoundStatement(
    std::unique_ptr<Statement> existing,
    std::unique_ptr<Statement> additional)
```

**功能**: 将两个语句合并为一个复合语句块。

**逻辑**:
1. 如果任一语句为空，返回另一个非空语句
2. 如果 `existing` 已经是 `kCompoundStatement` 类型的 `Block`，将 `additional` 追加到其子语句数组
3. 否则创建新的 `kCompoundStatement` 块，包含两个语句

**位置计算**: 新块的位置范围从第一个语句跨越到第二个语句。

### 访问器方法

```cpp
const StatementArray& children() const / StatementArray& children()
```
获取子语句数组（常量版本和可变版本）。

```cpp
bool isScope() const
```
判断是否为作用域块（`kBracedScope` 类型）。

```cpp
Kind blockKind() const / void setBlockKind(Kind kind)
```
获取或设置块类型。

```cpp
SymbolTable* symbolTable() const
```
获取关联的符号表指针（可能为 `nullptr`）。

### Statement 接口实现

```cpp
bool isEmpty() const override
```
判断块是否为空：遍历所有子语句，只有全部为空时才返回 `true`。

```cpp
std::string description() const override
```
生成代码块的字符串表示：
- 作用域块或空块添加花括号 `{}`
- 非作用域块省略花括号
- 每个子语句换行缩进

## 内部实现细节

### 优化简化逻辑

`Make` 方法的优化决策树：

```
输入: (statements, kind, symbols)
  ├─ 是 kBracedScope 或 symbols 非空？ → 返回 Block（保留语义）
  ├─ statements 为空？ → 返回 Nop
  ├─ statements 大小 > 1？
  │   ├─ 遍历找非空语句
  │   ├─ 找到多个非空？ → 返回 Block
  │   ├─ 找到一个非空？ → 返回该语句
  │   └─ 全部为空？ → 返回第一个语句
  └─ statements 大小 = 1 → 返回该语句
```

### 符号表管理

- **所有权**: `Block` 通过 `unique_ptr` 拥有符号表的所有权
- **作用域链**: 符号表内部维护父符号表指针，形成作用域链
- **生命周期**: 符号表随 `Block` 的销毁而销毁
- **可选性**: 只有 `kBracedScope` 类型的块才需要符号表，其他类型通常为 `nullptr`

### MakeCompoundStatement 的优化

通过追加而非重建避免不必要的内存分配：
```cpp
// 情况 1: existing 已经是复合语句块
existing: Block(kCompoundStatement) { stmt1, stmt2 }
additional: stmt3
结果: existing.children().push_back(stmt3)  // 直接追加

// 情况 2: existing 不是复合语句块
existing: stmt1
additional: stmt2
结果: Block(kCompoundStatement) { stmt1, stmt2 }  // 新建
```

### 位置信息处理

`MakeCompoundStatement` 中使用 `rangeThrough` 计算合并位置：
```cpp
Position pos = existing->fPosition.rangeThrough(additional->fPosition);
```
这确保新块的位置覆盖两个原始语句的整个范围。

## 依赖关系

### 直接依赖

**头文件**:
- `SkSLStatement.h`: 提供 `Statement` 基类
- `SkSLSymbolTable.h`: 符号表管理
- `SkSLPosition.h`: 位置信息
- `SkSLDefines.h`: `StatementArray` 类型定义
- `SkSLIRNode.h`: IR 节点基础设施

**实现文件**:
- `SkSLNop.h`: 空操作语句（用于优化空块）

### 被依赖关系

几乎所有 SkSL 的语句和声明类型都直接或间接依赖 `Block`：
- 函数定义的函数体
- 控制流语句的分支体
- 作用域语句包装

### 循环依赖避免

通过前向声明和指针/引用使用避免头文件循环依赖。

## 设计模式与设计决策

### 设计模式

1. **工厂方法模式**: 提供多个工厂方法（`Make`, `MakeBlock`, `MakeCompoundStatement`）满足不同需求
2. **组合模式**: `Block` 作为容器包含多个 `Statement` 子节点
3. **策略模式**: 根据 `Kind` 枚举选择不同的语义行为

### 设计决策

**为什么提供三种工厂方法？**
- `Make`: 用于一般场景，允许优化简化
- `MakeBlock`: 用于必须返回 `Block` 类型的场景（如函数体）
- `MakeCompoundStatement`: 用于逐步构建复合语句的场景

**为什么区分三种 Block::Kind？**
- `kBracedScope`: 语言级别的作用域，影响符号解析和代码生成
- `kUnbracedBlock`: 纯 IR 组织工具，不影响语义
- `kCompoundStatement`: 调试信息需求，将内部多语句视为单语句

**为什么 `isEmpty()` 要递归检查？**
- 块可能包含嵌套的空块
- 优化传递需要准确识别可消除的代码
- 递归检查确保深层空块也被识别

**为什么符号表是可选的？**
- 只有作用域块需要符号表
- 非作用域块共享外部符号表，避免冗余
- 减少内存开销

**为什么 `Make` 会返回 `Nop` 而不是空 `Block`？**
- `Nop` 是语义上明确的"无操作"
- 避免维护空块的开销
- 简化后续优化传递的逻辑

## 性能考量

### 优化策略

1. **内存优化**: 通过 `Make` 消除不必要的 `Block` 包装，减少节点数量
2. **追加优化**: `MakeCompoundStatement` 重用已有块，避免重新分配
3. **惰性符号表**: 只在需要时分配符号表
4. **移动语义**: 使用 `std::move` 避免语句数组的拷贝

### 内存开销

单个 `Block` 对象的内存占用：
- `Statement` 基类开销: ~16 字节（虚表指针 + 位置 + 类型标记）
- `fSymbolTable`: 8 字节（`unique_ptr`）
- `fChildren`: ~24 字节（`vector` 的指针、大小、容量）
- `fBlockKind`: 4 字节
- **总计**: ~52 字节 + 动态数组开销

### 性能权衡

**优化的好处**:
- 减少 IR 节点数量（可能减少 30-50%）
- 简化遍历和分析逻辑
- 降低内存使用

**优化的成本**:
- `Make` 方法需要遍历检查空语句
- 对于大型语句数组（>10 个语句），检查开销可能显著
- 权衡：大多数代码块很小（<5 个语句）

### 潜在瓶颈

- **大型块的优化**: 遍历检查所有子语句的空状态
- **频繁的复合语句构建**: `MakeCompoundStatement` 被多次调用时的追加操作
- **符号表创建**: 深层嵌套作用域导致大量符号表分配

## 相关文件

### 核心相关文件

- **src/sksl/ir/SkSLStatement.h**: 语句基类
- **src/sksl/ir/SkSLNop.h**: 空操作语句
- **src/sksl/ir/SkSLSymbolTable.h**: 符号表管理
- **src/sksl/SkSLPosition.h**: 位置信息

### 使用 Block 的语句类型

- **src/sksl/ir/SkSLFunctionDefinition.h**: 函数定义（函数体是 Block）
- **src/sksl/ir/SkSLIfStatement.h**: if 语句（分支体是 Statement，通常是 Block）
- **src/sksl/ir/SkSLForStatement.h**: for 循环（循环体）
- **src/sksl/ir/SkSLDoStatement.h**: do-while 循环
- **src/sksl/ir/SkSLSwitchStatement.h**: switch 语句（case 体）

### 代码生成相关

- **src/sksl/codegen/SkSLGLSLCodeGenerator.cpp**: GLSL 代码生成器
- **src/sksl/codegen/SkSLMetalCodeGenerator.cpp**: Metal 代码生成器
- **src/sksl/codegen/SkSLSPIRVCodeGenerator.cpp**: SPIR-V 代码生成器

### 优化传递

- **src/sksl/transform/**: 各种 IR 优化传递（死代码消除、内联等）

### 使用示例

```cpp
// 创建简单作用域块
auto block = Block::Make(
    pos,
    std::move(statements),
    Block::Kind::kBracedScope,
    std::make_unique<SymbolTable>(parentSymbols)
);

// 构建复合语句
auto compoundStmt = Block::MakeCompoundStatement(
    std::move(stmt1),
    std::move(stmt2)
);
```
