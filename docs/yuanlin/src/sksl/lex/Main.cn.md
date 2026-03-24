# Main (SkSL 词法分析器生成器)

> 源文件: src/sksl/lex/Main.cpp

## 概述

`Main.cpp` 是 SkSL 词法分析器生成工具 `sksllex` 的主程序,负责将词法规则定义文件(`.lex`)转换为 C++ 词法分析器代码。该工具读取正则表达式形式的 token 定义,构建 NFA,转换为 DFA,并生成高效的表驱动词法分析器的头文件和实现文件。

这是一个离线工具,在 Skia 构建时运行一次,生成的代码被编译到 SkSL 编译器中。采用经典的编译器构建策略:使用专门的工具生成词法分析器,而不是手工编写或运行时构建。

## 架构位置

`Main.cpp` 是词法分析器生成工具链的入口点:

```
词法分析器生成完整流程:
  SkSL.lex (词法规则)
      ↓
  ┌─────────────┐
  │  Main.cpp   │ ← 本文件
  │  (sksllex)  │
  └─────────────┘
      ↓
  解析 .lex → RegexParser → NFA → NFAtoDFA → DFA
      ↓
  代码生成 (writeH, writeCPP)
      ↓
  SkSLLexer.h + SkSLLexer.cpp
```

生成的词法分析器被 SkSL 编译器使用,在运行时进行高效的 token 识别。

## 主要类与结构体

本文件不定义类,主要包含独立函数和常量定义。

**常量定义:**

```cpp
static constexpr const char HEADER[] = "/*\n * Copyright 2017 Google LLC ...";
```

生成的文件头部的版权声明和警告信息。

## 公共 API 函数

### writeH

```cpp
static void writeH(const DFA& dfa, const char* lexer, const char* token,
                   const std::vector<std::string>& tokens, const char* hPath)
```

**功能:** 生成词法分析器的头文件(.h)

**参数:**
- `dfa`: 编译好的 DFA
- `lexer`: 词法分析器类名(如 `SkSLLexer`)
- `token`: Token 类名(如 `Token`)
- `tokens`: 所有 token 名称列表
- `hPath`: 输出头文件路径

**生成内容:**

1. **Token 枚举:**
```cpp
enum class Kind {
    TK_INT,
    TK_FLOAT,
    TK_IDENTIFIER,
    // ...
    TK_END_OF_FILE,
    TK_NONE,
};
```

2. **Token 结构体:**
```cpp
struct Token {
    Kind fKind      = Kind::TK_NONE;
    int32_t fOffset = -1;
    int32_t fLength = -1;
};
```

3. **Lexer 类声明:**
```cpp
class SkSLLexer {
public:
    void start(std::string_view text);
    Token next();
    Checkpoint getCheckpoint() const;
    void rewindToCheckpoint(Checkpoint checkpoint);
private:
    std::string_view fText;
    int32_t fOffset;
};
```

### writeCPP

```cpp
static void writeCPP(const DFA& dfa, const char* lexer, const char* token,
                     const char* include, const char* cppPath)
```

**功能:** 生成词法分析器的实现文件(.cpp)

**参数:**
- `dfa`: 编译好的 DFA
- `lexer`: 词法分析器类名
- `token`: Token 类名
- `include`: 头文件路径
- `cppPath`: 输出实现文件路径

**生成内容:**

1. **状态类型定义:**
```cpp
using State = uint8_t;  // 或 uint16_t,取决于状态数
```

2. **字符映射表:**
```cpp
static constexpr uint8_t kMappings[...] = { ... };
```

3. **转移表:**
```cpp
static State get_transition(uint8_t charMapping, State state) {
    // 生成的转移逻辑
}
```

4. **接受状态表:**
```cpp
static const uint8_t kAccepts[...] = { ... };
```

