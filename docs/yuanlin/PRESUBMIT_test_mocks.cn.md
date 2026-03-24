# PRESUBMIT_test_mocks.py

> 源文件: PRESUBMIT_test_mocks.py

## 概述

PRESUBMIT_test_mocks.py 是一个用于预提交测试的模拟框架模块,源自 Chromium 项目。该文件提供了一套完整的模拟类,用于在单元测试环境中模拟 Skia 预提交系统的输入和输出接口。这些模拟类使得开发者能够在不依赖实际版本控制系统和文件系统的情况下测试预提交检查逻辑。

模块包含了模拟文件、模拟变更、模拟输入 API 和模拟输出 API 等核心组件,完整地复制了预提交系统的接口,使得测试可以在隔离、可控的环境中运行。这对于保证预提交检查的正确性至关重要,因为这些检查直接影响代码质量和提交流程。

## 架构位置

该文件位于 Skia 项目根目录,是预提交测试基础设施的核心组件:

- **位置**: 项目根目录
- **角色**: 测试工具库
- **用途**: 为 PRESUBMIT_test.py 和其他预提交相关测试提供模拟对象
- **继承关系**: 代码来自 Chromium 项目,被 Skia 项目采用

该模块不直接参与生产代码的执行,仅在测试阶段使用。

## 主要类与结构体

### MockCannedChecks

模拟预定义检查类,提供通用的代码检查功能。

**主要方法**:

- `_FindNewViolationsOfRule(callable_rule, input_api, source_file_filter=None, error_formatter=_ReportErrorFileAndLine)`: 查找新引入的违规行为

该方法接受一个可调用的规则函数,对每个受影响的文件执行检查,返回违规列表。它实现了两遍扫描策略:首先检查整个文件,如果发现问题再检查具体的变更行,这种优化策略在大多数文件没有问题时能显著提高性能。

### MockInputApi

模拟输入 API 类,提供文件访问和系统信息。

**核心属性**:

- `canned_checks`: MockCannedChecks 实例
- `fnmatch`, `json`, `re`: 标准库模块引用
- `os_path`, `platform`, `subprocess`, `sys`: 系统模块引用
- `python_executable`, `python3_executable`: Python 解释器路径
- `files`: 受影响文件的列表
- `is_committing`: 是否正在提交的标志
- `change`: MockChange 实例
- `presubmit_local_path`: 预提交脚本所在路径
- `is_windows`: 是否为 Windows 平台
- `no_diffs`: 是否禁用差异的标志
- `verbose`: 详细输出标志

**主要方法**:

- `CreateMockFileInPath(f_list)`: 模拟文件存在性检查
- `AffectedFiles(file_filter=None, include_deletes=True)`: 获取受影响的文件
- `RightHandSideLines(source_file_filter=None)`: 获取变更后的代码行
- `AffectedSourceFiles(file_filter=None)`: 获取受影响的源文件
- `FilterSourceFile(file, files_to_check=(), files_to_skip=())`: 过滤源文件
- `LocalPaths()`: 获取文件的本地路径列表
- `PresubmitLocalPath()`: 获取预提交脚本路径
- `ReadFile(filename, mode='r')`: 读取文件内容

### MockOutputApi

模拟输出 API 类,提供结果输出功能。

**内部类**:

- `PresubmitResult`: 基础结果类
  - `message`: 结果消息
  - `items`: 相关项目列表
  - `long_text`: 详细文本

- `PresubmitError`: 错误结果(继承自 PresubmitResult)
  - `type`: 'error'

- `PresubmitPromptWarning`: 警告结果(继承自 PresubmitResult)
  - `type`: 'warning'

- `PresubmitNotifyResult`: 通知结果(继承自 PresubmitResult)
  - `type`: 'notify'

- `PresubmitPromptOrNotify`: 提示或通知结果(继承自 PresubmitResult)
  - `type`: 'promptOrNotify'

**属性**:

- `more_cc`: 额外的抄送人员列表

**方法**:

- `AppendCC(more_cc)`: 添加抄送人员

### MockFile

模拟文件类,表示版本控制中的文件。

**构造参数**:

- `local_path`: 文件的本地路径
- `new_contents`: 文件的新内容(字符串列表)
- `old_contents`: 文件的旧内容(可选)
- `action`: 文件操作类型(默认 'A' 表示添加)
- `scm_diff`: 源代码管理差异(可选)

**主要方法**:

- `Action()`: 返回文件操作类型
- `ChangedContents()`: 返回变更的内容(行号,内容)元组列表
- `NewContents(flush_cache=False)`: 返回文件的新内容
- `LocalPath()`: 返回本地路径
- `AbsoluteLocalPath()`: 返回绝对路径
- `GenerateScmDiff()`: 生成源代码管理差异
- `OldContents()`: 返回旧内容
- `rfind(p)`, `__getitem__(i)`, `__len__()`, `replace(altsep, sep)`: 字符串操作方法,用于支持 os.path.basename 等操作

### MockAffectedFile

继承自 MockFile,表示受变更影响的文件。重写了 `AbsoluteLocalPath()` 方法以返回本地路径。

### MockChange

模拟变更类,表示一个代码变更集。

**构造参数**:

- `changed_files`: 变更的文件列表

**属性**:

- `author_email`: 作者邮箱
- `footers`: 提交信息脚注字典(使用 defaultdict)

**方法**:

- `LocalPaths()`: 返回变更文件的路径列表
- `AffectedFiles(include_dirs=False, include_deletes=True, file_filter=None)`: 返回受影响的文件
- `GitFootersFromDescription()`: 从描述中提取 Git 脚注

## 公共 API 函数

### _ReportErrorFileAndLine(filename, line_num, dummy_line)

默认的错误格式化函数。

**参数**:
- `filename`: 文件名
- `line_num`: 行号
- `dummy_line`: 行内容(未使用)

**返回**: 格式化的错误字符串 'filename:line_num'

该函数是 `_FindNewViolationsOfRule` 的默认错误格式化器,可以被自定义函数替换以产生不同格式的错误报告。

## 内部实现细节

### 两遍扫描优化

`_FindNewViolationsOfRule` 方法实现了一个重要的性能优化:

1. **第一遍**: 检查文件的完整内容
2. **第二遍**: 只有在第一遍发现问题时,才调用 SCM(源代码管理)获取变更区域并逐行检查

这种设计假设大多数文件都不会有问题,从而避免了昂贵的 SCM 操作。在 Windows 平台上,SCM 操作特别耗时,这个优化尤为重要。

### 文件内容缓存

MockFile 类自动生成 SCM 差异信息:

```python
self._scm_diff = (
    "--- /dev/null\n+++ %s\n@@ -0,0 +1,%d @@\n" %
    (local_path, len(new_contents)))
for l in new_contents:
    self._scm_diff += "+%s\n" % l
```

这个实现模拟了 Git 的统一差异格式,使得测试可以验证处理 SCM 差异的代码。

### 字符串接口实现

MockFile 实现了多个字符串特殊方法(`__getitem__`, `__len__`, `rfind`, `replace`),这是因为 Python 的 `os.path.basename` 和其他路径处理函数需要这些方法。这种设计允许 MockFile 对象在需要字符串路径的地方无缝使用。

### 文件过滤逻辑

`FilterSourceFile` 方法实现了灵活的文件过滤机制:

1. 首先检查文件是否匹配 `files_to_check` 模式
2. 然后检查文件是否匹配 `files_to_skip` 模式
3. 使用正则表达式进行模式匹配

这种两阶段过滤允许精确控制哪些文件应该被检查。

### Footers 字典

MockChange 使用 `defaultdict(list)` 来存储提交信息脚注,这允许多个相同键的脚注(如多个 "Bug: " 条目)被存储为列表。

## 依赖关系

### 标准库依赖

- **collections.defaultdict**: 用于实现 footers 字典
- **fnmatch**: 文件名模式匹配
- **json**: JSON 解析和生成
- **os**, **os.path**: 文件系统操作
- **re**: 正则表达式
- **subprocess**: 进程执行
- **sys**: 系统信息和配置

### 被依赖关系

- **PRESUBMIT_test.py**: 主要使用者,用于测试预提交检查
- 任何需要测试预提交功能的其他测试文件

## 设计模式与设计决策

### 鸭子类型(Duck Typing)

模拟类不需要继承真实的预提交 API 类,只需要实现相同的接口。这种设计遵循 Python 的鸭子类型原则:"如果它走起来像鸭子,叫起来像鸭子,那它就是鸭子。"

### 组合优于继承

MockInputApi 通过组合包含 MockCannedChecks 实例,而不是继承。这提供了更大的灵活性,允许独立修改各个组件。

### 惰性求值

模拟类只在需要时生成数据。例如,SCM 差异只在构造时生成一次,后续调用 `GenerateScmDiff()` 直接返回缓存的结果。

### 接口隔离

不同的模拟类关注不同的职责:
- MockFile 处理文件内容和差异
- MockInputApi 提供输入数据和工具
- MockOutputApi 收集输出结果
- MockChange 表示整个变更集

这种分离使得测试可以只关注需要的部分。

### 配置灵活性

MockInputApi 从命令行参数读取 verbose 标志(`'--verbose' in sys.argv`),这使得测试可以通过命令行控制输出详细程度,而无需修改测试代码。

### 默认值策略

许多方法提供合理的默认值:
- `file_filter=None`: 不过滤
- `include_deletes=True`: 包含删除的文件
- `action='A'`: 默认为添加操作

这简化了测试代码的编写。

## 性能考量

### 避免实际 I/O

所有文件操作都在内存中完成,没有实际的磁盘 I/O。这使得测试可以快速运行,通常在毫秒级完成。

### 两遍扫描优化

如前所述,`_FindNewViolationsOfRule` 的两遍扫描策略显著减少了需要检查的代码量,特别是在大型变更集中。

### 预生成差异

SCM 差异在 MockFile 构造时生成并缓存,避免了重复生成的开销。

### 轻量级对象

模拟对象只包含测试所需的最少数据,避免了真实预提交系统中可能存在的大量元数据。

## 相关文件

- **PRESUBMIT.py**: 实际的预提交检查脚本,定义了所有检查规则
- **PRESUBMIT_test.py**: 使用这些模拟类的测试脚本
- **DEPS**: 项目依赖文件,可能被预提交检查验证
- **RELEASE_NOTES.md**: 发布说明文件,被某些预提交检查验证
- **relnotes/**: 单个发布说明目录
- **.git/**: Git 版本控制目录(真实系统中)

该模块是 Skia 项目测试基础设施的关键组成部分,提供了一个可靠、快速、灵活的测试环境,使得预提交检查的开发和维护变得简单和安全。通过这些模拟类,开发者可以快速迭代预提交规则,而无需担心影响实际的代码库或版本控制系统。
