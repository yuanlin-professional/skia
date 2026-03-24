# SkSL IndexExpression (索引表达式)

> 源文件:
> - `src/sksl/ir/SkSLIndexExpression.h`
> - `src/sksl/ir/SkSLIndexExpression.cpp`

## 概述

`IndexExpression` 是 SkSL 编译器中间表示（IR）中用于表示数组、向量或矩阵索引操作的表达式类，对应 SkSL/GLSL 语法中的 `m[2]` 形式。除了基本的索引语义外，该类在构造阶段内置了丰富的编译时优化：常量索引的越界检查、向量索引到 swizzle 的转换、常量数组/矩阵的元素提取等。

## 架构位置

`IndexExpression` 继承自 `Expression` 基类，属于 SkSL IR 层的表达式节点。它在解析器将 `[]` 运算符转换为 IR 时创建，并在代码生成阶段被各后端转换为目标语言的索引操作。

```
Expression
  |-- IndexExpression  (arr[i], vec[2], mat[1])
  |-- Swizzle          (vec.xy) -- IndexExpression 可优化为此
  |-- FieldAccess      (struct.field)
  |-- ...
```

## 主要类与结构体

### `IndexExpression`

`final` 类，继承自 `Expression`。

**关键成员变量：**

| 成员 | 类型 | 说明 |
|------|------|------|
| `fBase` | `unique_ptr<Expression>` | 被索引的基础表达式（数组、向量或矩阵） |
| `fIndex` | `unique_ptr<Expression>` | 索引表达式（必须为整数类型） |

**IR 节点类型标识：** `Kind::kIndex`

## 公共 API 函数

### 构造与工厂方法

- **`IndexExpression(context, pos, base, index)`** -- 公共构造函数，通过 `IndexType()` 自动推导结果类型。
- **`Convert(context, pos, base, index)`** -- 完整的转换方法，处理以下场景：
  1. **数组类型引用**：将 `int[10]` 形式的类型引用转换为 `TypeReference`
  2. **类型验证**：确保基础表达式为数组、向量或矩阵类型
  3. **索引类型强制转换**：将非整数索引强制转换为 `int`
  4. **编译时越界检查**：对常量索引进行边界验证
- **`Make(context, pos, base, index)`** -- 带优化的构造方法，执行常量折叠优化。

### 类型推导

- **`IndexType(context, type)`** (静态方法) -- 根据被索引类型推导索引操作的结果类型：
  - 矩阵索引返回列向量类型（如 `mat3` 索引返回 `float3`）
  - 数组和向量索引返回组件类型

### 访问器

- **`base()` / `base() const`** -- 返回基础表达式的引用
- **`index()` / `index() const`** -- 返回索引表达式的引用
- **`clone(pos)`** -- 通过私有构造函数克隆，保留已计算的类型信息
- **`description(OperatorPrecedence)`** -- 输出格式为 `base[index]`

## 内部实现细节

### 数组类型引用处理

`Convert()` 方法检测 `base` 是否为 `TypeReference`。如果是，将 `Type[size]` 语法解释为数组类型声明而非索引操作。例如 `int[10]` 被转换为表示 `int[10]` 类型的 `TypeReference`。

### 常量索引优化（Make 方法）

当索引为编译时常量整数且未越界时，`Make()` 执行以下优化：

1. **向量索引转 Swizzle**：`v[2]` 优化为 `v.z`。Swizzle 是更高效的操作，且可以触发进一步的简化。

2. **常量数组元素提取**：当基础表达式是 `ConstructorArray` 且无副作用时，直接从构造器参数中提取对应索引的元素。例如 `int[3](1,2,3)[1]` 简化为 `2`。

3. **常量矩阵列提取**：当基础表达式是常量矩阵且无副作用时，使用 `getConstantValue()` 逐槽位提取列向量的值，然后通过 `ConstructorCompound::MakeFromConstants` 重建向量。

