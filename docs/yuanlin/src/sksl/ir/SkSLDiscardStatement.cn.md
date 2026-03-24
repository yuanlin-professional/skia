# SkSL DiscardStatement（丢弃语句）

> 源文件：[src/sksl/ir/SkSLDiscardStatement.h](../../../src/sksl/ir/SkSLDiscardStatement.h)、[src/sksl/ir/SkSLDiscardStatement.cpp](../../../src/sksl/ir/SkSLDiscardStatement.cpp)

## 概述

`DiscardStatement` 是 SkSL 中间表示（IR）中的 `discard` 语句节点。`discard` 是片段着色器专有的语句，用于丢弃当前片段（即不输出任何颜色到帧缓冲区）。该类在创建时验证 `discard` 仅出现在片段着色器程序中，其他着色器阶段（如顶点、计算着色器）中的 `discard` 会被报告为编译错误。

## 架构位置

`DiscardStatement` 位于 SkSL IR 的语句节点层：

```
SkSL 源代码: discard;
       |
       v
  Parser -> DiscardStatement::Convert()（验证着色器阶段）
       |
       v
  DiscardStatement（IR 节点）
       |
       v
  CodeGen（生成目标平台的 discard 指令）
```

## 主要类与结构体

### `class DiscardStatement`

继承自 `Statement`，final 类：

| 成员 | 说明 |
|------|------|
| （无额外成员） | 仅包含继承自 Statement 的 `fPosition` 和 `fKind` |

静态常量：
| 常量 | 值 | 说明 |
|------|----|------|
| `kIRNodeKind` | `Kind::kDiscard` | IR 节点类型标识 |

## 公共 API 函数

### 工厂方法

- **`static Convert(context, pos)`** —— 创建 discard 语句，验证当前程序是片段着色器。如果在非片段着色器中使用，通过 `ErrorReporter` 报告错误并返回 `nullptr`。

- **`static Make(context, pos)`** —— 创建 discard 语句，仅通过断言验证。用于编译器内部已知安全的场景（如内联器克隆）。

### 文本表示

- **`description()`** —— 返回固定字符串 `"discard;"`

## 内部实现细节

### 着色器阶段验证

`Convert` 方法使用 `ProgramConfig::IsFragment()` 检查当前编译的程序类型：

```cpp
if (!ProgramConfig::IsFragment(context.fConfig->fKind)) {
    context.fErrors->error(pos, "discard statement is only permitted in fragment shaders");
    return nullptr;
}
```

这确保了 `discard` 语句仅出现在以下 `ProgramKind` 中：
- `kFragment`
- `kGraphiteFragment`

### 极简的节点结构

`DiscardStatement` 是 SkSL IR 中最简单的语句节点之一——它不包含任何子表达式或子语句，仅记录源代码位置。构造函数只需一个 `Position` 参数。

### ProgramVisitor 中的叶子节点

在 `SkSLAnalysis.cpp` 的 `TProgramVisitor` 中，`DiscardStatement` 被作为叶子语句处理（直接返回 `false`，无需递归遍历子节点）。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLStatement.h` | 语句基类 |
| `SkSLIRNode.h` | IR 节点基础设施 |
| `SkSLContext.h` | 编译上下文 |
| `SkSLErrorReporter.h` | 错误报告 |
| `SkSLProgramSettings.h` | `ProgramConfig::IsFragment` 检查 |
| `SkSLPosition.h` | 源代码位置 |

## 设计模式与设计决策

1. **Convert/Make 双入口**：遵循 SkSL IR 的标准模式，`Convert` 用于用户代码路径，`Make` 用于编译器内部路径。
2. **编译时验证**：着色器阶段检查在语句创建时执行，而非延迟到代码生成阶段，提供更早、更清晰的错误信息。
3. **零开销设计**：`DiscardStatement` 不包含任何额外数据，仅继承基类的位置信息。
4. **固定描述**：`description()` 返回编译时常量字符串，无需动态构造。

## 性能考量

- `DiscardStatement` 节点极其轻量（仅包含位置信息，约 8-12 字节）
- `Convert` 的验证为单次布尔检查，O(1) 开销
- `description()` 返回字面量字符串，无内存分配

## 相关文件

- `src/sksl/ir/SkSLStatement.h` —— 语句基类
- `src/sksl/ir/SkSLReturnStatement.h` —— return 语句（类似的控制流语句）
- `src/sksl/ir/SkSLBreakStatement.h` —— break 语句（另一个简单控制流语句）
- `src/sksl/ir/SkSLContinueStatement.h` —— continue 语句
- `src/sksl/SkSLInliner.cpp` —— 内联器使用 `DiscardStatement::Make` 克隆 discard 语句
- `src/sksl/SkSLProgramKind.h` —— `ProgramKind` 枚举定义
