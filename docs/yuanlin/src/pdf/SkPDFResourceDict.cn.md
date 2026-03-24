# SkPDFResourceDict — PDF 资源字典生成

> 源文件：[src/pdf/SkPDFResourceDict.h](../../src/pdf/SkPDFResourceDict.h)、[src/pdf/SkPDFResourceDict.cpp](../../src/pdf/SkPDFResourceDict.cpp)

## 概述

`SkPDFResourceDict` 模块负责生成 PDF 页面和 Form XObject 的资源字典（Resource Dictionary）。资源字典是 PDF 内容流引用外部资源（图形状态、着色器模式、XObject、字体）的命名映射。

该模块提供两个核心功能：
- 根据资源引用列表构建完整的 PDF 资源字典
- 生成资源名称（如 `/G42`、`/P7`、`/X12`、`/F3`）

## 架构位置

```
SkPDFDevice::makeResourceDict()
    │
    └── SkPDFMakeResourceDict()
            │
            └── PDF Resource Dictionary
                ├── ProcSet [PDF, Text, ImageB, ImageC, ImageI]
                ├── ExtGState { G0: ref, G1: ref, ... }
                ├── Pattern { P0: ref, P1: ref, ... }
                ├── XObject { X0: ref, X1: ref, ... }
                └── Font { F0: ref, F1: ref, ... }
```

## 主要类与结构体

### `SkPDFResourceType`（枚举）

| 值 | 含义 | 前缀 | 字典键 |
|----|------|------|--------|
| `kExtGState` (0) | 图形状态 | `G` | `ExtGState` |
| `kPattern` (1) | 着色器模式 | `P` | `Pattern` |
| `kXObject` (2) | 外部对象 | `X` | `XObject` |
| `kFont` (3) | 字体 | `F` | `Font` |

PDF 规范还定义了 ColorSpace、Shading、Properties 类型，但 Skia 目前未使用。

## 公共 API 函数

### `SkPDFMakeResourceDict(graphicStateResources, shaderResources, xObjectResources, fontResources) -> unique_ptr<SkPDFDict>`

创建完整的 PDF 资源字典。自动添加完整的 ProcSet 条目（`[/PDF /Text /ImageB /ImageC /ImageI]`）以保持向后兼容性。每类资源生成一个子字典，键为前缀+引用值（如 `G42`），值为间接引用。

### `SkPDFWriteResourceName(SkWStream*, SkPDFResourceType type, int key)`

将资源名称（带前导 `/`）直接写入输出流。格式为 `/<prefix><key>`，例如 `/G0`、`/P7`、`/X12`。

## 内部实现细节

### 资源命名规则

每种资源类型有固定的单字符前缀：
- `G` — ExtGState（图形状态扩展）
- `P` — Pattern（模式/着色器）
- `X` — XObject（外部对象，如图像、Form）
- `F` — Font（字体）

资源键为间接引用的 `fValue` 整数值，通过 `SkStrAppendS32` 转为十进制字符串。最大名称长度为 1 + `kSkStrAppendS32_MaxSize` 字符。

### ProcSet 条目

资源字典始终包含完整的 ProcSet 数组，列出所有可能的过程集：`PDF`、`Text`、`ImageB`（灰度图像）、`ImageC`（彩色图像）、`ImageI`（索引图像）。这是 PDF 规范推荐的向后兼容做法。

### 编译期验证

使用 `static_assert` 验证 `SkPDFResourceType` 枚举值与前缀/名称数组索引的一致性。

## 依赖关系

| 依赖项 | 说明 |
|--------|------|
| `SkPDFTypes` | PDF 字典和数组构建（`SkPDFMakeDict`、`SkPDFMakeArray`） |
| `SkStream` | 输出流 |
| `SkString` | 字符串操作（`SkStrAppendS32`） |

## 设计模式与设计决策

1. **紧凑命名**：单字符前缀 + 整数 ID 的命名方式既人类可读又节省空间。

2. **完整 ProcSet**：总是包含所有 ProcSet 条目，避免按页面内容动态计算，简化实现。

3. **空列表跳过**：空资源列表不会生成对应的子字典，减少无用的 PDF 对象。

4. **引用值作为键**：使用 `SkPDFIndirectReference.fValue` 作为资源名中的整数部分，确保同一引用在不同页面有相同的名称。

## 性能考量

- **O(n) 字典构建**：每类资源一次遍历，总复杂度为所有资源数量之和。
- **栈分配缓冲区**：`get_resource_name` 使用固定大小栈缓冲区，避免堆分配。
- **直接流写入**：`SkPDFWriteResourceName` 直接写入输出流，无中间字符串分配。

## 相关文件

- `src/pdf/SkPDFDevice.h` — 调用 `makeResourceDict()` 生成页面资源
- `src/pdf/SkPDFTypes.h` — PDF 基本类型（Dict、Array、IndirectReference）
- `src/pdf/SkPDFFormXObject.h` — Form XObject 资源
