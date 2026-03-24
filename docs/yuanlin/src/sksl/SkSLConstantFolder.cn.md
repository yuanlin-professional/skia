# SkSLConstantFolder

> 源文件: src/sksl/SkSLConstantFolder.h, src/sksl/SkSLConstantFolder.cpp

## 概述

`ConstantFolder` 是SkSL编译器中负责常量折叠优化的核心组件。常量折叠是编译器优化技术的基础,它能在编译时计算包含常量的表达式,将诸如`Literal(2) + Literal(2)`这样的表达式简化为`Literal(4)`。该组件不仅处理简单的算术运算,还能处理复杂的向量、矩阵运算,以及布尔表达式的短路优化。

ConstantFolder的设计采用纯静态方法,作为一组工具函数供编译器各个阶段调用。它能够识别常量变量、执行类型转换、处理向量和矩阵的逐分量运算、优化特殊值(如乘以1、加0等)、以及将除法转换为乘以倒数等高级优化。这些优化不仅减少了运行时的计算量,还为后续的编译阶段提供了更简洁的中间表示。

## 架构位置

在SkSL编译器的优化流程中,ConstantFolder位于表达式优化层:

```
编译流程:
    Parser (解析器) → 生成IR树
        ↓
    优化阶段:
        ├── ConstantFolder (常量折叠) ←── 当前组件
        ├── Inliner (函数内联)
        └── Transform (其他优化)
        ↓
    CodeGenerator (代码生成)
```

ConstantFolder在多个编译阶段被调用:
- **解析阶段**: 构建表达式时立即进行常量折叠
- **优化阶段**: 在其他优化后继续折叠新产生的常量表达式
- **内联阶段**: 内联展开后对参数进行常量折叠

## 主要类与结构体

### ConstantFolder 类

```cpp
class ConstantFolder {
public:
    // 获取整数常量值
    static bool GetConstantInt(const Expression& value, SKSL_INT* out);

    // 获取标量常量值
    static bool GetConstantValue(const Expression& value, double* out);

    // 获取常量变量的值表达式
    static const Expression* GetConstantValueForVariable(const Expression& value);

    // 尝试获取常量值(可能返回nullptr)
    static const Expression* GetConstantValueOrNull(const Expression& value);

    // 检查表达式是否所有分量都是指定值
    static bool IsConstantSplat(const Expression& expr, double value);

    // 为常量变量创建值的克隆
    static std::unique_ptr<Expression> MakeConstantValueForVariable(
        Position pos, std::unique_ptr<Expression> expr);

    // 简化二元表达式
    static std::unique_ptr<Expression> Simplify(
        const Context& context,
        Position pos,
        const Expression& left,
        Operator op,
        const Expression& right,
        const Type& resultType);
};
```

该类完全由静态方法组成,不需要实例化,作为纯工具类使用。

## 公共 API 函数

### GetConstantInt

```cpp
static bool GetConstantInt(const Expression& value, SKSL_INT* out);
```

**功能**: 从表达式中提取整数常量值。

**参数**:
- `value`: 待检查的表达式
- `out`: 输出参数,存储提取的整数值

**返回值**: 如果表达式是整数字面量或已知值的const int变量,返回true并设置`out`;否则返回false。

**应用场景**:
- 数组大小检查
- 循环展开条件判断
- 编译时常量验证

### GetConstantValue

```cpp
static bool GetConstantValue(const Expression& value, double* out);
```

**功能**: 从表达式中提取标量常量值(支持整数和浮点数)。

**实现细节**: 先调用`GetConstantValueForVariable`解析常量变量,然后检查是否为字面量,最后提取值。

### GetConstantValueForVariable

```cpp
static const Expression* GetConstantValueForVariable(const Expression& value);
```

**功能**: 如果表达式是const变量引用且有已知值,返回该值;否则返回原表达式。

**实现逻辑**:
1. 检查表达式是否为`VariableReference`
2. 验证变量是否为const且为读取引用
3. 递归查找变量的初始化值
4. 验证初始化值是否为编译时常量

这个函数能够穿透多层变量引用,找到最终的常量值。

### IsConstantSplat

