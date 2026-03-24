# SkSLIsConstantExpression

> 源文件: src/sksl/analysis/SkSLIsConstantExpression.cpp

## 概述

`SkSLIsConstantExpression.cpp` 实现了 SkSL 编译器中常量表达式的验证功能。该模块负责判断表达式是否符合 ES2 标准定义的常量表达式规则,并验证数组索引表达式是否为常量索引表达式。这对于确保 SkSL 程序符合 GLSL ES2 规范至关重要,特别是在需要编译时常量的上下文中(如数组大小、case 标签等)。

该文件的核心功能包括两个主要方面:
1. 判断任意表达式是否为常量表达式
2. 验证程序元素中的所有索引表达式是否符合 ES2 常量索引规范

## 架构位置

此文件位于 SkSL 编译器的分析层,路径为 `src/sksl/analysis/`。它作为静态分析工具的一部分,在编译流程的语义检查阶段使用:

```
SkSL 编译器架构:
  词法分析 (Lexer)
    ↓
  语法分析 (Parser)
    ↓
  语义分析 (Analysis) ← 本文件所在层
    ├── 常量表达式验证 (IsConstantExpression)
    ├── 类型检查
    └── 其他分析
    ↓
  IR 优化
    ↓
  代码生成
```

该模块与 SkSL 的 IR 层紧密配合,访问和分析表达式树结构。

## 主要类与结构体

### ConstantExpressionVisitor

继承自 `ProgramVisitor`,实现常量表达式的递归验证。

**成员变量:**
- `fLoopIndices`: 指向循环索引变量集合的指针,用于常量索引表达式验证

**核心方法:**
- `visitExpression(const Expression& e)`: 访问并验证表达式节点

**验证规则:**
根据 ES2 规范,常量表达式可以是:
- 字面量 (`kLiteral`)
- 设置值 (`kSetting`)
- 带 `const` 修饰的全局或局部变量
- 循环索引变量(仅用于常量索引表达式)
- 由上述元素组成的复合表达式

**排除项:**
- 函数调用(即使参数都是常量)
- 序列表达式(逗号运算符)
- 无效的引用类型

### ES2IndexingVisitor

继承自 `ProgramVisitor`,验证函数中的所有数组索引是否为常量索引表达式。

**成员变量:**
- `fErrors`: 错误报告器引用
- `fLoopIndices`: 当前作用域内的循环索引变量集合

**核心方法:**
- `visitStatement(const Statement& s)`: 访问语句,管理 `for` 循环索引的生命周期
- `visitExpression(const Expression& e)`: 验证索引表达式

**功能:**
- 跟踪嵌套 `for` 循环的索引变量
- 确保所有 `IndexExpression` 使用常量索引表达式
- 在索引变量离开作用域时自动清理

## 公共 API 函数

### Analysis::IsConstantExpression

```cpp
bool Analysis::IsConstantExpression(const Expression& expr)
```

**功能:** 判断给定表达式是否为常量表达式

**参数:**
- `expr`: 待验证的表达式

**返回值:** 如果表达式是常量表达式返回 `true`,否则返回 `false`

**实现细节:**
- 创建 `ConstantExpressionVisitor` 实例,不传入循环索引集合
- 通过访问者模式遍历表达式树
- 返回验证结果的逻辑反转(visitor 返回 `true` 表示失败)

### Analysis::ValidateIndexingForES2

```cpp
void Analysis::ValidateIndexingForES2(const ProgramElement& pe, ErrorReporter& errors)
```

**功能:** 验证程序元素中的索引表达式是否符合 ES2 规范

**参数:**
- `pe`: 待验证的程序元素
- `errors`: 错误报告器,用于记录验证失败信息

**实现细节:**
- 创建 `ES2IndexingVisitor` 实例
- 遍历程序元素的所有语句和表达式
- 自动跟踪循环索引变量的作用域
- 对每个索引表达式进行常量验证

## 内部实现细节

### 常量表达式的分类验证

代码通过 `switch` 语句对不同类型的表达式进行分类处理:

1. **直接认可的常量:**
   - 字面量(数字、布尔值等)
   - 设置值(fragment processor 中的参数)

2. **条件认可的常量:**
   - 变量引用:必须是 `const` 修饰的全局或局部变量
   - 对于常量索引表达式,还允许循环索引变量

3. **递归验证的表达式:**
   - 构造器表达式(数组、结构体、向量等)
   - 字段访问、索引、swizzle
   - 前缀、后缀、三元运算符
   - 二元表达式(排除逗号运算符)

