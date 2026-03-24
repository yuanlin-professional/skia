# NFAtoDFA

> 源文件: src/sksl/lex/NFAtoDFA.h

## 概述

`NFAtoDFA` 类实现了将非确定性有限自动机(NFA)转换为确定性有限自动机(DFA)的子集构造算法(Subset Construction)。这是词法分析器生成的关键步骤,将易于从正则表达式构建但执行效率低的 NFA 转换为执行高效的 DFA。

该类还实现了转移表的压缩优化,通过合并具有相同转移模式的字符来减少最终 DFA 的空间占用。转换后的 DFA 被序列化为 C++ 代码,成为 SkSL 词法分析器的核心。

## 架构位置

`NFAtoDFA` 是词法分析器生成流程的核心转换环节:

```
词法分析器生成:
  正则表达式
      ↓
  NFA (易于构建,难以执行)
      ↓
  ┌──────────────┐
  │  NFAtoDFA    │ ← 本文件
  │ (子集构造算法)│
  └──────────────┘
      ↓
  DFA (难以构建,易于执行)
      ↓
  生成 C++ 代码
```

该算法将 NFA 的非确定性转换为 DFA 的确定性,同时保持识别相同语言的能力。

## 主要类与结构体

### NFAtoDFA

```cpp
class NFAtoDFA
```

执行 NFA 到 DFA 转换的主类。

**公共常量:**

```cpp
inline static constexpr char START_CHAR = 9;   // 制表符 '\t'
inline static constexpr char END_CHAR = 126;   // 波浪号 '~'
```

定义词法分析器考虑的字符范围,覆盖可打印 ASCII 字符。

**构造函数:**

```cpp
NFAtoDFA(NFA* nfa) : fNFA(*nfa) {}
```

**成员变量:**

```cpp
const NFA& fNFA;  // 输入的 NFA
std::unordered_map<DFAState::Label, std::unique_ptr<DFAState>> fStates;  // DFA 状态集
std::vector<std::vector<int>> fTransitions;  // 转移表(未压缩)
std::vector<int> fCharMappings;  // 字符到转移行的映射
std::vector<int> fAccepts;  // 接受状态的 token ID
```

## 公共 API 函数

### convert

```cpp
DFA convert()
```

**功能:** 将 NFA 转换为 DFA

**返回值:** 包含转移表、字符映射和接受状态的 `DFA` 对象

**算法流程:**

1. **创建拒绝状态:**
```cpp
getState(DFAState::Label({}));  // 状态 0,空集
```

2. **创建起始状态:**
```cpp
std::vector<int> startStates = fNFA.fStartStates;
std::sort(startStates.begin(), startStates.end());
DFAState* start = getState(DFAState::Label(startStates));  // 状态 1
```

3. **扫描状态并构建转移:**
```cpp
this->scanState(start);
```

4. **压缩转移表:**
```cpp
this->computeMappings();
```

5. **返回 DFA:**
```cpp
return DFA(fCharMappings, fTransitions, fAccepts);
```

## 内部实现细节

### getState

```cpp
DFAState* getState(DFAState::Label label)
```

**功能:** 获取或创建具有指定标签的 DFA 状态

**返回值:** 指向 DFA 状态的指针

**逻辑:**
- 如果标签已存在,返回已有状态
- 否则创建新状态,分配唯一 ID

这是子集构造的核心:每个 NFA 状态集合对应一个唯一的 DFA 状态。

### add

```cpp
void add(int nfaState, std::vector<int>* states)
```

**功能:** 将 NFA 状态添加到状态集合,处理重映射状态

**参数:**
- `nfaState`: 要添加的 NFA 状态 ID
- `states`: 目标状态集合

**逻辑:**
```cpp
NFAState state = fNFA.fStates[nfaState];
if (state.fKind == NFAState::kRemapped_Kind) {
    // 递归添加所有重映射的状态
    for (int next : state.fData) {
        this->add(next, states);
    }
} else {
    // 去重添加
    if (!contains(states, nfaState)) {
        states->push_back(nfaState);
    }
}
```

处理 epsilon 转换:重映射状态展开为多个实际状态。

### addTransition

```cpp
void addTransition(char c, int start, int next)
```

**功能:** 添加从状态 `start` 在字符 `c` 下转移到状态 `next`

**实现:**
```cpp
while (fTransitions.size() <= (size_t) c) {
    fTransitions.push_back(std::vector<int>());
}
std::vector<int>& row = fTransitions[c];
while (row.size() <= (size_t) start) {
    row.push_back(INVALID);
}
row[start] = next;
```

按需扩展转移表,使用字符作为行索引。

### scanState

```cpp
void scanState(DFAState* state)
```

**功能:** 扫描 DFA 状态,为每个字符计算后继状态

**算法:**

```cpp
state->fIsScanned = true;
for (char c = START_CHAR; c <= END_CHAR; ++c) {
    std::vector<int> next;      // 后继 NFA 状态集合
    int bestAccept = INT_MAX;   // 最高优先级的 token

    // 对当前 DFA 状态的每个 NFA 状态
    for (int idx : state->fLabel.fStates) {
        const NFAState& nfaState = fNFA.fStates[idx];
        if (nfaState.accept(c)) {  // 如果接受字符 c
            for (int nextState : nfaState.fNext) {
                // 记录接受状态的 token
                if (fNFA.fStates[nextState].fKind == NFAState::kAccept_Kind) {
                    bestAccept = std::min(bestAccept, fNFA.fStates[nextState].fData[0]);
                }
                this->add(nextState, &next);
            }
        }
    }

    // 创建或获取对应的 DFA 状态
    std::sort(next.begin(), next.end());
    DFAState* nextState = this->getState(DFAState::Label(next));
    this->addTransition(c, state->fId, nextState->fId);

    // 记录接受状态
    if (bestAccept != INT_MAX) {
        fAccepts[nextState->fId] = bestAccept;
    }

    // 递归扫描新状态
    if (!nextState->fIsScanned) {
        this->scanState(nextState);
    }
}
```

