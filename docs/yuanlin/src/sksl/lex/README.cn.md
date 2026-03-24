# SkSL Lex - 词法分析器生成工具

## 概述

`src/sksl/lex` 目录包含 SkSL (Skia Shading Language) 的词法分析器生成工具 `sksllex`。该工具读取 `.lex` 格式的词法规则定义文件，通过经典的正则表达式 -> NFA -> DFA 编译管道，自动生成高效的词法分析器 C++ 源代码。生成的词法分析器被 SkSL 编译器在运行时使用，将着色器源代码文本分解为一系列标记 (Token)。

该目录实现了一个完整的词法分析器生成器（lexer generator），类似于经典工具 lex/flex 的简化版本。核心流程是：首先使用 `RegexParser` 将每条正则表达式规则解析为 `RegexNode` 解析树；然后通过 `RegexNode::createStates()` 将解析树转换为 NFA（非确定性有限自动机）状态；接着使用子集构造算法（`NFAtoDFA`）将 NFA 转换为 DFA（确定性有限自动机）；最后通过 `TransitionTable` 将 DFA 转换表压缩编码，输出到生成的 C++ 文件中。

词法规则定义在 `sksl.lex` 文件中，包含了 SkSL 语言的所有词法单元：关键字（`if`、`else`、`for`、`while` 等）、字面量（整数、浮点数）、运算符（`+`、`-`、`*`、`/`、`==` 等）、标识符、注释以及保留字。该文件是 SkSL 语言词法层面的完整定义，直接决定了编译器前端能够识别的 token 类型。

值得注意的是，该工具是一个独立的构建时工具程序（而非运行时库），仅在需要修改 SkSL 词法规则时运行。生成的 `SkSLLexer.h` 和 `SkSLLexer.cpp` 文件位于 SkSL 源码主目录中，被编译器直接使用。该目录有自己独立的断言宏（`LexUtil.h`），不依赖完整的 Skia 构建环境。

## 架构图

```
                    sksl.lex (词法规则定义文件)
                         |
                         v
                  +------+------+
                  |  Main.cpp   |  (sksllex 入口)
                  |  process()  |
                  +------+------+
                         |
            +------------+------------+
            |                         |
            v                         v
     正则表达式解析               字面字符串解析
            |                         |
            v                         |
     +------+------+                  |
     | RegexParser |                  |
     |   parse()   |                  |
     +------+------+                  |
            |                         |
            v                         |
     +------+------+                  |
     |  RegexNode  | <----------------+
     |  (解析树)   |
     +------+------+
            |
            v  createStates()
     +------+------+
     |     NFA     |
     |  (状态机)   |
     +------+------+
            |
            v  NFAtoDFA::convert()
     +------+------+
     |     DFA     |
     |  (确定机)   |
     +------+------+
            |
    +-------+-------+
    |               |
    v               v
 writeH()     writeCPP()
    |               |
    v               v
SkSLLexer.h  SkSLLexer.cpp
 (Token      (转换表 +
  定义)       next()函数)
              |
              +-- WriteTransitionTable()
                  (压缩编码转换表)
```

## 目录结构

```
src/sksl/lex/
|-- BUILD.bazel            # Bazel 构建配置
|-- Main.cpp               # sksllex 工具入口点，读取 .lex 文件并生成代码
|-- sksl.lex               # SkSL 词法规则定义文件（核心输入）
|
|-- RegexParser.h          # 正则表达式解析器声明
|-- RegexParser.cpp        # 正则表达式解析器实现
|-- RegexNode.h            # 正则表达式解析树节点定义
|-- RegexNode.cpp          # 解析树节点到 NFA 状态的转换
|
|-- NFA.h                  # 非确定性有限自动机定义
|-- NFA.cpp                # NFA 匹配实现（仅用于调试）
|-- NFAState.h             # NFA 状态节点定义
|
|-- NFAtoDFA.h             # NFA 到 DFA 的子集构造转换器
|-- DFA.h                  # 确定性有限自动机定义
|-- DFAState.h             # DFA 状态节点定义
|
|-- TransitionTable.h      # 转换表压缩编码声明
|-- TransitionTable.cpp    # 转换表压缩编码实现
|
|-- LexUtil.h              # 独立的工具宏定义（INVALID, SkASSERT, SK_ABORT）
```

## 关键类与函数

### RegexParser (`RegexParser.h`)

```cpp
class RegexParser {
public:
    RegexNode parse(std::string source);
private:
    void term();           // 匹配字符字面量、括号组、字符集或通配符
    void quantifiedTerm(); // 匹配带量词的 term（*、+、?）
    void sequence();       // 匹配量化项的序列
    void regex();          // 匹配完整正则表达式（包含 | 交替）
    void literal();        // 匹配字面字符或转义序列
    void group();          // 匹配括号分组 ()
    void set();            // 匹配字符集 [...]
    void setItem();        // 匹配字符集中的单个项或范围
    RegexNode escapeSequence(char c);  // 处理转义序列 (\n, \r, \t, \s)
};
```

