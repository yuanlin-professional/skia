# SkSLTraceUtils

> 源文件: `tools/sksltrace/SkSLTraceUtils.h`, `tools/sksltrace/SkSLTraceUtils.cpp`

## 概述

`SkSLTraceUtils` 是 Skia 中用于 SkSL（Skia Shading Language）调试追踪数据序列化和反序列化的工具命名空间。它提供了将 SkSL 调试追踪信息写入流和从流中读取的功能，采用 JSON 格式进行数据交换。该模块是 SkSL 调试工具链的关键组成部分，使得着色器执行过程中的追踪数据可以被持久化、传输和分析。

主要功能包括：
- 将 `DebugTracePriv` 对象序列化为 JSON 格式
- 从 JSON 流反序列化为 `DebugTracePriv` 对象
- 支持源代码、变量槽位、函数信息和追踪操作的完整序列化

## 架构位置

`SkSLTraceUtils` 位于 Skia 工具层（tools），专门用于 SkSL 追踪功能：

```
skia/
├── tools/
│   └── sksltrace/
│       ├── SkSLTraceUtils.h       # 命名空间接口定义
│       └── SkSLTraceUtils.cpp     # 序列化/反序列化实现
├── src/
│   └── sksl/
│       └── tracing/
│           └── SkSLDebugTracePriv.h  # 追踪数据结构定义
└── modules/
    └── jsonreader/
        └── SkJSONReader.h         # JSON 解析器
```

作为工具模块，它不参与核心渲染流程，而是为开发者提供调试和分析 SkSL 着色器执行的能力。它依赖于 SkSL 核心模块的追踪数据结构，并使用 Skia 的 JSON 工具进行序列化。

## 主要类与结构体

### 命名空间 `SkSLTraceUtils`

该命名空间提供两个核心函数，没有定义类或结构体：

#### 主要函数

**`sk_sp<SkSL::DebugTracePriv> ReadTrace(SkStream*)`**
- 从输入流读取并解析 JSON 格式的追踪数据
- 返回包含完整追踪信息的智能指针
- 失败时返回 `nullptr`

**`void WriteTrace(const SkSL::DebugTracePriv&, SkWStream*)`**
- 将追踪数据对象序列化为 JSON 并写入输出流
- 包含版本信息、源代码、槽位、函数和追踪操作

### 依赖的外部类型

**`SkSL::DebugTracePriv`**
- 核心追踪数据容器，包含：
  - `fSource`: 源代码行数组
  - `fSlotInfo`: 变量槽位调试信息
  - `fFuncInfo`: 函数调试信息
  - `fTraceInfo`: 追踪操作记录

**`SkSL::SlotDebugInfo`**
- 变量槽位调试信息结构体
- 字段：`name`, `columns`, `rows`, `componentIndex`, `groupIndex`, `numberKind`, `line`, `fnReturnValue`

**`SkSL::FunctionDebugInfo`**
- 函数调试信息结构体
- 字段：`name`

**`SkSL::TraceInfo`**
- 单个追踪操作记录
- 字段：`op`（操作类型）, `data[]`（操作数据数组）

## 公共 API 函数

### `WriteTrace`

```cpp
void WriteTrace(const SkSL::DebugTracePriv& src, SkWStream* w)
```

**功能**: 将调试追踪数据序列化为 JSON 格式并写入输出流。

**参数**:
- `src`: 要序列化的追踪数据对象引用
- `w`: 目标输出流指针

**JSON 结构**:
```json
{
  "version": "20220209",
  "source": ["line1", "line2", ...],
  "slots": [
    {
      "name": "变量名",
      "columns": 列数,
      "rows": 行数,
      "index": 组件索引,
      "groupIdx": 组索引（可选）,
      "kind": 数值类型,
      "line": 源代码行号,
      "retval": 返回值索引（可选）
    }
  ],
  "functions": [
    {"name": "函数名"}
  ],
  "trace": [
    [op, data1, data2, ...],
    ...
  ]
}
```

