# SkSLModuleDataFile — 从文件加载 SkSL 模块数据

> 源文件：[`src/sksl/SkSLModuleDataFile.cpp`](../../src/sksl/SkSLModuleDataFile.cpp)

## 概述

SkSLModuleDataFile.cpp 实现了 SkSL 编译器模块数据的文件加载机制。与默认实现（`SkSLModuleDataDefault.cpp`）将模块数据编译时嵌入不同，此实现从可执行文件所在目录中读取 SkSL 模块文件。它主要用于开发和调试场景，允许在不重新编译的情况下修改 SkSL 内置模块。

该文件仅 30 行，是模块加载系统的替代实现。

## 架构位置

```
SkSL 模块加载系统
  ├── SkSLModuleDataDefault.cpp （编译时嵌入，生产环境默认）
  └── SkSLModuleDataFile.cpp   （运行时文件加载，本文件）
        ├── 从可执行文件路径定位模块文件
        └── 使用 std::ifstream 读取
```

在构建系统中，通过链接不同的 `.cpp` 文件来选择使用哪种模块加载策略。

## 主要类与结构体

本文件不定义类或结构体，仅实现一个函数。

## 公共 API 函数

```cpp
std::string GetModuleData(ModuleType name, const char* filename);
```
- 根据文件名从磁盘加载 SkSL 模块源代码
- `name` 参数（`ModuleType`）在此实现中被忽略
- `filename` 参数用于定位模块文件
- 文件路径：可执行文件所在目录 + `filename`
- 如果读取失败，调用 `SK_ABORT` 终止程序

## 内部实现细节

### 文件定位策略

```cpp
std::string exePath = SkGetExecutablePath();
SkString exeDir = SkOSPath::Dirname(exePath.c_str());
SkString modulePath = SkOSPath::Join(exeDir.c_str(), filename);
```

模块文件的查找路径基于可执行文件的目录。这假设 SkSL 模块文件在构建时被部署到与可执行文件相同的目录中。

### 文件读取

```cpp
std::ifstream in(std::string{modulePath.c_str()});
std::string moduleSource{std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
```

使用 C++ `std::ifstream` 一次性读取整个文件内容为字符串。如果文件不存在或读取出错，通过 `SK_ABORT` 终止程序。

### 与默认实现的差异

| 特性 | Default 实现 | File 实现 |
|------|-------------|-----------|
| 数据来源 | 编译时嵌入 | 运行时文件读取 |
| 使用参数 | `ModuleType` | `filename` |
| Graphite 模块 | 支持延迟初始化 | 不特殊处理 |
| 错误处理 | `SkUNREACHABLE` | `SK_ABORT` |
| 适用场景 | 生产环境 | 开发/调试 |

## 依赖关系

- `src/sksl/SkSLModule.h` — `ModuleType` 枚举和 `GetModuleData` 声明
- `include/core/SkString.h` — `SkString` 字符串类
- `src/utils/SkGetExecutablePath.h` — 获取可执行文件路径
- `src/utils/SkOSPath.h` — 路径操作工具
- `<fstream>` — 文件流

## 设计模式与设计决策

- **策略模式**：与 `SkSLModuleDataDefault.cpp` 共享同一函数签名，通过链接时选择实现编译时/运行时模块加载策略的切换。
- **快速失败**：文件读取失败时直接 `SK_ABORT`，因为缺少内置模块将导致编译器完全无法工作。
- **路径约定**：基于可执行文件目录定位模块文件，避免依赖环境变量或配置文件。

## 性能考量

1. **I/O 开销**：每次调用都需要磁盘 I/O，相比默认实现的编译时嵌入较慢。
2. **仅用于开发**：此实现不适合生产环境使用，其 I/O 开销在开发场景中可接受。
3. **一次性读取**：使用 `istreambuf_iterator` 一次性读取整个文件，避免多次 I/O 操作。

## 相关文件

- `src/sksl/SkSLModuleDataDefault.cpp` — 默认模块数据实现（编译时嵌入）
- `src/sksl/SkSLModule.h` — 模块类型定义和接口声明
- `src/utils/SkGetExecutablePath.h` — 可执行文件路径获取工具
- `src/utils/SkOSPath.h` — 路径操作工具
