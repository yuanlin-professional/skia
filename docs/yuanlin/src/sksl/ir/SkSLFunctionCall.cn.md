# SkSL FunctionCall - 函数调用

> 源文件:
> - `src/sksl/ir/SkSLFunctionCall.h`
> - `src/sksl/ir/SkSLFunctionCall.cpp`

## 概述

`FunctionCall` 表示 SkSL IR 中的函数调用表达式。它是 SkSL 中最复杂的 IR 节点之一,负责处理函数重载解析、泛型类型解析、参数类型强制转换以及大量内置函数(intrinsic)的编译期常量折叠优化。

该类覆盖了 GLSL 规范中 8.1-8.7 节定义的所有内置函数的编译期优化,包括三角函数、指数函数、通用函数、几何函数、矩阵函数和向量关系函数。

## 架构位置

```
SkSL 编译器
└── IR (中间表示)
    └── 表达式 (Expression)
        └── FunctionCall  <-- 本文件
            ├── 引用 FunctionDeclaration
            ├── 包含参数列表 (ExpressionArray)
            └── 编译期内置函数优化引擎
```

## 主要类与结构体

### `FunctionCall`

继承自 `Expression`。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fFunction` | `const FunctionDeclaration&` | 被调用的函数声明 |
| `fArguments` | `ExpressionArray` | 参数列表 |
| `fStablePointer` | `const FunctionCall*` | 稳定指针,用于在克隆后仍能标识同一调用 |

### `IntrinsicArguments`

```cpp
using IntrinsicArguments = std::array<const Expression*, 3>;
```

内置函数最多接受 3 个参数的固定大小数组。

## 公共 API 函数

### `FunctionCall::Convert` (两个重载)

```cpp
// 从表达式值(可能是类型引用、函数引用或方法引用)
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           std::unique_ptr<Expression> functionValue,
                                           ExpressionArray arguments);

// 从已确定的函数声明
static std::unique_ptr<Expression> Convert(const Context& context,
                                           Position pos,
                                           const FunctionDeclaration& function,
                                           ExpressionArray arguments);
```

第一个重载根据表达式类型分发:
- **TypeReference**: 转为构造器调用 (`Constructor::Convert`)
- **FunctionReference**: 执行重载解析后调用第二个重载
- **MethodReference**: 将 `self` 添加到参数末尾,执行重载解析

第二个重载执行完整的函数调用验证:
1. ES3 函数在严格 ES2 模式下被拒绝
2. 验证参数数量匹配
3. 验证参数修饰符匹配(像素格式等)
4. 解析泛型类型
5. 强制转换参数类型
6. 更新 out 参数的变量引用类型
7. 拒绝对 `main()` 的调用
8. 将 `eval()` 方法调用转为 `ChildCall`

### `FunctionCall::Make`

```cpp
static std::unique_ptr<Expression> Make(const Context& context,
                                        Position pos,
                                        const Type* returnType,
                                        const FunctionDeclaration& function,
                                        ExpressionArray arguments);
```

如果函数是内置函数且所有参数为编译期常量,尝试优化:
- 调用 `optimize_intrinsic_call()` 进行编译期求值
- 如果无法优化,创建普通的 `FunctionCall` 节点

### `FunctionCall::FindBestFunctionForCall`

```cpp
static const FunctionDeclaration* FindBestFunctionForCall(
    const Context& context,
    const FunctionDeclaration* overloads,
    const ExpressionArray& arguments);
