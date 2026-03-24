# SkUnicode_client - 客户端提供数据的 Unicode 后端

> 源文件: `modules/skunicode/include/SkUnicode_client.h`

## 概述

`SkUnicode_client.h` 声明了一个特殊的 `SkUnicode` 后端工厂，它不依赖任何外部 Unicode 库，而是由调用方直接提供预计算好的文本分析数据（词边界、字素簇边界、行分割点）。这种"客户端数据"模式适用于已经在其他系统中完成了 Unicode 文本分析，只需要将结果传递给 Skia 的场景，例如 Web 浏览器引擎中的 Skia 集成。

该后端是 Skia Unicode 架构中"零依赖"理念的极致体现：它将 Unicode 数据处理的职责完全转移到调用方，使 Skia 不需要链接任何 Unicode 库即可完成文本排版。

## 架构位置

该文件位于 `skunicode` 模块的公共接口层，是 `SkUnicode` 抽象接口的后端实现之一。在 Skia 的 Unicode 后端架构中，Client 后端的独特之处在于：

```
传统后端:  SkUnicode -> 调用 ICU4X/libgrapheme -> 返回结果
Client 后端: 调用方预计算结果 -> 传入 SkUnicode::Client -> Skia 使用
```

这种"透传"模式使 Client 后端成为集成 Skia 到已有文本处理管线的理想选择。

## 主要类与结构体

该文件不定义新的类或结构体，仅声明工厂函数。该函数使用 `SkUnicode.h` 中定义的数据类型：
- `SkUnicode::Position` — 文本位置（`size_t` 类型）
- `SkUnicode::LineBreakBefore` — 行分割点（包含位置和类型：硬/软）

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `sk_sp<SkUnicode> SkUnicodes::Client::Make(text, words, graphemeBreaks, lineBreaks)` | 从预计算数据创建 SkUnicode 实例 |

```cpp
namespace SkUnicodes::Client {
SKUNICODE_API sk_sp<SkUnicode> Make(
    SkSpan<char> text,
    std::vector<SkUnicode::Position> words,
    std::vector<SkUnicode::Position> graphemeBreaks,
    std::vector<SkUnicode::LineBreakBefore> lineBreaks);
}
```

### 参数详解

| 参数 | 类型 | 所有权 | 说明 |
|------|------|--------|------|
| `text` | `SkSpan<char>` | 非拥有（引用） | 要处理的 UTF-8 文本 |
| `words` | `std::vector<Position>` | 移动或复制 | 预计算的词边界位置列表 |
| `graphemeBreaks` | `std::vector<Position>` | 移动或复制 | 预计算的字素簇边界位置列表 |
| `lineBreaks` | `std::vector<LineBreakBefore>` | 移动或复制 | 预计算的行分割点列表 |

### 使用示例
```cpp
// 外部系统已计算好分析数据
std::vector<SkUnicode::Position> words = {0, 5, 6, 11};
std::vector<SkUnicode::Position> graphemes = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11};
std::vector<SkUnicode::LineBreakBefore> lines = {
    {5, SkUnicode::LineBreakType::kSoftLineBreak}
};

auto unicode = SkUnicodes::Client::Make(textSpan, words, graphemes, lines);
// 现在可以将 unicode 传给 SkShaper 等 Skia 组件
```

## 内部实现细节

工厂函数接收调用方提供的文本分析数据，创建一个 `SkUnicode` 实例。该实例将在被查询时返回这些预计算的数据，而不进行实际的 Unicode 分析。

### `text` 参数的特殊性
`text` 参数使用 `SkSpan<char>`（非 const），这暗示实现可能需要对文本进行就地修改。最可能的场景是 `computeCodeUnitFlags` 方法的 `replaceTabs` 参数为 true 时，需要将制表符替换为空格。

### 预期的方法实现行为
- **`computeCodeUnitFlags()`**: 基于提供的 `words`、`graphemeBreaks`、`lineBreaks` 数据生成 `CodeUnitFlags`
- **`getWords()`/`getUtf8Words()`**: 返回构造时提供的 `words` 数据
- **`getBidiRegions()`**: 可能不支持或返回简单的 LTR 结果
- **字符属性方法**: 可能使用硬编码的简单实现

## 依赖关系

- **直接依赖**: `SkSpan.h`（Skia 的非拥有型数据切片）、`SkUnicode.h`（基类定义，提供 `Position`、`LineBreakBefore` 等类型）
- **标准库**: `<memory>`（智能指针）、`<vector>`（数据容器）
- **无外部 Unicode 库依赖**: 这是此后端的核心设计特点，使其成为最轻量的选择

## 设计模式与设计决策

- **依赖注入/控制反转**: Unicode 分析数据由外部提供而非内部计算。这将数据生产与消费完全解耦，使 Skia 的文本管线可以适配任意外部 Unicode 处理系统
- **零外部依赖**: 不依赖 ICU、libgrapheme 等任何外部库。这最大程度减少了 Skia 的构建依赖，降低了集成复杂度
- **集成友好设计**: 专为嵌入场景优化。当宿主应用（如浏览器引擎、游戏引擎）已有自己的 Unicode 处理能力时，无需引入重复的 Unicode 库
- **数据所有权明确**:
  - `words`、`graphemeBreaks`、`lineBreaks` 通过值传递（`std::vector`），`SkUnicode` 实例拥有这些数据的副本（或通过移动语义获取所有权）
  - `text` 通过 `SkSpan` 传递（非拥有型），调用方需确保文本数据在 `SkUnicode` 实例存活期间有效
- **与其他后端的对比**: 这是唯一一个将数据生产职责完全外移的后端，其他后端（ICU4X、libgrapheme）都在内部完成 Unicode 分析

## 性能考量

- **零计算开销**: 所有 Unicode 分析在外部完成，`SkUnicode` 实例创建和查询的开销仅为数据查找
- **数据移动优化**: `std::vector` 参数可以通过 `std::move` 传递，避免数据拷贝。对于大文本的词边界和字素簇列表，这可以节省显著的分配和复制时间
- **最小二进制体积**: 不链接任何 Unicode 库，是所有后端中对最终二进制体积影响最小的选择
- **避免重复计算**: 如果宿主应用已经为自身目的计算了文本分析数据，使用此后端避免了 Skia 内部的重复计算
- **内存占用**: 需要同时保持文本数据和分析数据在内存中，总内存使用量取决于输入数据的大小

## 相关文件

- `modules/skunicode/include/SkUnicode.h` — `SkUnicode` 基类，定义 `Position`、`LineBreakBefore`、`CodeUnitFlags` 等类型
- `modules/skunicode/include/SkUnicode_icu4x.h` — ICU4X 后端（自主计算，功能最全面）
- `modules/skunicode/include/SkUnicode_libgrapheme.h` — libgrapheme 后端（自主计算，轻量级）
- `modules/skunicode/include/SkUnicode_bidi.h` — 双向文本后端（仅 Bidi 功能）
- `modules/skunicode/src/SkUnicode_client.cpp` — Client 后端的具体实现
- `include/core/SkSpan.h` — `SkSpan` 非拥有型数据切片定义
