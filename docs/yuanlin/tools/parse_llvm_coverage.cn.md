# parse_llvm_coverage

> 源文件
> - tools/parse_llvm_coverage.py

## 概述

parse_llvm_coverage 是一个 Python 命令行工具,用于解析 LLVM 代码覆盖率报告并生成可用的结构化数据。该工具能够将 llvm-cov 工具生成的文本格式覆盖率报告转换为 JSON 格式,并且可以生成与 nanobench 兼容的性能数据格式,以便将覆盖率数据上传到 Skia 的性能监控系统。

这个工具解决了 LLVM 覆盖率报告难以自动化处理的问题,特别是处理文件路径匹配和数据汇总的复杂性。它支持生成逐行覆盖率详情和文件级汇总统计两种输出格式。

## 架构位置

parse_llvm_coverage 位于 Skia 项目的工具目录中,是持续集成和代码质量监控流程的一部分:

```
skia/
├── tools/
│   ├── parse_llvm_coverage.py      # 本工具
│   ├── nanobench 相关工具           # 性能数据收集工具
│   └── 其他 CI/CD 工具
├── tests/                           # 测试代码
└── infra/                          # 基础设施配置
    └── bots/                       # CI 机器人配置
```

该工具在持续集成流程中的位置:
1. 运行测试并生成 LLVM 覆盖率报告
2. **parse_llvm_coverage** 解析报告生成结构化数据
3. 上传到覆盖率监控系统或性能面板

## 主要类与结构体

### 核心函数

#### _fix_filename(filename)
修复 llvm-cov 输出的文件名格式,去除路径中的冗余部分。

#### _file_in_repo(filename, all_files)
使用后缀匹配确定文件是否属于代码仓库。

#### _get_per_file_per_line_coverage(report)
从覆盖率报告中提取逐行覆盖率信息,返回字典结构。

#### _testname(filename)
将文件名转换为测试名称,替换特殊字符。

#### _nanobench_json(results, properties, key)
生成 nanobench 兼容的 JSON 格式数据。

#### _parse_key_value(kv_list)
将键值对列表转换为字典。

#### _get_per_file_summaries(line_by_line)
汇总逐行覆盖率数据,生成文件级统计。

## 公共 API 函数

### main()

主函数,处理命令行参数并执行覆盖率解析流程。

**命令行参数**:

```bash
python parse_llvm_coverage.py \
  --report <coverage_report_file> \
  [--nanobench <output_json>] \
  [--key key1 value1 key2 value2 ...] \
  [--properties prop1 value1 prop2 value2 ...] \
  [--linebyline <output_json>]
```

**参数说明**:
- `--report`: 必需,输入的 llvm-cov 覆盖率报告文件
- `--nanobench`: 可选,输出 nanobench 格式 JSON 的文件路径
- `--key`: 可选,标识 bot 的键值对(与 --nanobench 配合使用)
- `--properties`: 可选,构建属性的键值对(与 --nanobench 配合使用)
- `--linebyline`: 可选,输出逐行覆盖率 JSON 的文件路径

**输出格式**:

1. **逐行覆盖率格式** (--linebyline):
```json
{
  "path/to/file.cpp": [
    [行号, 覆盖次数, "代码内容"],
    [1, 5, "void function() {"],
    [2, null, "  // 注释行"],
    [3, 0, "  uncovered_code();"]
  ]
}
```

2. **Nanobench 格式** (--nanobench):
```json
{
  "key": {"bot": "coverage-bot"},
  "properties": {"build": "Debug"},
  "results": {
    "path_to_file_cpp": {
      "coverage": {
        "percent": 85.5,
        "lines_not_covered": 10,
        "options": {
          "fullname": "path/to/file.cpp",
          "dir": "path/to",
          "source_type": "coverage"
        }
      }
    }
  }
}
```

## 内部实现细节

### 文件路径处理

LLVM 覆盖率报告中的文件路径问题:
```
原始路径: /path/to/repo/out/dir/../../src/filename.cpp
截断后:   ...../../src/filename.cpp
```

`_fix_filename()` 的处理策略:
1. 按 `..` 分割路径
2. 取最后一部分
3. 去除前导 `./`

这种简化的路径处理方法虽然不能保证 100% 准确,但在实践中效果良好。

### 文件匹配逻辑

`_file_in_repo()` 使用后缀匹配来确定文件归属:
- 遍历仓库中所有文件
- 查找以处理后路径为后缀的文件
- 如果恰好一个匹配,返回该文件
- 如果多个匹配,输出警告并跳过
- 如果无匹配,跳过该文件

**排除规则**:
- 隐藏文件(以 `.` 开头)
- `.pyc` 编译文件
- `third_party/externals` 目录下的文件

### 覆盖率数据提取

报告解析逻辑:
1. 按行扫描报告文件
2. 使用正则 `([a-zA-Z0-9\./_-]+):` 识别文件名行
3. 解析后续行的格式: `覆盖次数|行号|代码`
4. 跳过分隔线和标题行

