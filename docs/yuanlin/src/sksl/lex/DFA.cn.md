# DFA

> 源文件: src/sksl/lex/DFA.h

## 概述

`DFA` 结构体表示确定性有限自动机(Deterministic Finite Automaton)的最终形式,以紧凑的转移表格式存储词法分析器的状态转换信息。这是从 NFA 转换而来的高效表示,用于生成 SkSL 词法分析器的 C++ 代码。

该结构将 DFA 的所有状态和转移关系编码为三个向量,提供 O(1) 的状态转移查找,是实际词法分析器执行的核心数据结构。

## 架构位置

`DFA` 是词法分析器生成流程的最终产物:

```
词法分析器生成:
  正则表达式 → NFA → DFAState → DFA (本文件) → 生成代码
```

生成的 C++ 词法分析器直接使用 `DFA` 的数据结构进行高效的 token 匹配。

## 主要类与结构体

### DFA

```cpp
struct DFA {
    std::vector<int> fCharMappings;            // 字符到转移行的映射
    std::vector<std::vector<int>> fTransitions; // 转移表
    std::vector<int> fAccepts;                 // 接受状态的 token ID
};
```

**构造函数:**

```cpp
DFA(std::vector<int> charMappings,
    std::vector<std::vector<int>> transitions,
    std::vector<int> accepts)
```

**成员说明:**

1. **fCharMappings:** 字符映射表
   - 索引: 字符的 ASCII 值
   - 值: 对应的转移表行索引
   - 目的: 压缩转移表(多个字符可能有相同转移)

2. **fTransitions:** 二维转移表
   - 行: 字符映射索引
   - 列: 当前状态
   - 值: 下一个状态 ID
   - 格式: `transitions[charMapping][currentState]`

3. **fAccepts:** 接受状态表
   - 索引: 状态 ID
   - 值: 匹配的 token ID(-1 表示非接受状态)

## 公共 API 函数

### 构造函数

```cpp
DFA(std::vector<int> charMappings, std::vector<std::vector<int>> transitions,
    std::vector<int> accepts)
```

**功能:** 创建 DFA 对象

**参数:**
- `charMappings`: 字符到转移行的映射向量
- `transitions`: 完整的转移表
- `accepts`: 接受状态的 token 映射

**使用示例(在 NFAtoDFA 中):**

```cpp
return DFA(fCharMappings, fTransitions, fAccepts);
```

## 内部实现细节

### 状态转移逻辑

给定当前状态 `s` 和输入字符 `c`,下一状态计算为:

```cpp
int charMapping = fCharMappings[c];
int nextState = fTransitions[charMapping][s];
```

这是两步查找:
1. 将字符映射到转移行
2. 在该行中查找当前状态对应的下一状态

### 字符映射的优化

多个字符可能映射到同一行:
- 对于正则表达式 `[a-z]`,所有小写字母可能有相同的转移
- `fCharMappings['a'] == fCharMappings['b'] == ... == fCharMappings['z']`
- 大幅减少转移表的行数

**示例:**

假设只有两种转移模式:
- 数字 `[0-9]` → 映射到行 0
- 字母 `[a-z]` → 映射到行 1
- 其他字符 → 映射到行 2

则 `fTransitions` 只需 3 行,而不是 256 行(完整 ASCII)。

### 接受状态的识别

检查状态 `s` 是否为接受状态:

```cpp
if (s < fAccepts.size() && fAccepts[s] != -1) {
    int tokenId = fAccepts[s];
    // 匹配成功,返回 token
}
```

`-1` 表示该状态不接受任何 token。

### 转移表的维度

- **行数:** 等于唯一转移模式的数量(通常远小于 256)
- **列数:** 等于 DFA 状态总数
- **大小:** 通常在几 KB 到几十 KB

## 依赖关系

**标准库:**
- `<vector>`: 动态数组
- `<string>`: 字符串(间接)

**被依赖文件:**
- `src/sksl/lex/NFAtoDFA.h`: 生成 DFA
- `src/sksl/lex/Main.cpp`: 使用 DFA 生成代码
- `src/sksl/lex/TransitionTable.h`: 序列化 DFA 到 C++ 代码

**生成的代码:**
- `src/sksl/SkSLLexer.cpp`: 包含硬编码的 DFA 表

## 设计模式与设计决策

### 表驱动的词法分析

使用转移表而非代码分支:
- **优势:** 统一的匹配逻辑,高度可预测
- **劣势:** 初始化数据较大

### 字符映射的压缩

通过 `fCharMappings` 间接寻址:
- **空间节省:** 行数从 256 降至通常 10-20
- **时间成本:** 增加一次数组查找
- **权衡:** 空间节省远大于时间损失

### 值语义

`DFA` 使用值语义,所有数据通过拷贝或移动传递:
- 简化生命周期管理
- 适合作为函数返回值
- 移动语义使大型表的传递高效

### 静态数据结构

DFA 构建后不再修改:
- 所有向量使用 `const` 引用传递
- 适合编译到常量数据段
- 多线程安全(只读)

## 性能考量

### 状态转移速度

两次数组查找:
- `charMapping = fCharMappings[c]`: O(1)
- `nextState = fTransitions[charMapping][s]`: O(1)
- 总计: O(1)常数时间

### 缓存友好性

转移表是连续内存:
- 良好的空间局部性
- 预取优化生效
- 分支预测友好

### 内存占用

假设:
- 20 种转移模式
- 50 个 DFA 状态
- 转移表: `20 * 50 * 4字节 = 4KB`
- 字符映射: `256 * 4字节 = 1KB`
- 接受表: `50 * 4字节 = 200字节`
- **总计:** 约 5KB

对于嵌入式系统仍然可接受。

### 生成代码优化

编译器可以将表优化为只读数据:
```cpp
static const State kTransitions[20][50] = { /* ... */ };
```

放置在 `.rodata` 段,共享于所有实例。

## 相关文件

**构建流程:**
- `src/sksl/lex/NFA.h`: NFA 构建
- `src/sksl/lex/NFAtoDFA.h`: NFA 到 DFA 转换
- `src/sksl/lex/DFAState.h`: 中间 DFA 状态

**代码生成:**
- `src/sksl/lex/Main.cpp`: 词法分析器生成器主程序
- `src/sksl/lex/TransitionTable.h`: 将 DFA 写入 C++ 代码

**生成的词法分析器:**
- `src/sksl/SkSLLexer.h`: 词法分析器接口
- `src/sksl/SkSLLexer.cpp`: 包含 DFA 表的实现

**理论背景:**
- DFA 最小化(Hopcroft 算法): 可进一步减少状态数
- 表压缩技术(行位移、行合并): 进一步减少内存占用
