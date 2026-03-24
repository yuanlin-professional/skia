# SkSLProgramElement

> 源文件: src/sksl/ir/SkSLProgramElement.h

## 概述

`ProgramElement` 是程序顶层元素的抽象基类,表示函数定义、全局变量声明、结构体定义等顶层构造。

## 架构位置

位于 IR 层次结构的顶层,与 `Statement` 和 `Expression` 并列:

```
IRNode
  ├── ProgramElement (本类) ← 顶层元素
  │   ├── FunctionDefinition
  │   ├── GlobalVarDeclaration
  │   └── StructDefinition
  ├── Statement
  └── Expression
```

## 主要类与结构体

### ProgramElement

```cpp
class ProgramElement : public IRNode
```

**构造:**
```cpp
ProgramElement(Position pos, Kind kind)
    : INHERITED(pos, (int) kind)
```

**类型方法:**
```cpp
Kind kind() const {
    return (Kind) fKind;
}
```

## 设计决策

作为纯抽象基类,只提供类型标识,不包含任何数据成员。所有具体信息由派生类实现。

## 相关文件

**派生类:**
- `SkSLFunctionDefinition.h`: 函数定义
- `SkSLGlobalVarDeclaration.h`: 全局变量
- `SkSLInterfaceBlock.h`: 接口块
- `SkSLStructDefinition.h`: 结构体定义

**基类:**
- `SkSLIRNode.h`: IR 节点根类
