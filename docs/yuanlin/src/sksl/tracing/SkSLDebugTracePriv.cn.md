# SkSL DebugTracePriv（调试追踪数据）

> 源文件：[src/sksl/tracing/SkSLDebugTracePriv.h](../../../src/sksl/tracing/SkSLDebugTracePriv.h)、[src/sksl/tracing/SkSLDebugTracePriv.cpp](../../../src/sksl/tracing/SkSLDebugTracePriv.cpp)

## 概述

`DebugTracePriv` 是 SkSL 调试追踪子系统的数据容器，继承自公共接口 `DebugTrace`。它存储着色器执行过程中收集的所有调试信息，包括追踪事件序列（`TraceInfo`）、变量槽位信息（`SlotDebugInfo`）、函数信息（`FunctionDebugInfo`）以及源代码。该类还提供了数据的格式化转储和值的类型转换功能。

## 架构位置

`DebugTracePriv` 是调试追踪子系统的核心数据层：

```
代码生成器 -> 填充 fSlotInfo、fFuncInfo
着色器运行时 -> 通过 TraceHook 填充 fTraceInfo
DebugTracePriv（数据容器）
       |
       +-> SkSLDebugTracePlayer（回放）
       +-> dump()（文本转储）
```

## 主要类与结构体

### `struct TraceInfo`

单个追踪事件：

| 字段 | 类型 | 说明 |
|------|------|------|
| `op` | `TraceInfo::Op` | 操作类型 |
| `data[2]` | `int32_t[2]` | 操作数据（含义取决于 op） |

操作类型：

| Op | data[0] | data[1] | 说明 |
|----|---------|---------|------|
| `kLine` | 行号 | (未使用) | 执行到某一行 |
| `kVar` | 槽位索引 | 值 | 变量值变更 |
| `kEnter` | 函数索引 | (未使用) | 进入函数 |
| `kExit` | 函数索引 | (未使用) | 退出函数 |
| `kScope` | 作用域变化量 | (未使用) | 作用域深度变化 |

### `struct SlotDebugInfo`

变量槽位的调试信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `std::string` | 变量全名（如 `myArray[3].myStruct.myVector`） |
| `columns` | `uint8_t` | 列数（1=标量, N=向量, NxM=矩阵） |
| `rows` | `uint8_t` | 行数 |
| `componentIndex` | `uint8_t` | 分量索引 |
| `groupIndex` | `int` | 组内索引（复合类型的相邻槽位） |
| `numberKind` | `Type::NumberKind` | 数值类型（float/int/uint/bool） |
| `line` | `int` | 变量在源代码中的行号 |
| `pos` | `Position` | 变量在源代码中的位置 |
| `fnReturnValue` | `int` | 是否为函数返回值（1 或 -1） |

### `struct FunctionDebugInfo`

函数调试信息：

| 字段 | 类型 | 说明 |
|------|------|------|
| `name` | `std::string` | 完整的函数声明（如 `float myFunction(half4 color)`） |

### `class DebugTracePriv`

继承自 `DebugTrace`，核心数据成员：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fTraceCoord` | `SkIPoint` | 被追踪的设备坐标像素 |
| `fUniformInfo` | `std::vector<SlotDebugInfo>` | Uniform 槽位信息 |
| `fSlotInfo` | `std::vector<SlotDebugInfo>` | 变量槽位信息 |
| `fFuncInfo` | `std::vector<FunctionDebugInfo>` | 函数信息 |
| `fTraceInfo` | `std::vector<TraceInfo>` | 追踪事件序列 |
| `fSource` | `std::vector<std::string>` | 源代码（按行分割） |
| `fTraceHook` | `std::unique_ptr<TraceHook>` | 追踪钩子 |

## 公共 API 函数

### 数据设置

- **`setTraceCoord(coord)`** —— 设置要追踪的设备坐标像素
- **`setSource(source)`** —— 附加 SkSL 源代码（自动按行分割）

### 值转换

- **`interpretValueBits(slotIndex, valueBits)`** —— 将 int32_t 位模式按类型解释为 double（float 用 memcpy，uint 用 memcpy，其他直接转换）
- **`slotValueToString(slotIndex, value)`** —— 将数值转为文本（bool 为 "true"/"false"，其他为 "%.8g" 格式）
- **`getSlotValue(slotIndex, value)`** —— 组合 `interpretValueBits` 和 `slotValueToString`
- **`getSlotComponentSuffix(slotIndex)`** —— 获取分量后缀（向量为 ".x/.y/.z/.w"，矩阵为 "[col][row]"）

### 调试输出

- **`dump(o)`** —— 生成人类可读的完整追踪转储，包括槽位信息、函数信息和缩进格式化的追踪事件

## 内部实现细节

### 值的位模式转换

变量值以 `int32_t` 位模式存储。`interpretValueBits` 使用 `memcpy` 进行安全的类型双关（type punning），遵循 C++ 的严格别名规则：

```cpp
case NumberKind::kFloat: {
    float floatValue;
    memcpy(&floatValue, &valueBits, sizeof(floatValue));
    return floatValue;
}
```

### dump 的格式化输出

`dump` 方法生成结构化的文本输出：
1. 先输出所有变量槽位信息（格式：`$0 = name (type, L行号)`）
2. 再输出所有函数信息（格式：`F0 = declaration`）
3. 最后输出缩进的追踪事件（`enter`/`exit` 调整缩进层级，`scope` 也调整缩进）

### 源代码按行分割

`setSource` 使用 `stringstream` 和 `getline` 将源代码按换行符分割为行数组，行号直接用作数组索引。

### 矩阵分量后缀

对于矩阵类型，分量后缀格式为 `[column][row]`，使用 `componentIndex / rows` 和 `componentIndex % rows` 计算列和行索引。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLDebugTrace.h` | 公共基类 |
| `SkSLType.h` | `NumberKind` 枚举 |
| `SkSLPosition.h` | 源代码位置 |
| `SkSLTraceHook.h` | 追踪钩子 |
| `SkStream.h` | `SkWStream` 输出 |
| `SkPoint.h` | `SkIPoint` 坐标 |

## 设计模式与设计决策

1. **分层设计**：`DebugTrace`（公共接口）-> `DebugTracePriv`（内部实现），隐藏实现细节。
2. **延迟类型解释**：值以原始位模式存储，类型转换仅在需要显示时执行。
3. **组索引机制**：复合类型（数组、结构体）的多个槽位通过 `groupIndex` 关联，支持整体更新写入时间。
4. **Uniform 分离**：`fUniformInfo` 独立于 `fSlotInfo`，因为 Uniform 的存储和访问方式不同。

## 性能考量

- `TraceInfo` 使用定长数组（12 字节），对缓存友好
- 位模式转换使用 `memcpy` 而非 `reinterpret_cast`，确保正确性且编译器可优化
- `snprintf` 用于浮点格式化，精度为 8 位有效数字
- 源代码按行存储，行号索引为 O(1)

## 相关文件

- `include/sksl/SkSLDebugTrace.h` —— 公共调试追踪接口
- `src/sksl/tracing/SkSLTraceHook.h` / `.cpp` —— 追踪钩子
- `src/sksl/tracing/SkSLDebugTracePlayer.h` / `.cpp` —— 追踪回放器
- `src/sksl/ir/SkSLType.h` —— `NumberKind` 枚举定义
