# SkSLGetLoopUnrollInfo

> 源文件: src/sksl/analysis/SkSLGetLoopUnrollInfo.cpp

## 概述

`SkSLGetLoopUnrollInfo` 模块负责分析 for 循环是否满足展开(unroll)条件,并提取展开所需的关键信息。循环展开是 SkSL 编译器的重要优化技术,将循环体复制多次以消除循环开销,特别适用于迭代次数确定的小型循环。

该模块实现了严格的 GLSL ES 循环展开规范,验证循环的初始化、条件、步进表达式是否符合可展开的形式,计算循环的精确迭代次数,并确保循环在有限步骤内终止。这对于 GPU 着色器至关重要,因为无限循环会导致 GPU 挂起。

## 架构位置

此模块位于 SkSL 优化层,为循环展开变换提供分析支持:

```
SkSL 编译流程:
  IR 构建 → 语义分析
              ↓
        ┌─────────────────┐
        │  循环分析        │ ← 本模块
        │  (GetLoopUnrollInfo) │
        └─────────────────┘
              ↓
        ┌─────────────────┐
        │  循环展开优化    │
        │  (UnrollLoops)   │
        └─────────────────┘
              ↓
          代码生成
```

分析结果 (`LoopUnrollInfo`) 被循环展开器使用来执行实际的代码变换。

## 主要类与结构体

### LoopUnrollInfo (定义在 SkSLAnalysis.h)

存储循环展开所需的信息:

```cpp
struct LoopUnrollInfo {
    const Variable* fIndex;   // 循环索引变量
    double fStart;            // 起始值
    double fDelta;            // 步进值
    int fCount;               // 迭代次数
};
```

**成员说明:**
- `fIndex`: 循环控制变量(如 `for (int i=0; ...)` 中的 `i`)
- `fStart`: 初始值(如 `i=0` 中的 `0`)
- `fDelta`: 每次迭代的增量(如 `i++` 对应 `+1`,`i+=2` 对应 `+2`)
- `fCount`: 循环将执行的确切次数

### ForLoopPositions

辅助结构,记录 for 循环各部分的源码位置:

```cpp
struct ForLoopPositions {
    Position initPosition;       // 初始化表达式位置
    Position conditionPosition;  // 条件表达式位置
    Position nextPosition;       // 步进表达式位置
};
```

用于在验证失败时提供精确的错误位置。

## 公共 API 函数

### Analysis::GetLoopUnrollInfo

```cpp
std::unique_ptr<LoopUnrollInfo> Analysis::GetLoopUnrollInfo(
    const Context& context,
    Position loopPos,
    const ForLoopPositions& positions,
    const Statement* loopInitializer,
    std::unique_ptr<Expression>* loopTest,
    const Expression* loopNext,
    const Statement* loopStatement,
    ErrorReporter* errorPtr)
```

**功能:** 分析 for 循环并提取展开信息

**参数:**
- `context`: 编译上下文
- `loopPos`: 整个循环的源码位置
- `positions`: 循环各部分的详细位置
- `loopInitializer`: 初始化语句(如 `int i=0`)
- `loopTest`: 条件表达式(如 `i<10`),可能被修改(浮点 `!=` 改为 `<` 或 `>`)
- `loopNext`: 步进表达式(如 `i++`)
- `loopStatement`: 循环体
- `errorPtr`: 错误报告器,传 `nullptr` 则不报告错误

**返回值:**
- 成功: 包含展开信息的 `LoopUnrollInfo` 对象
- 失败: `nullptr`(循环不可展开)

**验证规则:**

1. **初始化 (init_declaration):**
   - 必须是变量声明(`VarDeclaration`)
   - 类型必须是数值类型(整数或浮点)
   - 必须有初始化值
   - 初始值必须是编译时常量

2. **条件 (condition):**
   - 必须是二元表达式
   - 左侧必须是循环索引变量
   - 运算符必须是关系运算符:`>`, `>=`, `<`, `<=`, `==`, `!=`
   - 右侧必须是常量表达式

