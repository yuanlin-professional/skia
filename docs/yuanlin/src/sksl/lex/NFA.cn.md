# NFA

> 源文件: src/sksl/lex/NFA.h, src/sksl/lex/NFA.cpp

## 概述

`NFA` 是 SkSL 词法分析器中的非确定性有限自动机(Nondeterministic Finite Automaton)实现。它用于将一组正则表达式转换为状态机,以便同时匹配多个正则表达式模式。NFA 是词法分析器构建流程中的核心组件,负责将正则表达式转换为可执行的状态机表示,最终会被转换为更高效的 DFA(确定性有限自动机)。

## 架构位置

NFA 位于 SkSL 编译器的词法分析层,具体在词法分析器生成工具链中:

```
src/sksl/
  ├── lex/
  │   ├── NFA.h/cpp           ← 当前组件
  │   ├── NFAState.h          ← NFA 状态定义
  │   ├── DFA.h               ← 目标 DFA 表示
  │   ├── NFAtoDFA.h          ← NFA 到 DFA 转换器
  │   ├── RegexNode.h         ← 正则表达式节点
  │   └── RegexParser.h       ← 正则表达式解析器
```

在编译流程中的位置:
1. RegexParser 将正则表达式字符串解析为 RegexNode 树
2. NFA 从 RegexNode 构建状态机(当前组件)
3. NFAtoDFA 将 NFA 转换为 DFA
4. 生成最终的词法分析器代码

## 主要类与结构体

### NFA 结构体

主要的 NFA 结构体,包含以下核心成员:

```cpp
struct NFA {
    int fRegexCount;                    // 已添加的正则表达式数量
    std::vector<NFAState> fStates;      // 所有 NFA 状态的集合
    std::vector<int> fStartStates;      // 各个正则表达式的起始状态索引
};
```

**关键成员说明:**
- `fRegexCount`: 跟踪已添加的正则表达式数量,token 0 预留给 END_OF_FILE
- `fStates`: 存储所有状态的线性数组,通过索引引用
- `fStartStates`: 每个正则表达式对应一个或多个起始状态索引

### 关键方法

**addRegex()**
```cpp
int addRegex(const RegexNode& regex);
```
将新的正则表达式添加到 NFA 中:
- 为该正则表达式创建接受状态
- 调用 `regex.createStates()` 生成状态转换链
- 返回正则表达式的索引

**addState()**
```cpp
int addState(NFAState s);
```
向 NFA 添加新状态:
- 将状态添加到 `fStates` 向量
- 返回新状态的索引

**match()**
```cpp
int match(std::string s) const;
```
匹配字符串,返回第一个匹配的正则表达式索引:
- 从所有起始状态开始
- 逐字符推进状态转换
- 返回最小的接受状态 token ID
- 仅用于调试,实际使用会转换为 DFA

## 公共 API 函数

### addRegex

**函数签名:**
```cpp
int addRegex(const RegexNode& regex)
```

**功能:** 将一个正则表达式添加到 NFA 中,并返回其索引

**实现细节:**
- 创建接受状态,token ID 从 1 开始(0 预留给 END_OF_FILE)
- 调用 `regex.createStates()` 构建状态转换
- 将生成的起始状态添加到 `fStartStates`

**返回值:** 正则表达式的索引,用于后续识别匹配的 token 类型

### addState

**函数签名:**
```cpp
int addState(NFAState s)
```

**功能:** 添加新状态到 NFA

**参数:**
- `s`: 要添加的 NFAState 对象

**返回值:** 新状态在 `fStates` 向量中的索引

### match

**函数签名:**
```cpp
int match(std::string s) const
```

**功能:** 使用 NFA 匹配字符串(调试用途)

**算法流程:**
1. 初始化当前状态集为所有起始状态
2. 对字符串中的每个字符:
   - 检查当前状态集中哪些状态接受该字符
   - 收集这些状态的后继状态
   - 处理重映射状态(kRemapped_Kind)
   - 更新当前状态集
3. 检查最终状态集中是否有接受状态
4. 返回最小的接受 token ID(优先级最高)

**返回值:**
- 匹配成功:返回 token ID(>= 1)
- 匹配失败:返回 INVALID(-1)

**性能说明:** 此方法相对较慢,仅用于调试。生产环境应使用转换后的 DFA。

## 内部实现细节

### 状态索引系统