`RegexParser` 是一个递归下降解析器，支持正则表达式的基本语法：字符字面量、字符集（`[a-z]`）、分组（`()`）、交替（`|`）和量词（`*`、`+`、`?`）。它将正则表达式字符串解析为 `RegexNode` 树结构，使用栈（`fStack`）来管理解析过程中的中间结果。

### RegexNode (`RegexNode.h`)

```cpp
struct RegexNode {
    enum Kind {
        kChar_Kind,      // 匹配单个字符
        kCharset_Kind,   // 匹配字符集 [...]
        kConcat_Kind,    // 连接操作 AB
        kDot_Kind,       // 通配符 .（匹配除换行外的任意字符）
        kOr_Kind,        // 交替操作 A|B
        kPlus_Kind,      // 一次或多次 A+
        kRange_Kind,     // 范围 a-z（仅在字符集内）
        kQuestion_Kind,  // 零次或一次 A?
        kStar_Kind       // 零次或多次 A*
    };

    std::vector<int> createStates(NFA* nfa, const std::vector<int>& accept) const;
    // 将解析树递归地转换为 NFA 状态
};
```

`RegexNode` 代表正则表达式解析树中的一个节点。核心方法 `createStates()` 将解析树递归转换为 NFA 状态。对于 `kPlus_Kind` 和 `kStar_Kind`，它使用占位状态和 `kRemapped_Kind` 实现反向引用，从而构造循环结构。

### NFAState (`NFAState.h`)

```cpp
struct NFAState {
    enum Kind {
        kAccept_Kind,    // 接受状态，表示成功匹配某个 token
        kChar_Kind,      // 匹配单个字符 fChar
        kDot_Kind,       // 匹配除 '\n' 外的任意字符
        kRemapped_Kind,  // 占位状态，转换时展开为 fData 中的多个状态
        kTable_Kind      // 使用查找表匹配，fData[c] 表示是否接受字符 c
    };

    bool accept(char c) const;   // 判断是否接受字符 c
    Kind fKind;
    char fChar;                  // kChar_Kind 使用
    bool fInverse;               // kTable_Kind 的取反标志
    std::vector<int> fData;      // token ID (kAccept) 或字符表 (kTable)
    std::vector<int> fNext;      // 成功匹配后的后继状态列表
};
```

`NFAState` 表示 NFA 中的单个状态。`kRemapped_Kind` 是一种优化机制：当我们需要转换到多个状态时（如 `A*` 的循环），不直接在每个前驱状态中存储所有后继，而是使用一个中间占位状态，在匹配时动态展开。

### NFA (`NFA.h`)

```cpp
struct NFA {
    int addRegex(const RegexNode& regex);  // 添加正则表达式，返回索引
    int addState(NFAState s);              // 添加状态，返回索引
    int match(std::string s) const;        // 匹配字符串（仅调试用）

    int fRegexCount;                       // 正则表达式计数（token 从 1 开始）
    std::vector<NFAState> fStates;         // 所有状态
    std::vector<int> fStartStates;         // 起始状态集
};
```

NFA 维护所有正则表达式的状态。`addRegex()` 将新正则表达式的 NFA 状态合并到全局 NFA 中。token ID 从 1 开始（0 保留给 `END_OF_FILE`）。`match()` 方法通过同时模拟所有可能的状态路径进行匹配，返回首个匹配的 token ID，但效率较低，仅用于调试。

### NFAtoDFA (`NFAtoDFA.h`)

```cpp
class NFAtoDFA {
public:
    static constexpr char START_CHAR = 9;    // 制表符 (Tab)
    static constexpr char END_CHAR = 126;    // '~'

    NFAtoDFA(NFA* nfa);
    DFA convert();

private:
    DFAState* getState(DFAState::Label label);  // 获取或创建 DFA 状态
    void scanState(DFAState* state);             // 扫描状态的所有字符转换
    void computeMappings();                      // 压缩相同转换行
    void add(int nfaState, std::vector<int>* states);        // 展开 Remapped 状态
    void addTransition(char c, int start, int next);         // 添加转换
};
```

`NFAtoDFA` 实现经典的子集构造算法（subset construction），将 NFA 转换为等价的 DFA。核心思路是将 NFA 中可能同时处于的状态集合视为 DFA 的单个状态。当多个正则表达式同时匹配（如 `while` 同时匹配 `WHILE` 和 `IDENTIFIER`）时，优先选择先添加的正则表达式。`computeMappings()` 通过合并具有相同转换行为的字符来减小转换表大小。

