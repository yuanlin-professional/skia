# SkSLIsTrivialExpression

> 源文件: src/sksl/analysis/SkSLIsTrivialExpression.cpp

## 概述

`SkSLIsTrivialExpression` 模块提供了判断 SkSL 表达式是否"平凡"(trivial)的功能。平凡表达式是指那些计算成本极低、可以安全内联或复制而不会导致性能问题或副作用的表达式。这个分析对于 SkSL 编译器的优化决策至关重要,特别是在决定是否内联表达式、是否需要引入临时变量等场景。

该模块实现了 `Analysis::IsTrivialExpression` 函数,通过递归分析表达式树来判断其是否满足平凡性条件。平凡表达式通常包括字面量、变量引用、简单的 swizzle 和字段访问等。

## 架构位置

此文件位于 SkSL 分析层,为编译器优化提供决策依据:

```
SkSL 编译器:
  解析 → IR 构建 → 分析与优化 ← 本模块
                    ├── 平凡性分析 (IsTrivialExpression)
                    ├── 常量性分析
                    ├── 副作用分析
                    └── ...
                    ↓
                  代码生成
```

该模块通常在以下场景中被调用:
- 优化器决定是否内联表达式
- 判断是否需要引入临时变量
- 代码生成阶段的表达式复制决策

## 主要类与结构体

本文件没有定义类或结构体,只提供一个独立的分析函数。

## 公共 API 函数

### Analysis::IsTrivialExpression

```cpp
bool Analysis::IsTrivialExpression(const Expression& expr)
```

**功能:** 判断表达式是否为平凡表达式

**参数:**
- `expr`: 待分析的表达式引用

**返回值:**
- `true`: 表达式是平凡的,可以安全复制或内联
- `false`: 表达式不平凡,需要谨慎处理

**平凡表达式的定义:**

1. **字面量 (Literal):** 数字、布尔值等常量
2. **变量引用 (VariableReference):** 简单的变量访问
3. **Swizzle:** 向量的分量重排,如 `v.xyz`
4. **前缀运算符 (Prefix):**
   - 一元正号 (`+`)
   - 一元负号 (`-`)
   - 逻辑非 (`!`)
   - 按位取反 (`~`)
5. **字段访问 (FieldAccess):** 结构体字段访问
6. **常量索引 (Index):** 数组或向量的常量索引访问
7. **小型编译时常量构造器:**
   - 数组/结构体构造器,但需满足:
     - 槽位数量 ≤ 4
     - 所有元素都是编译时常量
   - 复合构造器(向量、矩阵),需是编译时常量
   - 单参数构造器(类型转换、splat、对角矩阵),需参数平凡

**非平凡表达式:**

- **函数调用:** 可能有副作用或计算成本高
- **数组转换 (ConstructorArrayCast):** Metal 需要函数调用
- **矩阵调整大小 (ConstructorMatrixResize):** Metal 需要函数调用
- **复杂构造器:** 超过 4 个槽位或非常量的构造器
- **二元运算:** 涉及计算,不算平凡
- **三元运算:** 包含分支逻辑

## 内部实现细节

### 递归分析策略

函数使用 `switch` 语句对表达式类型进行分类,对于组合表达式递归检查其子表达式:

```cpp
case Expression::Kind::kSwizzle:
    return IsTrivialExpression(*expr.as<Swizzle>().base());
```

### 特殊处理的构造器

代码对不同类型的构造器有细致的处理:

1. **数组和结构体构造器:**
```cpp
case Expression::Kind::kConstructorArray:
case Expression::Kind::kConstructorStruct:
    return expr.type().slotCount() <= 4 && IsCompileTimeConstant(expr);
```
限制大小为 4,避免内联大型数据结构。

2. **禁止的构造器:**
```cpp
case Expression::Kind::kConstructorArrayCast:
case Expression::Kind::kConstructorMatrixResize:
    return false;  // Metal needs function calls
```
这些操作在某些后端(如 Metal)需要函数调用,不能视为平凡。

3. **单参数构造器:**
```cpp
case Expression::Kind::kConstructorCompoundCast:
case Expression::Kind::kConstructorScalarCast:
case Expression::Kind::kConstructorSplat:
case Expression::Kind::kConstructorDiagonalMatrix:
    SkASSERT(expr.asAnyConstructor().argumentSpan().size() == 1);
    const Expression& inner = *expr.asAnyConstructor().argumentSpan().front();
    return IsTrivialExpression(inner);
```
只有当参数平凡时,构造器才平凡。

