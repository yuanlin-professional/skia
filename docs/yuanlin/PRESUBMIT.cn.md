# PRESUBMIT.py

> 源文件: PRESUBMIT.py

## 概述

PRESUBMIT.py 是 Skia 项目的顶层预提交检查脚本,实现了代码提交前的自动化质量检查系统。该脚本定义了一系列检查规则,在代码上传或提交到版本控制系统之前自动执行,确保代码符合项目的编码规范、构建要求和文档要求。

脚本包含 20+ 个不同的检查函数,覆盖代码格式、版权信息、构建文件同步、API 文档、依赖管理等多个方面。通过集成 depot_tools 的预提交框架,该脚本为 Skia 项目提供了强大的代码质量保障机制,防止常见错误和不规范的代码进入代码库。

## 架构位置

PRESUBMIT.py 位于 Skia 项目的根目录,是代码审查流程的第一道防线:

- **位置**: 项目根目录
- **触发时机**: git cl upload(上传代码审查)和提交前
- **集成**: 与 Gerrit 代码审查系统和 depot_tools 工具链集成
- **作用范围**: 覆盖整个 Skia 代码库的所有文件类型

该脚本是自动化质量保证系统的核心,与 CI/CD 流程、构建系统和文档生成工具紧密配合。

## 主要类与结构体

### CodeReview

代码审查抽象类,封装与代码审查系统(Gerrit)的交互。

**构造函数**:
- `__init__(self, input_api)`: 初始化,从 input_api 获取变更信息和 Gerrit 接口

**方法**:

- `GetOwnerEmail()`: 获取变更所有者的邮箱地址
- `GetSubject()`: 获取变更的标题
- `GetDescription()`: 获取变更的完整描述
- `GetReviewers()`: 获取所有审查者的邮箱列表
- `GetApprovers()`: 获取已批准(+1)的审查者邮箱列表

该类提供了统一的接口来访问代码审查信息,屏蔽了底层 Gerrit API 的复杂性。

### _WarningsAsErrors

上下文管理器,将警告临时转换为错误。

**方法**:

- `__init__(self, output_api)`: 保存 output_api 引用
- `__enter__(self)`: 保存原始警告函数,替换为错误函数
- `__exit__(self, ex_type, ex_value, ex_traceback)`: 恢复原始警告函数

这个上下文管理器用于在特定检查中强制将警告视为错误,提高代码质量标准。使用方式:

```python
with _WarningsAsErrors(output_api):
    results.extend(input_api.canned_checks.CheckChangeHasNoCR(...))
```

## 公共 API 函数

### 核心检查函数

#### CheckChangeOnUpload(input_api, output_api)

代码上传时执行的检查函数,是 depot_tools 预提交框架调用的标准入口点。

**执行的检查**:
- 所有通用检查(通过 _CommonChecks)
- 基础设施测试(_InfraTests)
- 发布说明检查(_CheckTopReleaseNotesChanged, _CheckReleaseNotesForPublicAPI)
- Buildifier 检查(_CheckBuildifier)
- DEPS 文件检查(_CheckDEPS)
- Bazel BUILD 文件生成检查(_CheckGeneratedBazelBUILDFiles)
- GNI 文件生成检查(_CheckGNIGenerated)

#### CheckChangeOnCommit(input_api, output_api)

代码提交时执行的检查函数。

**执行的检查**:
- 所有通用检查(通过 _CommonChecks)
- DO NOT SUBMIT 检查

#### PostUploadHook(gerrit, change, output_api)

代码上传后执行的钩子函数,用于自动修改变更描述。

**功能**:
- 为纯文档变更自动添加 'No-Try: true' 标签
- 跳过服务账户的自动修改(避免影响 CQ+2 投票)

### 文件格式检查

#### _CheckChangeHasEol(input_api, output_api, source_file_filter=None)

检查文件是否以换行符结尾。

**返回**: 如果文件不以 '\n' 结尾,返回警告列表

#### _JsonChecks(input_api, output_api)

验证 JSON 文件的格式正确性。

