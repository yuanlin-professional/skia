# SkSLProgramVisitor

> 源文件: src/sksl/analysis/SkSLProgramVisitor.h

## 概述

`SkSLProgramVisitor` 是 SkSL 编译器中用于遍历程序 IR 树的访问者模式基类。它提供了一个统一的接口来访问 SkSL 程序中的每个元素、语句和表达式,是实现各种静态分析和转换的基础设施。

该模块采用经典的访问者模式设计,允许子类通过重写虚函数来定制遍历行为。设计的核心思想是分离树的遍历逻辑和对节点的处理逻辑,使得添加新的分析或转换操作变得简单而不需要修改 IR 节点类。

## 架构位置

`ProgramVisitor` 位于 SkSL 分析层的核心位置,是整个分析基础设施的基石:

```
SkSL 编译流程:
  IR 构建
    ↓
  ┌──────────────────────────┐
  │   分析与转换层           │
  │  ┌────────────────────┐  │
  │  │ ProgramVisitor (基类) │ ← 本文件
  │  └────────────────────┘  │
  │         ↓                │
  │  各种具体访问者实现:      │
  │  - ConstantExpressionVisitor │
  │  - UsageVisitor          │
  │  - FinalizationVisitor   │
  │  - 等等...               │
  └──────────────────────────┘
    ↓
  代码生成
```

所有需要遍历 IR 树的分析和转换都继承自这个基类。

## 主要类与结构体

### TProgramVisitor (模板基类)

```cpp
template <typename T>
class TProgramVisitor
```

泛型访问者基类,支持 const 和非 const 两种访问模式。

**类型参数 T:** 定义了访问的类型语义(const 或 mutable)

**核心虚函数:**

```cpp
virtual bool visitExpression(typename T::Expression& expression);
virtual bool visitStatement(typename T::Statement& statement);
virtual bool visitProgramElement(typename T::ProgramElement& programElement);
```

**返回值语义:**
- `false`: 继续递归遍历子节点
- `true`: 停止遍历并向上传播(短路求值)

**纯虚函数:**

```cpp
virtual bool visitExpressionPtr(typename T::UniquePtrExpression& expr) = 0;
virtual bool visitStatementPtr(typename T::UniquePtrStatement& stmt) = 0;
```

这些方法由派生类实现,处理智能指针包装的节点。

### ProgramVisitorTypes

定义只读访问的类型别名:

```cpp
struct ProgramVisitorTypes {
    using Program = const SkSL::Program;
    using Expression = const SkSL::Expression;
    using Statement = const SkSL::Statement;
    using ProgramElement = const SkSL::ProgramElement;
    using UniquePtrExpression = const std::unique_ptr<SkSL::Expression>;
    using UniquePtrStatement = const std::unique_ptr<SkSL::Statement>;
};
```

所有类型都带 `const` 修饰,确保访问者不能修改 IR。

### ProgramVisitor (具体类)

```cpp
class ProgramVisitor : public TProgramVisitor<ProgramVisitorTypes>
```

只读访问者的具体实现,是最常用的访问者基类。

**公共方法:**

```cpp
bool visit(const Program& program);
```

遍历整个程序的入口点,访问程序中的所有元素。

**实现细节:**

```cpp
bool visitExpressionPtr(const std::unique_ptr<Expression>& e) final {
    return this->visitExpression(*e);
}
bool visitStatementPtr(const std::unique_ptr<Statement>& s) final {
    return this->visitStatement(*s);
}
```

这些 `final` 方法自动解引用智能指针,简化子类实现。子类通常不需要直接访问智能指针,只需重写 `visitExpression` 等方法。

## 公共 API 函数

### visit

```cpp
bool visit(const Program& program);
```

**功能:** 遍历整个 SkSL 程序

**参数:**
- `program`: 待遍历的程序对象

**返回值:**
- `false`: 成功遍历所有节点
- `true`: 遍历过程中被中断(某个 visit 方法返回了 `true`)

**用法示例:**

```cpp
class MyVisitor : public ProgramVisitor {
    bool visitExpression(const Expression& expr) override {
        // 处理表达式
        return INHERITED::visitExpression(expr);  // 继续递归
    }
};

MyVisitor visitor;
visitor.visit(program);
```

### visitExpression

```cpp
virtual bool visitExpression(typename T::Expression& expression);
```

**功能:** 访问单个表达式节点

**子类重写策略:**
1. 检查表达式类型
2. 执行自定义逻辑
3. 决定是否继续递归:
   - 调用 `INHERITED::visitExpression(expr)` 继续遍历子节点
   - 返回 `true` 停止遍历
   - 返回 `false` 继续遍历但不递归子节点(需自行控制)

### visitStatement

```cpp
virtual bool visitStatement(typename T::Statement& statement);
```

**功能:** 访问单个语句节点

**行为:** 与 `visitExpression` 类似,支持自定义递归控制

### visitProgramElement

