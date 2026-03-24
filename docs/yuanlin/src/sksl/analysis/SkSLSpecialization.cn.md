# SkSL Specialization（函数特化分析）

> 源文件：[src/sksl/analysis/SkSLSpecialization.h](../../../src/sksl/analysis/SkSLSpecialization.h)、[src/sksl/analysis/SkSLSpecialization.cpp](../../../src/sksl/analysis/SkSLSpecialization.cpp)

## 概述

`SkSLSpecialization` 模块实现了 SkSL 的函数特化（function specialization）分析。函数特化是一种优化技术，当函数参数在所有调用点都绑定到全局 uniform 变量时，编译器可以为每种参数组合生成特化版本，将 uniform 参数内联到函数体中。该模块负责发现需要特化的函数、收集特化参数映射，并为代码生成器提供特化查询接口。

## 架构位置

函数特化分析在编译管道的后期阶段运行，为代码生成器提供信息：

```
编译完成的 Program
       |
       v
FindFunctionsToSpecialize()（分析阶段）
       |
       v
SpecializationInfo（特化信息）
       |
       v
代码生成器（生成特化函数副本）
```

## 主要类与结构体

### 类型别名

| 别名 | 类型 | 说明 |
|------|------|------|
| `SpecializationIndex` | `int` | 特化版本索引（-1 = 未特化） |
| `SpecializedParameters` | `THashMap<const Variable*, const Expression*>` | 单个特化的参数映射 |
| `Specializations` | `TArray<SpecializedParameters>` | 某函数的所有特化版本 |
| `SpecializationMap` | `THashMap<const FunctionDeclaration*, Specializations>` | 全局特化映射 |
| `SpecializedCallMap` | `THashMap<SpecializedCallKey, SpecializationIndex>` | 函数调用到特化索引的映射 |
| `ParameterMatchesFn` | `std::function<bool(const Variable&)>` | 参数是否需要特化的判断回调 |

### `struct SpecializedFunctionKey`

特化函数的键（用于代码生成阶段的查找）：

| 字段 | 说明 |
|------|------|
| `fDeclaration` | 函数声明指针 |
| `fSpecializationIndex` | 特化索引 |

### `struct SpecializedCallKey`

特化调用的键：

| 字段 | 说明 |
|------|------|
| `fStablePointer` | 函数调用的稳定指针 |
| `fParentSpecializationIndex` | 父级特化索引 |

### `struct SpecializationInfo`

完整的特化信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fSpecializationMap` | `SpecializationMap` | 函数到特化版本列表的映射 |
| `fSpecializedCallMap` | `SpecializedCallMap` | 调用点到特化索引的映射 |

## 公共 API 函数

### `FindFunctionsToSpecialize(program, info, specializationFn)`

主分析函数。遍历程序的调用图，找出所有需要特化的函数及其参数映射。

- 从 `main()` 开始遍历调用图
- 对每个函数调用，检查参数是否满足特化条件
- 支持特化的继承传播（如果函数 A 的特化参数传递给函数 B，则 B 也会被特化）
- 确保不可达的特化函数也在映射中注册（避免代码生成器错误）

### `FindSpecializationIndexForCall(call, info, activeSpecializationIndex)`

给定函数调用和当前活跃的特化索引，查找调用目标的特化索引。

### `FindSpecializedParametersForFunction(func, info)`

返回指定函数中被特化参数的位掩码（`SkBitSet`）。

### `GetParameterMappingsForFunction(func, info, specializationIndex, callback)`

遍历函数在特定特化索引下的所有特化参数，对每个参数调用回调函数。

## 内部实现细节

### Searcher 访问者

`FindFunctionsToSpecialize` 内部的 `Searcher` 类继承 `ProgramVisitor`，实现以下逻辑：

1. **参数匹配**：对每个函数调用的参数，检查是否为变量引用或字段访问
2. **全局/参数变量检查**：
   - 全局变量（uniform）直接添加到特化参数
   - 函数参数则从继承的特化映射中查找其对应的 uniform
3. **去重**：使用 `parameter_mappings_are_equal` 检查相同的特化是否已存在
4. **递归遍历**：如果发现新的特化，递归进入被调用函数的定义，传播继承的特化参数
5. **非特化函数**：对未特化但被调用的函数也进行遍历（但跳过重复遍历）

### 特化参数的继承

当特化函数 A 调用函数 B，且将特化参数传递给 B 的参数时，B 会继承这些特化。这通过 `fInheritedSpecializations` 和 `fInheritedSpecializationIndex` 实现。

### 参数等价性比较

`parameter_mappings_are_equal` 使用 `Analysis::IsSameExpressionTree` 比较两个特化的参数映射是否等价，确保相同参数组合的特化不会被重复创建。

### 不可达函数处理

即使函数从 `main()` 不可达，只要它有需要特化的参数，就会被添加到特化映射中（特化数组为空）。这避免了代码生成器尝试生成未特化的通用版本。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkTHash.h` | 哈希映射和哈希集 |
| `SkChecksum.h` | `SkGoodHash` 用于键的哈希 |
| `SkBitSet.h` | 参数位掩码 |
| `SkSLAnalysis.h` | `IsSameExpressionTree` 表达式比较 |
| `SkSLProgramVisitor.h` | IR 遍历框架 |

## 设计模式与设计决策

1. **回调式参数匹配**：通过 `ParameterMatchesFn` 回调让调用者决定哪些参数需要特化，增加灵活性。
2. **稳定指针键**：使用 `FunctionCall::stablePointer()` 而非直接指针，避免 IR 变换后指针失效。
3. **双层映射**：`SpecializationMap` 存储"函数 -> 特化列表"，`SpecializedCallMap` 存储"调用点 -> 特化索引"，分离了不同维度的查询需求。
4. **特化继承传播**：自动处理特化参数在调用链中的传播，无需调用者手动管理。

## 性能考量

- 使用 `THashSet` 跟踪已访问的非特化函数，避免重复遍历
- 特化参数映射的等价比较使用表达式树比较而非简单的指针比较，确保语义正确性
- `SkBitSet` 用于高效的参数位掩码操作
- 通过 `swap` 操作而非复制来切换继承的特化上下文

## 相关文件

- `src/sksl/SkSLAnalysis.h` —— `IsSameExpressionTree` 等分析工具
- `src/sksl/codegen/` 目录 —— 代码生成器使用特化信息生成特化函数
- `src/sksl/ir/SkSLFunctionCall.h` —— 函数调用节点，`stablePointer()` 方法
- `src/sksl/ir/SkSLFunctionDeclaration.h` —— 函数声明节点
