# SkUnicode_libgrapheme - libgrapheme Unicode 后端工厂

> 源文件: `modules/skunicode/include/SkUnicode_libgrapheme.h`

## 概述

`SkUnicode_libgrapheme.h` 声明了基于 libgrapheme 库的 `SkUnicode` 实现的工厂函数。libgrapheme 是一个轻量级的 C 语言 Unicode 文本分割库，专注于字素簇 (grapheme cluster)、词和句子的分割功能。该头文件仅包含一个工厂函数 `Make()`，是 Skia 中提供完整文本分割能力的最轻量后端选项之一。

libgrapheme 库严格遵循 Unicode 标准中的文本分割规范（UAX #29），以最小的代码量和依赖实现了字素簇、词和句子的边界检测。

## 架构位置

该文件位于 `skunicode` 模块的公共接口层，是 `SkUnicode` 抽象接口的后端实现之一。在 Skia 的 Unicode 后端选择策略中：

| 后端 | 功能完整性 | 二进制体积 | 外部依赖 |
|------|-----------|-----------|---------|
| ICU4X | 最全面 | 较大 | ICU4X (Rust) |
| libgrapheme | 文本分割 | 很小 | libgrapheme (C) |
| Client | 取决于输入 | 最小 | 无 |
| Bidi | 仅双向文本 | 很小 | Bidi 算法 |

libgrapheme 后端适用于对二进制体积敏感且不需要完整 ICU 功能（如大小写转换、区域感知排序等）的场景，但又需要可靠的文本分割能力。

## 主要类与结构体

该文件不定义任何新的类或结构体。它仅在 `SkUnicodes::Libgrapheme` 嵌套命名空间中声明工厂函数。具体的实现类在对应的 `.cpp` 文件中定义，对调用方完全隐藏。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `sk_sp<SkUnicode> SkUnicodes::Libgrapheme::Make()` | 创建 libgrapheme 后端的 SkUnicode 实例 |

```cpp
namespace SkUnicodes::Libgrapheme {
SKUNICODE_API sk_sp<SkUnicode> Make();
}
```

- **返回值**: `sk_sp<SkUnicode>` — 引用计数管理的 SkUnicode 实例
- **SKUNICODE_API**: 动态库导出宏
- **无参数**: libgrapheme 不需要外部配置

## 内部实现细节

该文件仅为声明文件，实际实现位于对应的 `.cpp` 源文件中。libgrapheme 后端预期实现以下 `SkUnicode` 接口方法：

- **字素簇分割**: 基于 UAX #29 的字素簇边界检测
- **词分割**: 基于 UAX #29 的词边界检测
- **行分割**: 基于 UAX #14 的行分割机会检测
- **句子分割**: 基于 UAX #29 的句子边界检测
- **字符属性**: 部分字符属性查询可能通过 libgrapheme 或硬编码实现

对于 libgrapheme 不原生支持的功能（如完整的 Bidi 算法、大小写转换），该后端可能提供简化的实现或返回默认值。

### 头文件结构
```cpp
#ifndef SkUnicode_libgrapheme_DEFINED
#define SkUnicode_libgrapheme_DEFINED

#include "modules/skunicode/include/SkUnicode.h"
#include <memory>

namespace SkUnicodes::Libgrapheme {
SKUNICODE_API sk_sp<SkUnicode> Make();
}

#endif
```

## 依赖关系

- **直接依赖**: `SkUnicode.h`（基类定义）、`<memory>`
- **运行时依赖**: libgrapheme 库 — 一个纯 C 语言实现的 Unicode 文本分割库
- **编译选项**: 需要在构建系统中链接 libgrapheme 库
- **数据依赖**: libgrapheme 通常将 Unicode 数据编译到库自身中

## 设计模式与设计决策

- **抽象工厂模式**: 与 ICU4X、Client 等后端使用统一的工厂函数模式，通过命名空间区分
- **最小依赖原则**: libgrapheme 是一个依赖极少的纯 C 库，没有额外的运行时依赖，适合在嵌入式或受限环境中使用
- **后端互换性**: 通过 `SkUnicode` 接口的多态性，libgrapheme 后端可以无缝替换 ICU4X 等其他后端，调用方代码无需修改
- **功能子集策略**: 在二进制体积和功能完整性之间做出有意识的权衡，为不需要完整 ICU 功能的使用者提供轻量选择
- **C 语言互操作**: libgrapheme 使用纯 C API，与 C++ 代码的互操作没有额外开销

## 性能考量

- **C 语言实现**: libgrapheme 以纯 C 语言编写，运行时开销极小，无垃圾回收或运行时系统开销
- **小二进制体积**: 编译后的库体积远小于完整 ICU 库（通常小几个数量级），对于移动端和嵌入式应用非常重要
- **内存效率**: 简单的 C 数据结构，内存占用可预测且较低
- **Unicode 版本**: libgrapheme 跟随特定的 Unicode 版本，升级需要更新库本身
- **功能限制**: 在某些复杂 Unicode 场景下（如特定区域的词分割规则），可能不如 ICU 全面
- **工厂调用**: `Make()` 调用开销可忽略，通常仅在初始化时调用一次

## 相关文件

- `modules/skunicode/include/SkUnicode.h` — `SkUnicode` 抽象基类定义
- `modules/skunicode/include/SkUnicode_icu4x.h` — ICU4X 后端（功能最全面）
- `modules/skunicode/include/SkUnicode_client.h` — 客户端数据后端（无外部依赖）
- `modules/skunicode/include/SkUnicode_bidi.h` — 双向文本后端（功能最精简）
- `modules/skunicode/src/SkUnicode_libgrapheme.cpp` — libgrapheme 后端的具体实现