```cpp
virtual bool visitProgramElement(typename T::ProgramElement& programElement);
```

**功能:** 访问顶层程序元素(函数定义、全局变量等)

**行为:** 是程序遍历的入口级别,通常会递归到语句和表达式

## 内部实现细节

### 模板实例化

代码使用外部模板声明避免重复实例化:

```cpp
extern template class TProgramVisitor<ProgramVisitorTypes>;
```

这优化了编译时间和二进制大小,因为模板实例化只发生在 `.cpp` 文件中。

### 智能指针处理

访问者区分原始引用和智能指针:
- `visitExpression` 等处理原始引用,是子类主要重写的方法
- `visitExpressionPtr` 等处理智能指针,通常由具体类(如 `ProgramVisitor`)自动实现

`ProgramVisitor` 将指针访问方法标记为 `final`,防止子类错误重写:

```cpp
bool visitExpressionPtr(const std::unique_ptr<Expression>& e) final {
    return this->visitExpression(*e);
}
```

### 递归遍历机制

基类的默认实现会递归遍历 IR 树:
- 表达式包含子表达式(如 `BinaryExpression` 有左右操作数)
- 语句可能包含子语句(如 `Block` 包含语句列表)
- 程序元素包含语句(如 `FunctionDefinition` 包含函数体)

子类通过调用 `INHERITED::visitXxx()` 触发递归。

## 依赖关系

**核心依赖:**
- `src/sksl/ir/SkSLProgram.h`: 程序结构定义
- `src/sksl/ir/SkSLExpression.h`: 表达式节点
- `src/sksl/ir/SkSLStatement.h`: 语句节点
- `src/sksl/ir/SkSLProgramElement.h`: 程序元素

**STL 依赖:**
- `<memory>`: `std::unique_ptr` 支持

**被依赖文件(示例):**
- `SkSLIsConstantExpression.cpp`: `ConstantExpressionVisitor`
- `SkSLFinalizationChecks.cpp`: `FinalizationVisitor`
- `SkSLProgramUsage.cpp`: `UsageVisitor`
- `SkSLGetLoopUnrollInfo.cpp`: 循环分析访问者

## 设计模式与设计决策

### 访问者模式 (Visitor Pattern)

经典的 GoF 设计模式,解决在不修改元素类的情况下定义新操作的问题。

**优势:**
- **开闭原则:** 添加新分析不需要修改 IR 节点类
- **单一职责:** 每个访问者专注于一种分析
- **类型安全:** 编译时检查节点类型

**与传统访问者的区别:**
- IR 节点不需要 `accept` 方法
- 访问者通过类型判断和向下转型访问具体节点

### 双模式设计 (Const/Mutable)

使用模板支持两种访问模式:
- `ProgramVisitor`: 只读访问,用于分析
- `ProgramWriter`: 可写访问,用于转换(在其他文件中定义)

这种设计通过类型系统强制只读语义,防止分析过程意外修改 IR。

### 短路求值机制

返回值 `bool` 实现早期退出:
```cpp
if (visitExpression(expr1)) return true;  // 发现问题,立即停止
if (visitExpression(expr2)) return true;
```

这对于错误检测特别有用,一旦发现问题就可以停止遍历。

### 继承辅助宏

子类通常定义:
```cpp
using INHERITED = ProgramVisitor;
```

然后调用 `INHERITED::visitExpression(expr)`,这种模式:
- 简化基类更改的影响
- 明确表示递归意图
- 提高代码可读性

### 最小接口原则

基类只提供三个核心虚函数,保持接口简洁:
- `visitExpression`
- `visitStatement`
- `visitProgramElement`

这减少了子类的实现负担,大多数分析只需重写其中一两个方法。

## 性能考量

### 虚函数开销

每次节点访问都是虚函数调用,这是访问者模式的固有成本。然而:
- 现代 CPU 的分支预测减轻了虚函数开销
- 相比于树遍历的内存访问,虚函数开销可忽略不计

### 内联优化

将 `visitExpressionPtr` 等方法标记为 `final` 允许编译器内联这些方法,消除一层虚函数调用。

### 单次遍历

访问者模式鼓励在单次遍历中收集所有需要的信息,避免多次遍历 IR 树。

### 外部模板实例化

使用 `extern template` 避免在每个编译单元重复实例化模板,减少编译时间和目标文件大小。

## 相关文件

**派生访问者(分析类):**
- `SkSLIsConstantExpression.cpp`: `ConstantExpressionVisitor`, `ES2IndexingVisitor`
- `SkSLProgramUsage.cpp`: `UsageVisitor`
- `SkSLFinalizationChecks.cpp`: `FinalizationVisitor`

**派生访问者(转换类):**
- `src/sksl/transform/SkSLProgramWriter.h`: 可写访问者基类

**IR 定义:**
- `src/sksl/ir/*.h`: 各种 IR 节点定义

**使用示例:**
- `src/sksl/SkSLAnalysis.cpp`: 多个分析功能的实现
