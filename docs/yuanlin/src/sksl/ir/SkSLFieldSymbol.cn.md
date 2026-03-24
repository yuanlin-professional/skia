# SkSLFieldSymbol

> 源文件: src/sksl/ir/SkSLFieldSymbol.h

## 概述

`FieldSymbol` 表示结构体字段的符号,用于处理裸标识符应解析为字段访问的情况。这主要发生在声明匿名接口块时,其字段直接进入符号表。

## 架构位置

作为符号表条目,将标识符绑定到结构体字段,简化 GLSL 匿名接口块的语义。

## 主要类与结构体

### FieldSymbol

```cpp
class FieldSymbol final : public Symbol
```

**成员:**
```cpp
const Variable* fOwner;    // 拥有此字段的变量(接口块)
int fFieldIndex;           // 字段在结构体中的索引
```

**构造:**
```cpp
FieldSymbol(Position pos, const Variable* owner, int fieldIndex)
```

从 owner 的类型中提取字段名称和类型。

**核心方法:**
```cpp
int fieldIndex() const           // 返回字段索引
const Variable& owner() const    // 返回拥有者变量
```

**描述:**
```cpp
std::string description() const override
```
生成 `owner.fieldName` 或 `fieldName`(对于匿名拥有者)。

## 设计决策

简化匿名接口块的实现,允许 `fieldName` 直接引用而非 `blockName.fieldName`。字段符号指向实际的拥有者变量和字段索引,在代码生成时转换为正确的访问语法。

## 相关文件

- `SkSLSymbol.h`: 符号基类
- `SkSLVariable.h`: 拥有者变量
- `SkSLInterfaceBlock.h`: 匿名接口块
- `SkSLFieldAccess.h`: 实际的字段访问表达式
