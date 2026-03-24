# run_sksllex.py

> 源文件: gn/run_sksllex.py

## 概述

`run_sksllex.py` 是 Skia 着色器语言 (SkSL) 词法分析器生成工具的包装脚本。该脚本自动化了 SkSL 词法分析器的生成流程:首先运行 `sksllex` 工具从词法规则文件生成 C++ 词法分析器代码,然后使用 `clang-format` 格式化生成的代码,确保输出符合 Skia 的代码风格规范。

这个工具是 Skia 图形编译管线的重要组成部分,在 构建过程中自动生成解析 SkSL 着色器代码所需的词法分析器,支持 Skia 的实时着色器编译能力。

## 架构位置

`run_sksllex.py` 在 Skia 着色器编译流程中的位置:

```
skia/
├── gn/
│   └── run_sksllex.py               # 本脚本 - 词法分析器生成包装器
├── src/
│   └── sksl/
│       ├── lex/
│       │   └── sksl.lex             # 词法规则定义
│       ├── SkSLLexer.h              # 生成的词法分析器头文件
│       ├── SkSLLexer.cpp            # 生成的词法分析器实现
│       ├── SkSLCompiler.cpp         # SkSL 编译器(使用词法分析器)
│       └── ...
├── out/
│   └── <config>/
│       └── sksllex                  # 词法分析器生成工具
└── tools/
    └── sksllex/                     # 词法分析器生成工具源码
```

编译流程:
1. **构建 sksllex**: 从 `tools/sksllex` 编译词法分析器生成工具
2. **生成词法分析器**: `run_sksllex.py` 调用 `sksllex` 处理 `sksl.lex`
3. **格式化代码**: 使用 `clang-format` 格式化生成的 C++ 代码
4. **编译 SkSL**: 将生成的词法分析器编译到 Skia 库中

## 主要类与结构体

该脚本采用函数式编程风格,不定义类或结构体。

## 公共 API 函数

### 命令行接口

```python
sksllex = sys.argv[1]
clangFormat = sys.argv[2]
fetchClangFormat = sys.argv[3]
src = sys.argv[4]
```

**参数**:
1. `sksllex`: 词法分析器生成工具的可执行文件路径
2. `clangFormat`: `clang-format` 工具的路径
3. `fetchClangFormat`: 获取 `clang-format` 的脚本路径
4. `src`: SkSL 源代码目录路径

**功能**:
1. 运行 `sksllex` 生成词法分析器代码
2. 检查 `clang-format` 是否存在,不存在则下载
3. 使用 `clang-format` 格式化生成的代码

**调用示例**:
```bash
python gn/run_sksllex.py \
    out/Release/sksllex \
    buildtools/linux64/clang-format \
    tools/git-sync-deps \
    src
```

### GN 构建集成

```gn
action("run_sksllex") {
  script = "gn/run_sksllex.py"
  sources = [ "src/sksl/lex/sksl.lex" ]
  outputs = [
    "$target_gen_dir/SkSLLexer.h",
    "$target_gen_dir/SkSLLexer.cpp",
  ]
  args = [
    rebase_path("$root_build_dir/sksllex"),
    rebase_path("$clang_format_executable"),
    rebase_path("tools/git-sync-deps"),
    rebase_path("src"),
  ]
  deps = [ ":sksllex($host_toolchain)" ]
}
```

## 内部实现细节

### sksllex 工具调用

```python
subprocess.check_output([sksllex, src + "/sksl/lex/sksl.lex", "Lexer",
                         "Token", src + "/sksl/SkSLLexer.h", src +
                         "/sksl/SkSLLexer.cpp"])
```

**参数解析**:
- **输入**: `src/sksl/lex/sksl.lex` - 词法规则定义文件
- **类名**: `Lexer` - 生成的词法分析器类名
- **令牌类**: `Token` - 令牌类名
- **输出头文件**: `src/sksl/SkSLLexer.h`
- **输出实现文件**: `src/sksl/SkSLLexer.cpp`

**sksl.lex 文件格式**:
词法规则文件定义了 SkSL 的词法单元(token),如关键字、标识符、操作符等:
```lex
// 示例词法规则
IDENTIFIER  [a-zA-Z_][a-zA-Z0-9_]*
NUMBER      [0-9]+
FLOAT       [0-9]+\.[0-9]+
```

### 平台特定可执行文件处理

```python
exeSuffix = '.exe' if sys.platform.startswith('win') else '';
```

**跨平台支持**:
- **Windows**: 可执行文件需要 `.exe` 后缀
- **Unix/macOS**: 无后缀
- 用于检查 `clang-format` 文件存在性

### clang-format 自动下载

```python
if not os.path.isfile(clangFormat + exeSuffix):
    subprocess.check_call([sys.executable, fetchClangFormat]);
```

**自动化依赖管理**:
- 检查 `clang-format` 是否已安装
- 不存在时自动运行下载脚本
- 确保构建环境完整性
- 使用 `sys.executable` 确保使用相同的 Python 解释器

### 代码格式化

```python
subprocess.check_call(clangFormat + " -i \"" + src + "/sksl/SkSLLexer.h\"",
                      shell=True)
subprocess.check_call(clangFormat + " -i \"" + src +
                      "/sksl/SkSLLexer.cpp\"", shell=True)
```

**格式化参数**:
- **`-i`**: 原地修改文件(in-place)
- **路径引号**: 处理包含空格的路径
- **shell=True**: 通过 shell 执行,支持路径展开和引号

**为什么分两次调用?**
- 头文件和实现文件分别格式化
- 可以独立处理每个文件的格式化错误
- 明确的输出和错误报告

