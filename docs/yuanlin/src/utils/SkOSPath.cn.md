# SkOSPath - 跨平台文件路径工具

> 源文件:
> - `src/utils/SkOSPath.h`
> - `src/utils/SkOSPath.cpp`

## 概述

SkOSPath 是 Skia 中用于操作文件系统路径字符串的跨平台工具类。它提供了三个核心静态函数：路径拼接 (Join)、获取文件名 (Basename) 和获取目录名 (Dirname)。该类通过编译时平台检测自动选择正确的路径分隔符（Windows 下为 `\`，其他平台为 `/`）。

## 架构位置

```
Skia 基础设施
├── 平台抽象层
│   ├── SkOSPath (本模块 - 路径字符串操作)
│   ├── SkOSFile (文件 I/O)
│   └── 其他平台工具
├── 测试框架 (tools/, tests/)
└── 资源加载 (resources/)
```

SkOSPath 是一个基础工具类，主要被测试框架、资源加载器和工具程序使用。

## 主要类与结构体

### `SkOSPath`
- 纯静态类，所有成员均为 `static`。
- **常量**: `SEPARATOR` - 平台特定的路径分隔符 (`'/'` 或 `'\\'`)。

## 公共 API 函数

### `Join`
```cpp
static SkString Join(const char* rootPath, const char* relativePath);
```
- **功能**: 将根路径和相对路径拼接为完整路径，自动在两者之间添加分隔符。
- **特殊情况**: 如果 `rootPath` 已以分隔符结尾或为空字符串，则不重复添加分隔符。
- **返回值**: 拼接后的 SkString。

### `Basename`
```cpp
static SkString Basename(const char* fullPath);
```
- **功能**: 提取路径中的文件名部分（最后一个分隔符之后的内容）。
- **行为**: 类似 Python 的 `os.path.basename()`。如果路径以分隔符结尾（如 `/dir/subdir/`），返回空字符串。
- **空值处理**: 如果输入为 nullptr，返回空 SkString。

### `Dirname`
```cpp
static SkString Dirname(const char* fullPath);
```
- **功能**: 提取路径中的目录部分（最后一个分隔符之前的内容）。
- **行为**: 类似 Python 的 `os.path.dirname()`。如果路径以分隔符结尾，返回完整路径。
- **特殊情况**: 如果路径以根分隔符开头（如 `/file`），返回 `/`。
- **空值处理**: 如果输入为 nullptr 或不含分隔符，返回空 SkString。

## 内部实现细节

- **分隔符检测**: 使用 `strrchr()` 从右向左查找最后一个分隔符位置。
- **Join 实现**: 检查 `rootPath` 是否已以 `SEPARATOR` 结尾（通过 `SkString::endsWith()`），仅在需要时追加分隔符。
- **Dirname 边界处理**: 当分隔符位于字符串起始位置时（如路径 `/file`），返回包含分隔符的目录名 `/`。

## 依赖关系

- `include/core/SkString.h`: Skia 字符串类，用于返回值和字符串操作。
- `include/core/SkTypes.h`: Skia 基础类型和断言宏 (`SkASSERT`)。
- `<string.h>`: 标准 C 字符串函数 (`strrchr`)。

## 设计模式与设计决策

1. **编译时平台适配**: 通过 `#ifdef _WIN32` 在编译时选择分隔符，避免运行时开销。

2. **纯静态接口**: 类仅包含静态方法，无需实例化，使用简洁。

3. **Python 行为对齐**: `Basename` 和 `Dirname` 的语义明确对标 Python 的 `os.path` 模块，降低使用者的学习成本。

4. **安全的空值处理**: 所有函数都能安全处理 nullptr 输入，返回空字符串而非崩溃。

## 性能考量

该模块的函数都是简单的字符串操作，开销极小。`strrchr` 是 O(n) 的线性扫描，对于典型路径长度而言开销可以忽略。

## 相关文件

- `include/core/SkString.h`: Skia 字符串类。
- `tools/Resources.h`: 测试资源加载，使用 `SkOSPath::Join` 拼接资源路径。
- `tools/flags/CommandLineFlags.h`: 命令行参数处理中使用路径操作。