**关键点:**
- 遍历所有字符(START_CHAR 到 END_CHAR)
- 收集所有可能的 NFA 后继状态
- 对应的 NFA 状态集合成为新的 DFA 状态
- 优先级处理:选择最小 token ID(先定义的规则优先)

### computeMappings

```cpp
void computeMappings()
```

**功能:** 压缩转移表,合并具有相同转移的字符

**算法:**

```cpp
std::vector<std::vector<int>*> uniques;  // 唯一的转移行
for (size_t i = 0; i < fTransitions.size(); ++i) {
    int found = -1;
    // 查找是否已有相同的转移行
    for (size_t j = 0; j < uniques.size(); ++j) {
        if (*uniques[j] == fTransitions[i]) {
            found = j;
            break;
        }
    }
    if (found == -1) {
        found = (int) uniques.size();
        uniques.push_back(&fTransitions[i]);
    }
    fCharMappings.push_back(found);  // 字符 i 映射到行 found
}

// 重建转移表,只保留唯一的行
std::vector<std::vector<int>> newTransitions;
for (std::vector<int>* row : uniques) {
    newTransitions.push_back(*row);
}
fTransitions = newTransitions;
```

**效果:**
- 大幅减少转移表的行数
- 对于 `[a-z]` 等字符类,所有字符映射到同一行
- 典型压缩率:从 256 行降至 10-30 行

## 依赖关系

**核心依赖:**
- `src/sksl/lex/DFA.h`: 输出的 DFA 结构
- `src/sksl/lex/DFAState.h`: 中间 DFA 状态
- `src/sksl/lex/NFA.h`: 输入的 NFA 结构
- `src/sksl/lex/NFAState.h`: NFA 状态定义

**标准库:**
- `<algorithm>`: `std::sort`, `std::max`
- `<climits>`: `INT_MAX`
- `<memory>`: `std::unique_ptr`
- `<unordered_map>`: 状态去重
- `<set>`, `<vector>`: 容器

**被使用:**
- `src/sksl/lex/Main.cpp`: 调用 `convert()` 生成 DFA

## 设计模式与设计决策

### 子集构造算法

经典的 NFA 到 DFA 转换算法:
- **DFA 状态 = NFA 状态集合:** 每个 DFA 状态对应一组 NFA 状态
- **转移计算:** 收集所有 NFA 状态在给定字符下的后继
- **状态去重:** 相同的 NFA 状态集合共享同一个 DFA 状态

### 惰性状态创建

只创建可达的 DFA 状态:
- 从起始状态开始扫描
- 按需创建后继状态
- 避免生成不可达的状态

### 优先级消歧

当多个正则表达式匹配时:
```cpp
bestAccept = std::min(bestAccept, tokenId);
```

选择最小的 token ID,对应最先定义的规则。这实现了 "最长匹配,先定义优先" 的词法规则。

### 两阶段优化

1. **构建阶段:** 使用字符作为转移表索引(256 行)
2. **压缩阶段:** 合并相同的行,生成字符映射

分离关注点,简化算法逻辑。

### 深度优先扫描

`scanState` 递归扫描状态:
- 简洁的实现
- 利用调用栈管理待访问状态
- 自动避免重复访问(`fIsScanned` 标志)

## 性能考量

### 状态爆炸

最坏情况下,DFA 状态数是 NFA 状态数的指数级:
- `O(2^n)` 其中 n 是 NFA 状态数
- 实际中通常远小于这个上界
- 词法规则的结构限制了状态数

### 转移表压缩

`computeMappings` 的时间复杂度:
- `O(c * r * s)` 其中 c=字符数(256),r=唯一行数,s=状态数
- `O(n^2)` 比较,但 n 很小(通常 < 50 状态)
- 可以用哈希优化,但当前实现已足够快

### 内存占用

未压缩转移表:
- `256 * 状态数 * 4 字节`
- 对于 50 个状态: 约 50KB

压缩后:
- `唯一行数 * 状态数 * 4 字节`
- 对于 20 行, 50 状态: 约 4KB

压缩比通常 10:1 或更高。

### 字符范围限制

只考虑 `START_CHAR` (9) 到 `END_CHAR` (126):
- 跳过不可打印字符
- 减少扫描次数
- 足以覆盖 SkSL 的所有 token

## 相关文件

**输入:**
- `src/sksl/lex/NFA.h`: NFA 结构
- `src/sksl/lex/NFAState.h`: NFA 状态
- `src/sksl/lex/RegexNode.cpp`: 构建 NFA

**输出:**
- `src/sksl/lex/DFA.h`: DFA 结构

**调用者:**
- `src/sksl/lex/Main.cpp`: 词法分析器生成器

**理论:**
- Subset Construction Algorithm(子集构造算法)
- Powerset Construction(幂集构造)
- Rabin-Scott Theorem(证明 NFA 和 DFA 等价)