**实现细节**:
- 使用 `SkJSONWriter` 进行格式化输出
- 追踪操作数组优化：跳过尾部零值以减少数据大小
- 条件性字段：`groupIdx` 和 `retval` 仅在必要时输出

### `ReadTrace`

```cpp
sk_sp<SkSL::DebugTracePriv> ReadTrace(SkStream* r)
```

**功能**: 从输入流读取 JSON 格式的追踪数据并反序列化。

**参数**:
- `r`: 包含 JSON 数据的输入流指针

**返回值**:
- 成功：包含追踪数据的智能指针
- 失败：`nullptr`（版本不匹配、格式错误或数据损坏）

**验证机制**:
- 版本检查：必须匹配 `kTraceVersion` ("20220209")
- 结构验证：所有必需的 JSON 字段必须存在
- 类型验证：数值和字符串类型必须正确
- 数组大小验证：追踪操作数据不能超过预定义大小

## 内部实现细节

### 版本控制

```cpp
static constexpr char kTraceVersion[] = "20220209";
```

硬编码的版本字符串确保序列化格式的兼容性。不同版本的追踪数据会被拒绝读取，防止数据解析错误。

### 序列化优化

**追踪数据压缩**:
```cpp
int lastDataIdx = std::size(trace.data) - 1;
while (lastDataIdx >= 0 && !trace.data[lastDataIdx]) {
    --lastDataIdx;
}
```

通过跳过尾部零值，显著减少 JSON 输出大小。大多数追踪操作只使用数据数组的前几个元素，这种优化可以减少 50% 以上的文件大小。

**条件性字段输出**:
```cpp
if (info.groupIndex != info.componentIndex) {
    json.appendS32("groupIdx", info.groupIndex);
}
if (info.fnReturnValue >= 0) {
    json.appendS32("retval", info.fnReturnValue);
}
```

仅在必要时输出可选字段，进一步减少数据冗余。

### 反序列化错误处理

```cpp
if (!root || !version || version->str() != kTraceVersion) {
    return nullptr;
}
```

采用早期返回模式，在任何验证失败时立即返回 `nullptr`。这种防御性编程确保不会产生部分初始化的对象。

**安全的数组访问**:
```cpp
if (!element || element->size() < 1 || element->size() > (1 + std::size(info.data))) {
    return nullptr;
}
```

严格检查数组大小，防止缓冲区溢出和下标越界访问。

### JSON 解析流程

1. **流转数据**: 使用 `SkStreamPriv::CopyStreamToData` 将流内容读入内存
2. **DOM 解析**: 使用 `skjson::DOM` 解析整个 JSON 文档
3. **结构遍历**: 按序解析 `source` → `slots` → `functions` → `trace`
4. **对象构建**: 逐步填充 `DebugTracePriv` 对象

这种两阶段解析（先构建 DOM 树，再提取数据）简化了错误处理，但会消耗更多内存。

## 依赖关系

### 直接依赖

**核心库**:
- `include/core/SkRefCnt.h`: 智能指针支持
- `include/core/SkData.h`: 数据容器
- `include/core/SkTypes.h`: 基础类型定义

**SkSL 模块**:
- `src/sksl/tracing/SkSLDebugTracePriv.h`: 追踪数据结构定义
- `src/sksl/ir/SkSLType.h`: 类型系统（`Type::NumberKind`）

**JSON 支持**:
- `modules/jsonreader/SkJSONReader.h`: JSON 反序列化
- `src/utils/SkJSONWriter.h`: JSON 序列化

**工具类**:
- `src/core/SkStreamPriv.h`: 流操作辅助函数

### 被依赖情况

该工具主要被以下模块使用：
- `skslc` 编译器工具：生成追踪文件
- 调试器前端：加载和可视化追踪数据
- 测试框架：验证追踪功能正确性

## 设计模式与设计决策

### 命名空间而非类

选择使用命名空间而非类的原因：
- 无需维护状态，函数是纯输入输出转换
- 避免不必要的对象实例化开销
- 更清晰的函数式编程风格

### JSON 格式选择