### DFA (`DFA.h`)

```cpp
struct DFA {
    std::vector<int> fCharMappings;             // 字符到转换表行的映射
    std::vector<std::vector<int>> fTransitions; // 转换表 [映射行][状态] -> 新状态
    std::vector<int> fAccepts;                  // 每个状态对应的 token ID（-1 表示不接受）
};
```

DFA 是最终的确定性有限自动机表示。`fCharMappings` 将多个字符映射到同一行（因为如 `[0-9]` 在所有规则中行为一致），减小了转换表的列数。查找逻辑为：`新状态 = fTransitions[fCharMappings[字符]][当前状态]`。

### TransitionTable (`TransitionTable.h/cpp`)

```cpp
void WriteTransitionTable(std::ofstream& out, const DFA& dfa, size_t states);
```

`WriteTransitionTable` 将 DFA 转换表压缩编码后写入 C++ 源文件。它使用 2-bit 紧凑编码：大多数 DFA 状态只有少量非零转换值（通常不超过 3 个），因此可以用 2-bit 索引加一个小型查找表来替代完整的状态值。无法紧凑编码的状态使用全尺寸条目。`IndexEntry` 的正值指向紧凑表，负值（按位取反）指向全尺寸表。

### Main.cpp (sksllex 入口)

```cpp
static void process(const char* inPath, const char* lexer, const char* token,
                    const char* hPath, const char* cppPath);
int main(int argc, const char** argv);
// 用法: sksllex <input.lex> <lexername> <tokenname> <output.h> <output.cpp>
```

`Main.cpp` 是 `sksllex` 工具的入口。`process()` 函数读取 `.lex` 文件，逐行解析 token 定义（格式：`TOKEN_NAME = pattern`），构建 NFA、转换为 DFA，然后调用 `writeH()` 和 `writeCPP()` 生成词法分析器的头文件和实现文件。生成的词法分析器使用单次前进扫描（forward-only scan），利用 DFA 转换表进行快速状态转移。

### sksl.lex (词法规则)

`sksl.lex` 文件定义了 SkSL 的完整词法，包含约 103 条规则：

- **字面量**: `FLOAT_LITERAL`、`INT_LITERAL`、`TRUE_LITERAL`、`FALSE_LITERAL`、`BAD_OCTAL`
- **关键字**: `IF`、`ELSE`、`FOR`、`WHILE`、`DO`、`SWITCH`、`CASE`、`DEFAULT`、`BREAK`、`CONTINUE`、`DISCARD`、`RETURN`、`STRUCT`、`LAYOUT` 等
- **类型修饰符**: `IN`、`OUT`、`INOUT`、`UNIFORM`、`CONST`、`FLAT`、`NOPERSPECTIVE`、`READONLY`、`WRITEONLY`、`BUFFER`
- **内部修饰符**: `PURE` (`$pure`)、`ES3` (`$es3`)、`EXPORT` (`$export`)
- **精度修饰符**: `HIGHP`、`MEDIUMP`、`LOWP`
- **标识符**: `IDENTIFIER`、`PRIVATE_IDENTIFIER` (`$名称`)、`DIRECTIVE` (`#名称`)
- **运算符**: 算术、比较、位运算、逻辑运算、赋值运算等
- **分隔符**: 括号、花括号、方括号、点、逗号、分号
- **保留字**: `RESERVED` 包含大量 GLSL 保留字和 `gl_*` 内置变量名
- **空白和注释**: `WHITESPACE`、`LINE_COMMENT`、`BLOCK_COMMENT`

## 依赖关系

```
sksllex 工具依赖关系:
+------------------------------------------+
| LexUtil.h (独立的宏定义)                  |
|   - INVALID = -1                         |
|   - SK_ABORT, SkASSERT, SkUNREACHABLE   |
|   (不依赖 Skia 主框架)                    |
+------------------------------------------+
         ^
         |  (被所有文件引用)
         |
+--------+---+   +----------+   +-----------+
| RegexParser |-->| RegexNode |-->|    NFA    |
| (解析正则)  |   | (解析树)  |   | (自动机)  |
+-------------+   +----------+   +-----+-----+
                                        |
                                        v
                                  +-----------+
                                  | NFAtoDFA  |
                                  | (子集构造) |
                                  +-----+-----+
                                        |
                                +-------+-------+
                                |               |
                           +----+----+   +------+------+
                           |   DFA   |   | DFAState    |
                           | (结果)  |   | (带 Label)  |
                           +----+----+   +-------------+
                                |
                                v
                       +--------+--------+
                       | TransitionTable |
                       | (压缩编码)       |
                       +--------+--------+
                                |
                                v
                        生成的 C++ 代码:
                    SkSLLexer.h + SkSLLexer.cpp
```

