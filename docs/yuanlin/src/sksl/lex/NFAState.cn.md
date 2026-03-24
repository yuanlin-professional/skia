# NFAState

> 源文件: src/sksl/lex/NFAState.h

## 概述

`NFAState` 定义了非确定性有限自动机(NFA, Nondeterministic Finite Automaton)的状态节点,是 SkSL 词法分析器生成工具的核心数据结构之一。每个 NFA 状态表示正则表达式匹配过程中的一个节点,可以根据输入字符转移到多个后继状态,支持正则表达式的各种匹配模式。

该结构体用于从正则表达式构建 NFA,随后转换为 DFA(确定性有限自动机)以生成高效的词法分析器代码。它支持字符匹配、通配符、字符类、接受状态等正则表达式的基本构造。

## 架构位置

`NFAState` 位于 SkSL 词法分析器生成工具链的核心:

```
SkSL 词法分析器构建流程:
  .lex 文件 (词法规则)
      ↓
  RegexParser (正则表达式解析)
      ↓
  ┌───────────┐
  │ NFA 构建  │ ← NFAState (本文件)
  └───────────┘
      ↓
  NFAtoDFA (NFA 转 DFA)
      ↓
  DFA (确定性自动机)
      ↓
  代码生成 (.h 和 .cpp)
```

NFA 是正则表达式的直接表示,随后被转换为更高效的 DFA 用于实际的词法分析。

## 主要类与结构体

### NFAState

表示 NFA 中的单个状态节点。

**枚举类型 Kind:**

```cpp
enum Kind {
    kAccept_Kind,     // 接受状态:匹配成功,返回 token
    kChar_Kind,       // 匹配单个字符
    kDot_Kind,        // 匹配任意字符(除换行符)
    kRemapped_Kind,   // 重映射状态:转移到多个其他状态
    kTable_Kind       // 字符表:通过查表判断是否接受字符
};
```

**成员变量:**

```cpp
Kind fKind;                // 状态类型
char fChar = 0;            // 对于 kChar_Kind,要匹配的字符
bool fInverse = false;     // 对于 kTable_Kind,是否反转匹配结果
std::vector<int> fData;    // 多用途数据:token ID、状态列表或字符表
std::vector<int> fNext;    // 成功匹配后的后继状态列表
```

**构造函数:**

1. **通用构造(Dot/Remapped):**
```cpp
NFAState(Kind kind, std::vector<int> next)
```

2. **字符匹配:**
```cpp
NFAState(char c, std::vector<int> next)
```

3. **重映射状态:**
```cpp
NFAState(std::vector<int> states)
```

4. **字符表匹配:**
```cpp
NFAState(bool inverse, std::vector<bool> accepts, std::vector<int> next)
```

5. **接受状态:**
```cpp
NFAState(int token)
```

## 公共 API 函数

### accept

```cpp
bool accept(char c) const
```

**功能:** 判断状态是否接受给定字符

**参数:**
- `c`: 输入字符

**返回值:**
- `true`: 状态接受该字符,可以转移
- `false`: 状态不接受该字符

**实现逻辑:**

```cpp
switch (fKind) {
    case kAccept_Kind:
        return false;  // 接受状态不再匹配字符

    case kChar_Kind:
        return c == fChar;  // 精确字符匹配

    case kDot_Kind:
        return c != '\n';  // 匹配除换行外的任意字符

    case kTable_Kind:
        bool value = (c < fData.size()) ? fData[c] : false;
        return value != fInverse;  // 支持反转语义

    default:
        SkUNREACHABLE;
}
```

**字符表逻辑:**
- `fData[c]` 为 `true` 且 `fInverse` 为 `false`:接受
- `fData[c]` 为 `false` 且 `fInverse` 为 `true`:接受(反转模式,如 `[^abc]`)

### description (调试版本)

```cpp
std::string description() const  // SK_DEBUG 下可用
```

**功能:** 生成状态的文本描述,用于调试

**输出格式示例:**

- **接受状态:** `Accept(5)` (token ID 为 5)
- **字符状态:** `Char('a', 3, 7)` (匹配 'a',后继状态 3 和 7)
- **点状态:** `Dot(2, 5)` (匹配任意字符,后继状态 2 和 5)
- **重映射状态:** `Remapped(1, 4, 9)` (转移到状态 1, 4, 9)
- **字符表状态:** `Table(false, [true, false, true], 6)` (查表匹配,后继状态 6)

## 内部实现细节

### 状态类型的语义

**kAccept_Kind:**
- 终止状态,表示成功匹配一个 token
- `fData[0]` 存储 token ID
- 不再转移到其他状态

**kChar_Kind:**
- 匹配单个特定字符
- 用于字面字符,如 `'a'` 或 `'+'`
- `fChar` 存储要匹配的字符

**kDot_Kind:**
- 正则表达式的 `.` 操作符
- 匹配除换行符外的任意字符
- 简化了 "任意字符" 的表示

**kRemapped_Kind:**
- epsilon 转换的集合表示
- 自动转移到 `fData` 中列出的所有状态
- 用于实现 NFA 的非确定性