**覆盖次数处理**:
- 数字: 该行被执行的次数
- 空白: 不可执行行(注释、空行等),记为 `None`
- 0: 未被覆盖的可执行行

### 统计汇总

`_get_per_file_summaries()` 计算每个文件的覆盖率:
```python
覆盖率 = (已覆盖行数 / 总可执行行数) * 100.0
未覆盖行数 = 总可执行行数 - 已覆盖行数
```

只统计可执行行(`cov is not None`),忽略注释和空行。

### Nanobench 格式转换

`_nanobench_json()` 生成的数据结构:
- `key`: 标识测试环境(机器人、平台等)
- `properties`: 构建属性(配置、版本等)
- `results`: 每个文件的覆盖率数据
  - 测试名: 文件名转换(替换特殊字符)
  - 覆盖率百分比
  - 未覆盖行数
  - 元数据(完整路径、目录、类型)

## 依赖关系

### Python 标准库依赖
- `argparse`: 命令行参数解析
- `json`: JSON 数据处理
- `os`: 文件系统操作
- `re`: 正则表达式匹配
- `subprocess`: 未使用(可能为历史遗留)
- `sys`: 系统交互

### 外部工具依赖
- **llvm-cov**: 生成覆盖率报告的前置工具
- **nanobench**: 数据格式的目标系统

### 数据流

```
LLVM 测试运行
    ↓
llvm-cov 生成报告
    ↓
parse_llvm_coverage 解析
    ↓ (分支)
    ├─→ 逐行覆盖率 JSON
    └─→ Nanobench 格式 JSON
        ↓
    上传到 perf.skia.org
```

## 设计模式与设计决策

### 容错设计

**多匹配处理**:
当文件路径匹配多个仓库文件时,工具选择跳过而非猜测,并输出警告信息到 stderr。这避免了错误的数据污染结果集。

**未匹配文件**:
未匹配的文件被静默跳过,因为它们通常是外部依赖或生成文件,不属于项目源码。

### 数据格式兼容性

工具设计为与 Skia 现有基础设施兼容:
- Nanobench 格式: 允许覆盖率数据与性能数据使用相同的展示和监控系统
- JSON 输出: 易于被其他工具消费

### 文件遍历策略

`_get_per_file_per_line_coverage()` 在每次运行时遍历整个仓库:
- **优点**: 获取完整的文件列表,支持新增文件
- **缺点**: 对大型仓库可能较慢
- **优化**: 排除 `third_party/externals` 等明显的非项目目录

### Python 2 兼容性

代码使用了 Python 2 的语法:
- `print >> sys.stderr`: Python 2 风格的 stderr 输出
- `xrange`: Python 2 的 range
- `iteritems()`: Python 2 的字典迭代

这表明该工具可能需要更新以支持 Python 3。

## 性能考量

### 文件系统遍历

每次运行都进行完整的仓库遍历:
- 对于包含数千个文件的仓库,这可能需要几秒钟
- 可以考虑缓存文件列表或使用 git 命令获取文件列表来优化

### 内存使用

整个报告和结果数据都在内存中处理:
- 对于大型项目的覆盖率报告(可能几十 MB),内存占用可控
- 逐行解析避免了一次性加载所有数据到复杂结构中

### 正则表达式

使用预编译的正则表达式可以提升性能:
```python
# 当前: 每次循环都编译
m = re.match('([a-zA-Z0-9\./_-]+):', line)

# 优化: 预编译
file_pattern = re.compile('([a-zA-Z0-9\./_-]+):')
m = file_pattern.match(line)
```

### 字符串处理

使用字符串的 `split()` 而非正则来解析数据行,这是合理的性能选择:
```python
cov, linenum, code = line.split('|', 2)  # 高效
```

## 相关文件

### 工具链文件
- `tools/coverage/`: 其他覆盖率相关工具
- `tools/nanobench`: 性能基准测试工具

### 配置文件
- `infra/bots/recipe_modules/coverage/`: 覆盖率 CI 配置
- `.clang-format`: 代码格式配置(用于判断源文件)

### 输出目标
- `perf.skia.org`: 性能和覆盖率数据可视化平台

### 使用示例

典型的 CI 使用场景:
```bash
# 1. 编译带覆盖率的版本
ninja -C out/Coverage skia

# 2. 运行测试
out/Coverage/tests --coverage

# 3. 生成覆盖率报告
llvm-cov show ... > coverage.txt

# 4. 解析报告
python tools/parse_llvm_coverage.py \
  --report coverage.txt \
  --nanobench coverage.json \
  --key bot coverage-bot \
  --properties config Debug
```

parse_llvm_coverage 工具是 Skia 代码质量监控流程的重要组成部分,它将编译器生成的原始覆盖率数据转换为可操作的洞察信息,帮助开发团队识别未测试的代码区域。
