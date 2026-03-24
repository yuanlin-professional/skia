# SkSLGetReturnComplexity — 函数返回复杂度分析

> 源文件：[`src/sksl/analysis/SkSLGetReturnComplexity.cpp`](../../src/sksl/analysis/SkSLGetReturnComplexity.cpp)

## 概述

SkSLGetReturnComplexity.cpp 实现了对 SkSL 函数定义的返回语句复杂度分析。它将函数的返回模式分为三个级别：单一安全返回、作用域返回和提前返回。此分析结果被 SkSL 内联器使用，以决定函数能否被内联以及内联时需要何种处理策略。

该文件 131 行，包含两个辅助分析类和一个公共分析函数。

## 架构位置

```
SkSL 编译器
  └── 分析（Analysis）模块
        └── 函数分析
              └── GetReturnComplexity（本文件）
                    ├── CountReturnsAtEndOfControlFlow — 统计控制流末尾的 return
                    └── CountReturnsWithLimit — 统计所有 return 并记录深度信息
```

此分析直接服务于 SkSL 的函数内联优化。

## 主要类与结构体

### `ReturnComplexity` 枚举（定义在 SkSLAnalysis.h）

```
kSingleSafeReturn  — 函数只有一个 return 或所有 return 都在控制流末尾
kScopedReturns     — 函数有多个 return 但都在作用域块的末尾
kEarlyReturns      — 函数有提前返回（return 不在控制流末尾）
```

### `CountReturnsAtEndOfControlFlow`（局部类）

统计位于函数控制流末尾的 return 语句数量。"控制流末尾"指的是 block 的最后一条语句位置。

- 只检查 block 的最后一条语句
- 不进入 switch、for、do 循环内部
- 遇到 return 时计数

### `CountReturnsWithLimit`（文件作用域类）

统计函数中所有 return 语句的数量和相关信息：

| 成员变量 | 说明 |
|---------|------|
| `fNumReturns` | return 语句总数 |
| `fDeepestReturn` | 最深的 return 所在的作用域块深度 |
| `fLimit` | 达到此计数后停止搜索 |
| `fScopedBlockDepth` | 当前作用域块嵌套深度 |
| `fVariablesInBlocks` | 是否在嵌套块中存在变量声明 |

## 公共 API 函数

```cpp
Analysis::ReturnComplexity Analysis::GetReturnComplexity(const FunctionDefinition& funcDef);
```

分析算法：
1. 调用 `count_returns_at_end_of_control_flow` 统计控制流末尾的 return 数量（N）
2. 调用 `CountReturnsWithLimit` 统计最多 N+1 个 return
3. 判断逻辑：
   - 如果总 return 数 > N：存在提前返回 → `kEarlyReturns`
   - 如果总 return 数 > 1：多个末尾返回 → `kScopedReturns`
   - 如果嵌套块中有变量声明且最深 return 深度 > 1：→ `kScopedReturns`
   - 否则：→ `kSingleSafeReturn`

## 内部实现细节

### 控制流末尾的定义

`CountReturnsAtEndOfControlFlow` 只检查每个 block 的最后一条语句：

```cpp
case Statement::Kind::kBlock: {
    const auto& block = stmt.as<Block>();
    return !block.children().empty() &&
           this->visitStatement(*block.children().back());
}
```

这意味着只有出现在控制流的"自然退出路径"上的 return 才被计入。位于 if 分支中间、循环体中间的 return 不计入。

### 变量声明与作用域的交互

`CountReturnsWithLimit` 跟踪嵌套块中的变量声明，因为：
- 如果 return 和变量声明都在嵌套块中，内联时需要特殊处理作用域
- 如果在遇到任何 return 之前所有变量声明的块已经关闭，则可以忽略这些声明

```cpp
if (fNumReturns == 0 && fScopedBlockDepth <= 1) {
    fVariablesInBlocks = false;
}
```

### CountReturnsWithLimit 的限制机制

通过 `fLimit` 参数，一旦发现足够多的 return 语句就停止搜索。这避免了在确认为 `kEarlyReturns` 后继续不必要的遍历。

### 两阶段分析设计

分为两个独立的遍历器而非合并为一个的原因：
1. `CountReturnsAtEndOfControlFlow` 只检查 block 末尾（快速遍历）
2. `CountReturnsWithLimit` 检查所有 return（完整遍历）
3. 第一阶段的结果用于设置第二阶段的 `fLimit`，实现早期终止优化

## 依赖关系

- `src/sksl/SkSLAnalysis.h` — `Analysis::ReturnComplexity` 枚举
- `src/sksl/SkSLDefines.h` — 基础定义
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/ir/SkSLBlock.h` — Block 语句
- `src/sksl/ir/SkSLFunctionDefinition.h` — 函数定义
- `src/sksl/ir/SkSLIRNode.h` — IR 节点基类
- `src/sksl/ir/SkSLStatement.h` — 语句类型
- `<algorithm>` — `std::max`

## 设计模式与设计决策

- **两阶段分析**：先快速判断控制流末尾的 return 数量，再用此结果优化完整分析的搜索范围。
- **访问者模式**：两个分析类都继承 `ProgramVisitor`。
- **三级分类**：将返回复杂度分为三个级别，每个级别对应内联器的不同处理策略。
- **保守分析**：不深入 switch/loop 结构检查末尾 return，因为这些结构的控制流不够线性。

## 性能考量

1. **限制搜索**：`CountReturnsWithLimit` 通过 `fLimit` 参数实现早期终止。
2. **表达式跳过**：两个分析类都跳过表达式遍历。
3. **两次遍历**：虽然进行两次遍历，但第一次（末尾 return）非常快速（只检查 block 最后语句），第二次可能因 `fLimit` 提前终止。
4. **内联决策影响**：此分析的结果直接影响函数是否被内联，间接影响生成代码的运行时性能。

## 相关文件

- `src/sksl/SkSLAnalysis.h` — `ReturnComplexity` 枚举和分析函数声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/transform/SkSLTransform.h` — 优化变换
- `src/sksl/SkSLInliner.cpp` — 函数内联器（使用此分析结果）
