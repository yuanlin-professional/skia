# SkSL TransitionTable（状态转移表生成器）

> 源文件：[src/sksl/lex/TransitionTable.h](../../../src/sksl/lex/TransitionTable.h)、[src/sksl/lex/TransitionTable.cpp](../../../src/sksl/lex/TransitionTable.cpp)

## 概述

`TransitionTable` 模块负责将 DFA（确定性有限自动机）的状态转移表编码为紧凑的 C++ 源代码。它是 SkSL 词法分析器生成工具 `sksllex` 的最终阶段，输出的代码直接嵌入到自动生成的 `SkSLLexer.cpp` 中。该模块实现了一种混合编码方案：使用 2-bit 紧凑表示高稀疏度的状态行，使用全表表示低稀疏度的状态行。

## 架构位置

`TransitionTable` 是词法分析器生成管道的最终输出阶段：

```
正则表达式 -> RegexParser -> NFA -> DFA
                                      |
                                      v
                          WriteTransitionTable()（生成 C++ 代码）
                                      |
                                      v
                              SkSLLexer.cpp
```

## 主要类与结构体

### 内部结构

| 结构 | 说明 |
|------|------|
| `IndexEntry` | 状态到表条目的索引（类型 + 位置） |
| `CompactEntry` | 紧凑编码的状态行（最多 3 个唯一非零值） |
| `FullEntry` | 完整编码的状态行（所有转移值） |

### 编码参数（编译时常量）

| 常量 | 值 | 说明 |
|------|----|------|
| `kNumBits` | 2 | 每个紧凑条目使用的位数 |
| `kNumValues` | 3 | 紧凑条目中可区分的非零值数量 |
| `kDataPerByte` | 4 | 每字节可存储的紧凑条目数 |

## 公共 API 函数

### `void WriteTransitionTable(std::ofstream& out, const DFA& dfa, size_t states)`

将 DFA 的状态转移表写入输出文件流。生成的代码包括：

1. 类型定义（`IndexEntry`、`FullEntry`、`CompactEntry`）
2. `kFull[]` 数组（完整状态行）
3. `kCompact[]` 数组（紧凑编码的状态行）
4. `kIndices[]` 数组（索引表）
5. `get_transition()` 函数（查找转移目标状态）

## 内部实现细节

### 紧凑编码方案

对于只包含少量唯一非零转移目标的状态行（<= 3 个唯一值），使用紧凑编码：

1. **值表**：将 3 个唯一值打包到一个 `uint32_t` 中，每个值使用 `bitsPerValue` 位
2. **数据表**：每个转移用 2 位编码（0=零、1/2/3=值表索引），4 个转移压缩进 1 字节
3. **查找过程**：
   - 从 `data` 中提取 2-bit 索引
   - 乘以 `bitsPerValue` 得到位偏移
   - 从 `values` 中提取对应的状态值

### 全表编码

对于包含大量唯一非零值的状态行，直接存储完整的转移数组（每个转移占用一个 `State`）。

### 索引编码

使用 `int16_t` 索引区分两种表：
- 非负值：指向 `kCompact[]` 数组
- 负值（取反后）：指向 `kFull[]` 数组

### 去重优化

`add_compact_entry` 和 `add_full_entry` 都会检查是否已存在相同的条目，避免重复存储。

### 生成的 get_transition 函数

```cpp
static State get_transition(uint8_t transition, State state) {
    IndexEntry index = kIndices[state];
    if (index < 0) { return kFull[~index].data[transition]; }
    const CompactEntry& entry = kCompact[index];
    int v = entry.data[transition >> 2];     // 提取包含目标的字节
    v >>= 2 * (transition & 3);              // 移位到目标位置
    v &= 3;                                   // 提取 2-bit 值
    v *= bitsPerValue;                        // 计算值表偏移
    return (entry.values >> v) & maxValue;    // 提取状态值
}
```

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `DFA.h` | DFA 状态和转移数据 |
| `<fstream>` | 文件输出 |
| `<cmath>` | `log2`、`ceil` 计算 |

## 设计模式与设计决策

1. **混合编码**：根据状态行的稀疏度自动选择紧凑或全表编码，在空间和速度之间平衡。
2. **2-bit 编码**：经过实验，2-bit 是 SkSL 词法数据的最佳紧凑度。1-bit 不够用，4-bit 节省不够多。
3. **条目去重**：相同的状态行只存储一次，通过索引共享。
4. **代码生成**：直接生成 C++ 代码，而非二进制数据，使生成的词法分析器自包含。
5. **值表打包**：将最多 3 个唯一值打包到 32 位整数中，使用位移和掩码操作解码。

## 性能考量

- 紧凑编码显著减少了 `SkSLLexer.cpp` 中转移表的大小
- `get_transition` 函数使用位操作实现 O(1) 查找
- 全表条目为零成本查找（直接索引），紧凑条目需要几次额外的位操作
- 去重减少了存储的唯一条目数量
- 编码选择的 2-bit 设计使得 SkSL 中几乎所有稀疏状态行都能使用紧凑格式

## 相关文件

- `src/sksl/lex/DFA.h` —— DFA 数据结构
- `src/sksl/lex/sksllex.cpp` —— 词法分析器生成工具主程序
- `src/sksl/SkSLLexer.cpp` —— 生成的词法分析器（包含转移表）
- `src/sksl/lex/NFA.h` —— NFA 数据结构（DFA 的前置阶段）
