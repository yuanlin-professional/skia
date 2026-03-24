# tools/sksltrace - SkSL 调试追踪工具

## 概述

`tools/sksltrace` 目录包含了 SkSL（Skia Shading Language）调试追踪数据的序列化和反序列化工具。SkSL 着色器调试追踪是 Skia 提供的一项开发者工具功能，允许在着色器执行过程中记录详细的调试信息，包括变量值、函数调用和执行流程。

本目录提供了 `SkSLTraceUtils` 命名空间下的两个核心函数：`WriteTrace` 用于将调试追踪数据序列化为 JSON 格式，`ReadTrace` 用于从 JSON 格式反序列化调试追踪数据。这种 JSON 格式的追踪数据可以持久化存储、跨进程传输，或在调试器 UI 中加载显示。

追踪数据的 JSON 格式（版本标识为 "20220209"）包含四个主要部分：`source` 数组存储着色器源代码行；`slots` 数组描述每个调试变量的元信息（名称、维度、类型、行号等）；`functions` 数组列出所有函数的名称；`trace` 数组记录实际的执行追踪事件序列。

每个 slot（变量槽位）包含详细的类型信息：`columns` 和 `rows` 描述变量的矩阵维度（标量为 1x1）；`index` 和 `groupIdx` 标识组件在变量中的位置；`kind` 表示数值类型（浮点、有符号整数等）；`line` 记录变量声明的源代码行号；`retval` 标识是否为函数返回值。

追踪事件（trace entries）使用紧凑的数组格式，每个事件包含一个操作码和若干数据值，尾部的零值会被省略以节省空间。

## 目录结构

```
tools/sksltrace/
├── BUILD.bazel            # Bazel 构建配置
├── SkSLTraceUtils.h       # 追踪工具声明
└── SkSLTraceUtils.cpp     # 追踪工具实现
```

## 关键类与函数

### SkSLTraceUtils 命名空间

#### WriteTrace
- **签名**: `void WriteTrace(const SkSL::DebugTracePriv& src, SkWStream* w)`
- **功能**: 将调试追踪数据序列化为 JSON 格式
- **输出格式**:
  ```json
  {
    "version": "20220209",
    "source": ["line1", "line2", ...],
    "slots": [{"name": "x", "columns": 1, "rows": 1, ...}],
    "functions": [{"name": "main"}],
    "trace": [[opcode, data1, data2, ...]]
  }
  ```
- **依赖**: 使用 `SkJSONWriter` 进行 JSON 序列化

#### ReadTrace
- **签名**: `sk_sp<SkSL::DebugTracePriv> ReadTrace(SkStream* r)`
- **功能**: 从 JSON 格式反序列化调试追踪数据
- **返回值**: 成功时返回 `DebugTracePriv` 的智能指针，失败时返回 nullptr
- **验证**: 检查版本号匹配，验证所有必要字段存在
- **依赖**: 使用 `skjson::DOM` 进行 JSON 解析

### 数据结构

#### SlotDebugInfo（变量槽位信息）
- `name` - 变量名称
- `columns` / `rows` - 矩阵维度
- `componentIndex` / `groupIndex` - 组件和组索引
- `numberKind` - 数值类型（`SkSL::Type::NumberKind`）
- `line` - 源代码行号
- `fnReturnValue` - 函数返回值标记（-1 表示非返回值）

#### FunctionDebugInfo（函数信息）
- `name` - 函数名称

#### TraceInfo（追踪事件）
- `op` - 操作码（`SkSL::TraceInfo::Op`）
- `data[]` - 操作数据数组

## 依赖关系

- **核心依赖**: `src/sksl/tracing/SkSLDebugTracePriv.h`（调试追踪数据结构）
- **JSON 读取**: `modules/jsonreader/SkJSONReader.h`（JSON 解析器）
- **JSON 写入**: `src/utils/SkJSONWriter.h`（JSON 序列化器）
- **流处理**: `include/core/SkStream.h`（SkStream、SkWStream）
- **类型信息**: `src/sksl/ir/SkSLType.h`（NumberKind 枚举）
- **被引用**: SkSL 调试器工具、着色器调试 UI

## JSON 追踪格式详细说明

### 顶层结构
```json
{
  "version": "20220209",
  "source": [...],
  "slots": [...],
  "functions": [...],
  "trace": [...]
}
```

### source 数组
存储着色器的完整源代码，每行作为一个字符串元素。行号与 `slots` 中的 `line` 字段对应。

### slots 数组
每个元素描述一个调试变量槽位：
- 标量变量：`columns=1, rows=1`
- vec3 变量：`columns=3, rows=1`
- mat3x3 变量：`columns=3, rows=3`，包含 9 个槽位（每个组件一个）
- `groupIdx` 字段仅在与 `index` 不同时序列化（节省空间）
- `retval` 字段仅在为函数返回值时序列化

### trace 数组
追踪事件使用紧凑数组格式 `[opcode, data1, data2, ...]`，尾部零值被省略。操作码定义在 `SkSL::TraceInfo::Op` 枚举中，涵盖行执行、变量写入、函数进入/退出等事件。

## 与 skslc 的集成

`skslc` 编译器通过 `/*#pragma settings DebugTrace*/` 注释启用追踪代码生成。启用后：
1. 编译器禁用优化（`settings.fOptimize = false`）
2. 创建 `DebugTracePriv` 实例
3. Raster Pipeline 代码生成器插入追踪操作
4. 追踪数据可通过本工具序列化为 JSON

## 相关文档与参考

- `src/sksl/tracing/SkSLDebugTracePriv.h` - 调试追踪私有数据结构
- `tools/skslc/` - SkSL 编译器（支持 `DebugTrace` 编译设置）
- `src/sksl/codegen/SkSLRasterPipelineCodeGenerator.h` - 支持追踪操作的代码生成器
- `modules/jsonreader/` - JSON 解析模块
- 追踪数据版本: "20220209"（2022年2月9日格式）
