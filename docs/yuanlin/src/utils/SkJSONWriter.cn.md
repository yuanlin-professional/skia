# SkJSONWriter — JSON 结构化写入器

> 源文件：[src/utils/SkJSONWriter.h](../../src/utils/SkJSONWriter.h)、[src/utils/SkJSONWriter.cpp](../../src/utils/SkJSONWriter.cpp)

## 概述

`SkJSONWriter` 是一个轻量级的 JSON 生成类，按照 RFC-4627 规范生成结构正确的 JSON 数据。它采用流式输出，直接将 JSON 写入 `SkWStream`，支持紧凑模式（`kFast`）和美化模式（`kPretty`）。

核心特性：
- 严格的状态机确保 JSON 结构正确性（仅在 debug 构建中检查）
- 支持对象（Object）和数组（Array）的嵌套
- 支持多种值类型：字符串、布尔、整数、浮点数、指针、十六进制
- 32KB 缓冲区优化写入性能
- JSON 字符串自动转义（引号、反斜杠、控制字符、无效 UTF-8）
- 可控制每个对象/数组的多行/单行输出

## 架构位置

`SkJSONWriter` 主要用于 Skia 的调试和跟踪系统（如 Chrome tracing、性能分析输出）。

## 主要类与结构体

### `SkJSONWriter`

| 成员 | 类型 | 说明 |
|------|------|------|
| `fBlock` | `char*` | 32KB 写入缓冲区 |
| `fWrite` | `char*` | 缓冲区当前写入位置 |
| `fStream` | `SkWStream*` | 目标输出流 |
| `fMode` | `Mode` | kFast（紧凑）或 kPretty（美化） |
| `fState` | `State` | 当前状态机状态 |
| `fScopeStack` | `STArray<16, Scope>` | 嵌套作用域栈 |
| `fNewlineStack` | `STArray<16, bool>` | 每层的多行标志栈 |

### `Mode` 枚举

- **`kFast`**：最小化输出，无空白和换行，适合机器解析
- **`kPretty`**：人类可读格式，3 空格缩进，每值一行

### `State` 枚举

状态机包含 7 个状态：`kStart`、`kEnd`、`kObjectBegin`、`kObjectName`、`kObjectValue`、`kArrayBegin`、`kArrayValue`，确保 JSON 结构正确。

## 公共 API 函数

### 结构控制

- **`beginObject(name, multiline)`** / **`endObject()`**：对象的开始/结束
- **`beginArray(name, multiline)`** / **`endArray()`**：数组的开始/结束
- **`appendName(name)`**：追加对象成员的键

### 值追加（单参数版本用于数组或 appendName 之后）

- `appendString` / `appendCString` / `appendNString`：字符串值
- `appendBool`：布尔值
- `appendS32` / `appendS64` / `appendU32` / `appendU64`：整数值
- `appendFloat` / `appendDouble`：浮点值
- `appendFloatDigits` / `appendDoubleDigits`：控制有效位数的浮点值
- `appendHexU32` / `appendHexU64`：十六进制字符串值
- `appendPointer`：指针地址字符串值

所有值类型都有对应的命名版本（两参数：name + value），用于对象内部。

### 流控制

- **`flush()`**：刷出缓冲区到底层流

## 内部实现细节

### 缓冲区管理

使用 32KB 栈缓冲区（`kBlockSize = 32 * 1024`）。当写入超出缓冲区时先 flush 再继续。超过 32KB 的单次写入直接传递给底层流（unbuffered）。

### 字符串转义

`appendString` 逐字符处理 UTF-8 输入：
- 转义特殊字符：`"`、`\`、`\b`、`\f`、`\n`、`\r`、`\t`
- 控制字符（< 0x20）：输出 `\uXXXX` 形式
- 无效 UTF-8：逐字节输出 `\uXXXX`
- 其他 Unicode：直接输出 UTF-8 字节

### Pretty 模式缩进

每层嵌套使用 3 个空格缩进。`multiline` 参数可以按对象/数组控制是否换行，不换行时使用空格分隔。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkWStream` | 输出流 |
| `SkString` | 字符串操作（十六进制格式化） |
| `SkUTF` | UTF-8 解码 |
| `STArray` | 小数组优化容器（scope 和 newline 栈） |

## 设计模式与设计决策

1. **状态机**：防止无效 JSON 结构（如对象外部直接追加值），所有检查通过 assert 实现，不影响 release 性能。
2. **栈式作用域**：`fScopeStack` 和 `fNewlineStack` 跟踪嵌套层级，支持正确的逗号插入和缩进。
3. **32KB 缓冲区**：实验显示 32KB 是性能/内存的最优平衡点，更大的缓冲区收益递减。
4. **不可复制**：继承 `SkNoncopyable`，防止意外复制导致双重写入。

## 性能考量

- 32KB 缓冲区减少了 90%+ 的流写入调用。
- 超大写入直接传递给流，避免多次缓冲区 flush。
- 紧凑模式零额外空白字符，最小化输出大小。
- `STArray<16>` 避免小型嵌套的堆分配。

## 相关文件

- `src/utils/SkJSONWriter.cpp` — `appendS64`、`appendU64`、`appendHexU64`、`appendf` 的实现
- `include/core/SkStream.h` — 输出流