**检查范围**:
- 所有 .json 文件
- site/ 目录下的 METADATA 文件

#### _IfDefChecks(input_api, output_api)

确保 #if/#ifdef 不在 #include 之前(参见 skbug/3362)。

**检查逻辑**: 跳过注释和空行后,第一个真实行不应该是 #if 或 #ifdef(允许 #if 0)

#### _CopyrightChecks(input_api, output_api, source_file_filter=None)

验证版权信息的正确性。

**检查规则**:
- 版权信息格式: "Copyright (C) YYYY-YYYY 组织名"
- 新文件应使用 "Google LLC" 而不是 "Google Inc"
- 排除 third_party/, tests/sksl/, bazel/rbe/ 等目录

#### _CheckGNFormatted(input_api, output_api)

确保 .gn 和 .gni 文件已正确格式化。

**执行步骤**:
1. 运行 bin/fetch-gn 获取 gn 工具
2. 对每个 .gn/.gni 文件运行 `gn format --dry-run`
3. 如果格式不正确,建议运行 `bin/gn format <file>`

#### _CheckIncludesFormatted(input_api, output_api)

检查 #include 语句是否已格式化。

**工具**: tools/rewrite_includes.py --dry-run

#### _CheckGitConflictMarkers(input_api, output_api)

检测 Git 冲突标记。

**检测模式**: `^(?:<<<<<<<|>>>>>>>) |^=======$`
**例外**: .md 文件(一级标题可能看起来像冲突标记)

### 代码质量检查

#### _CheckBannedAPIs(input_api, output_api)

检查源代码中是否使用了禁止的 API、包和符号。

**禁止的 API 示例**:

1. **抛出异常的函数**: std::stof, std::stod, std::stold(应使用 std::strtof 等)
2. **多线程标准库**: std::mutex(使用 SkMutex), std::thread(除测试外), std::future 等
3. **已废弃的宏**: GR_TEST_UTILS, GRAPHITE_TEST_UTILS(使用 GPU_TEST_UTILS)
4. **原始字符串字面量**: R"(...)"(在非测试代码中,使用字符串自动连接)
5. **条件编译**: #if SK_GANESH(应使用 #if defined(SK_GANESH))

**文件类型**: .h, .cpp, .cc, .m, .mm

#### _CheckIncludeForOutsideDeps(input_api, output_api)

确保 include/ 目录只依赖其他 include/ 文件。

**目的**: 保持公共 API 的自包含性,防止客户端意外访问私有实现

**禁止模式**:
- `#include "src/..."`
- `#include "tools/..."`

#### _CheckExamplesForPrivateAPIs(input_api, output_api)

确保 docs/examples/ 中的示例代码只使用公共 API。

**禁止模式**:
- `#include "src/..."`
- `#include "include/private/..."`

### 构建系统检查

#### _CheckBazelBUILDFiles(input_api, output_api)

确保 BUILD.bazel 文件符合 G3(Google 内部构建系统)要求。

**检查规则**:
1. 必须包含 `licenses(["notice"])`
2. 必须使用 `skia_cc_library` 而不是原生 `cc_library`
3. 必须包含 `package(default_applicable_licenses = ["//:license"])`

**排除路径**: infra/, bazel/rbe/, experimental/, third_party/ 等

#### _CheckGeneratedBazelBUILDFiles(input_api, output_api)

验证生成的 Bazel BUILD 文件是最新的。

**执行**: `make -C bazel generate_go`
**平台限制**: 跳过 Windows 和 macOS

#### _CheckGNIGenerated(input_api, output_api)

确保从 Bazel 生成的 .gni 文件是最新的。

**执行**: `make -C bazel generate_gni`
**触发条件**: BUILD.bazel 或 .gni 文件被修改

#### _CheckBuildifier(input_api, output_api)

运行 Buildifier 对 Bazel 文件进行 lint 和格式化。

**命令**: `buildifier --mode=fix --lint=fix --warnings -native-android,-native-cc,-native-py`
**检查文件**: BUILD.bazel, *.bzl(排除 public.bzl, bazel/rbe/, third_party/externals/, node_modules/)

