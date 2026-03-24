# SkSL Constructor (构造器)

> 源文件:
> - `src/sksl/ir/SkSLConstructor.h`
> - `src/sksl/ir/SkSLConstructor.cpp`

## 概述

`Constructor` 模块定义了 SkSL 编译器中构造器表达式的基类层次结构和通用构造逻辑。它包含三个抽象基类（`AnyConstructor`、`SingleArgumentConstructor`、`MultiArgumentConstructor`）和一个 `Constructor::Convert` 工厂函数。该工厂函数负责将 GLSL/SkSL 源码中的构造器语法（如 `float2(x, y)`、`mat3x3(m)`、`int[2](0, i)`）转换为合适的具体构造器 IR 节点，同时进行类型检查和优化。

## 架构位置

构造器系统是 SkSL IR 表达式层次结构中的重要组成部分。`AnyConstructor` 是所有构造器表达式的公共基类，下辖多种具体构造器类型：

```
Expression
  |-- AnyConstructor (抽象基类)
       |-- SingleArgumentConstructor (单参数构造器基类)
       |     |-- ConstructorScalarCast      (标量类型转换)
       |     |-- ConstructorCompoundCast    (复合类型转换)
       |     |-- ConstructorDiagonalMatrix  (对角矩阵构造)
       |     |-- ConstructorSplat           (标量展开为向量)
       |     |-- ConstructorMatrixResize    (矩阵尺寸调整)
       |-- MultiArgumentConstructor (多参数构造器基类)
            |-- ConstructorCompound   (复合构造)
            |-- ConstructorArray      (数组构造)
            |-- ConstructorStruct     (结构体构造)
```

`Constructor::Convert` 命名空间函数是进入这个体系的统一入口。

## 主要类与结构体

### `AnyConstructor`

所有构造器的抽象基类，继承自 `Expression`。

**核心接口：**
- `argumentSpan()` -- 纯虚方法，返回参数列表的 span（可读写或只读）。
- `componentType()` -- 返回构造器结果类型的组件类型。
- `supportsConstantValues()` -- 始终返回 `true`，构造器支持常量值查询。
- `getConstantValue(n)` -- 按槽位索引获取常量值，遍历参数列表按槽位偏移查找。
- `compareConstant(other)` -- 逐槽位比较两个常量构造器是否相等。
- `description(OperatorPrecedence)` -- 生成 `Type(arg1, arg2, ...)` 格式的描述。

### `SingleArgumentConstructor`

单参数构造器的基类，继承自 `AnyConstructor`。

**特点：**
- 持有单个 `unique_ptr<Expression>` 参数。
- `argumentSpan()` 返回大小为 1 的 span。
- 提供 `argument()` 访问器获取唯一参数。

### `MultiArgumentConstructor`

多参数构造器的基类，继承自 `AnyConstructor`。

**特点：**
- 持有 `ExpressionArray` 参数列表。
- `argumentSpan()` 返回完整参数数组的 span。
- 提供 `arguments()` 访问器获取参数数组。

### `Constructor` 命名空间

包含 `Convert` 工厂函数，是所有构造器创建的统一入口。

## 公共 API 函数

### Constructor::Convert

```cpp
static unique_ptr<Expression> Convert(const Context& context,
                                      Position pos,
                                      const Type& type,
                                      ExpressionArray args);
```

根据目标类型和参数列表，选择并创建合适的构造器类型：

1. **冗余转换消除**：如果参数已经是目标类型，直接返回原参数（不创建构造器）。
2. **标量构造**：委托给 `ConstructorScalarCast::Convert`。
3. **向量/矩阵构造**：委托给内部 `convert_compound_constructor` 函数。
4. **数组构造**：委托给 `ConstructorArray::Convert`。
5. **结构体构造**：委托给 `ConstructorStruct::Convert`。

### AnyConstructor 方法

- **`getConstantValue(n)`** -- 遍历参数列表，按槽位偏移定位到正确的参数，然后委托给该参数的 `getConstantValue`。
- **`compareConstant(other)`** -- 逐槽位比较，任意一方不支持常量值则返回 `kUnknown`。
- **`description()`** -- 输出 `TypeName(arg1, arg2, ...)` 格式文本。

## 内部实现细节

### 复合构造器转换（convert_compound_constructor）

这是 Constructor 模块最复杂的内部函数，处理向量和矩阵的构造。

**单参数场景：**

| 参数类型 | 目标类型 | 处理方式 |
|----------|----------|----------|
| 标量 | 向量 | `ConstructorSplat`（展开） |
| 标量 | 矩阵 | `ConstructorDiagonalMatrix`（对角矩阵） |
| 同列数向量 | 向量 | `ConstructorCompoundCast`（类型转换） |
| 矩阵 | 矩阵 | 先 `ConstructorCompoundCast`（类型转换），再 `ConstructorMatrixResize`（尺寸调整） |
| 2x2 矩阵 | 4 分量向量 | `ConstructorCompound` + `ConstructorCompoundCast` |
| 更大向量 | 更小向量 | **禁止** -- 建议使用 swizzle |

