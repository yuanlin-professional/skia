# SkSL CheckProgramStructure 分析

> 源文件: `src/sksl/analysis/SkSLCheckProgramStructure.cpp`

## 概述

`SkSLCheckProgramStructure.cpp` 实现了 SkSL 编译器中的程序结构检查功能。该模块主要执行两项关键验证：

1. **递归检测**: 检测 SkSL 程序中是否存在函数调用环（function call cycle），即直接递归或间接递归。SkSL 作为着色器语言不允许递归调用，因为 GPU 着色器执行模型不支持动态调用栈。
2. **调用深度限制**: 检查函数调用链深度是否超过预设上限（50 层），防止过深的调用层次导致编译或执行问题。

该分析通过深度优先搜索（DFS）遍历函数调用图，使用着色标记法（三色标记）检测图中的环路。

## 架构位置

```
Skia
└── src/sksl/
    ├── SkSLAnalysis.h                      // 分析接口声明
    ├── SkSLContext.h                        // 编译上下文（含错误报告器）
    ├── analysis/
    │   ├── SkSLCheckProgramStructure.cpp    // 本文件
    │   └── SkSLProgramVisitor.h            // 访问者基类
    └── ir/
        ├── SkSLProgram.h                   // 程序 IR
        ├── SkSLFunctionDefinition.h        // 函数定义
        └── SkSLFunctionCall.h              // 函数调用
```

本模块在编译器的语义检查阶段被调用，位于类型检查之后、代码生成之前。

## 主要类与结构体

### `ProgramStructureVisitor`（局部类）

- **继承关系**: 继承自 `ProgramVisitor`
- **作用域**: 定义在 `CheckProgramStructure` 函数体内部
- **核心职责**: 实现函数调用图的 DFS 遍历与环检测

### `FunctionState`（枚举）

- `kVisiting`: 函数正在被访问中（在当前 DFS 路径上）
- `kVisited`: 函数已完成访问

### 成员变量

| 成员 | 类型 | 用途 |
|------|------|------|
| `fContext` | `const Context&` | 编译上下文，用于错误报告 |
| `fFunctionMap` | `THashMap<const FunctionDeclaration*, FunctionState>` | 函数访问状态映射表 |
| `fStack` | `std::vector<const FunctionDeclaration*>` | 当前 DFS 调用栈，用于构建错误消息 |

## 公共 API 函数

### `bool Analysis::CheckProgramStructure(const Program& program)`

- **功能**: 检查 SkSL 程序的结构有效性，包括递归检测和调用深度检查
- **参数**: `program` — 待检查的 SkSL 程序
- **返回值**: 始终返回 `true`（错误通过 `ErrorReporter` 报告）
- **副作用**: 若检测到递归或调用深度过大，通过 `Context::fErrors` 报告错误

## 内部实现细节

### 递归检测算法

该实现采用经典的 DFS 环检测算法：

1. **入口**: 遍历程序中所有函数定义（包括未被引用的函数）
2. **首次访问**: 将函数标记为 `kVisiting`，压入调用栈，递归遍历函数体
3. **函数调用处理**: 遇到 `FunctionCall` 表达式时，跳转到被调用函数的定义继续 DFS
4. **环检测**: 如果在 DFS 过程中遇到一个状态为 `kVisiting` 的函数，说明存在调用环
5. **完成访问**: 函数遍历完成后，标记为 `kVisited`，弹出调用栈
6. **剪枝**: 已标记为 `kVisited` 的函数不会被重复访问

### 错误消息构建

当检测到递归时，算法从 `fStack` 中回溯构建调用链信息：

```
potential recursion (function call cycle) not allowed:
    funcA(...)
    funcB(...)
    funcC(...)
    funcA(...)
```

### 深度限制

```cpp
static constexpr size_t kProgramStackDepthLimit = 50;
```

当调用栈深度达到 50 时，即使没有递归也会报错，防止过深的调用链。

### 内建函数处理

在 `visitExpression` 中，内建函数（`isIntrinsic() == true`）和无定义的函数声明被跳过，因为它们不可能参与用户代码中的递归。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkTHash.h` | `THashMap` 高性能哈希表，存储函数状态 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLProgramVisitor.h` | 访问者基类 |
| `SkSLFunctionCall.h` | 函数调用表达式 |
| `SkSLFunctionDeclaration.h` | 函数声明（用于唯一标识函数） |
| `SkSLFunctionDefinition.h` | 函数定义（函数体） |
| `SkSLProgram.h` | 程序 IR（包含所有程序元素） |

## 设计模式与设计决策

1. **DFS 环检测（三色标记法）**: 使用 `kVisiting`（灰色）和 `kVisited`（黑色）两种状态，配合 `fFunctionMap` 中的缺失状态（白色），实现经典的有向图环检测
2. **访问者模式**: 继承 `ProgramVisitor` 实现 AST 遍历，与 SkSL 分析框架保持一致
3. **全函数扫描**: 遍历所有函数定义（包括未被调用的），确保即使在死代码中也能检测递归，这是语言规范要求的
4. **提前终止**: 错误发生时将函数标记为 `kVisited` 避免重复报告
5. **返回值设计**: 函数始终返回 `true`，错误通过 `ErrorReporter` 机制报告，这与 SkSL 编译器的整体错误处理策略一致

## 性能考量

- **记忆化**: `fFunctionMap` 确保每个函数最多被遍历一次，整体复杂度为 O(V + E)，其中 V 为函数数量，E 为调用边数量
- **高效哈希表**: 使用 Skia 自定义的 `THashMap`（开放寻址哈希表），比 `std::unordered_map` 更高效
- **深度限制**: 50 层的硬编码限制既能容纳合理的调用链，又能防止病态输入导致的栈溢出
- **编译期分析**: 所有开销发生在编译时，不影响着色器运行时性能

## 相关文件

- `src/sksl/SkSLAnalysis.h` — `CheckProgramStructure` 函数声明
- `src/sksl/analysis/SkSLProgramVisitor.h` — 访问者基类
- `src/sksl/SkSLContext.h` — 编译上下文
- `src/sksl/SkSLErrorReporter.h` — 错误报告接口
- `src/sksl/ir/SkSLProgram.h` — 程序 IR 定义
- `src/sksl/ir/SkSLFunctionDefinition.h` — 函数定义节点
- `src/sksl/ir/SkSLFunctionCall.h` — 函数调用节点