#### _CheckDEPS(input_api, output_api)

当 DEPS 文件修改时,更新 bazel/deps.json。

**执行**: `bazelisk run //bazel/deps_parser`

### 发布说明检查

#### _CheckReleaseNotesForPublicAPI(input_api, output_api)

检查公共 API 变更是否伴随发布说明。

**逻辑**:
- 如果修改了 include/ 下的 .h 文件(非 private)
- 但没有在 relnotes/ 目录添加或修改文件
- 则发出警告

#### _CheckTopReleaseNotesChanged(input_api, output_api)

警告不要直接编辑顶层 RELEASE_NOTES.md。

**原因**: 该文件由工具自动生成,应该在 relnotes/ 目录添加单独的说明文件

### 其他检查

#### _InfraTests(input_api, output_api)

运行基础设施相关的测试。

**条件**: infra/ 目录下有文件变更
**命令**: `python3 infra/bots/infra_tests.py`

#### _RegenerateAllExamplesCPP(input_api, output_api)

当添加或删除示例时,重新生成 all_examples.cpp。

**条件**: docs/examples/ 目录下有文件变更
**命令**: `python3 tools/fiddle/make_all_examples_cpp.py --print-diff`

### 工具函数

#### np(path)

规范化路径,将所有路径分隔符转换为正斜杠。

**用途**: 在跨平台代码中统一路径格式

#### _RunCommandAndCheckDiff(output_api, command, files_to_check)

运行命令并检查是否产生文件差异。

**流程**:
1. 保存文件的当前内容
2. 执行命令
3. 比较执行后的文件内容
4. 如果有差异,返回错误,要求提交或丢弃更改

**用途**: 验证代码生成工具、格式化工具等的输出是否与仓库一致

## 内部实现细节

### 常量定义

```python
RELEASE_NOTES_DIR = 'relnotes'
RELEASE_NOTES_FILE_NAME = 'RELEASE_NOTES.md'
RELEASE_NOTES_README = '//relnotes/README.md'
GOLD_TRYBOT_URL = 'https://gold.skia.org/search?issue='
SERVICE_ACCOUNT_SUFFIX = ['@...iam.gserviceaccount.com']
USE_PYTHON3 = True
```

### 服务账户检测

PostUploadHook 跳过服务账户,防止自动修改影响 CQ 投票:

```python
for suffix in SERVICE_ACCOUNT_SUFFIX:
    if change.author_email.endswith(suffix):
        return []
```

支持的服务账户域名包括 skia-buildbots、skia-swarming-bots、skia-public、skia-corp 和 chops-service-accounts。

### 差异生成

使用 Python 标准库的 difflib 生成统一差异格式:

```python
diff = difflib.unified_diff(prev_content, new_content, path, path, lineterm='')
```

### 错误收集模式

大多数检查函数遵循相同的模式:

1. 初始化空的 results 列表
2. 遍历受影响的文件
3. 对每个文件执行检查
4. 将违规添加到 results
5. 返回 results 列表

这种模式允许一次性报告所有错误,而不是在第一个错误处停止。

## 依赖关系

### 标准库依赖

- **difflib**: 生成文件差异
- **os**, **os.path**: 文件系统操作
- **re**: 正则表达式匹配
- **subprocess**: 执行外部命令
- **sys**: 系统信息和平台检测

### 外部工具依赖

- **gn**: GN 构建系统工具
- **bazelisk**: Bazel 构建工具的包装器
- **buildifier**: Bazel 文件格式化和 lint 工具
- **python3**: Python 3 解释器

### 项目内依赖

- **tools/rewrite_includes.py**: Include 语句格式化工具
- **tools/fiddle/make_all_examples_cpp.py**: 示例代码生成工具
- **infra/bots/infra_tests.py**: 基础设施测试
- **bazel/deps_parser**: 依赖解析工具
- **bin/fetch-gn**: GN 工具下载脚本

### 集成依赖

- **depot_tools**: Google 的代码审查工具链
- **Gerrit**: 代码审查系统

## 设计模式与设计决策

### 检查函数标准接口