**多参数场景：**
- 验证每个参数为标量或向量类型
- 对每个参数进行类型转换（确保组件类型匹配）
- 计算总标量数，与目标类型期望的标量数匹配
- 创建 `ConstructorCompound`

### 常量值获取

`getConstantValue(n)` 的算法：
1. 遍历参数列表
2. 对每个参数计算其槽位数（`slotCount()`）
3. 如果 `n < argSlots`，则从该参数获取值
4. 否则 `n -= argSlots`，继续下一个参数

### 常量比较

`compareConstant()` 逐槽位比较两个构造器：
- 获取双方第 n 个槽位的常量值
- 任一方返回 `nullopt` 则结果为 `kUnknown`
- 所有槽位值相等则返回 `kEqual`
- 发现不等槽位则返回 `kNotEqual`

## 依赖关系

**内部依赖（具体构造器类型）：**
- `SkSLConstructorScalarCast` -- 标量类型转换
- `SkSLConstructorCompoundCast` -- 复合类型转换
- `SkSLConstructorDiagonalMatrix` -- 对角矩阵
- `SkSLConstructorMatrixResize` -- 矩阵尺寸调整
- `SkSLConstructorSplat` -- 标量展开
- `SkSLConstructorCompound` -- 复合构造
- `SkSLConstructorArray` -- 数组构造
- `SkSLConstructorStruct` -- 结构体构造

**其他内部依赖：**
- `SkSLExpression` -- 表达式基类
- `SkSLType` -- 类型系统
- `SkSLContext` -- 编译器上下文
- `SkSLErrorReporter` -- 错误报告
- `SkSLOperator` / `SkSLString` -- 文本输出辅助

**外部依赖：**
- `SkSpan` -- 跨度视图
- `<memory>`, `<optional>`, `<string>` -- 标准库

## 设计模式与设计决策

1. **策略模式的工厂入口**：`Constructor::Convert` 作为统一入口，根据类型和参数选择不同的构造器策略。调用者不需要知道具体构造器类型。

2. **三层继承体系**：`AnyConstructor` -> `SingleArgumentConstructor`/`MultiArgumentConstructor` -> 具体类型。这种设计避免了代码重复：参数存储逻辑在中间层实现，常量值操作在顶层实现。

3. **argumentSpan 统一接口**：无论单参数还是多参数构造器，都通过 `argumentSpan()` 提供统一的 span 视图。这使得 `getConstantValue` 和 `compareConstant` 的实现只需写一次。

4. **冗余转换消除**：当参数已是目标类型时直接返回，避免创建无意义的构造器节点。这是一个重要的性能优化和 IR 简化。

5. **GLSL 语义兼容**：保留了 GLSL 的复杂构造语义（标量展开、矩阵对角构造、矩阵尺寸调整等），同时通过内部分解为更精确的构造器类型，简化了后端代码生成。

6. **安全的 Swizzle 建议**：当用户尝试用大向量构造小向量（GLSL 切片语法）时，SkSL 不允许该操作，而是建议使用 swizzle。这提高了代码清晰度。

## 性能考量

- **O(slots) 常量查询**：`getConstantValue` 需要遍历参数列表来定位槽位，但由于向量/矩阵通常很小（最多 16 个槽位），实际开销可忽略。
- **冗余构造器消除**：避免了生成 `float(float_var)` 这样的无意义类型转换，减少 IR 节点数和后续处理开销。
- **类型转换链最小化**：矩阵的类型转换和尺寸调整分两步处理，但每步都可能被优化为 no-op，最终只保留必要的变换。
- **参数列表的移动语义**：`ExpressionArray` 参数在整个构造流程中使用移动语义传递，避免了不必要的深拷贝。

## 相关文件

- `src/sksl/ir/SkSLExpression.h` -- 表达式基类
- `src/sksl/ir/SkSLConstructorScalarCast.h` -- 标量类型转换
- `src/sksl/ir/SkSLConstructorCompoundCast.h` -- 复合类型转换
- `src/sksl/ir/SkSLConstructorDiagonalMatrix.h` -- 对角矩阵构造
- `src/sksl/ir/SkSLConstructorMatrixResize.h` -- 矩阵尺寸调整
- `src/sksl/ir/SkSLConstructorSplat.h` -- 标量展开
- `src/sksl/ir/SkSLConstructorCompound.h` -- 复合构造
- `src/sksl/ir/SkSLConstructorArray.h` -- 数组构造
- `src/sksl/ir/SkSLConstructorStruct.h` -- 结构体构造
- `src/sksl/ir/SkSLType.h` -- 类型系统
