# DFAState

> 源文件: src/sksl/lex/DFAState.h

## 概述

`DFAState` 表示确定性有限自动机(DFA, Deterministic Finite Automaton)的状态节点,是 SkSL 词法分析器从 NFA 转换到 DFA 过程中的关键数据结构。每个 DFA 状态对应一组 NFA 状态的组合,通过子集构造算法(Subset Construction)将非确定性的 NFA 转换为确定性的 DFA。

该结构用于 NFA 到 DFA 转换的中间阶段,最终转换结果会被序列化为转移表,生成高效的词法分析器代码。

## 架构位置

`DFAState` 处于词法分析器生成流程的转换阶段:

```
词法分析器生成流程:
  正则表达式
      ↓
  NFA (非确定性自动机)
      ↓
  ┌──────────────────┐
  │ NFA → DFA 转换   │
  │  ↓               │
  │ DFAState (本文件) │ ← 中间表示
  └──────────────────┘
      ↓
  DFA (转移表形式)
      ↓
  生成词法分析器代码
```

DFA 状态是临时的构建工具,最终会被压缩为数组形式的转移表。

## 主要类与结构体

### DFAState

表示 DFA 中的一个状态。

**成员变量:**

```cpp
int fId;                // 状态的唯一标识符
Label fLabel;           // 状态的标签(NFA 状态集合)
bool fIsScanned = false; // 是否已被扫描(转换过程中使用)
```

**构造函数:**

1. **默认构造:**
```cpp
DFAState() : fId(INVALID), fLabel({})
```
创建无效状态。

2. **标准构造:**
```cpp
DFAState(int id, Label label)
    : fId(id), fLabel(std::move(label))
```
创建带标识和标签的状态。

**特性:**
- 禁止拷贝构造:`DFAState(const DFAState& other) = delete`
- 状态通过唯一指针管理,防止意外复制

### DFAState::Label

嵌套结构体,表示 DFA 状态对应的 NFA 状态集合。

**成员变量:**

```cpp
std::vector<int> fStates;  // NFA 状态 ID 的有序列表
```

**构造函数:**

```cpp
Label(std::vector<int> states) : fStates(std::move(states))
```

**比较运算符:**

```cpp
bool operator==(const Label& other) const {
    return fStates == other.fStates;
}

bool operator!=(const Label& other) const {
    return !(*this == other);
}
```

标签相等当且仅当 NFA 状态集合完全相同(顺序和元素都相同)。

**调试方法:**

```cpp
std::string description() const  // SK_DEBUG 下可用
```

输出格式: `<1, 3, 5>` 表示包含 NFA 状态 1、3、5。

## 公共 API 函数

### Label::operator==

```cpp
bool operator==(const Label& other) const
```

**功能:** 比较两个标签是否相等

**实现:** 直接比较 `vector`,要求元素顺序和值都相同

**用途:** 在转换过程中检测是否已存在相同的 DFA 状态

### Label::description

```cpp
std::string description() const
```

**功能:** 生成标签的文本表示(仅调试版本)

**示例输出:**
- 空集: `<>`
- 单状态: `<7>`
- 多状态: `<2, 5, 8, 11>`

## 内部实现细节

### 标签的唯一性

在 NFA 到 DFA 转换中,标签用作哈希表的键:
```cpp
std::unordered_map<DFAState::Label, std::unique_ptr<DFAState>> fStates;
```

两个 DFA 状态具有相同标签意味着它们代表相同的 NFA 状态组合,应该合并为同一个 DFA 状态。

### 状态 ID 的分配

状态 ID 在创建时按顺序分配:
```cpp
int id = fStates.size();
fStates[label] = std::unique_ptr<DFAState>(new DFAState(id, label));
```

ID 从 0 开始递增,对应最终转移表的列索引。

### fIsScanned 标志

标记状态是否已被处理:
- 防止重复扫描
- 实现深度优先或广度优先遍历
- 在 `NFAtoDFA::scanState` 中使用

```cpp
void scanState(DFAState* state) {
    state->fIsScanned = true;
    // ... 处理转移
    if (!nextState->fIsScanned) {
        this->scanState(nextState);
    }
}
```

### 标签的排序要求

`fStates` 向量必须是排序的:
```cpp
std::sort(next.begin(), next.end());
DFAState* nextState = this->getState(DFAState::Label(next));
```

排序确保相同的 NFA 状态集合生成相同的标签,无论添加顺序如何。

