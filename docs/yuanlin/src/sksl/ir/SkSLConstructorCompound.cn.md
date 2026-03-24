# SkSL ConstructorCompound - 复合类型构造器

> 源文件:
> - `src/sksl/ir/SkSLConstructorCompound.h`
> - `src/sksl/ir/SkSLConstructorCompound.cpp`

## 概述

`ConstructorCompound` 表示 SkSL IR 中由多个表达式组合而成的向量或矩阵构造操作,例如 `half3(pos.xy, 1)` 或 `mat3(a.xyz, b.xyz, 0, 0, 1)`。

与 `ConstructorSplat`(从单个标量展开)和 `ConstructorDiagonalMatrix`(从单个标量构造对角矩阵)不同,`ConstructorCompound` 处理包含标量和聚合类型(向量)混合的多参数构造。参数的总标量槽数必须与目标类型的槽数精确匹配,且所有参数的分量类型必须一致。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── 构造器 (Constructor)
            └── MultiArgumentConstructor
                └── ConstructorCompound  <-- 本文件
```

## 主要类与结构体

### `ConstructorCompound`

继承自 `MultiArgumentConstructor`。

| 成员 | 说明 |
|------|------|
| `kIRNodeKind` | 值为 `Kind::kConstructorCompound` |

## 公共 API 函数

### `ConstructorCompound::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type& type,
                                        ExpressionArray args);
```

创建复合构造器,包含多种优化:

1. **空操作消除**: 单参数且类型匹配(标量或同类型向量)时直接返回参数
2. **嵌套展平**: 将嵌套的 `ConstructorCompound` 展平为单层
3. **常量变量替换**: 将常量变量替换为字面量值
4. **展开构造器化简**: 如果所有参数都是相同的标量,转换为 `ConstructorSplat`

### `ConstructorCompound::MakeFromConstants`

```cpp
static std::unique_ptr<Expression> MakeFromConstants(const Context& context,
                                                     Position pos,
                                                     const Type& returnType,
                                                     const double values[]);
```

从常量数组创建构造器,将每个值包装为 `Literal` 后调用 `Make()`。主要用于编译期常量折叠的结果构造。

## 内部实现细节

### 空操作消除 (`is_safe_to_eliminate`)

两种情况下单参数构造器可以被消除:
- **标量目标**: 单标量参数到标量类型(技术上不是"复合"构造,但简化调用方)
- **同类型向量**: 单向量参数与目标向量类型匹配

注意:向量从矩阵构造、矩阵从向量构造等情况不会被消除。

### 嵌套展平

当优化开启时,将嵌套的 `ConstructorCompound` 展平:

```
float4(float2(1, 2), 3, 4) → float4(1, 2, 3, 4)
mat2(float2(a, b), float2(c, d)) → mat2(a, b, c, d)
```

实现方式:
1. 计算展平后的总字段数
2. 如果字段数增加,说明有可展平的嵌套构造器
3. 将嵌套构造器的内部参数移入新的参数列表

### 展开构造器化简 (`make_splat_from_arguments`)

检测所有参数是否表示相同的标量值:
- 参数必须全是标量或 `ConstructorSplat`(含相同标量)
- 使用 `Analysis::IsSameExpressionTree` 判断值相等性
- 有副作用的表达式会被自动排除
- 仅适用于向量(矩阵不适用)

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLConstructor.h` (MultiArgumentConstructor) | 基类 |
| `SkSLConstructorSplat.h` | 展开构造器化简目标 |
| `SkSLConstantFolder.h` | 常量变量替换 |
| `SkSLAnalysis.h` | 表达式相等性判断(`IsSameExpressionTree`) |
| `SkSLLiteral.h` | 字面量创建(`MakeFromConstants`) |
| `SkSLType.h` | 类型系统 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLProgramSettings.h` | 优化开关 |

## 设计模式与设计决策

1. **积极优化**: `Make()` 方法包含三种不同的优化路径(空操作消除、嵌套展平、展开化简)
2. **常量构造辅助**: `MakeFromConstants()` 提供从原始数值数组构造表达式的便捷接口,被内置函数优化广泛使用
3. **展平而非递归**: 嵌套的复合构造器被展平为单层,简化后端代码生成
4. **优化开关感知**: 嵌套展平和展开化简仅在优化开启时执行
5. **标量兼容**: 虽然名为"Compound",但允许标量通过此路径(单参数),简化了调用方逻辑

## 性能考量

- 嵌套展平减少了 IR 树的深度和节点数量
- 展开化简将多参数构造器替换为单参数 splat,减少代码生成的复杂度
- 常量变量在构造阶段替换,为后续的常量折叠创造条件
- `MakeFromConstants()` 在编译期直接构造结果,避免运行时计算
- 参数的总槽数验证使用 `std::accumulate`,在 debug 构建中执行
- 嵌套展平的字段计数仅在检测到可展平的构造器时才分配新数组

### 展开化简的条件

`make_splat_from_arguments` 函数的化简条件相当严格:

1. 目标类型不能是矩阵(矩阵不能用 splat 表示)
2. 所有参数必须是标量或 `ConstructorSplat`
3. 所有参数的值必须相同(通过 `IsSameExpressionTree` 判断)
4. 有副作用的表达式会被自动排除(因为 `IsSameExpressionTree` 拒绝有副作用的表达式)

例如:
- `float3(1.0, 1.0, 1.0)` -> `float3(1.0)` (splat)
- `float3(x, x, x)` -> `float3(x)` (splat,前提是 x 无副作用)
- `float3(f(), f(), f())` -> 不优化(f() 可能有副作用)
- `mat2(1.0, 1.0, 1.0, 1.0)` -> 不优化(矩阵不支持 splat)

### 与 ConstructorArray 的区别

| 特性 | ConstructorCompound | ConstructorArray |
|------|-------------------|-----------------|
| 目标类型 | 向量、矩阵 | 数组 |
| 参数类型 | 可混合标量和向量 | 全部为数组分量类型 |
| 嵌套展平 | 支持 | 不支持 |
| Splat 化简 | 支持 | 不支持 |
| ES2 支持 | 是 | 否 |

## 相关文件

- `src/sksl/ir/SkSLConstructorSplat.h` -- 展开构造器(优化目标)
- `src/sksl/ir/SkSLConstructorDiagonalMatrix.h` -- 对角矩阵构造器
- `src/sksl/ir/SkSLConstructorArray.h` -- 数组构造器
- `src/sksl/ir/SkSLConstructor.h` -- 构造器基类层次
- `src/sksl/ir/SkSLSwizzle.cpp` -- 混洗优化中使用 ConstructorCompound
- `src/sksl/ir/SkSLFunctionCall.cpp` -- 内置函数优化中使用 MakeFromConstants
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