5. **next() 方法实现:**
```cpp
Token SkSLLexer::next() {
    int32_t startOffset = fOffset;
    State state = 1;
    for (;;) {
        // 状态转移循环
        if (fOffset >= fText.length()) {
            // 处理 EOF
        }
        uint8_t c = (uint8_t)(fText[fOffset] - startChar);
        State newState = get_transition(kMappings[c], state);
        if (!newState) {
            break;
        }
        state = newState;
        ++fOffset;
    }
    Token::Kind kind = (Token::Kind) kAccepts[state];
    return Token(kind, startOffset, fOffset - startOffset);
}
```

### process

```cpp
static void process(const char* inPath, const char* lexer, const char* token,
                    const char* hPath, const char* cppPath)
```

**功能:** 处理词法规则文件并生成代码

**参数:**
- `inPath`: 输入的 .lex 文件路径
- `lexer`: 词法分析器类名
- `token`: Token 类名
- `hPath`: 输出头文件路径
- `cppPath`: 输出实现文件路径

**处理流程:**

1. **初始化:**
```cpp
NFA nfa;
std::vector<std::string> tokens;
tokens.push_back("END_OF_FILE");  // 总是添加 EOF token
```

2. **解析 .lex 文件:**
```cpp
std::ifstream in(inPath);
while (std::getline(in, line)) {
    // 跳过空行和注释(//开头)
    // 解析格式: TOKEN_NAME = pattern
    std::istringstream split(line);
    std::string name, delimiter, pattern;
    split >> name >> delimiter >> pattern;
    tokens.push_back(name);
```

3. **处理两种模式:**

**字面量模式:**
```cpp
if (pattern[0] == '"') {
    // "while" -> 构建字符序列的 NFA
    RegexNode node = RegexNode(RegexNode::kChar_Kind, pattern[1]);
    for (size_t i = 2; i < pattern.size() - 1; ++i) {
        node = RegexNode(RegexNode::kConcat_Kind, node,
                         RegexNode(RegexNode::kChar_Kind, pattern[i]));
    }
    nfa.addRegex(node);
}
```

**正则表达式模式:**
```cpp
else {
    nfa.addRegex(RegexParser().parse(pattern));
}
```

4. **转换为 DFA:**
```cpp
NFAtoDFA converter(&nfa);
DFA dfa = converter.convert();
```

5. **生成代码:**
```cpp
writeH(dfa, lexer, token, tokens, hPath);
writeCPP(dfa, lexer, token, include, cppPath);
```

### main

```cpp
int main(int argc, const char** argv)
```

**功能:** 程序入口点

**命令行格式:**
```
sksllex <input.lex> <lexername> <tokenname> <output.h> <output.cpp>
```

**示例:**
```bash
sksllex SkSL.lex SkSLLexer Token SkSLLexer.h SkSLLexer.cpp
```

**参数验证:**
```cpp
if (argc != 6) {
    printf("usage: sksllex <input.lex> <lexername> <tokenname> <output.h> <output.cpp>\n");
    exit(1);
}
```

## 内部实现细节

### .lex 文件格式

每行定义一个 token:
```
INT = [0-9]+
FLOAT = [0-9]*\.[0-9]+
IDENTIFIER = [a-zA-Z_][a-zA-Z0-9_]*
IF = "if"
WHILE = "while"
LPAREN = "("
```

**语法规则:**
- `TOKEN_NAME = pattern`
- `pattern` 可以是正则表达式或双引号包围的字面量
- 空行和 `//` 开头的注释行被忽略

### 字符范围限制

```cpp
inline static constexpr char START_CHAR = 9;   // '\t'
inline static constexpr char END_CHAR = 126;   // '~'
```

生成的代码调整字符索引:
```cpp
uint8_t c = (uint8_t)(fText[fOffset] - startChar);
```

超出范围的字符映射到 `kInvalidChar`(18),通常触发错误。

### 状态类型选择

```cpp
size_t states = 0;
for (const auto& row : dfa.fTransitions) {
    states = std::max(states, row.size());
}
out << "using State = " << (states <= 256 ? "uint8_t" : "uint16_t") << ";\n";
```

- ≤256 状态:使用 `uint8_t`(节省空间)
- >256 状态:使用 `uint16_t`