NFA 使用基于索引的状态引用系统:
- 所有状态存储在 `fStates` 向量中
- 状态通过整数索引相互引用
- 索引从 0 开始,连续分配

### Token ID 分配

- Token ID 0 预留给 END_OF_FILE
- 用户定义的正则表达式从 ID 1 开始
- `fRegexCount` 在 `addRegex` 中递增
- 接受状态存储其对应的 token ID

### 状态转换处理

在 `match()` 方法中:
- 维护活动状态集合 `states`
- 对每个字符,计算下一个状态集 `next`
- 处理 kRemapped_Kind 状态的特殊情况:将其展开为 fData 中的所有状态
- 如果 `next` 为空,匹配失败

### 接受状态优先级

当多个正则表达式同时匹配时:
- 选择 token ID 最小的(最先添加的)
- 实现代码: `if (accept == INVALID || result < accept)`
- 保证了正则表达式的优先级语义

## 依赖关系

### 直接依赖

- `NFAState.h`: NFA 的状态定义
- `RegexNode.h`: 正则表达式的抽象语法树表示
- `LexUtil.h`: 词法分析器工具宏(INVALID 常量)

### 被依赖

- `NFAtoDFA.h`: 将 NFA 转换为 DFA
- `Main.cpp`: 词法分析器生成器的主程序

### 数据流

```
RegexParser → RegexNode → NFA → NFAtoDFA → DFA → 生成的词法分析器
```

## 设计模式与设计决策

### 设计模式

**1. 构建器模式 (Builder Pattern)**
- `addRegex()` 和 `addState()` 方法逐步构建 NFA
- 支持增量添加正则表达式
- 构建完成后可转换为 DFA

**2. 复合模式 (Composite Pattern)**
- NFA 包含多个 NFAState
- 每个 NFAState 可能引用其他状态
- 形成状态转换图

### 设计决策

**1. 索引而非指针**
- 使用整数索引而非指针引用状态
- 优点:序列化友好,内存布局紧凑
- 缺点:需要通过 `fStates[index]` 间接访问

**2. 多正则表达式同时匹配**
- 所有正则表达式共享同一个 NFA
- 不同正则表达式有不同的起始状态
- 优点:减少状态机数量,提高效率

**3. Token 0 预留**
- END_OF_FILE 使用 token ID 0
- 用户正则表达式从 1 开始编号
- 避免了特殊情况处理

**4. 仅用于中间表示**
- NFA 仅作为构建 DFA 的中间步骤
- `match()` 方法仅用于调试
- 生产代码使用转换后的 DFA

## 性能考量

### 空间复杂度

- **状态数量:** O(m * n),其中 m 是正则表达式数量,n 是平均正则表达式长度
- **状态转换:** 每个状态可能有多个后继状态,存储在 `NFAState::fNext` 中
- **内存布局:** 使用 `std::vector` 提供良好的缓存局部性

### 时间复杂度

**addRegex:** O(n),其中 n 是正则表达式的节点数
- 需要遍历整个 RegexNode 树
- 为每个节点创建相应的状态

**match:** O(s * k * t),其中:
- s: 字符串长度
- k: 活动状态数量(可能指数增长)
- t: 平均状态转换数量

**性能问题:**
- NFA 匹配可能导致状态爆炸
- 多个活动状态并行推进效率低
- 这就是为什么需要转换为 DFA

### 优化策略

**1. 延迟匹配**
- `match()` 仅用于调试
- 生产环境转换为 DFA 后使用

**2. 状态共享**
- 多个正则表达式共享相同的状态转换
- 减少状态总数

**3. 索引访问**
- 使用整数索引而非指针
- 提高缓存命中率

## 相关文件

### 核心文件

- `src/sksl/lex/NFAState.h`: NFA 状态的定义和实现
- `src/sksl/lex/RegexNode.h`: 正则表达式节点
- `src/sksl/lex/NFAtoDFA.h`: NFA 到 DFA 的转换算法

### 使用示例

- `src/sksl/lex/Main.cpp`: 词法分析器生成器主程序,展示了如何使用 NFA

### 相关工具

- `src/sksl/lex/RegexParser.h`: 将字符串解析为 RegexNode
- `src/sksl/lex/LexUtil.h`: 通用词法分析工具

### 输出文件

- `src/sksl/lex/DFA.h`: NFA 转换后的目标 DFA 结构
- `src/sksl/lex/TransitionTable.h`: DFA 转换表生成器