3. **步进 (expression):**
   - 形式1: `i++` 或 `++i` (delta=+1)
   - 形式2: `i--` 或 `--i` (delta=-1)
   - 形式3: `i += 常量` (delta=常量)
   - 形式4: `i -= 常量` (delta=-常量)

4. **循环体:**
   - 循环索引不能在体内被修改
   - 不能作为 `out` 或 `inout` 参数传递

5. **终止保证:**
   - 迭代次数必须 < `kLoopTerminationLimit` (100000)
   - 循环必须朝着终止条件前进

## 内部实现细节

### 迭代次数计算

核心函数 `calculate_count`:

```cpp
static int calculate_count(double start, double end, double delta,
                          bool forwards, bool inclusive)
```

**参数:**
- `start`: 起始值
- `end`: 结束值
- `delta`: 步进
- `forwards`: 是否向前迭代(如 `<` 或 `<=`)
- `inclusive`: 是否包含边界(如 `<=` vs `<`)

**计算逻辑:**

1. **初始状态检查:**
```cpp
if ((forwards && start > end) || (!forwards && start < end)) {
    return 0;  // 起始已超过终点
}
```

2. **进度检查:**
```cpp
if ((delta == 0.0) || forwards != (delta > 0.0)) {
    return kLoopTerminationLimit;  // 无限循环
}
```

3. **迭代计数:**
```cpp
double iterations = sk_ieee_double_divide(end - start, delta);
double count = std::ceil(iterations);
if (inclusive && (count == iterations)) {
    count += 1.0;
}
```

使用浮点除法和向上取整,处理整数和浮点循环变量。

4. **边界值检查:**
```cpp
if (count > kLoopTerminationLimit || !std::isfinite(count)) {
    return kLoopTerminationLimit;
}
```

### 关系运算符处理

不同运算符有不同的终止语义:

**小于/大于 (LT/GT):**
```cpp
case Operator::Kind::LT:
    loopInfo->fCount = calculate_count(loopInfo->fStart, loopEnd, loopInfo->fDelta,
                                      /*forwards=*/true, /*inclusive=*/false);
```

**小于等于/大于等于 (LTEQ/GTEQ):**
```cpp
case Operator::Kind::LTEQ:
    loopInfo->fCount = calculate_count(loopInfo->fStart, loopEnd, loopInfo->fDelta,
                                      /*forwards=*/true, /*inclusive=*/true);
```

**不等于 (NEQ):**
```cpp
case Operator::Kind::NEQ:
    float iterations = sk_ieee_double_divide(loopEnd - loopInfo->fStart, loopInfo->fDelta);
    loopInfo->fCount = std::ceil(iterations);
    if (loopInfo->fCount < 0 || loopInfo->fCount != iterations || !std::isfinite(iterations)) {
        loopInfo->fCount = kLoopTerminationLimit;  // 不会精确到达终点
    }
```

对于浮点类型,还会重写测试条件:
```cpp
if (loopInfo->fIndex->type().componentType().isFloat()) {
    Operator::Kind op = (loopInfo->fDelta > 0) ? Operator::Kind::LT : Operator::Kind::GT;
    *loopTest = BinaryExpression::Make(context, cond->fPosition,
                                       cond->left()->clone(), op, cond->right()->clone());
}
```

这避免了浮点舍入误差导致的无限循环。

**等于 (EQEQ):**
```cpp
case Operator::Kind::EQEQ:
    if (loopInfo->fStart == loopEnd) {
        loopInfo->fCount = (loopInfo->fDelta) ? 1 : kLoopTerminationLimit;
    } else {
        loopInfo->fCount = 0;
    }
```

只有起点等于终点时执行一次。

### 循环体内索引变量写入检查

```cpp
if (Analysis::StatementWritesToVariable(*loopStatement, *initDecl.var())) {
    errors.error(loopStatement->fPosition,
                 "loop index must not be modified within body of the loop");
    return nullptr;
}
```

利用其他分析函数 `StatementWritesToVariable` 检查循环体。