4. **明确拒绝的表达式:**
   - 函数调用(尽管 GLSL 规范允许内置函数的常量调用,但 SkSL 通过优化将其折叠为字面量)
   - 引用类型(`FunctionReference`, `MethodReference`, `TypeReference`)
   - 错误节点(`Poison`, `Empty`)

### 循环索引管理

`ES2IndexingVisitor` 在访问 `ForStatement` 时:
1. 获取循环初始化器中的变量
2. 将变量添加到 `fLoopIndices` 集合
3. 递归访问循环体
4. 从集合中移除变量,确保作用域正确

这种设计支持嵌套循环,每层循环的索引变量在其作用域内都有效。

### 错误报告

当发现非常量索引表达式时,通过 `ErrorReporter` 报告位置和错误信息:
```cpp
fErrors.error(i.fPosition, "index expression must be constant");
```

## 依赖关系

**外部依赖:**
- `src/sksl/SkSLAnalysis.h`: 分析功能的公共接口
- `src/sksl/SkSLErrorReporter.h`: 错误报告机制
- `src/sksl/analysis/SkSLProgramVisitor.h`: 访问者模式基类

**IR 节点依赖:**
- `SkSLExpression.h`: 表达式基类
- `SkSLBinaryExpression.h`: 二元表达式
- `SkSLIndexExpression.h`: 索引表达式
- `SkSLForStatement.h`: for 循环语句
- `SkSLVariable.h`, `SkSLVariableReference.h`: 变量相关
- `SkSLVarDeclarations.h`: 变量声明

**工具依赖:**
- `src/core/SkTHash.h`: 哈希集合容器
- `SkSLOperator.h`: 运算符定义

## 设计模式与设计决策

### 访问者模式

使用 `ProgramVisitor` 作为基类,实现两个专门的访问者:
- 分离关注点:常量验证和索引验证使用不同的访问者
- 可扩展性:易于添加新的分析类型
- 统一遍历:利用基类提供的递归遍历机制

### 双重返回语义

`visitExpression` 返回 `bool`,语义为"是否应停止遍历":
- `true`: 发现非常量表达式,停止遍历
- `false`: 当前节点有效,继续检查子节点

公共 API `IsConstantExpression` 对结果取反,返回直观的布尔语义。

### 延迟验证策略

索引表达式验证在需要时才执行,而不是在解析时立即验证:
- 灵活性:不同的编译目标有不同的要求
- 性能:只在需要时执行昂贵的遍历
- 模块化:验证逻辑独立于 IR 构建

### 内联优化处理

代码注释指出,SkSL 不直接处理内置函数的常量调用,而是依赖 `FunctionCall::Make` 在构建时进行常量折叠:
```cpp
// SkSL handles this by optimizing fully-constant function calls
// into literals in FunctionCall::Make.
```

这种设计将优化和验证分离,简化了常量验证的逻辑。

## 性能考量

### 最小化遍历

`ConstantExpressionVisitor` 采用短路求值:
- 一旦发现非常量节点,立即返回 `true` 停止遍历
- 避免检查已知非常量表达式的子树

### 哈希集合查找

使用 `THashSet` 存储循环索引,提供 O(1) 的查找性能:
```cpp
return !fLoopIndices || !fLoopIndices->contains(v);
```

### 栈式作用域管理

循环索引通过栈式添加/移除管理,避免复制整个集合:
```cpp
fLoopIndices.add(var);
// ... 递归访问
fLoopIndices.remove(var);
```

### 避免冗余验证

`ValidateIndexingForES2` 仅在需要 ES2 兼容性时调用,其他情况下不执行这些检查,节省编译时间。

## 相关文件

**同目录分析工具:**
- `SkSLProgramVisitor.h`: 访问者基类定义
- `SkSLProgramUsage.cpp`: 符号使用分析
- `SkSLGetLoopUnrollInfo.cpp`: 循环展开信息提取

**IR 表示:**
- `src/sksl/ir/SkSLExpression.h`: 表达式节点类型定义
- `src/sksl/ir/SkSLStatement.h`: 语句节点基类

**优化相关:**
- `src/sksl/SkSLConstantFolder.cpp`: 常量折叠优化

**代码生成:**
- ES2 代码生成器依赖此模块确保生成符合规范的代码

**测试文件:**
- `tests/sksl/shared/ConstantExpression.sksl`: 常量表达式测试用例
