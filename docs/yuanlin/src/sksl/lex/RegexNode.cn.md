# SkSL RegexNode（正则表达式解析树节点）

> 源文件：[src/sksl/lex/RegexNode.h](../../../src/sksl/lex/RegexNode.h)、[src/sksl/lex/RegexNode.cpp](../../../src/sksl/lex/RegexNode.cpp)

## 概述

`RegexNode` 表示正则表达式解析树中的一个节点。每个节点对应正则表达式的一个语法结构（字符、字符集、连接、交替、量词等），并能够递归地将自身转换为 NFA（非确定性有限自动机）的状态。该结构是 SkSL 词法分析器生成工具链中连接正则解析和 NFA 构建的关键数据类型。

## 架构位置

`RegexNode` 位于 RegexParser 和 NFA 之间：

```
RegexParser::parse() -> RegexNode 树
                            |
                            v
               RegexNode::createStates() -> NFA 状态
                                              |
                                              v
                                        NFA -> DFA 转换
```

## 主要类与结构体

### `struct RegexNode`

正则表达式解析树节点：

| 成员 | 类型 | 说明 |
|------|------|------|
| `fKind` | `Kind` | 节点类型 |
| `fPayload` | `union Payload` | 附加数据（字符值或布尔标志） |
| `fChildren` | `std::vector<RegexNode>` | 子节点列表 |

### `enum Kind`

节点类型枚举：

| Kind | 说明 | 子节点 | Payload |
|------|------|--------|---------|
| `kChar_Kind` | 单个字符 | 无 | `fChar`：匹配的字符 |
| `kCharset_Kind` | 字符集 `[...]` | 字符或范围列表 | `fBool`：是否取反 |
| `kConcat_Kind` | 连接（顺序匹配） | 2 个子节点（左、右） | - |
| `kDot_Kind` | 任意字符 `.` | 无 | - |
| `kOr_Kind` | 交替（`a\|b`） | 2 个子节点（左、右） | - |
| `kPlus_Kind` | 一次或多次（`+`） | 1 个子节点 | - |
| `kQuestion_Kind` | 零次或一次（`?`） | 1 个子节点 | - |
| `kRange_Kind` | 字符范围（`a-z`） | 2 个子节点（起始、结束字符） | - |
| `kStar_Kind` | 零次或多次（`*`） | 1 个子节点 | - |

### `union Payload`

| 字段 | 类型 | 说明 |
|------|------|------|
| `fChar` | `char` | 字符值（用于 `kChar_Kind`） |
| `fBool` | `bool` | 取反标志（用于 `kCharset_Kind`） |

## 公共 API 函数

### `std::vector<int> createStates(NFA* nfa, const std::vector<int>& accept) const`

递归地为此节点创建 NFA 状态。`accept` 参数指定成功匹配后转移到的状态集合。返回值是此节点的起始状态集合。

### `std::string description() const`（仅 DEBUG）

返回节点的人类可读描述，用于调试输出。

## 内部实现细节

### NFA 状态构建的递归逻辑

每种节点类型有不同的 NFA 构建策略：

| Kind | NFA 构建策略 |
|------|-------------|
| `kChar_Kind` | 创建一个字符匹配状态，转移到 accept 集合 |
| `kCharset_Kind` | 构建字符布尔数组，创建字符集匹配状态 |
| `kConcat_Kind` | 右子节点的起始状态作为左子节点的 accept |
| `kDot_Kind` | 创建一个通配符状态（匹配任意字符） |
| `kOr_Kind` | 合并两个子节点的起始状态集合 |
| `kPlus_Kind` | 创建循环：子节点的起始状态可同时转移到 accept 和自身 |
| `kQuestion_Kind` | 子节点的起始状态并上 accept 集合（可跳过） |
| `kStar_Kind` | 类似 `kPlus_Kind` 但额外包含 accept（可匹配零次） |

### kPlus 和 kStar 的循环实现

使用占位符状态实现循环引用：
1. 先创建一个占位符 NFA 状态
2. 将占位符 ID 加入 `next` 集合
3. 用 `next` 集合创建子节点的状态
4. 用子节点的起始状态回填占位符

### 字符集的布尔数组

字符集将所有包含的字符编码为 `vector<bool>`，索引为字符的 ASCII 值，值为是否包含。字符范围 `a-z` 在循环中设置所有中间字符。

## 依赖关系

| 依赖项 | 用途 |
|--------|------|
| `NFA.h` | NFA 数据结构和状态管理 |
| `NFAState.h` | NFA 状态类型 |
| `LexUtil.h` | `SkASSERT` 断言 |

## 设计模式与设计决策

1. **值类型设计**：`RegexNode` 使用 `struct` 并支持移动语义，子节点通过 `vector` 按值存储。
2. **联合体 Payload**：使用 `union` 存储不同类型的附加数据，最小化内存占用。
3. **递归构建**：`createStates` 采用递归方式构建 NFA，自然地将正则表达式的层次结构映射到状态机。
4. **Thompson 构造法变体**：NFA 构建遵循 Thompson 构造法的思想，每种正则运算符对应一种 NFA 构造模式。

## 性能考量

- 仅在编译时工具链中使用，运行时性能不敏感
- NFA 状态构建为 O(n)，其中 n 为正则表达式的长度
- `vector<bool>` 用于字符集的紧凑表示

## 相关文件

- `src/sksl/lex/RegexParser.h` / `.cpp` —— 正则表达式解析器
- `src/sksl/lex/NFA.h` —— NFA 数据结构
- `src/sksl/lex/NFAState.h` —— NFA 状态
- `src/sksl/lex/DFA.h` —— DFA 数据结构（NFA 转换后）
