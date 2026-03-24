# CommandLineFlags - 命令行参数解析框架

> 源文件:
> - [tools/flags/CommandLineFlags.h](../../../tools/flags/CommandLineFlags.h)
> - [tools/flags/CommandLineFlags.cpp](../../../tools/flags/CommandLineFlags.cpp)

## 概述

CommandLineFlags 是 Skia 的命令行参数解析框架，灵感来自 Google gflags。它通过 `DEFINE_bool`、`DEFINE_string`、`DEFINE_int`、`DEFINE_double` 宏在全局命名空间中声明标志变量，然后在 `main` 函数中调用 `Parse()` 解析命令行参数。支持长名称（`--name`）、短名称（`-n`）、布尔否定（`--noname`）以及多值字符串数组。

## 架构位置

位于 `tools/flags/` 目录下，是所有 Skia 工具程序（DM、nanobench、viewer、fiddle 等）的基础命令行解析组件。其他 `CommonFlags*.h/cpp` 文件在此基础上定义具体的标志组。

## 主要类与结构体

### `CommandLineFlags`
静态工具类，管理全局标志链表和命令行解析。
- `gHead` - 全局标志链表头指针
- `gUsage` - 使用说明字符串

### `CommandLineFlags::StringArray`
字符串数组标志值容器，提供只读访问。
- 支持 `operator[]`、`size()`、`isEmpty()`、`contains()`
- `parseAndValidate()` 模板方法验证值在合法集合中

### `SkFlagInfo`
单个标志的元数据和值存储。
- 支持 4 种类型：`kBool_FlagType`、`kString_FlagType`、`kInt_FlagType`、`kDouble_FlagType`
- 通过链表串联所有注册的标志
- 提供 `match()` 方法匹配命令行字符串

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SetUsage(usage)` | 设置程序使用说明 |
| `PrintUsage()` | 打印帮助信息 |
| `Parse(argc, argv)` | 解析命令行参数（只能调用一次） |
| `ShouldSkip(strings, name)` | 基于匹配模式判断是否跳过 |

### 宏

| 宏 | 说明 |
|------|------|
| `DEFINE_bool(name, default, help)` | 定义布尔标志 |
| `DEFINE_string(name, default, help)` | 定义字符串数组标志 |
| `DEFINE_int(name, default, help)` | 定义整数标志 |
| `DEFINE_double(name, default, help)` | 定义浮点标志 |
| `DECLARE_x(name)` | 在其他文件中声明标志 |

## 内部实现细节

- **自注册机制**：DEFINE 宏创建 `SkFlagInfo` 对象，构造函数将其插入全局链表头。
- **布尔标志解析**：支持 `--name`、`--noname`、`--name=true/false/1/0/TRUE/FALSE`。
- **字符串数组**：一个标志后面的所有非 `-` 开头参数都被收集到数组中。
- **ShouldSkip 匹配规则**：`~` 表示跳过、`^` 要求匹配开头、`$` 要求匹配结尾、同时使用 `^$` 要求精确匹配。
- **短名称约束**：短名称必须为单个字符，通过断言检查。

## 依赖关系

- **Skia 基础**：SkString、SkTArray、SkTDArray、SkTHash
- **标准库**：通过 SkMacros（`SK_MACRO_STRINGIFY`）

## 设计模式与设计决策

- **自注册模式**：通过全局变量初始化时的副作用自动注册标志。
- **链表管理**：使用侵入式链表避免额外容器。
- **类型安全宏**：每种类型有专用的 DEFINE/DECLARE 宏和对应的全局变量类型。
- **gflags 兼容性**：使用 `FLAGS_name` 命名约定和类似的命令行语法。

## 性能考量

- 标志查找是线性链表遍历，但仅在 `Parse()` 中使用一次。
- StringArray 使用 TArray 存储，支持高效追加。
- `ShouldSkip` 的匹配逻辑对每个名称遍历所有模式，适合配置时使用。

## 相关文件

- `tools/flags/CommonFlagsConfig.h` - 渲染配置标志
- `tools/flags/CommonFlagsGanesh.h` - Ganesh GPU 标志
- `tools/flags/CommonFlagsGraphite.h` - Graphite 标志
- `dm/DM.cpp` - 主要使用者