### 索引表达式的验证

常量索引访问被认为是平凡的:
```cpp
case Expression::Kind::kIndex:
    const IndexExpression& inner = expr.as<IndexExpression>();
    return inner.index()->isIntLiteral() && IsTrivialExpression(*inner.base());
```

必须同时满足:
- 索引是整数字面量
- 被索引的基础表达式也是平凡的

### 前缀运算符的白名单

只有特定的前缀运算符被视为平凡:
```cpp
case Expression::Kind::kPrefix:
    switch (prefix.getOperator().kind()) {
        case OperatorKind::PLUS:
        case OperatorKind::MINUS:
        case OperatorKind::LOGICALNOT:
        case OperatorKind::BITWISENOT:
            return IsTrivialExpression(*prefix.operand());
        default:
            return false;
    }
```

自增/自减等修改操作数的运算符不被视为平凡。

## 依赖关系

**核心依赖:**
- `src/sksl/SkSLAnalysis.h`: 分析功能的命名空间定义
- `src/sksl/ir/SkSLExpression.h`: 表达式基类
- `src/sksl/ir/SkSLType.h`: 类型系统

**具体表达式类型:**
- `SkSLConstructor.h`: 各种构造器表达式
- `SkSLFieldAccess.h`: 字段访问
- `SkSLIndexExpression.h`: 索引表达式
- `SkSLPrefixExpression.h`: 前缀运算符
- `SkSLSwizzle.h`: Swizzle 操作

**辅助分析:**
- `IsCompileTimeConstant`: 编译时常量判断(在 `SkSLAnalysis.cpp` 中定义)

**标准库:**
- `include/core/SkSpan.h`: 数组视图
- `include/core/SkTypes.h`: 基础类型定义

## 设计模式与设计决策

### 保守策略

代码采用保守的判断策略:当不确定时,倾向于将表达式判定为非平凡。这确保:
- 不会错误地内联复杂表达式
- 避免在某些后端产生低效代码
- 保证代码生成的正确性优先于激进优化

### 平台兼容性考虑

某些操作在不同后端有不同的成本:
```cpp
// These operations require function calls in Metal
case Expression::Kind::kConstructorArrayCast:
case Expression::Kind::kConstructorMatrixResize:
    return false;
```

设计考虑了最坏情况(Metal 后端),确保所有平台的一致性。

### 大小阈值

限制小型构造器为 4 个槽位:
```cpp
expr.type().slotCount() <= 4
```

这个魔数基于经验,平衡了内联收益和代码膨胀风险。4 个槽位对应 `vec4` 或 4 个 `float`,是 GPU 编程中常见的大小。

### 组合性原则

平凡性是可组合的:
- 平凡表达式的 swizzle 是平凡的
- 平凡表达式的字段访问是平凡的
- 平凡参数的单参数构造器是平凡的

这种递归定义简化了分析逻辑。

## 性能考量

### 快速路径

对最常见的情况(字面量、变量引用)使用快速路径,直接返回 `true`:
```cpp
case Expression::Kind::kLiteral:
case Expression::Kind::kVariableReference:
    return true;
```

### 避免深度递归

对于大型表达式树,递归可能导致栈溢出。然而:
- SkSL 表达式通常不会非常深
- 大多数平凡表达式都是浅层的(字面量、变量)
- 非平凡节点会立即中断递归

### 编译时常量检查的复用

对于构造器,复用 `IsCompileTimeConstant` 的结果:
```cpp
return expr.type().slotCount() <= 4 && IsCompileTimeConstant(expr);
```

避免重复遍历表达式树。

### Switch 语句优化

使用 `switch` 而非 `if-else` 链,编译器可生成跳转表,提高大型 `switch` 的性能。

## 相关文件

**同模块分析:**
- `SkSLAnalysis.h`: 分析功能的公共接口
- `SkSLIsConstantExpression.cpp`: 常量表达式判断
- `SkSLHasSideEffects.cpp`: 副作用分析

**IR 表示:**
- `src/sksl/ir/SkSLExpression.h`: 表达式类型层次结构

**优化器:**
- `src/sksl/transform/SkSLInlineExpression.cpp`: 使用平凡性判断决定内联
- `src/sksl/transform/SkSLOptimizer.cpp`: 通用优化器

**代码生成:**
- 各后端代码生成器使用此函数决定是否需要临时变量

**测试:**
- `tests/sksl/shared/InlinerTrivial.sksl`: 平凡表达式内联测试