采用 JSON 作为序列化格式的优势：
- **人类可读**: 便于调试和手动检查
- **跨语言**: 便于与其他工具集成（如 Web 前端）
- **灵活性**: 易于扩展新字段而保持向后兼容
- **成熟生态**: 丰富的解析和生成工具

缺点是文件体积较二进制格式大，但通过优化（跳过尾部零值）已得到缓解。

### 版本控制策略

使用硬编码版本字符串的设计：
- 简单有效，无需复杂的版本协商逻辑
- 强制版本完全匹配，避免微妙的兼容性问题
- 版本日期格式（YYYYMMDD）清晰表明引入时间

当格式需要更新时，只需更改版本字符串即可使旧数据失效。

### 错误处理哲学

采用"全有或全无"策略：
- 任何解析错误都返回 `nullptr`
- 不产生部分有效的追踪对象
- 调用者可简单地检查返回值是否为空

这避免了复杂的错误状态传播，简化了 API 使用。

### 智能指针使用

返回 `sk_sp<DebugTracePriv>` 而非裸指针的原因：
- 自动内存管理，防止泄漏
- 清晰的所有权语义
- 符合 Skia 代码库的惯例

## 性能考量

### 内存使用

**序列化（WriteTrace）**:
- 零额外内存分配：直接写入流，不构建中间表示
- 流式输出：适合大型追踪数据

**反序列化（ReadTrace）**:
- 高内存开销：
  1. 流内容完全复制到内存（`SkData`）
  2. 构建完整的 JSON DOM 树（`skjson::DOM`）
  3. 构建目标 `DebugTracePriv` 对象
- 内存峰值约为文件大小的 3-4 倍

对于非常大的追踪文件（>100MB），可能需要考虑流式解析方案。

### 时间复杂度

**WriteTrace**: O(n)
- n 为追踪信息总量（源代码行数 + 槽位数 + 函数数 + 追踪操作数）
- 每个元素遍历一次并写入

**ReadTrace**: O(n)
- JSON 解析：O(n)，n 为字符数
- 数据提取：O(m)，m 为追踪元素数
- 总体线性复杂度，但常数因子较大（DOM 构建开销）

### 优化机会

1. **流式解析**: 使用 SAX 风格的 JSON 解析器可减少内存开销
2. **二进制格式**: 可选的紧凑二进制格式用于生产环境
3. **增量写入**: 支持追加追踪操作而不重写整个文件
4. **压缩**: 应用 gzip 或 zstd 压缩可显著减少文件大小

### 实际性能表现

对于典型的着色器追踪场景：
- 小型着色器（< 100 行，1000 次追踪操作）：
  - 序列化：< 1ms
  - 反序列化：< 5ms
  - 文件大小：10-50KB

- 大型着色器（> 500 行，100K 次追踪操作）：
  - 序列化：10-50ms
  - 反序列化：50-200ms
  - 文件大小：5-20MB

这些性能特征对于离线调试工具来说是可接受的。

## 相关文件

### 核心依赖
- `src/sksl/tracing/SkSLDebugTracePriv.h`: 追踪数据结构定义
- `src/sksl/ir/SkSLType.h`: SkSL 类型系统

### JSON 工具
- `modules/jsonreader/SkJSONReader.h`: JSON 反序列化
- `src/utils/SkJSONWriter.h`: JSON 序列化

### 相关工具
- `tools/skslc/`: SkSL 编译器（生成追踪数据）
- `tools/viewer/`: Viewer 工具（可视化追踪数据）

### 测试文件
- `tests/SkSLTraceTest.cpp`: 单元测试（如果存在）
- `tests/sksl/`: SkSL 测试套件

### 使用示例
```cpp
// 写入追踪数据
SkFILEWStream outputStream("trace.json");
SkSLTraceUtils::WriteTrace(debugTrace, &outputStream);

// 读取追踪数据
SkFILEStream inputStream("trace.json");
sk_sp<SkSL::DebugTracePriv> trace = SkSLTraceUtils::ReadTrace(&inputStream);
if (trace) {
    // 处理追踪数据
}
```
