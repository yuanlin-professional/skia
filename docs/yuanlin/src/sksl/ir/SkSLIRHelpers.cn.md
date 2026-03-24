# SkSLIRHelpers

> 源文件: src/sksl/ir/SkSLIRHelpers.h

## 概述

`IRHelpers` 提供便捷的 IR 节点构建辅助函数,简化手动创建表达式和语句的代码。采用流畅的 API 风格,使 IR 构建代码更接近实际的着色器语法。

## 架构位置

作为 IR 构建的辅助工具,主要用于代码生成和转换阶段手动创建 IR 节点。

## 主要类与结构体

### IRHelpers

```cpp
struct IRHelpers {
    IRHelpers(const Context& c) : fContext(c) {}
    const Context& fContext;
```

**核心方法:**

- `Ref(var)`: 创建变量引用
- `Field(var, idx)`: 创建字段访问
- `Swizzle(base, components)`: 创建 swizzle
- `Index(base, idx)`: 创建索引表达式
- `Binary(l, op, r)`: 创建二元表达式
- `Mul(l, r)`: 乘法表达式
- `Add(l, r)`: 加法表达式
- `Float(value)`: 浮点字面量
- `Int(value)`: 整数字面量
- `CtorXYZW(xy, z, w)`: 构建 float4
- `Assign(l, r)`: 赋值语句

## 设计决策

不遵循 Skia 命名约定(函数名大写,无 `this->` 前缀),使嵌套表达式更自然可读。例如:
```cpp
Assign(Field(var, 0), Add(Mul(Ref(x), Float(2.0)), Float(1.0)))
```

## 相关文件

**使用场景:**
- `src/sksl/codegen/*`: 代码生成器
- `src/sksl/transform/*`: IR 转换器

**创建的节点类型:**
- `SkSLVariableReference.h`, `SkSLBinaryExpression.h`, `SkSLLiteral.h` 等
