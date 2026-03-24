# SkSL TraceHook（追踪钩子）

> 源文件：[src/sksl/tracing/SkSLTraceHook.h](../../../src/sksl/tracing/SkSLTraceHook.h)、[src/sksl/tracing/SkSLTraceHook.cpp](../../../src/sksl/tracing/SkSLTraceHook.cpp)

## 概述

`TraceHook` 和 `Tracer` 定义了 SkSL 着色器调试追踪的回调接口和默认实现。`TraceHook` 是一个纯虚基类，声明了着色器执行过程中的五种追踪事件：行号变更、变量值变更、函数进入、函数退出和作用域变化。`Tracer` 是其具体实现，将所有追踪事件记录到 `TraceInfo` 向量中，供调试器回放使用。

## 架构位置

`TraceHook` 位于 SkSL 调试追踪子系统中：

```
代码生成器（插入追踪指令）
       |
       v
着色器运行时（调用 TraceHook 回调）
       |
       v
Tracer（记录 TraceInfo）
       |
       v
DebugTracePriv（持有追踪数据）
       |
       v
SkSLDebugTracePlayer（回放追踪数据）
```

## 主要类与结构体

### `class TraceHook`（抽象基类）

定义追踪回调接口，所有方法为纯虚函数。

### `class Tracer`（具体实现）

继承 `TraceHook`，将追踪事件写入 `TraceInfo` 向量。

| 成员 | 类型 | 说明 |
|------|------|------|
| `fTraceInfo` | `std::vector<TraceInfo>*` | 指向追踪数据存储的指针 |

## 公共 API 函数

### TraceHook 虚函数

| 方法 | 参数 | 说明 |
|------|------|------|
| `line(lineNum)` | 行号 | 执行到某一行 |
| `var(slot, val)` | 槽位索引、值 | 变量值发生变化 |
| `enter(fnIdx)` | 函数索引 | 进入函数 |
| `exit(fnIdx)` | 函数索引 | 退出函数 |
| `scope(delta)` | 作用域变化量 | 作用域深度增减 |

### Tracer 工厂方法

- **`static Make(traceInfo)`** —— 创建 `Tracer` 实例并绑定到指定的 `TraceInfo` 向量

## 内部实现细节

每个 `Tracer` 回调方法都简单地将一个 `TraceInfo` 结构体追加到 `fTraceInfo` 向量中：

```cpp
void Tracer::line(int lineNum) {
    fTraceInfo->push_back({TraceInfo::Op::kLine, {lineNum, 0}});
}
```

`TraceInfo` 使用固定大小的 `int32_t data[2]` 数组，不同操作类型使用不同的字段含义。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `SkSLDebugTracePriv.h` | `TraceInfo` 结构体定义 |

## 设计模式与设计决策

1. **策略模式**：`TraceHook` 作为抽象接口，允许不同的追踪实现（如直接记录、网络传输等）。
2. **工厂方法**：`Tracer::Make` 隐藏构造细节，返回 `unique_ptr`。
3. **最小化接口**：仅五个虚函数，覆盖所有必要的追踪事件类型。
4. **延迟类型转换**：变量值以原始 `int32_t` 位模式存储，类型解释延迟到回放阶段。

## 性能考量

- 每个追踪事件仅涉及一次 `push_back` 操作
- `TraceInfo` 使用固定大小（12 字节），避免动态分配
- 虚函数调用的开销在调试模式下可接受

## 相关文件

- `src/sksl/tracing/SkSLDebugTracePriv.h` —— `TraceInfo` 定义和追踪数据容器
- `src/sksl/tracing/SkSLDebugTracePlayer.h` —— 追踪数据的回放器
- `src/sksl/codegen/` —— 代码生成器插入追踪指令
