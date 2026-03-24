# SkSLModuleDataDefault — SkSL 默认模块数据加载

> 源文件：[`src/sksl/SkSLModuleDataDefault.cpp`](../../src/sksl/SkSLModuleDataDefault.cpp)

## 概述

SkSLModuleDataDefault.cpp 实现了 SkSL 编译器默认的模块数据加载机制。它从编译时嵌入的 SkSL 源代码文件（预先生成的 minified 或 unoptimized 版本）中获取内置模块的源代码。此外，它还提供了 Graphite 后端模块的延迟初始化接口。

该文件 80 行，是 SkSL 模块加载系统的默认实现（与 `SkSLModuleDataFile.cpp` 的文件加载方式互为替代）。

## 架构位置

```
SkSL 模块加载系统
  ├── SkSLModuleDataDefault.cpp （编译时嵌入，默认实现）
  └── SkSLModuleDataFile.cpp   （运行时文件加载，调试/工具用）

模块数据来源:
  src/sksl/generated/sksl_*.minified.sksl   （Release/优化大小）
  src/sksl/generated/sksl_*.unoptimized.sksl（Debug）
```

## 主要类与结构体

本文件不定义类，仅实现函数和管理静态变量。

### 静态变量
```cpp
static const char* sdata_sksl_graphite_frag = "";
static const char* sdata_sksl_graphite_vert = "";
```
- Graphite 模块数据指针，初始为空字符串
- 通过 `Loader::SetGraphiteModuleData` 延迟设置

## 公共 API 函数

```cpp
std::string GetModuleData(ModuleType type, const char* filename);
```
- 根据模块类型返回对应的 SkSL 源代码字符串
- `filename` 参数在默认实现中被忽略（仅在文件加载实现中使用）
- 支持的模块类型：
  - `sksl_shared` — 共享基础模块
  - `sksl_compute` — 计算着色器模块
  - `sksl_frag` — 片段着色器模块
  - `sksl_gpu` — GPU 通用模块
  - `sksl_public` — 公共 API 模块
  - `sksl_rt_shader` — 运行时着色器模块
  - `sksl_vert` — 顶点着色器模块
  - `sksl_graphite_frag` / `sksl_graphite_vert` — Graphite 后端模块

```cpp
namespace Loader {
void SetGraphiteModuleData(const GraphiteModules& modules);
}
```
- 设置 Graphite 后端的模块数据
- 断言只能调用一次（防止重复初始化）
- 在 Graphite 后端初始化时被调用

## 内部实现细节

### 条件编译选择模块版本

```cpp
#if defined(SK_ENABLE_OPTIMIZE_SIZE) || !defined(SK_DEBUG)
#include "src/sksl/generated/sksl_*.minified.sksl"
#else
#include "src/sksl/generated/sksl_*.unoptimized.sksl"
#endif
```

- **minified 版本**：在 Release 构建或启用大小优化时使用。去除注释和多余空白，减小二进制大小。
- **unoptimized 版本**：在 Debug 构建时使用。保留完整源代码，便于调试。

这些 `.sksl` 文件通过 `#include` 宏被嵌入为 C 字符串字面量，使用 `SKSL_MINIFIED_*` 宏名称引用。

### 宏辅助的 switch 实现

```cpp
#define M(name) case ModuleType::name: return std::string(SKSL_MINIFIED_##name);
#define G(name) case ModuleType::name: if (sdata_##name) { return std::string(sdata_##name); } ...
```

- `M` 宏处理编译时嵌入的模块（直接从宏常量创建字符串）
- `G` 宏处理 Graphite 模块（从静态指针加载，需要检查空指针）

### Graphite 模块的延迟加载

Graphite 模块不在默认构建中包含，避免在仅使用 Ganesh 后端的构建中增加二进制大小。它们通过 `SetGraphiteModuleData` 在 Graphite 后端初始化时被设置。

## 依赖关系

- `include/core/SkTypes.h` — `SkASSERT`, `SkUNREACHABLE` 等宏
- `src/sksl/SkSLGraphiteModules.h` — `GraphiteModules` 结构体
- `src/sksl/SkSLModule.h` — `ModuleType` 枚举和 `GetModuleData` 声明
- `src/sksl/generated/sksl_*.sksl` — 预生成的 SkSL 模块源代码
- `<string>` — `std::string`

## 设计模式与设计决策

- **编译时嵌入**：将 SkSL 源代码在编译时嵌入为字符串常量，避免运行时文件 I/O 和路径查找。
- **策略模式**：`SkSLModuleDataDefault.cpp` 和 `SkSLModuleDataFile.cpp` 实现相同的 `GetModuleData` 接口但策略不同，通过链接时选择决定使用哪个实现。
- **延迟初始化**：Graphite 模块采用延迟初始化，按需加载，遵循了按需付费的设计原则。
- **Debug/Release 分离**：Debug 使用未优化版本便于调试，Release 使用精简版本减小大小。

## 性能考量

1. **零 I/O 开销**：模块数据编译时嵌入，无需运行时文件读取。
2. **字符串拷贝**：`GetModuleData` 返回 `std::string`，涉及一次字符串拷贝。这只在编译器初始化时发生，不影响着色器编译的性能。
3. **二进制大小**：使用 minified 版本可减小嵌入的模块源代码大小，有利于移动端等对二进制大小敏感的场景。

## 相关文件

- `src/sksl/SkSLModuleDataFile.cpp` — 替代实现（从文件加载模块数据）
- `src/sksl/SkSLModule.h` — 模块类型枚举和接口声明
- `src/sksl/SkSLGraphiteModules.h` — Graphite 模块数据结构
- `src/sksl/generated/` — 预生成的 SkSL 模块源代码目录
- `src/sksl/SkSLCompiler.cpp` — 编译器初始化时调用 `GetModuleData`
