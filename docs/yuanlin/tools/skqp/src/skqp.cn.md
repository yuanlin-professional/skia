# SkQP

> 源文件: `tools/skqp/src/skqp.h`, `tools/skqp/src/skqp.cpp`

## 概述

SkQP（Skia Quality Program）是 Skia 的 Android CTS（Compatibility Test Suite）测试框架。它管理 GPU 单元测试和 SkSL 错误测试的收集、执行和报告，用于验证 Android 设备上 Skia 渲染的正确性。SkQP 根据设备的 Android API 级别（`ro.vendor.api_level`）自动筛选需要执行的测试集。

## 架构位置

```
Android CTS
  +-- SkQP 测试模块
       +-- SkQPAssetManager  (资源管理抽象)
       +-- SkQP              (测试框架核心) <-- 本文件
       +-- CtsEnforcement    (API 级别强制执行策略)
```

## 主要类与结构体

### `SkQPAssetManager`（抽象基类）
- `open(path)`: 打开资源文件
- `iterateDir(directory, extension)`: 遍历目录中特定扩展名的文件

### `SkQP`
- **用途**: 测试框架核心，管理测试生命周期
- **类型别名**: `UnitTest = const skiatest::Test*`
- **不可拷贝**: 删除了拷贝构造和赋值运算符

### `SkQP::SkSLErrorTest`
- `name`: 测试名称
- `shaderText`: SkSL 着色器源码

### `SkQP::TestResult`（私有）
- `name`: 测试名称
- `errors`: 错误消息列表

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `init(assetManager, reportDirectory)` | 初始化 Skia 和 SkQP，收集测试列表 |
| `executeTest(UnitTest)` | 执行单个 GPU 单元测试，返回错误列表 |
| `makeReport()` | 将测试结果写入报告文件 |
| `getUnitTests()` | 获取所有待执行的 GPU 单元测试列表 |
| `getSkSLErrorTests()` | 获取所有 SkSL 错误测试列表 |
| `GetUnitTestName(UnitTest)` | 获取测试名称的静态方法 |

## 内部实现细节

### API 级别确定
- **Android 平台**: 读取 `ro.vendor.api_level` 系统属性，该属性按优先级反映主板当前/初始 API 级别和产品 API 级别
- **SKQP_ENFORCE_ALL_INCLUDED_TESTS**: 定义此宏时使用 `kNextRelease`，运行所有包含的测试（用于 Android 框架测试覆盖率验证）
- **非 Android**: 默认为 0，不强制执行任何特定级别

### 测试收集
- **GPU 单元测试**: 从 `skiatest::TestRegistry` 遍历所有测试，通过 `CtsEnforcement::eval()` 筛选当前 API 级别下需要运行的测试
- **SkSL 错误测试**: 从资源目录 `sksl/errors/` 和 `sksl/runtime_errors/` 读取 `.rts` 文件，应用排除规则（如 ES3 测试在 AGSL 支持前排除）

### 测试执行
- **Ganesh 测试**: 创建 `GrContextOptions`，严格模式下禁用驱动正确性变通方案（`fDisableDriverCorrectnessWorkarounds`）
- **Graphite 测试**: 类似配置，使用 `skiatest::graphite::TestOptions`
- 通过内联 Reporter 收集失败信息

### 报告生成
写入 `unit_tests.txt`，每个测试输出名称和 PASSED/FAILED 状态，失败时附带详细错误信息。

## 依赖关系

- **Skia 核心**: `SkGraphics`, `SkStream`, `SkSurface`
- **测试框架**: `Test.h`, `TestHarness.h`, `CtsEnforcement.h`
- **Ganesh**: `GrContextOptions`, `GrDirectContext`
- **Graphite**: `TestOptions` (条件编译)
- **工具**: `Resources`, `FontToolUtils`
- **Android 系统**: `<sys/system_properties.h>` (条件编译)

## 设计模式与设计决策

1. **API 级别驱动的测试筛选**: 通过 CtsEnforcement 机制自动确定每个测试在特定 API 级别下是否运行，以及是否以严格模式运行
2. **资源管理抽象**: `SkQPAssetManager` 接口允许不同平台提供不同的资源访问方式
3. **SkSL 排除规则**: 使用正则表达式和 CtsEnforcement 对组合来排除特定测试，提供灵活的版本控制
4. **TestHarness 标识**: 通过全局 `CurrentTestHarness()` 返回 `kSkQP`，使测试代码能够识别运行环境

## 性能考量

- 测试列表在 `init()` 时一次性收集和排序，避免重复遍历
- `ToolUtils::UsePortableFontMgr()` 确保跨设备一致的字体渲染结果
- 报告仅在所有测试完成后一次性写入

## 相关文件

- `tests/Test.h` - 测试注册和类型定义
- `tests/CtsEnforcement.h` - CTS 强制执行策略
- `tests/TestHarness.h` - 测试工具标识
- `tools/Resources.h` - 资源加载工具