### 矩阵索引类型推导

`IndexType()` 方法对矩阵类型进行特殊处理：根据矩阵的行数和组件类型（float 或 half），返回对应的向量类型。例如：
- `mat3x4` 索引 -> `float4`（4 行）
- `half2x3` 索引 -> `half3`（3 行）

### 越界检查

`index_out_of_range()` 辅助函数检查索引值是否在 `[0, columns)` 范围内。对于未定大小的数组（`kUnsizedArray`），不执行上界检查。

### 私有构造函数

私有构造函数接受预计算的 `Type*` 参数，用于 `clone()` 方法。这避免了克隆时重新计算索引结果类型。

## 依赖关系

**内部依赖：**
- `SkSLExpression` -- 表达式基类
- `SkSLType` / `SkSLBuiltinTypes` -- 类型系统和内建类型
- `SkSLContext` -- 编译器上下文
- `SkSLConstantFolder` -- 常量折叠（获取常量值）
- `SkSLAnalysis` -- 分析工具（副作用检测）
- `SkSLSwizzle` -- 向量混排（常量向量索引优化目标）
- `SkSLConstructorArray` -- 数组构造器（常量数组优化）
- `SkSLConstructorCompound` -- 复合构造器（矩阵列提取结果）
- `SkSLLiteral` -- 字面量（常量索引值提取）
- `SkSLTypeReference` -- 类型引用（数组类型声明处理）
- `SkSLSymbolTable` -- 符号表（数组类型创建）
- `SkSLErrorReporter` -- 错误报告

**外部依赖：**
- `<cstdint>`, `<memory>`, `<optional>`, `<string>` -- 标准库

## 设计模式与设计决策

1. **Convert/Make 分层**：`Convert` 处理类型检查和语法歧义（数组类型 vs 索引操作），`Make` 执行确定性的优化。这种分层确保了优化代码不需要处理错误情况。

2. **语法歧义消除**：`int[10]` 既可以解释为"对 int 类型索引 10"也可以解释为"声明 int[10] 数组类型"。`Convert` 通过检查 base 是否为 `TypeReference` 来消除此歧义。

3. **积极的常量折叠**：在 IR 构造阶段就执行优化，包括向量索引到 swizzle 的转换。这使得后续的优化 pass 有更多机会进行进一步简化。

4. **副作用感知优化**：只有当 base 表达式无副作用时才执行常量折叠，确保语义正确性。例如 `getArray()[0]` 中的 `getArray()` 调用不能被消除。

5. **克隆时类型保留**：私有构造函数允许克隆操作直接传入已有的类型指针，避免重复的类型推导。

## 性能考量

- **编译时越界检查**：常量索引的越界在编译时报错，避免运行时数组越界导致的 GPU 崩溃或未定义行为。
- **向量索引优化**：将 `v[i]`（i 为常量）转换为 swizzle，后端可以生成更高效的代码（GPU 的 swizzle 通常是零开销的）。
- **常量数组/矩阵折叠**：直接提取常量值可以消除运行时的数组访问，减少 GPU 着色器中的内存读取。
- **类型推导缓存**：通过在克隆时传递预计算类型，避免了不必要的 `IndexType` 重复调用。

## 相关文件

- `src/sksl/ir/SkSLExpression.h` -- 表达式基类
- `src/sksl/ir/SkSLSwizzle.h` -- 向量混排表达式（优化目标）
- `src/sksl/ir/SkSLConstructorArray.h` -- 数组构造器
- `src/sksl/ir/SkSLConstructorCompound.h` -- 复合构造器
- `src/sksl/ir/SkSLTypeReference.h` -- 类型引用
- `src/sksl/ir/SkSLType.h` -- 类型系统
- `src/sksl/SkSLConstantFolder.h` -- 常量折叠工具
- `src/sksl/SkSLAnalysis.h` -- 程序分析工具