```

在重载链中找到最佳匹配的函数:
- 对每个候选函数计算调用代价(`call_cost`)
- 选择代价最低的函数
- 如果最低代价为 Impossible,返回 null

## 内部实现细节

### 重载解析 (`call_cost`)

计算函数调用的类型强制转换代价:
1. 排除 ES3 函数(在严格 ES2 模式下)
2. 排除参数数量不匹配的函数
3. 通过 `determineFinalTypes` 解析泛型参数
4. 检查参数修饰符匹配(像素格式)
5. 累加每个参数的类型强制转换代价

### 内置函数编译期优化 (`optimize_intrinsic_call`)

这是该文件最大的部分(约 700 行),覆盖了大量内置函数:

#### 三角函数 (8.1)
`radians`, `degrees`, `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`

#### 指数函数 (8.2)
`pow`, `exp`, `log`, `exp2`, `log2`, `sqrt`, `inversesqrt`

#### 通用函数 (8.3)
`abs`, `sign`, `floor`, `ceil`, `fract`, `mod`, `min`, `max`, `clamp`, `saturate`, `mix`, `step`, `smoothstep`, `trunc`, `round`, `roundEven`, `fma`, `floatBitsToInt`, `floatBitsToUint`, `intBitsToFloat`, `uintBitsToFloat`

#### 打包/解包函数 (8.4)
`packUnorm2x16`, `packSnorm2x16`, `packHalf2x16`, `unpackUnorm2x16`, `unpackSnorm2x16`, `unpackHalf2x16`

#### 几何函数 (8.5)
`length`, `distance`, `dot`, `cross`, `normalize`, `faceforward`, `reflect`, `refract`

#### 矩阵函数 (8.6)
`matrixCompMult`, `transpose`, `outerProduct`, `determinant`, `inverse`

#### 向量关系函数 (8.7)
`lessThan`, `lessThanEqual`, `greaterThan`, `greaterThanEqual`, `equal`, `notEqual`, `any`, `all`, `not`

### 优化辅助函数

| 函数 | 说明 |
|------|------|
| `coalesce_vector` | 将向量折叠为标量(如 `length`, `dot`) |
| `coalesce_pairwise_vectors` | 对两个向量逐分量折叠 |
| `evaluate_intrinsic` | 逐分量求值(如 `sin`, `abs`) |
| `evaluate_pairwise_intrinsic` | 两参数逐分量求值(如 `pow`, `min`) |
| `evaluate_3_way_intrinsic` | 三参数逐分量求值(如 `clamp`, `mix`) |
| `optimize_comparison` | 向量比较(如 `lessThan`) |

### 稳定指针

`fStablePointer` 确保即使 `FunctionCall` 被克隆,也能通过同一指针在哈希表中找到它。克隆时使用原始节点的 `stablePointer`。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLExpression.h` | 基类 |
| `SkSLFunctionDeclaration.h` | 函数声明(泛型解析) |
| `SkSLFunctionReference.h` | 函数引用(重载入口) |
| `SkSLMethodReference.h` | 方法引用(效果子元素调用) |
| `SkSLTypeReference.h` | 类型引用(构造器调用) |
| `SkSLChildCall.h` | 子效果调用(eval 方法转换) |
| `SkSLConstructorCompound.h` | 常量结果构造 |
| `SkSLLiteral.h` | 标量常量结果 |
| `SkSLIntrinsicList.h` | 内置函数枚举 |
| `SkSLAnalysis.h` | 编译期常量检测、赋值分析 |
| `SkSLConstantFolder.h` | 常量变量值获取 |
| `SkMatrixInvert.h` | 矩阵求逆(determinant/inverse) |
| `SkHalf.h` | 半精度浮点(pack/unpack) |

## 设计模式与设计决策

1. **编译期求值引擎**: 将内置函数的常量折叠集成到 `FunctionCall::Make` 中,在 IR 构建阶段即完成优化
2. **函数指针模式**: 使用 `EvaluateFn`/`CoalesceFn`/`CompareFn` 函数指针实现通用的求值框架
3. **稳定指针标识**: 通过 `fStablePointer` 解决了克隆节点的身份标识问题
4. **eval-to-ChildCall 转换**: 将效果子元素的 `eval()` 方法调用转为专用的 `ChildCall` 节点,简化后端处理
5. **值域保护**: 所有编译期优化都检查结果是否在类型的合法范围内,越界时中止优化

## 性能考量

- 内置函数的编译期折叠避免了大量运行时数学运算
- `has_compile_time_constant_arguments` 快速判断是否值得尝试优化
- 参数数量固定为最多 3 个(`IntrinsicArguments` 为 `std::array<const Expression*, 3>`)
- 矩阵运算使用 `float[16]` 栈数组,避免堆分配
- `FindBestFunctionForCall` 在单一重载时直接返回,避免不必要的代价计算
- 值域保护确保优化后的结果不超出类型范围,NaN 和 Infinity 结果会中止优化

## 相关文件

- `src/sksl/ir/SkSLFunctionDeclaration.h` -- 函数声明
- `src/sksl/ir/SkSLFunctionDefinition.h` -- 函数定义
- `src/sksl/ir/SkSLChildCall.h` -- 子效果调用
- `src/sksl/ir/SkSLConstructor.h` -- 构造器(类型引用调用)
- `src/sksl/SkSLIntrinsicList.h` -- 内置函数枚举
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
- `src/core/SkMatrixInvert.h` -- 矩阵求逆算法
