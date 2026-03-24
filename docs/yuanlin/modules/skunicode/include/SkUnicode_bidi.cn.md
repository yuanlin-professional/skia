# SkUnicode_bidi - 双向文本专用 Unicode 后端

> 源文件: `modules/skunicode/include/SkUnicode_bidi.h`

## 概述

`SkUnicode_bidi.h` 声明了一个专注于双向文本 (Bidirectional Text, Bidi) 处理的 `SkUnicode` 后端工厂。如工厂函数注释所述，该后端"仅用于双向文本处理（以及可能的一些硬编码功能）"。这是所有 `SkUnicode` 后端中功能最精简的一个，适用于仅需要 Bidi 分析而不需要完整 Unicode 文本分割功能的场景。

双向文本处理是处理混合从左到右 (LTR) 和从右到左 (RTL) 书写系统（如阿拉伯语、希伯来语与拉丁语混排）的关键能力，由 Unicode 标准附件 UAX #9 定义。

## 架构位置

该文件位于 `skunicode` 模块的公共接口层，是 `SkUnicode` 抽象接口的功能最小化后端实现。在 Skia 的 Unicode 后端层次中，它处于最底层：

```
功能覆盖范围（从多到少）:
  ICU4X > libgrapheme > Client > Bidi

二进制体积（从大到小）:
  ICU4X > libgrapheme > Bidi > Client
```

适用于不需要词分割、行分割、字素簇分割等功能，只需要处理混合书写方向文本的场景。例如，一个仅渲染预排版文本但需要正确处理文本方向的轻量级应用。

## 主要类与结构体

该文件不定义新类或结构体，仅声明命名空间级别的工厂函数。具体的实现类在对应的 `.cpp` 源文件中，对调用方完全隐藏。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `sk_sp<SkUnicode> SkUnicodes::Bidi::Make()` | 创建仅支持 Bidi 处理的 SkUnicode 实例 |

```cpp
namespace SkUnicodes::Bidi {
SKUNICODE_API sk_sp<SkUnicode> Make(); // It's used for bidi only (and possibly some hardcode)
}
```

- **返回值**: `sk_sp<SkUnicode>` — 引用计数管理的 SkUnicode 实例
- **注释说明**: 原始代码注释明确限定了功能范围 — 仅 Bidi 和一些硬编码功能
- **SKUNICODE_API**: 动态库导出宏

## 内部实现细节

该文件仅为声明文件。根据注释 "possibly some hardcode"，该实现的特点包括：

### 预期实现的功能
- **双向文本分析**: `makeBidiIterator()` 和 `getBidiRegions()` — 实现 UAX #9 Unicode 双向算法
- **视觉重排序**: `reorderVisual()` — 将逻辑顺序转换为视觉显示顺序
- **硬编码字符属性**: `isControl()`、`isWhitespace()` 等基础属性可能使用硬编码的 Unicode 数据表实现

### 预期未实现或简化的功能
- **文本分割**: `makeBreakIterator()` 可能不支持或返回简化结果
- **词分割/句子分割**: `getWords()`、`getSentences()` 可能返回空结果
- **大小写转换**: `toUpper()` 可能不支持

### 头文件结构
```cpp
#ifndef SkUnicode_bidi_DEFINED
#define SkUnicode_bidi_DEFINED

#include "modules/skunicode/include/SkUnicode.h"
#include <memory>

namespace SkUnicodes::Bidi {
SKUNICODE_API sk_sp<SkUnicode> Make();
}

#endif // SkUnicode_bidi_DEFINED
```

## 依赖关系

- **直接依赖**: `SkUnicode.h`（基类定义）、`<memory>`
- **可能的运行时依赖**: 某种 Bidi 算法实现，可能是：
  - ICU 的 Bidi 子集 (ubidi)
  - 自行实现的 UAX #9 算法
  - 第三方轻量 Bidi 库
- **最小外部依赖**: 相比 ICU4X 和 libgrapheme，此后端的外部依赖最少
- **2025 年版权**: 这是最新添加的后端（其他为 2024 年）

## 设计模式与设计决策

- **最小化接口实现**: 仅实现 `SkUnicode` 接口中与 Bidi 相关的方法子集，体现了接口隔离原则 (ISP)。虽然必须实现所有纯虚方法，但非 Bidi 方法可以返回默认值或空结果
- **渐进式功能选择**: Skia 提供从最小（Bidi）到最大（ICU4X）的一系列后端，允许使用者根据需求选择适当的功能级别和二进制体积权衡
- **注释文档化**: 工厂函数的内联注释明确了功能范围限制（"bidi only"），帮助使用者在选择后端时做出知情决策
- **命名约定**: `SkUnicodes::Bidi` 命名空间名称清晰地传达了功能范围
- **最新架构演进**: 作为 2025 年添加的后端，反映了 Skia 团队对更细粒度 Unicode 功能选择的持续需求

## 性能考量

- **最小二进制体积**: 仅包含 Bidi 算法实现，不包含完整的 Unicode 字符数据库（如行分割规则表、词分割规则表）
- **最小内存占用**: 不需要加载词分割、行分割、字素簇分割等规则数据
- **Bidi 算法复杂度**: UAX #9 算法本身的时间复杂度为 O(n)，其中 n 是文本长度
- **适合简单场景**: 对于仅包含 LTR 文本的应用，Bidi 分析通常可以快速完成（所有字符的嵌入级别都是 0）
- **工厂调用**: 创建实例的开销可忽略，通常在应用初始化时仅调用一次
- **硬编码数据优势**: 使用硬编码的字符属性表比查询完整 Unicode 数据库更快，代价是可能不覆盖所有边缘情况

## 相关文件

- `modules/skunicode/include/SkUnicode.h` — `SkUnicode` 抽象基类，定义了 `SkBidiIterator` 接口和 `BidiRegion` 结构体
- `modules/skunicode/include/SkUnicode_icu4x.h` — 功能最完整的 ICU4X 后端
- `modules/skunicode/include/SkUnicode_libgrapheme.h` — 功能较完整的 libgrapheme 后端
- `modules/skunicode/include/SkUnicode_client.h` — 客户端提供数据的后端
- `modules/skunicode/src/SkUnicode_bidi.cpp` — Bidi 后端的具体实现