### 错误处理

```python
try:
    subprocess.check_output([sksllex, ...])
    # ...
    subprocess.check_call(clangFormat + " -i ...")
    subprocess.check_call(clangFormat + " -i ...")
except subprocess.CalledProcessError as err:
    print("### Lexer error:")
    print(err.output)
    exit(1)
```

**异常捕获策略**:
- 捕获所有 subprocess 调用的错误
- 打印友好的错误消息
- 输出工具的错误信息
- 以非零退出码终止(通知构建系统失败)

## 依赖关系

### Python 标准库

```python
import os          # 文件存在性检查
import subprocess  # 外部工具调用
import sys         # 命令行参数和平台检测
```

### 外部工具依赖

**sksllex**:
- Skia 自己的词法分析器生成工具
- 源码位于 `tools/sksllex`
- 构建时先编译,然后使用

**clang-format**:
- LLVM 项目的代码格式化工具
- Skia 使用特定版本以保证一致性
- 自动从 `buildtools` 仓库下载

**fetchClangFormat 脚本**:
- 通常是 `tools/git-sync-deps` 或类似脚本
- 负责下载构建工具依赖

### 文件依赖关系

```
sksl.lex (词法规则)
    ↓
sksllex 工具
    ↓
SkSLLexer.h + SkSLLexer.cpp (生成的代码)
    ↓
clang-format
    ↓
格式化的词法分析器代码
    ↓
编译到 libskia
```

## 设计模式与设计决策

### 管道模式
脚本将多个工具串联成处理管道:
```
输入文件 → sksllex → 原始 C++ → clang-format → 格式化 C++
```

### 自动化依赖管理
```python
if not os.path.isfile(clangFormat + exeSuffix):
    subprocess.check_call([sys.executable, fetchClangFormat])
```
**优势**:
- 开发者无需手动安装工具
- 确保工具版本一致性
- 简化首次构建流程

### 错误聚合
```python
try:
    # 多个 subprocess 调用
except subprocess.CalledProcessError as err:
    # 统一错误处理
```
所有 subprocess 错误在同一个 catch 块处理,提供一致的错误报告。

### 平台抽象

```python
exeSuffix = '.exe' if sys.platform.startswith('win') else ''
```
隐藏平台差异,使脚本在 Windows/macOS/Linux 上行为一致。

### 原地修改策略

**为什么使用 `-i` 而不是重定向?**
```python
# 当前方法
clang-format -i file.cpp

# 替代方法(未采用)
clang-format file.cpp > file.cpp.tmp && mv file.cpp.tmp file.cpp
```

**优势**:
- 更简洁的命令
- 保留文件权限和元数据
- 原子操作(clang-format 内部保证)

## 性能考量

### 执行时间

**典型构建时间**:
- `sksllex` 执行: 50-200ms
- `clang-format` (每个文件): 50-100ms
- 总计: ~200-400ms

**增量构建优化**:
- GN 跟踪 `sksl.lex` 的修改时间
- 仅在词法规则变更时重新生成
- 正常开发中很少触发

### 代码生成大小

**生成的文件**:
- `SkSLLexer.h`: ~5-10 KB
- `SkSLLexer.cpp`: ~20-50 KB
- 包含状态机和令牌识别逻辑

### 缓存和重复运行

**GN 依赖追踪**:
```gn
sources = [ "src/sksl/lex/sksl.lex" ]
outputs = [
  "$target_gen_dir/SkSLLexer.h",
  "$target_gen_dir/SkSLLexer.cpp",
]
```
- 输入文件未修改时,GN 跳过执行
- 输出文件时间戳用于依赖检查
- 避免不必要的重新生成

### 并行构建安全性

**文件冲突处理**:
- 生成的文件有唯一路径
- 不同配置使用不同的 `out` 目录
- 无竞争条件风险

## 相关文件

### SkSL 词法分析相关

**词法规则定义**:
- `src/sksl/lex/sksl.lex`: SkSL 词法规则(类 Lex/Flex 格式)

**生成的词法分析器**:
- `src/sksl/SkSLLexer.h`: 词法分析器头文件
- `src/sksl/SkSLLexer.cpp`: 词法分析器实现

**词法分析器生成工具**:
- `tools/sksllex/`: 词法分析器生成工具源码
- 类似于 Lex/Flex 但为 SkSL 定制

### SkSL 编译器组件

**语法分析**:
- `src/sksl/SkSLParser.h/cpp`: 语法分析器(使用词法分析器)

**编译器核心**:
- `src/sksl/SkSLCompiler.h/cpp`: SkSL 主编译器

**中间表示**:
- `src/sksl/ir/`: SkSL 中间表示 (IR) 类

### 代码格式化

**clang-format 配置**:
- `.clang-format`: Skia 的代码风格配置文件

**格式化脚本**:
- `tools/git-sync-deps`: 同步依赖工具

### 构建配置

**GN 文件**:
- `BUILD.gn`: 包含 `run_sksllex` action 的定义
- `gn/sksl.gni`: SkSL 构建模板

### 类似工具

**SkSL 语法分析器生成**:
- 可能有类似的 parser 生成脚本(如果使用 Bison/YACC)

**其他代码生成工具**:
- `tools/skslc`: SkSL 编译器命令行工具
- 用于离线编译着色器

该脚本通过自动化词法分析器生成和格式化流程,确保 SkSL 编译器始终使用最新的词法规则,同时保持代码风格的一致性,是 Skia 着色器系统构建流程中不可或缺的组件。
