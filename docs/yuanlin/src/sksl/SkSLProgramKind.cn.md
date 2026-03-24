# SkSLProgramKind — SkSL 程序类型枚举

> 源文件：[`src/sksl/SkSLProgramKind.h`](../../src/sksl/SkSLProgramKind.h)

## 概述

SkSLProgramKind.h 定义了 SkSL 支持的所有程序类型的枚举。SkSL 着色语言可用于编写多种类型的 GPU 程序，从传统的顶点/片段着色器到 Skia 特有的运行时效果和自定义 Mesh 程序。此枚举是 SkSL 编译器类型系统的基础，决定了编译器对程序的语法检查、功能限制和代码生成行为。

该文件仅 36 行，是一个纯枚举定义文件。

## 架构位置

```
SkSL 编译器类型系统
  └── ProgramKind 枚举 (SkSLProgramKind.h)
        ├── ProgramConfig (SkSLProgramSettings.h) — 使用此枚举进行类型判断
        ├── SkSL Compiler — 根据类型选择编译行为
        └── 代码生成器 — 根据类型选择输出格式
```

`ProgramKind` 在 SkSL 编译管线的入口处确定，贯穿整个编译和代码生成过程。

## 主要类与结构体

### `ProgramKind` 枚举

```cpp
enum class ProgramKind : int8_t {
    kFragment,                  // 片段着色器
    kVertex,                    // 顶点着色器
    kCompute,                   // 计算着色器
    kGraphiteFragment,          // Graphite 后端片段着色器
    kGraphiteVertex,            // Graphite 后端顶点着色器
    kRuntimeColorFilter,        // 运行时颜色过滤器
    kRuntimeShader,             // 运行时着色器
    kRuntimeBlender,            // 运行时混合器
    kPrivateRuntimeColorFilter, // 私有运行时颜色过滤器（放宽公共限制）
    kPrivateRuntimeShader,      // 私有运行时着色器
    kPrivateRuntimeBlender,     // 私有运行时混合器
    kMeshVertex,                // 自定义 Mesh 的顶点部分
    kMeshFragment,              // 自定义 Mesh 的片段部分
};
```

使用 `int8_t` 作为底层类型以最小化存储空间。

## 公共 API 函数

本文件不包含函数定义，仅定义枚举类型。程序类型的判断逻辑位于 `ProgramConfig`（参见 `SkSLProgramSettings.h`）。

## 内部实现细节

### 程序类型分类

程序类型可分为以下几个大类：

**GPU 着色器**：
- `kFragment` / `kVertex` — 标准 GPU 着色器
- `kGraphiteFragment` / `kGraphiteVertex` — Graphite 渲染后端的着色器变体
- `kCompute` — 计算着色器

**运行时效果**：
- `kRuntimeColorFilter` / `kRuntimeShader` / `kRuntimeBlender` — 公开 API 可用的运行时效果
- `kPrivateRuntimeColorFilter` / `kPrivateRuntimeShader` / `kPrivateRuntimeBlender` — Skia 内部使用的私有变体

**自定义 Mesh**：
- `kMeshVertex` / `kMeshFragment` — 自定义 Mesh 的顶点和片段处理

### 公开 vs 私有运行时效果

公开运行时效果（如 `kRuntimeShader`）对可用的语言功能有更严格的限制，不允许访问 Skia 内部标识符。私有变体（如 `kPrivateRuntimeShader`）放宽了这些限制，允许 Skia 内部代码使用更多功能。

## 依赖关系

- `<cinttypes>` — 提供 `int8_t` 类型

## 设计模式与设计决策

- **强类型枚举**：使用 `enum class` 确保类型安全，防止隐式转换。
- **紧凑存储**：使用 `int8_t` 底层类型（13 个枚举值远在 int8_t 范围内）。
- **公开/私有分离**：为每种运行时效果提供独立的公开和私有变体，而非通过额外的标志位控制访问权限，使类型判断更简洁直接。
- **Graphite 专用类型**：为 Graphite 后端单独定义了 `kGraphiteFragment` 和 `kGraphiteVertex`，允许编译器针对 Graphite 后端做专门处理。

## 性能考量

作为枚举定义，不涉及运行时性能问题。`int8_t` 底层类型减少了在 `ProgramConfig` 等结构体中的存储开销。

## 相关文件

- `src/sksl/SkSLProgramSettings.h` — 使用此枚举的 `ProgramConfig` 类
- `src/sksl/SkSLCompiler.h` — 编译器根据程序类型决定编译行为
- `include/sksl/SkSLVersion.h` — SkSL 版本定义
- `src/sksl/SkSLModule.h` — 模块系统（与程序类型配合使用）
