# SkSL DebugTracePlayer（调试追踪回放器）

> 源文件：[src/sksl/tracing/SkSLDebugTracePlayer.h](../../../src/sksl/tracing/SkSLDebugTracePlayer.h)、[src/sksl/tracing/SkSLDebugTracePlayer.cpp](../../../src/sksl/tracing/SkSLDebugTracePlayer.cpp)

## 概述

`SkSLDebugTracePlayer` 是 SkSL 着色器调试追踪数据的回放器，提供类似传统调试器的交互体验。它能够在预先录制的追踪数据上模拟单步执行（step）、跨步执行（step over）、跳出函数（step out）和运行到断点（run）等操作，并提供调用栈、变量值、行号等实时调试信息。

## 架构位置

`SkSLDebugTracePlayer` 位于调试追踪子系统的消费端：

```
着色器执行 -> Tracer（记录追踪数据）
                 |
                 v
         DebugTracePriv（存储追踪数据）
                 |
                 v
     SkSLDebugTracePlayer（回放和查询）
                 |
                 v
           调试器 UI（显示调试信息）
```

## 主要类与结构体

### `class SkSLDebugTracePlayer`

核心回放器类，主要成员：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fDebugTrace` | `sk_sp<DebugTracePriv>` | 追踪数据（共享所有权） |
| `fCursor` | `size_t` | 当前读取位置 |
| `fScope` | `int` | 当前作用域深度 |
| `fSlots` | `std::vector<Slot>` | 所有变量槽位的当前状态 |
| `fStack` | `std::vector<StackFrame>` | 执行栈 |
| `fDirtyMask` | `std::optional<SkBitSet>` | 最近一步中被修改的变量槽位 |
| `fReturnValues` | `std::optional<SkBitSet>` | 包含返回值的变量槽位 |
| `fLineNumbers` | `LineNumberMap` | 每行号的剩余到达次数 |
| `fBreakpointLines` | `BreakpointSet` | 已设置的断点行号集合 |

### `struct StackFrame`（内部）

| 字段 | 类型 | 说明 |
|------|------|------|
| `fFunction` | `int32_t` | 函数信息索引 |
| `fLine` | `int32_t` | 当前行号 |
| `fDisplayMask` | `SkBitSet` | 该函数中已触及的变量槽位 |

### `struct Slot`（内部）

| 字段 | 类型 | 说明 |
|------|------|------|
| `fValue` | `int32_t` | 当前值（原始位模式） |
| `fScope` | `int` | 变量所在的作用域深度 |
| `fWriteTime` | `size_t` | 最近写入的时间（游标位置） |

### `struct VariableData`

返回给调试器 UI 的变量数据：

| 字段 | 类型 | 说明 |
|------|------|------|
| `fSlotIndex` | `int` | 变量槽位索引 |
| `fDirty` | `bool` | 是否在最近一步中被修改 |
| `fValue` | `double` | 经过类型转换的值 |

## 公共 API 函数

### 执行控制

- **`reset(trace)`** —— 重置到追踪起始位置（保留断点设置）
- **`step()`** —— 前进到下一个 Line 操作
- **`stepOver()`** —— 前进到同一栈深度的下一个 Line 操作，跳过函数调用内部
- **`stepOut()`** —— 前进直到退出当前栈帧
- **`run()`** —— 运行直到遇到断点或追踪完成

### 断点管理

- **`setBreakpoints(lines)` / `addBreakpoint(line)` / `removeBreakpoint(line)`** —— 管理断点
- **`getBreakpoints()`** —— 获取所有断点

### 状态查询

- **`traceHasCompleted()`** —— 追踪是否已结束
- **`atBreakpoint()`** —— 当前是否在断点处
- **`cursor()`** —— 获取当前游标位置
- **`getCurrentLine()` / `getCurrentLineInStackFrame(index)`** —— 获取当前行号
- **`getCallStack()`** —— 获取调用栈（函数索引数组）
- **`getStackDepth()`** —— 获取栈深度
- **`getLineNumbersReached()`** —— 获取所有已到达/将到达的行号及剩余次数

### 变量查询

- **`getLocalVariables(stackFrameIndex)`** —— 获取指定栈帧的局部变量
- **`getGlobalVariables()`** —— 获取全局变量

## 内部实现细节

### execute 方法

核心执行方法，处理五种追踪操作：

| 操作 | 行为 | 返回值 |
|------|------|--------|
| `kLine` | 更新当前行号，减少行号计数 | `true`（停止点） |
| `kVar` | 更新变量值、作用域、写入时间和显示掩码 | `false` |
| `kEnter` | 将新栈帧压入执行栈 | `false` |
| `kExit` | 从执行栈弹出栈帧 | `true`（停止点） |
| `kScope` | 调整作用域深度，丢弃超出作用域的变量 | `false` |

### stepOver 的栈深度追踪

`stepOver` 记录初始栈深度，只有在栈深度回到初始深度或更浅时才会在 Line 操作处停止。这样可以跳过被调用函数的内部执行。

### 变量显示排序

`getVariablesForDisplayMask` 按最近写入时间降序排列变量，使最新修改的变量显示在顶部，方便开发者查看。

### 返回值处理

返回值变量与父函数（而非当前函数）关联，因为当前函数即将退出。`tidyState` 在每步执行前清除上一步的返回值标记。

### 全局帧

执行栈的第一个条目是"全局"帧（在进入 `main()` 之前），因此 `stackFrameIndex` 在对外接口中需要加 1 偏移。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLDebugTracePriv.h` | 追踪数据结构 |
| `SkRefCnt.h` | `sk_sp` 智能指针 |
| `SkBitSet.h` | 变量槽位的位集操作 |

## 设计模式与设计决策

1. **预录制回放**：追踪数据是预先录制的完整执行轨迹，回放器只是按序读取并模拟调试器的行为。
2. **脏位追踪**：`fDirtyMask` 高效标记最近修改的变量，避免全量比较。
3. **作用域感知**：当作用域减小时自动移除超出作用域的变量，保持显示的准确性。
4. **写入时间排序**：通过记录每个变量的最近写入时间，实现"最近修改优先"的显示排序。

## 性能考量

- `SkBitSet` 的使用使变量掩码操作为 O(1)
- `execute` 方法是 O(1) 的单步操作
- `getVariablesForDisplayMask` 的排序仅在用户查询时执行
- `updateVariableWriteTime` 更新整个变量组（而非单个槽位）

## 相关文件

- `src/sksl/tracing/SkSLDebugTracePriv.h` / `.cpp` —— 追踪数据存储和转储
- `src/sksl/tracing/SkSLTraceHook.h` / `.cpp` —— 追踪事件回调
- `include/sksl/SkSLDebugTrace.h` —— 公共调试追踪接口
- `src/utils/SkBitSet.h` —— 位集工具
