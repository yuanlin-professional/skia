# SkSLIRNode

> 源文件: src/sksl/ir/SkSLIRNode.h

## 概述

`IRNode` 是 SkSL 中间表示(IR)树的根基类,定义了所有 IR 节点的公共接口和类型系统。IR 是程序的完全解析和验证后的表示,包含所有类型信息,准备进行代码生成。

## 架构位置

作为整个 IR 类型层次的根:

```
IRNode (本类)
  ├── ProgramElement (函数、全局变量等)
  ├── Symbol (符号定义)
  ├── Statement (语句)
  └── Expression (表达式)
```

## 主要类与结构体

### 枚举类型

**ProgramElementKind:** 顶层程序元素类型(函数、全局变量等)
**SymbolKind:** 符号类型(类型、变量、函数声明等)
**StatementKind:** 语句类型(Block、For、If 等)
**ExpressionKind:** 表达式类型(Binary、Literal、FunctionCall 等)

### IRNode

```cpp
class IRNode : public Poolable
```

**成员:**
```cpp
Position fPosition;  // 源码位置
int fKind;           // 节点类型(Kind 枚举值)
```

**核心方法:**

```cpp
template <typename T>
bool is() const {
    return this->fKind == (int)T::kIRNodeKind;
}
```
类型检查,替代 `dynamic_cast`。

```cpp
template <typename T>
const T& as() const {
    SkASSERT(this->is<T>());
    return static_cast<const T&>(*this);
}
```
安全向下转型。

```cpp
virtual std::string description() const = 0;
```
生成节点的文本表示,用于调试和代码生成。

## 设计决策

使用整数 `fKind` 而非虚表实现 RTTI,提供更快的类型检查和更小的内存占用。位置信息存储在每个节点,便于错误报告。禁止拷贝构造,强制使用智能指针管理生命周期。

## 相关文件

**派生类:**
- `SkSLProgramElement.h`, `SkSLStatement.h`, `SkSLExpression.h`, `SkSLSymbol.h`

**内存管理:**
- `SkSLPool.h`: 对象池分配器

**工具:**
- `SkSLPosition.h`: 源码位置信息
