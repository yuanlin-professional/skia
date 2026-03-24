# SkSLSymbolTableStackBuilder

> 源文件: src/sksl/analysis/SkSLSymbolTableStackBuilder.cpp

## 概述

`SkSLSymbolTableStackBuilder` 是一个轻量级的 RAII(Resource Acquisition Is Initialization)辅助类,用于管理 SkSL 符号表栈的生命周期。在遍历包含作用域的语句(如代码块和 for 循环)时,该类自动将相应的符号表压入栈,并在析构时自动弹出,确保作用域管理的正确性和代码的简洁性。

该类主要用于配合 SkSL 的各种分析和转换工具,在需要维护符号解析上下文时提供简单可靠的栈管理机制。

## 架构位置

此类位于 SkSL 分析工具层,作为符号解析的基础设施:

```
SkSL 符号管理:
  SymbolTable (符号表)
      ↓
  SymbolTable Stack (符号表栈)
      ↓
  ┌────────────────────────────┐
  │ SymbolTableStackBuilder    │ ← 本文件
  │ (RAII 栈管理)               │
  └────────────────────────────┘
      ↓
  各种分析器和转换器使用
```

该类通常在遍历 IR 树时使用,配合访问者模式或其他遍历策略。

## 主要类与结构体

### Analysis::SymbolTableStackBuilder

```cpp
class SymbolTableStackBuilder
```

RAII 风格的符号表栈管理器。

**构造函数:**

```cpp
SymbolTableStackBuilder(const Statement* stmt, std::vector<SymbolTable*>* stack)
```

**参数:**
- `stmt`: 待处理的语句,可能包含符号表
- `stack`: 符号表栈的指针,由调用者维护

**功能:**
- 检查语句类型(Block 或 ForStatement)
- 如果语句包含符号表,将其压入栈
- 记录是否需要在析构时弹出

**析构函数:**

```cpp
~SymbolTableStackBuilder()
```

**功能:**
- 如果构造时压入了符号表,自动从栈中弹出
- 使用 `fStackToPop` 指针判断是否需要操作

**成员变量:**

```cpp
std::vector<SymbolTable*>* fStackToPop = nullptr;
```

如果为 `nullptr`,表示没有符号表被压入,析构时无操作;否则指向需要弹出的栈。

## 公共 API 函数

### 构造函数实现

```cpp
SymbolTableStackBuilder::SymbolTableStackBuilder(const Statement* stmt,
                                                 std::vector<SymbolTable*>* stack)
```

**内部逻辑:**

1. **空语句检查:**
```cpp
if (stmt) {
    // 处理...
}
```

2. **语句类型分发:**
```cpp
switch (stmt->kind()) {
    case Statement::Kind::kBlock:
        if (SymbolTable* symbols = stmt->as<Block>().symbolTable()) {
            stack->push_back(symbols);
            fStackToPop = stack;
        }
        break;

    case Statement::Kind::kFor:
        if (SymbolTable* symbols = stmt->as<ForStatement>().symbols()) {
            stack->push_back(symbols);
            fStackToPop = stack;
        }
        break;

    default:
        break;
}
```

只处理 `Block` 和 `ForStatement`,其他语句类型不产生新作用域。

### 析构函数实现

```cpp
SymbolTableStackBuilder::~SymbolTableStackBuilder() {
    if (fStackToPop) {
        fStackToPop->pop_back();
    }
}
```

简单而可靠:如果记录了栈指针,就弹出一个元素。

## 内部实现细节

### RAII 模式

该类是 RAII 模式的典型应用:
- **获取资源:** 构造时将符号表压入栈
- **释放资源:** 析构时自动弹出符号表
- **异常安全:** 即使发生异常,析构函数也会被调用

### 空指针语义

`fStackToPop` 使用空指针表示"无操作":
- 简化了条件判断
- 避免了额外的布尔标志
- 直接记录需要操作的栈指针

### 选择性处理

只有 `Block` 和 `ForStatement` 创建新作用域:
- **Block:** 花括号包围的代码块,如 `if`、`while` 的主体
- **ForStatement:** for 循环的初始化器声明的变量有独立作用域

其他语句(如 `BreakStatement`、`ReturnStatement`)不创建作用域,不需要栈操作。

### 符号表的可选性

代码检查符号表是否存在:
```cpp
if (SymbolTable* symbols = stmt->as<Block>().symbolTable()) {
    // ...
}
```

某些 Block 可能没有符号表(如空块或没有声明新符号的块),这是优化的结果。

## 依赖关系

**核心依赖:**
- `src/sksl/SkSLAnalysis.h`: 分析功能的命名空间
- `src/sksl/ir/SkSLBlock.h`: 代码块语句
- `src/sksl/ir/SkSLForStatement.h`: for 循环语句
- `src/sksl/ir/SkSLStatement.h`: 语句基类

**间接依赖:**
- `SymbolTable`: 符号表类(未直接包含,通过前向声明)

**标准库:**
- `<vector>`: 栈容器

**被使用的场景:**
- 符号查找时维护作用域链
- 变量阴影(shadowing)检查
- 作用域内变量收集

## 设计模式与设计决策

### RAII (Resource Acquisition Is Initialization)

这是 C++ 中管理资源的标准模式:

**优势:**
- **自动清理:** 无需手动调用清理函数
- **异常安全:** 栈展开时自动释放资源
- **简化代码:** 减少 `try-finally` 风格的代码

**应用场景:**
```cpp
{
    SymbolTableStackBuilder builder(&block, &symbolStack);
    // 符号表已压入,可以进行查找
    // ...
}  // 自动弹出符号表
```

### 轻量级设计

该类非常轻量:
- 只有一个指针成员(8 字节)
- 构造和析构都是简单的栈操作
- 不涉及内存分配或复杂逻辑

### 栈外部管理

符号表栈由调用者拥有和维护:
- 类只负责压入/弹出操作
- 不拥有栈的生命周期
- 支持在不同上下文中复用栈

### 类型安全的作用域绑定

通过语句类型分发,确保只有真正创建作用域的语句才操作栈:
- 编译时类型检查
- 避免运行时的错误状态

## 性能考量

### 零开销原则

当语句不包含符号表时:
- 构造函数只是几次条件判断
- 析构函数只检查一个空指针
- 不产生任何栈操作开销

### 内联潜力

所有方法都很短小,编译器可以内联:
- 消除函数调用开销
- 优化器可以进一步简化逻辑

### 栈操作成本

`vector::push_back` 和 `pop_back` 在栈不需要重新分配时是 O(1) 操作,且:
- 通常只涉及指针或整数的复制
- 没有内存分配
- 高度缓存友好

### 避免递归栈溢出

在深层嵌套的代码中,使用显式栈而非递归:
- 防止栈溢出
- 更容易控制遍历顺序
- 支持迭代式算法

## 相关文件

**符号表系统:**
- `src/sksl/SkSLSymbolTable.h`: 符号表定义
- `src/sksl/ir/SkSLSymbol.h`: 符号基类

**语句类型:**
- `src/sksl/ir/SkSLBlock.h`: 代码块
- `src/sksl/ir/SkSLForStatement.h`: for 循环
- `src/sksl/ir/SkSLStatement.h`: 语句基类

**使用该类的分析器:**
- 符号解析器
- 变量使用分析
- 作用域相关的转换

**类似的 RAII 辅助类:**
- `AutoSymbolTable`: 自动创建和销毁符号表
- `PoolAttachment`: 管理内存池附件

**测试:**
- 作用域相关的单元测试
- 符号查找测试