### 最长匹配策略

生成的 `next()` 方法实现最长匹配:
```cpp
for (;;) {
    // 持续转移直到无法转移
    if (!newState) {
        break;  // 使用当前状态的接受 token
    }
    state = newState;
    ++fOffset;
}
```

注释解释了简化(SkSL 没有需要回溯的模式,如 `while` vs `w`):
```cpp
// Note that we cheat here: normally a lexer needs to worry about
// the case where a token has a prefix which is not itself a valid token
// Our grammar doesn't have this property...
```

### 优先级处理

Token 定义的顺序决定优先级:
- 先定义的规则优先级更高
- 在 NFAtoDFA 中通过选择最小 token ID 实现
- 允许关键字覆盖标识符

## 依赖关系

**核心依赖:**
- `src/sksl/lex/DFA.h`: DFA 结构
- `src/sksl/lex/LexUtil.h`: 工具宏
- `src/sksl/lex/NFA.h`: NFA 构建
- `src/sksl/lex/NFAtoDFA.h`: NFA 到 DFA 转换
- `src/sksl/lex/RegexNode.h`: 正则表达式节点
- `src/sksl/lex/RegexParser.h`: 正则表达式解析
- `src/sksl/lex/TransitionTable.h`: 转移表序列化

**标准库:**
- `<stdio.h>`, `<stdlib.h>`: 输入输出和程序控制
- `<algorithm>`: 算法工具
- `<sstream>`: 字符串流
- `<string>`, `<vector>`: 容器

**生成的文件:**
- `src/sksl/SkSLLexer.h`: 词法分析器头文件
- `src/sksl/SkSLLexer.cpp`: 词法分析器实现

## 设计模式与设计决策

### 离线生成策略

构建时生成而非运行时构建:
- **优势:** 运行时零开销,词法分析速度快
- **劣势:** 需要构建工具,修改规则需要重新构建

### 表驱动词法分析

生成转移表而非嵌套 if-else:
- 统一的循环逻辑
- 易于优化(分支预测友好)
- 表可以放在只读数据段

### 简洁的接口

词法分析器接口极简:
- `start(text)`: 设置输入
- `next()`: 获取下一个 token
- `getCheckpoint()` / `rewindToCheckpoint()`: 支持回溯

### 分离的 Token 表示

Token 只包含位置信息,不包含文本:
- 节省内存
- 按需提取文本:`text.substr(token.fOffset, token.fLength)`
- 支持零拷贝

### 静态数据嵌入

所有转移表编译为静态常量:
- 程序启动时无需初始化
- 多线程安全(只读)
- 代码和数据紧凑

## 性能考量

### 生成代码的效率

生成的词法分析器:
- O(n) 时间复杂度,n 为输入长度
- 每字符: 2次数组查找 + 1次比较
- 无回溯,无正则表达式解释开销

### 空间占用

典型的 SkSL 词法分析器:
- 转移表: ~5KB
- 字符映射: ~1KB
- 接受表: ~200字节
- **总计:** <10KB

### 编译期计算

所有正则表达式在生成时处理:
- 运行时不需要正则表达式引擎
- 无动态内存分配
- 纯查表操作

## 相关文件

**输入:**
- `SkSL.lex`: SkSL 的词法规则定义

**输出:**
- `src/sksl/SkSLLexer.h`: 生成的头文件
- `src/sksl/SkSLLexer.cpp`: 生成的实现

**工具链:**
- `src/sksl/lex/RegexParser.h`: 解析正则表达式
- `src/sksl/lex/NFA.h`: 构建 NFA
- `src/sksl/lex/NFAtoDFA.h`: 转换为 DFA

**使用生成的词法分析器:**
- `src/sksl/SkSLCompiler.cpp`: SkSL 编译器主入口
- `src/sksl/SkSLParser.cpp`: SkSL 解析器

**构建集成:**
- `BUILD.gn` 或 `CMakeLists.txt`: 定义如何调用 `sksllex`