**kTable_Kind:**
- 字符类的高效表示,如 `[a-z0-9]`
- `fData` 是一个布尔数组,索引为字符 ASCII 值
- `fInverse` 支持否定字符类,如 `[^abc]`

### fNext 的语义

对于非接受状态,`fNext` 存储成功匹配后可以转移到的状态列表:
- 可以是空列表(死状态)
- 可以包含多个状态(非确定性)
- 索引指向 NFA 的状态数组

### fData 的多态用途

`fData` 根据状态类型有不同含义:
- **kAccept_Kind:** `fData[0]` = token ID
- **kRemapped_Kind:** `fData` = 目标状态列表
- **kTable_Kind:** `fData` = 字符接受表(布尔值列表)

这种设计减少了内存占用,避免为每种类型定义单独的字段。

### 字符范围限制

`accept` 方法中对字符表的访问:
```cpp
if ((size_t) c < fData.size()) {
    value = fData[c];
} else {
    value = false;
}
```

处理扩展 ASCII 或无效字符,超出表范围的字符默认不匹配。

## 依赖关系

**核心依赖:**
- `src/sksl/lex/LexUtil.h`: 宏定义(`SkUNREACHABLE`, `SkASSERT`)

**标准库:**
- `<string>`: 字符串操作(调试)
- `<vector>`: 动态数组

**被依赖文件:**
- `src/sksl/lex/NFA.h`: NFA 容器,包含状态数组
- `src/sksl/lex/NFAtoDFA.h`: NFA 到 DFA 转换器
- `src/sksl/lex/RegexNode.cpp`: 正则表达式节点构建 NFA

## 设计模式与设计决策

### 联合体式多态

使用 `fKind` 字段和共享数据成员实现多态:
- 替代虚函数表,减少内存开销
- 所有状态大小相同,便于数组存储
- 通过 `switch` 分发实现类型特定行为

**优势:**
- 紧凑的内存布局
- 缓存友好(连续存储)
- 避免虚函数调用开销

**劣势:**
- 需要手动类型检查
- 某些字段对某些类型无意义

### 非确定性支持

`fNext` 可以包含多个状态,直接表示 NFA 的非确定性:
- 在某个输入下可以同时处于多个状态
- 转换为 DFA 时,这些状态组合形成 DFA 的单一状态

### 字符表优化

对于字符类(如 `[a-z]`),使用查表而非多个 `kChar_Kind` 状态:
- 减少状态数量
- 加速字符匹配(O(1) 查表 vs 多次比较)
- 支持反转语义,无需构建补集

### 点(Dot)的特殊化

将 `.` 作为独立类型而非展开为 255 个字符:
- 简化 NFA 构建
- 减少状态数
- 转换为 DFA 时再处理具体字符集

### Remapped 状态的作用

表示 epsilon 转换或 NFA 子图的入口:
- 简化复杂正则表达式的构建
- 在转换为 DFA 时被 "扁平化"
- 不对应任何字符匹配

## 性能考量

### 紧凑的数据结构

单个 `NFAState` 占用内存:
- `fKind`: 4 字节(enum)
- `fChar`: 1 字节
- `fInverse`: 1 字节
- `fData`: 24 字节(vector)
- `fNext`: 24 字节(vector)
- **总计:** 约 54 字节(加上对齐)

对于包含数百个状态的 NFA,内存占用是可接受的。

### 字符匹配效率

`accept` 方法的时间复杂度:
- **kChar_Kind:** O(1) 字符比较
- **kDot_Kind:** O(1) 字符比较
- **kTable_Kind:** O(1) 数组查找
- **kAccept_Kind:** O(1) 常量返回

所有情况都是常数时间。

### NFA 到 DFA 的必要性

NFA 虽然构建简单,但匹配效率低:
- 每步需要跟踪多个活动状态
- DFA 将多状态组合转换为单一状态
- 最终生成的词法分析器只使用 DFA

### Vector 的内存分配

`fData` 和 `fNext` 使用 `vector`,可能引起动态分配:
- 对于小型状态,可以考虑使用小对象优化(SOO)
- 当前设计优先考虑简洁性而非极致性能

## 相关文件

**NFA 构建:**
- `src/sksl/lex/NFA.h`: NFA 容器类
- `src/sksl/lex/RegexNode.cpp`: 从正则表达式构建 NFA

**NFA 转 DFA:**
- `src/sksl/lex/NFAtoDFA.h`: 转换算法实现
- `src/sksl/lex/DFAState.h`: DFA 状态定义

**词法分析器生成:**
- `src/sksl/lex/Main.cpp`: 词法分析器生成器主程序

**工具:**
- `src/sksl/lex/LexUtil.h`: 调试和断言宏

**生成的代码:**
- `src/sksl/SkSLLexer.h`: 生成的词法分析器头文件
- `src/sksl/SkSLLexer.cpp`: 生成的词法分析器实现

**理论背景:**
- Thompson's Construction: 将正则表达式转换为 NFA 的经典算法
- Subset Construction: 将 NFA 转换为 DFA 的标准方法
