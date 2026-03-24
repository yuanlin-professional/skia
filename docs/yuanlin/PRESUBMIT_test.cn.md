# PRESUBMIT_test.py

> 源文件: PRESUBMIT_test.py

## 概述

PRESUBMIT_test.py 是 Skia 项目中用于测试预提交检查脚本(PRESUBMIT.py)的单元测试模块。该文件包含了针对发布说明检查和命令执行检查的测试用例,确保预提交钩子能够正确地验证代码变更,特别是针对公共 API 变更和发布说明文件的编辑。

该测试模块使用 Python 的 unittest 框架,通过模拟输入和输出 API 来验证 PRESUBMIT.py 中定义的各种检查函数的行为。测试覆盖了发布说明编辑警告、公共 API 变更检测以及命令执行后的文件差异检测等关键功能。

## 架构位置

本文件位于 Skia 项目的根目录,与 PRESUBMIT.py 和 PRESUBMIT_test_mocks.py 处于同一层级。它是代码审查和提交流程的重要组成部分:

- **根目录**: 与构建脚本、配置文件和主要的预提交脚本一起存放
- **测试基础设施**: 属于项目的质量保证系统
- **预提交系统**: 在代码提交到版本控制系统之前执行自动化检查

该文件依赖于 PRESUBMIT 模块和 PRESUBMIT_test_mocks 模块提供的功能。

## 主要类与结构体

### ReleaseNotesTest

用于测试发布说明相关检查的测试类。

**主要测试方法**:

- `testNoEditTopReleaseNotesNoWarning()`: 验证当没有编辑顶层发布说明文件时不产生警告
- `testUpdateTopReleaseNotesIssuesWarning()`: 验证直接编辑 RELEASE_NOTES.md 时会产生警告
- `testUpdateTopReleaseNotesNoWarning()`: 验证同时编辑发布说明和删除单个说明文件时不产生警告
- `testUpdatePublicHeaderAndNoReleaseNoteGeneratesWarning()`: 验证修改公共头文件但没有添加发布说明时产生警告
- `testUpdatePublicHeaderAndReleaseNoteGeneratesNoWarning()`: 验证修改公共头文件并添加发布说明时不产生警告

### RunCommandAndCheckDiffTest

用于测试命令执行和差异检查功能的测试类。

**主要测试方法**:

- `setUp()`: 初始化测试环境,创建模拟文件对象
- `setContents(file, contents)`: 辅助方法,用于设置文件的新内容
- `testNoChangesReturnsNoResults()`: 验证无变更时返回空结果
- `testChangingIrrelevantFilesReturnsNoResults()`: 验证修改不相关文件时返回空结果
- `testChangingRelevantFilesReturnsDiff()`: 验证修改相关文件时返回差异信息

**成员变量**:

- `foo_file`: 模拟的 foo.txt 文件对象
- `bar_file`: 模拟的 bar.txt 文件对象
- `mock_input_api`: 模拟的输入 API 对象
- `mock_output_api`: 模拟的输出 API 对象

## 公共 API 函数

本文件主要包含测试类,不提供公共 API 函数供外部调用,而是测试 PRESUBMIT.py 中的以下函数:

### 被测试的函数

1. **PRESUBMIT._CheckTopReleaseNotesChanged()**
   - 检查顶层发布说明文件是否被直接修改
   - 如果修改了 RELEASE_NOTES.md 但没有同时修改 relnotes/ 目录下的文件,则发出警告

2. **PRESUBMIT._CheckReleaseNotesForPublicAPI()**
   - 检查公共 API 变更是否伴随发布说明
   - 如果修改了 include/core/ 下的头文件但没有添加发布说明,则发出警告

3. **PRESUBMIT._RunCommandAndCheckDiff()**
   - 执行指定命令并检查文件是否产生差异
   - 用于验证代码生成工具、格式化工具等是否改变了文件内容

## 内部实现细节

### 测试设置与执行流程

测试使用 unittest.mock 模块的 @mock.patch 装饰器来模拟 subprocess.check_output 函数,避免实际执行外部命令。

### 模拟对象的使用

测试大量使用 PRESUBMIT_test_mocks 模块中定义的模拟类:

