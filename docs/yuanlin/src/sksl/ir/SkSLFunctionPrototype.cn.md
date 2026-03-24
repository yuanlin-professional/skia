# SkSLFunctionPrototype

> 源文件: src/sksl/ir/SkSLFunctionPrototype.h

## 概述

`FunctionPrototype` 表示函数原型声明(前向声明),不包含函数体。用于声明稍后定义的函数,或声明外部函数。

## 主要类与结构体

### FunctionPrototype
```cpp
class FunctionPrototype final : public ProgramElement
```

**成员:** 指向 `FunctionDeclaration` 的指针
**用途:** 在定义前声明函数签名

**工厂方法:** `Make(Position pos, const FunctionDeclaration* declaration)`

## 设计决策

分离声明和定义,支持前向引用和递归函数。原型只包含签名信息,不占用大量内存。

## 相关文件

- `SkSLFunctionDeclaration.h`: 函数签名
- `SkSLFunctionDefinition.h`: 带函数体的完整定义
- `SkSLProgramElement.h`: 顶层元素基类