### 禁止拷贝的原因

DFA 状态通过指针引用:
- 避免大量状态的深拷贝
- 确保状态 ID 的唯一性
- 简化状态间引用的管理

## 依赖关系

**核心依赖:**
- `src/sksl/lex/LexUtil.h`: 常量定义(`INVALID`)

**标准库:**
- `<vector>`: 动态数组
- `<string>`: 字符串(调试)

**被依赖文件:**
- `src/sksl/lex/NFAtoDFA.h`: 执行 NFA 到 DFA 转换
- `src/sksl/lex/DFA.h`: 最终的 DFA 表示

**哈希支持:**
文件提供了自定义哈希函数:
```cpp
namespace std {
    template<> struct hash<DFAState::Label> {
        size_t operator()(const DFAState::Label& s) const {
            size_t result = 0;
            for (int i : s.fStates) {
                result = result * 101 + i;
            }
            return result;
        }
    };
}
```

使用多项式滚动哈希,素数 101 作为基数。

## 设计模式与设计决策

### 子集构造算法

DFA 状态的标签实现了子集构造的核心思想:
- **NFA:** 在输入字符 c 下可以同时处于多个状态 {s1, s2, s3}
- **DFA:** 创建单一状态,标签为 {s1, s2, s3}

这将非确定性转换为确定性:给定输入,DFA 只有一个明确的后继状态。

### 状态去重

使用 `unordered_map` 存储状态,键为标签:
- 自动去重:相同标签的状态只创建一次
- O(1) 查找:快速检测是否已存在
- 内存高效:避免冗余状态

### 惰性状态创建

状态在需要时才创建:
```cpp
DFAState* getState(DFAState::Label label) {
    auto found = fStates.find(label);
    if (found == fStates.end()) {
        // 创建新状态
    }
    return found->second.get();
}
```

只生成可达的状态,减少最终 DFA 的大小。

### 标签的值语义

`Label` 使用值语义(允许拷贝),而 `DFAState` 使用指针语义(禁止拷贝):
- 标签是轻量的(只含一个 `vector`)
- 作为哈希表的键需要拷贝
- 状态本身较重,通过指针引用

### 分离关注点

`DFAState` 只关注状态本身,不包含转移逻辑:
- 转移关系存储在 `NFAtoDFA` 的 `fTransitions` 中
- 状态只是节点,边在外部管理
- 清晰的责任划分

## 性能考量

### 哈希函数质量

自定义哈希使用多项式滚动哈希:
```cpp
result = result * 101 + i;
```

**特性:**
- 良好的分布性(素数基数)
- 快速计算(只有乘法和加法)
- 顺序敏感(不同顺序产生不同哈希)

**潜在问题:**
- 对于大型状态集,可能溢出
- 但对于词法分析器,状态数通常较小

### 标签比较成本

标签比较需要 O(n) 时间,n 为状态集大小:
```cpp
return fStates == other.fStates;
```

但由于:
- 哈希表先用哈希过滤大部分不等情况
- 只在哈希冲突时才完整比较
- 实际开销可接受

### 排序的必要性

标签向量必须排序:
- 确保相同集合的唯一表示
- 比较和哈希都依赖顺序
- 排序成本 O(n log n),但只在创建时执行一次

### 状态数量

最坏情况下,DFA 状态数是 NFA 状态数的指数级:
- DFA 状态数 ≤ 2^(NFA 状态数)
- 实际中通常远小于这个上界
- 词法规则的特性限制了状态爆炸

### 智能指针管理

使用 `unique_ptr` 管理状态:
- 自动内存管理,无需手动 `delete`
- 移动语义高效(只转移指针)
- 防止内存泄漏

## 相关文件

**NFA 相关:**
- `src/sksl/lex/NFAState.h`: NFA 状态定义
- `src/sksl/lex/NFA.h`: NFA 容器

**DFA 转换:**
- `src/sksl/lex/NFAtoDFA.h`: 执行子集构造算法
- `src/sksl/lex/DFA.h`: 最终的 DFA 表示(转移表)

**词法分析器生成:**
- `src/sksl/lex/Main.cpp`: 调用转换过程

**工具:**
- `src/sksl/lex/LexUtil.h`: 宏和常量

**算法背景:**
- Subset Construction(子集构造法): NFA 到 DFA 的标准转换算法
- Powerset Construction(幂集构造法): 子集构造的另一种称呼