```cpp
static bool IsConstantSplat(const Expression& expr, double value);
```

**功能**: 检查表达式的所有分量是否都等于指定值。

**应用场景**:
- 检测零向量/矩阵: `IsConstantSplat(expr, 0.0)`
- 检测单位标量: `IsConstantSplat(expr, 1.0)`
- 优化特殊值运算

**实现**: 遍历表达式的所有槽位,使用`getConstantValue(index)`检查每个分量。

### Simplify

```cpp
static std::unique_ptr<Expression> Simplify(
    const Context& context,
    Position pos,
    const Expression& left,
    Operator op,
    const Expression& right,
    const Type& resultType);
```

**功能**: 尝试简化二元表达式`left op right`,是ConstantFolder的核心函数。

**优化类型**:

1. **常量变量替换**: 将常量变量替换为其字面量值
2. **自赋值检测**: `var = var` → `var`
3. **布尔短路**:
   - `false && expr` → `false`
   - `true || expr` → `true`
4. **算术简化**:
   - `x + 0` → `x`
   - `x * 1` → `x`
   - `x * 0` → `0`
   - `x - 0` → `x`
   - `0 - x` → `-x`
5. **除法优化**: `x / const` → `x * (1/const)` (如果倒数精确可表示)
6. **矩阵除法**: `matrix / scalar` → `matrix * (1/scalar)`
7. **完全常量折叠**: 两侧都是常量时直接计算结果

**返回值**: 如果能够简化,返回简化后的表达式;否则返回nullptr。

## 内部实现细节

### 常量折叠的多层策略

#### 1. 布尔表达式优化

```cpp
static std::unique_ptr<Expression> short_circuit_boolean(
    Position pos,
    const Expression& left,
    Operator op,
    const Expression& right);
```

处理短路求值:
- `false && anything` 立即返回false
- `true || anything` 立即返回true
- 对于右侧为布尔字面量的情况,尝试消除无操作的布尔运算

#### 2. 算术运算优化

```cpp
static std::unique_ptr<Expression> simplify_arithmetic(
    const Context& context,
    Position pos,
    const Expression& left,
    Operator op,
    const Expression& right,
    const Type& resultType);
```

识别并优化特殊模式:
- **加法**: 识别`x + 0`和`0 + x`
- **乘法**: 识别`x * 1`, `1 * x`, `x * 0`, `0 * x`, `x * -1`
- **减法**: 识别`x - 0`和`0 - x`
- **除法**: 识别`x / 1`,并尝试转换为乘法
- **复合赋值**: 优化`x += 0`, `x *= 1`等

#### 3. 向量和矩阵运算

```cpp
static std::unique_ptr<Expression> simplify_componentwise(
    const Context& context,
    Position pos,
    const Expression& left,
    Operator op,
    const Expression& right);
```

对向量和矩阵进行逐分量运算:
- 使用函数指针`FoldFn`抽象不同的运算
- 检查每个分量的结果是否在类型范围内
- 处理标量与向量/矩阵的混合运算

#### 4. 矩阵乘法

```cpp
static std::unique_ptr<Expression> simplify_matrix_times_matrix(...);
static std::unique_ptr<Expression> simplify_vector_times_matrix(...);
static std::unique_ptr<Expression> simplify_matrix_times_vector(...);
```

实现矩阵乘法的编译时计算:
- 从表达式中提取矩阵元素值
- 执行数学上的矩阵乘法运算
- 检查结果是否在float范围内
- 构造结果的复合构造器表达式

### 除零检测

```cpp
static bool error_on_divide_by_zero(
    const Context& context,
    Position pos,
    Operator op,
    const Expression& right);
```

在折叠除法/取模运算之前检查除数:
- 使用`contains_constant_zero`检查是否包含零值
- 对于向量/矩阵,检查所有分量
- 检测到除零时报告编译错误

### 倒数优化

```cpp
static std::unique_ptr<Expression> make_reciprocal_expression(
    const Context& context,
    const Expression& right);
```

将`x / literal`转换为`x * (1/literal)`:
- 验证除数是标量且为浮点类型
- 计算倒数并检查是否可精确表示为float
- 检查倒数是否有限且非零
- 构造倒数的字面量表达式

