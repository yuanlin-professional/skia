# SkSLModifiers

> 源文件: src/sksl/ir/SkSLModifiers.h

## 概述

`Modifiers` 结构体封装了 SkSL 声明的修饰符信息,包括布局限定符、存储限定符和其他属性标志。修饰符控制变量的存储位置、访问权限和着色器行为。

## 架构位置

作为变量、参数和函数声明的附属信息,在类型检查和代码生成阶段使用。

## 主要类与结构体

### Modifiers

```cpp
struct Modifiers {
    Position fPosition;          // 修饰符的源码位置
    SkSL::Layout fLayout;        // 布局限定符(binding, location 等)
    SkSL::ModifierFlags fFlags;  // 修饰符标志(const, in, out 等)
};
```

**fLayout:** 存储 `layout(...)` 中的所有限定符,如 `binding=0`, `location=1`, `set=2` 等。

**fFlags:** 位标志集合,表示 `const`, `in`, `out`, `inout`, `uniform`, `varying` 等修饰符。

## 设计决策

使用简单的 POD 结构,方便拷贝和传递。将布局和标志分离,清晰区分两类修饰符的语义。

## 相关文件

- `SkSLLayout.h`: 布局限定符定义
- `SkSLModifierFlags.h`: 修饰符标志位定义
- `SkSLVariable.h`: 使用修饰符的变量类
- `SkSLFunctionDeclaration.h`: 使用修饰符的函数声明
