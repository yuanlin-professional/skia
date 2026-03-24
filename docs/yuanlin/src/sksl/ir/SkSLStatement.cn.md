# SkSLStatement

> 源文件: src/sksl/ir/SkSLStatement.h

## 概述

`Statement` 是所有 SkSL 语句节点的抽象基类,定义了语句的通用接口和类型标识。所有可执行的代码块、控制流和声明语句都继承自此类。

## 架构位置

位于 SkSL IR 层次结构的根部,是语句类型体系的顶层抽象:

```
IRNode (所有 IR 节点基类)
  ↓
Statement (本类) ← 语句抽象基类
  ↓
├── Block          (代码块)
├── BreakStatement (break 语句)
├── ForStatement   (for 循环)
├── IfStatement    (if 条件)
└── ... (其他语句类型)
```

## 主要类与结构体

### Statement

```cpp
class Statement : public IRNode
```

**构造函数:**
```cpp
Statement(Position pos, Kind kind)
    : INHERITED(pos, (int) kind)
```

**核心方法:**

```cpp
Kind kind() const {
    return (Kind) fKind;
}
```
返回语句的具体类型。

```cpp
virtual bool isEmpty() const {
    return false;
}
```
判断语句是否为空(如 Nop),默认返回 `false`。

## 公共 API 函数

### kind
返回语句类型,用于类型判断和向下转型。

### isEmpty
检查语句是否为空操作,用于优化(删除空语句)。

## 设计决策

使用 `Kind` 枚举而非虚函数表实现类型识别,节省内存并提高缓存性能。所有语句共享相同的基类接口,简化遍历和分析逻辑。

## 相关文件

**派生类:**
- `SkSLBlock.h`, `SkSLBreakStatement.h`, `SkSLForStatement.h` 等

**基础设施:**
- `SkSLIRNode.h`: IR 节点基类
- `SkSLProgramVisitor.h`: 语句遍历工具
