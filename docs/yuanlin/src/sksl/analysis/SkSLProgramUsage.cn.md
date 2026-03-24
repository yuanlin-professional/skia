# SkSL ProgramUsage（程序使用量统计）

> 源文件：[src/sksl/analysis/SkSLProgramUsage.h](../../../src/sksl/analysis/SkSLProgramUsage.h)、[src/sksl/analysis/SkSLProgramUsage.cpp](../../../src/sksl/analysis/SkSLProgramUsage.cpp)

## 概述

`ProgramUsage` 是 SkSL 编译器中用于追踪程序 IR 中变量、函数和结构体使用情况的"侧车"类（side-car class）。它维护三个哈希映射表，分别记录变量的读/写计数、函数的调用计数和结构体的引用计数。这些使用量数据是死代码消除、内联决策和优化验证的关键依据。

## 架构位置

`ProgramUsage` 作为 `Program` 的附属数据存在，在编译和优化流程中被广泛使用：

```
Program
  +-- fUsage: ProgramUsage
         |
         +-> 用于死代码消除（EliminateDeadFunctions/Variables）
         +-> 用于内联决策（Inliner::analyze）
         +-> 用于优化验证（比较优化前后的使用量一致性）
```

## 主要类与结构体

### `class ProgramUsage`

使用量统计的核心类：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fStructCounts` | `THashMap<const Symbol*, int>` | 结构体类型引用计数 |
| `fCallCounts` | `THashMap<const Symbol*, int>` | 函数调用计数 |
| `fVariableCounts` | `THashMap<const Variable*, VariableCounts>` | 变量使用计数 |

### `struct VariableCounts`

变量的详细使用计数：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fVarExists` | `int` | 变量是否存在（0 表示可能已被删除） |
| `fRead` | `int` | 读取次数 |
| `fWrite` | `int` | 写入次数 |

## 公共 API 函数

### 查询

- **`get(variable)`** —— 获取变量的使用计数
- **`get(function)`** —— 获取函数的调用次数
- **`isDead(variable)`** —— 判断变量是否"死"（未被读取且未被有效写入）

### 增量更新

- **`add(expr)` / `add(stmt)` / `add(element)`** —— 增加表达式/语句/程序元素的引用计数
- **`remove(expr)` / `remove(stmt)` / `remove(element)`** —— 减少引用计数

### 比较

- **`operator==` / `operator!=`** —— 比较两个 ProgramUsage 是否等价

## 内部实现细节

### ProgramUsageVisitor

内部访问者类，使用 `delta` 参数（+1 或 -1）实现引用计数的增减：

- 遍历 `VariableReference` 时，根据 `refKind`（读/写/读写/指针）更新对应计数
- 遍历 `FunctionCall` 时，更新函数调用计数
- 遍历 `VarDeclaration` 时，标记变量存在（`fVarExists += delta`），初始值视为一次写入
- 遍历类型时，递归统计结构体和数组的引用

### isDead 的死变量判定

```cpp
bool ProgramUsage::isDead(const Variable& v) const {
    // 不消除 in/out/uniform 变量
    // 不消除 opaque 类型（采样器、原子等）
    // 变量"死"的条件：从未读取 且 写入次数 <= 初始值写入次数
    return !counts.fRead && (counts.fWrite <= (v.initialValue() ? 1 : 0));
}
```

### 等价比较的特殊处理

`operator==` 采用双向比较策略，因为：
- 优化后重新分析可能不包含已被移除的变量/函数（计数为 0）
- 原始使用量映射仍保留这些条目（计数归零但条目存在）
- 双向比较时跳过零计数条目，确保语义等价

### 模块使用量统计

`GetUsage(Module)` 从模块及其所有父模块中收集使用量，通过遍历模块继承链实现完整的统计。

### 结构体嵌套引用

类型访问器递归处理数组和结构体：数组类型递归到其组件类型，结构体类型计数引用并递归遍历其字段，确保嵌套结构体也被正确计数。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkTHash.h` | 哈希映射实现 |
| `SkSLAnalysis.h` | `GetUsage` 工厂函数声明 |
| `SkSLProgramVisitor.h` | IR 遍历框架 |
| 各种 IR 节点头文件 | 变量引用、函数调用、声明等 |

## 设计模式与设计决策

1. **增量更新模式**：通过 `add`/`remove` 支持增量维护使用量，无需每次变更后全量重算。
2. **delta 参数设计**：+1 表示添加引用，-1 表示移除引用，一套访问者代码同时处理两种操作。
3. **侧车类设计**：`ProgramUsage` 独立于 `Program` 的 IR 结构，可以在不修改 IR 的情况下维护使用量。
4. **保守的死变量判定**：永远不消除 in/out/uniform/opaque 变量，即使看似未使用。

## 性能考量

- 哈希映射查找为 O(1) 平均时间
- 增量更新避免了全量重算的开销
- `operator==` 使用双向遍历而非排序比较，适合映射表大小不对称的情况
- `VariableCounts` 结构体仅 12 字节，缓存友好

## 相关文件

- `src/sksl/SkSLAnalysis.h` —— `GetUsage` 工厂函数
- `src/sksl/analysis/SkSLProgramVisitor.h` —— 遍历框架
- `src/sksl/SkSLCompiler.cpp` —— 使用 `ProgramUsage` 进行优化
- `src/sksl/SkSLInliner.cpp` —— 使用 `ProgramUsage` 进行内联决策
- `src/sksl/transform/SkSLTransform.h` —— 死代码消除变换
- `src/sksl/ir/SkSLProgram.h` —— 持有 `ProgramUsage` 实例