- **MockFile**: 模拟文件对象,包含路径和内容
- **MockAffectedFile**: 模拟受影响的文件,支持内容修改
- **MockInputApi**: 模拟输入 API,提供文件列表和元数据
- **MockOutputApi**: 模拟输出 API,生成预提交结果对象

### 差异检测测试

`testChangingRelevantFilesReturnsDiff()` 测试验证了完整的差异输出格式:

```python
"""Diffs found after running "cmd":

--- foo.txt
+++ foo.txt
@@ -1 +1 @@
-foo
+bar

Please commit or discard the above changes."""
```

这个测试确保差异检测功能能够正确生成统一的差异格式(unified diff),并提供清晰的错误消息。

### 副作用模拟

在测试 `_RunCommandAndCheckDiff` 时,使用 side_effect 来模拟命令执行后文件内容的变化:

```python
mock_subprocess.side_effect = lambda *args, **kwargs: self.setContents(self.foo_file, ['bar'])
```

这种技术允许测试在不实际修改文件系统的情况下验证差异检测逻辑。

## 依赖关系

### 直接依赖

- **unittest**: Python 标准库,提供测试框架
- **unittest.mock**: 提供 mock 功能,用于模拟外部依赖
- **PRESUBMIT**: 被测试的主模块
- **PRESUBMIT_test_mocks**: 提供测试用的模拟类和函数

### 测试覆盖的依赖

间接测试了以下模块的交互:

- **subprocess**: 命令执行模块
- **difflib**: 用于生成文件差异的标准库
- **os/os.path**: 文件路径处理

## 设计模式与设计决策

### 测试隔离

每个测试方法都是独立的,使用独立的模拟对象,确保测试之间不会相互影响。RunCommandAndCheckDiffTest 使用 setUp() 方法为每个测试创建新的模拟对象。

### 模拟优于实际调用

使用 @mock.patch 装饰器模拟 subprocess.check_output,避免了实际的系统调用。这提高了测试速度,减少了对外部环境的依赖,使测试更加可靠和可重复。

### 断言策略

测试使用多种断言方法:

- `assertEqual()`: 验证结果数量和具体内容
- `assertIsInstance()`: 验证返回对象的类型
- `assertTrue()`: 验证条件为真(如消息内容包含特定文本)

这种组合确保了测试既能验证正确的行为,又能捕获错误的输出类型。

### 场景覆盖

测试覆盖了多个关键场景:

1. **正常情况**: 正确操作不产生警告
2. **错误情况**: 不当操作产生适当的警告
3. **边界情况**: 同时修改多个相关文件的情况

### 命名约定

测试方法名称遵循描述性命名约定,清楚地说明了测试的内容和预期结果,例如 `testUpdateTopReleaseNotesIssuesWarning` 明确表示测试更新顶层发布说明时应该产生警告。

## 性能考量

### 模拟的性能优势

使用模拟对象而不是实际的文件系统操作和进程执行大大提高了测试速度。整个测试套件可以在毫秒级别完成,而不需要秒级的 I/O 操作。

### 测试数据最小化

测试使用最小化的模拟数据(如单行文件内容),只包含验证功能所需的必要信息,减少了内存使用和测试复杂度。

### 快速失败

测试设计为快速失败,一旦检测到不符合预期的行为就立即报告,避免不必要的后续检查。

## 相关文件

- **PRESUBMIT.py**: 主预提交检查脚本,包含所有检查函数的实现
- **PRESUBMIT_test_mocks.py**: 提供测试用的模拟类和辅助函数
- **RELEASE_NOTES.md**: 项目的发布说明文件
- **relnotes/**: 存放单个发布说明文件的目录
- **include/core/**: Skia 的公共 API 头文件目录
- **tools/rewrite_includes.py**: 用于格式化 include 语句的工具
- **bin/fetch-gn**: 获取 GN 构建工具的脚本
- **infra/bots/infra_tests.py**: 基础设施相关的测试脚本

该测试模块是 Skia 项目质量保证体系的重要组成部分,确保预提交检查功能的正确性和可靠性。通过自动化测试,开发团队可以放心地修改预提交脚本,知道任何回归都会被及时捕获。