所有检查函数遵循统一的签名:

```python
def _CheckXXX(input_api, output_api) -> List[PresubmitResult]
```

这种一致性使得添加新检查变得简单,只需实现函数并在 _CommonChecks 或 CheckChangeOnUpload 中调用。

### 延迟执行

检查只在相关文件变更时执行。例如:

```python
if not any(f.LocalPath().startswith('infra') for f in input_api.AffectedFiles()):
    return results  # 跳过 infra 测试
```

这种条件执行显著提高了性能,避免不必要的检查。

### 上下文管理器模式

_WarningsAsErrors 使用上下文管理器模式临时修改行为:

```python
with _WarningsAsErrors(output_api):
    # 在这个块中,警告被视为错误
```

这种模式保证了修改会被正确恢复,即使发生异常。

### 策略模式

错误格式化使用策略模式,允许自定义错误报告格式:

```python
error_formatter=_ReportErrorFileAndLine  # 默认策略
```

### 命令执行封装

_RunCommandAndCheckDiff 封装了"运行命令并检查差异"的通用模式,避免代码重复。

### 平台感知

许多检查考虑平台差异:

```python
if 'win32' in sys.platform:
    return []  # Windows 不支持
if 'darwin' in sys.platform:
    return []  # macOS 太慢,跳过
```

### 白名单/黑名单模式

多个检查使用例外列表,如 _CheckBannedAPIs 允许某些文件使用特定 API:

```python
(r'std::thread', '', ['^tests/', 'SkExecutor'])  # 测试和 SkExecutor 可以使用
```

### 提前返回

检查函数在无相关变更时提前返回空列表,避免不必要的处理。

## 性能考量

### 条件执行

只在必要时运行检查:
- _InfraTests 仅在 infra/ 变更时运行
- _CheckGNFormatted 仅在 .gn/.gni 变更时运行
- _CheckDEPS 仅在 DEPS 或 deps.json 变更时运行

### 工具可用性检查

在执行昂贵操作前检查工具是否可用:

```python
try:
    subprocess.check_output(['buildifier', '--version'], ...)
except:
    return [output_api.PresubmitNotifyResult('工具不可用,跳过检查')]
```

### 平台跳过

在不支持或太慢的平台上跳过特定检查:
- Windows: 跳过 Bazel 相关检查
- macOS: 跳过耗时的生成检查(由于沙箱开销)

### 批量处理

文件过滤一次性完成,避免多次遍历:

```python
files = [f for f in input_api.AffectedFiles() if condition(f)]
if not files:
    return []
```

### 两阶段检查

某些检查(如 _FindNewViolationsOfRule)先检查整个文件,只在发现问题时才检查具体行,减少 SCM 操作。

## 相关文件

### 测试文件

- **PRESUBMIT_test.py**: 单元测试
- **PRESUBMIT_test_mocks.py**: 测试模拟类

### 配置文件

- **DEPS**: 项目依赖定义
- **BUILD.bazel**: Bazel 构建文件
- **.gn**, **.gni**: GN 构建文件
- **bazel/deps.json**: Bazel 依赖 JSON

### 文档文件

- **RELEASE_NOTES.md**: 发布说明(自动生成)
- **relnotes/**: 单个发布说明目录
- **relnotes/README.md**: 发布说明指南

### 工具脚本

- **tools/rewrite_includes.py**: Include 格式化
- **tools/fiddle/make_all_examples_cpp.py**: 示例代码生成
- **infra/bots/infra_tests.py**: 基础设施测试
- **bazel/deps_parser**: DEPS 解析工具
- **bin/fetch-gn**: GN 下载脚本

### 目录

- **include/**: 公共 API 头文件
- **src/**: 私有实现
- **docs/examples/**: 示例代码(fiddles)
- **infra/**: CI/CD 基础设施
- **bazel/**: Bazel 构建配置

该预提交脚本是 Skia 项目质量保证的基石,通过自动化检查确保代码库的一致性、正确性和可维护性。它的设计充分考虑了性能、可扩展性和开发者体验,是大型开源项目预提交系统的优秀范例。