### 常量表达式验证

使用 `ConstantFolder::GetConstantValue` 提取常量值:

```cpp
if (!ConstantFolder::GetConstantValue(*initDecl.value(), &loopInfo->fStart)) {
    errors.error(loopInitializer->fPosition,
                 "loop index initializer must be a constant expression");
    return nullptr;
}
```

这确保循环边界在编译时已知。

## 依赖关系

**核心依赖:**
- `src/sksl/SkSLAnalysis.h`: 分析功能接口
- `src/sksl/SkSLConstantFolder.h`: 常量折叠
- `src/sksl/SkSLErrorReporter.h`: 错误报告

**IR 节点:**
- `SkSLForStatement.h`: for 循环
- `SkSLBinaryExpression.h`: 二元表达式
- `SkSLPrefixExpression.h`, `SkSLPostfixExpression.h`: 自增/自减
- `SkSLVarDeclarations.h`, `SkSLVariable.h`: 变量
- `SkSLVariableReference.h`: 变量引用

**数学工具:**
- `include/private/base/SkFloatingPoint.h`: `sk_ieee_double_divide`
- `<cmath>`: `std::ceil`, `std::isfinite`

**辅助:**
- `src/sksl/analysis/SkSLNoOpErrorReporter.h`: 空错误报告器

## 设计模式与设计决策

### 可选错误报告

通过 `errorPtr` 参数支持两种模式:
- 传入报告器:详细报告所有错误
- 传入 `nullptr`:静默失败,只返回 `nullptr`

这支持不同的使用场景(诊断 vs 快速检查)。

### 浮点安全处理

对浮点循环索引特殊处理:
- 使用 IEEE 除法避免除零
- 重写 `!=` 测试为 `<` 或 `>` 避免舍入误差
- 检查 `isfinite` 防止 NaN 或无穷大

### 保守的终止限制

`kLoopTerminationLimit = 100000` 是一个保守值:
- 防止过大的循环导致代码膨胀
- 确保编译时间可控
- 符合 GPU 着色器的实际需求

### 提前验证策略

在计算迭代次数前验证所有语法约束:
- 失败时立即返回,避免无效计算
- 提供详细的错误信息
- 位置信息精确到子表达式

### Lambda 表达式简化

使用 lambda 检查循环索引:
```cpp
auto is_loop_index = [&](const std::unique_ptr<Expression>& expr) {
    return expr->is<VariableReference>() &&
           expr->as<VariableReference>().variable() == loopInfo->fIndex;
};
```

提高代码可读性,避免重复逻辑。

## 性能考量

### 编译时计算

所有迭代次数计算都在编译时完成:
- 不影响运行时性能
- 结果用于编译器决策,不存储到生成的代码中

### 单次遍历验证

对循环结构只遍历一次:
- 线性时间复杂度 O(n),n 为循环节点数
- 早期失败减少不必要的检查

### 浮点精度

使用 `double` 进行所有计算:
- 即使索引是 `int` 或 `float`
- 避免整数溢出和浮点精度损失
- 最终转换为 `int` 迭代次数

### 避免无限循环验证开销

通过简单的方向性检查快速识别无限循环:
```cpp
if ((delta == 0.0) || forwards != (delta > 0.0)) {
    return kLoopTerminationLimit;
}
```

不需要模拟执行循环。

## 相关文件

**循环展开:**
- `src/sksl/transform/SkSLUnrollLoops.cpp`: 使用本模块的结果执行展开

**常量折叠:**
- `src/sksl/SkSLConstantFolder.cpp`: 计算常量表达式的值

**其他分析:**
- `src/sksl/SkSLAnalysis.cpp`: `StatementWritesToVariable` 实现

**IR 构建:**
- `src/sksl/ir/SkSLForStatement.cpp`: for 循环的 IR 表示

**测试:**
- `tests/sksl/shared/LoopUnrolling.sksl`: 循环展开测试用例
- `tests/sksl/errors/LoopStructure.sksl`: 非法循环结构测试