该目录是完全独立的构建时工具，不依赖 Skia 运行时库。`LexUtil.h` 提供了精简版的 `SkASSERT` 和 `SK_ABORT` 宏，使得工具可以在没有完整 Skia 环境的情况下编译运行。

## 设计模式分析

### 1. 管道模式 (Pipeline Pattern)

整个词法分析器生成过程形成了一条清晰的编译管道：
```
正则表达式文本 -> RegexParser -> RegexNode 树 -> NFA -> DFA -> 压缩转换表 -> C++ 代码
```
每个阶段的输出是下一阶段的输入，各阶段职责单一，便于理解和调试。

### 2. 访问者模式的变体

`RegexNode::createStates()` 根据节点类型（`Kind` 枚举）执行不同的 NFA 状态构建逻辑。虽然使用 switch 而非虚函数，但本质上是访问者模式的变体，对每种正则表达式节点类型执行特定的转换操作。

### 3. 占位符/延迟解析模式

NFA 中的 `kRemapped_Kind` 状态是一种占位符模式：在构建循环结构（如 `A+` 和 `A*`）时，先创建一个空占位状态，建立引用关系后再回填实际目标状态。这解决了循环依赖的构建问题。

### 4. 字符映射压缩

`NFAtoDFA::computeMappings()` 将具有相同转换行为的字符合并为同一映射，显著减小了 DFA 转换表的大小。例如，字符 `0` 到 `9` 在所有词法规则中的行为完全一致，因此只需要一行转换数据。

### 5. 两级压缩编码

`TransitionTable` 使用两级压缩：首先将大多数状态（仅有 3 个或更少非零转换值）压缩为 2-bit 紧凑条目；无法压缩的状态使用全尺寸条目。索引表通过正/负值区分两种类型。

## 数据流

```
输入: sksl.lex 文件
   |
   v  逐行解析
"TOKEN_NAME = pattern"
   |
   +---> 双引号字面量 (如 "if")
   |        |
   |        v  直接构造 RegexNode::kConcat_Kind 链
   |        RegexNode('i') + RegexNode('f')
   |
   +---> 正则表达式 (如 [0-9]+)
            |
            v  RegexParser::parse()
            RegexNode (kPlus, kCharset[0-9])
   |
   v  RegexNode::createStates()
   |
NFA (非确定性有限自动机)
   |  - fStates: 所有 NFAState 节点
   |  - fStartStates: 所有起始状态
   |  - 多个正则表达式的状态共享同一个 NFA
   |
   v  NFAtoDFA::convert()
   |  - 子集构造: NFA 状态集合 -> DFA 单状态
   |  - 状态 0 = 拒绝状态
   |  - 状态 1 = 起始状态（所有 NFA 起始状态的并集）
   |  - 歧义消解: 多个 token 匹配时选择先定义的
   |
DFA (确定性有限自动机)
   |  - fCharMappings: 字符 -> 转换表行索引
   |  - fTransitions: [行][状态] -> 新状态
   |  - fAccepts: [状态] -> token ID
   |
   +---> writeH(): 生成 Token 枚举和 Lexer 类声明
   +---> writeCPP(): 生成转换表和 next() 函数
              |
              v  WriteTransitionTable()
              |  - 分析每个状态的非零转换值数量
              |  - <= 3 个: CompactEntry (2-bit 编码)
              |  - > 3 个: FullEntry (完整数组)
              |  - 生成 get_transition() 内联函数
              |
              v
      SkSLLexer.h + SkSLLexer.cpp
         |
         v  运行时使用
      SkSL 编译器前端
         |
         +---> Lexer::start(源代码文本)
         +---> Lexer::next() -> Token(kind, offset, length)
         +---> 支持 Checkpoint/rewindToCheckpoint 回溯
```

## 相关文档与参考

- **经典编译原理**: NFA/DFA 转换算法参见《编译原理》(Dragon Book) 第 3 章。
- **子集构造算法**: 该目录实现了标准的子集构造 (subset construction / powerset construction) 算法。
- **生成的输出文件**: `src/sksl/SkSLLexer.h` 和 `src/sksl/SkSLLexer.cpp` 是由该工具生成的文件。
- **使用说明**: 修改 `sksl.lex` 后需要设置 GN 参数 `skia_lex = true` 并重新构建以重新生成词法分析器。
- **Token ID 稳定性**: 由于 token ID 会被烘焙到 `.dehydrated.sksl` 文件中，修改 token 顺序可能需要重新生成脱水二进制文件。
- **相关目录**:
  - `src/sksl/` - SkSL 编译器主目录
  - `src/sksl/codegen/` - 代码生成后端
  - `src/sksl/ir/` - 中间表示定义
  - `src/sksl/generated/` - 生成的 SkSL 内置模块代码