这种优化在GPU上特别有价值,因为乘法通常比除法快。

### 常量相等性比较

```cpp
static std::unique_ptr<Expression> simplify_constant_equality(
    const Context& context,
    Position pos,
    const Expression& left,
    Operator op,
    const Expression& right);
```

优化`==`和`!=`运算符:
- 调用`compareConstant`方法比较两个常量
- 根据比较结果直接返回true/false字面量
- 处理向量、矩阵、数组和结构体的比较

## 依赖关系

### 内部依赖

| 依赖项 | 用途 |
|--------|------|
| `SkSLContext` | 访问类型系统和错误报告器 |
| `SkSLAnalysis` | 检查表达式是否为编译时常量 |
| `Expression` | IR表达式节点 |
| `Literal` | 字面量表达式 |
| `BinaryExpression` | 二元表达式 |
| `PrefixExpression` | 前缀表达式 |
| `ConstructorCompound` | 复合构造器 |
| `VariableReference` | 变量引用 |

### 外部使用者

| 使用者 | 场景 |
|--------|------|
| `Parser` | 解析时立即折叠常量 |
| `BinaryExpression::Make` | 创建二元表达式时尝试折叠 |
| `Optimizer` | 优化过程中持续折叠 |
| `Inliner` | 内联后对参数折叠 |

## 设计模式与设计决策

### 1. 纯静态工具类

ConstantFolder不维护任何状态,所有方法都是静态的。这种设计:
- **线程安全**: 无共享状态,天然线程安全
- **易于使用**: 不需要创建实例,直接调用
- **性能优异**: 无对象创建开销

### 2. 分层优化策略

优化按复杂度分层:
```
第一层: 常量变量替换
    ↓
第二层: 布尔短路和自赋值
    ↓
第三层: 特殊值算术优化
    ↓
第四层: 完全常量折叠
```

这种分层使得简单优化能快速返回,复杂优化仅在必要时执行。

### 3. 防御性类型检查

所有运算前都进行严格的类型和范围检查:
- 检查结果是否溢出
- 验证浮点运算结果是否有限
- 确保类型转换的安全性

### 4. 渐进式优化

`Simplify`函数返回nullptr表示"无法优化",而不是抛出异常。这允许:
- 调用者决定如何处理未优化的情况
- 多次尝试优化(在其他转换后)
- 保持原始表达式不变

## 性能考量

### 1. 编译时计算 vs 运行时计算

常量折叠将计算从运行时移到编译时:
- **时间换空间**: 编译时间增加,但生成的代码更小更快
- **GPU友好**: 减少着色器指令数,降低GPU负载

### 2. 倒数优化的GPU价值

GPU架构中:
- 乘法通常是单周期操作
- 除法可能需要多个周期
- 将`x / 2.0`转换为`x * 0.5`可显著提升性能

### 3. 短路优化的分支消除

优化布尔短路表达式可以:
- 消除运行时的条件分支
- 减少着色器的动态分支
- 提高GPU的执行效率(避免warp分歧)

### 4. 缓存友好的实现

- 使用栈分配的临时数组(如`double args[16]`)
- 避免不必要的内存分配
- 直接在原表达式上操作,减少复制

### 5. 向量化机会

将向量运算折叠为常量可以:
- 减少内存访问
- 利用常量寄存器
- 提高缓存命中率

## 相关文件

| 文件路径 | 关系 | 说明 |
|----------|------|------|
| `src/sksl/SkSLAnalysis.h` | 依赖 | 提供表达式分析功能 |
| `src/sksl/ir/SkSLBinaryExpression.h` | 使用者 | 创建二元表达式时调用折叠 |
| `src/sksl/ir/SkSLLiteral.h` | 依赖 | 创建字面量结果 |
| `src/sksl/ir/SkSLExpression.h` | 依赖 | 表达式基类 |
| `src/sksl/SkSLOperator.h` | 依赖 | 运算符定义 |
| `src/sksl/SkSLContext.h` | 依赖 | 编译上下文 |
| `src/sksl/transform/SkSLTransform.h` | 协作 | 其他优化转换 |
