# SkUnicode_icu4x - ICU4X Unicode 后端工厂

> 源文件: `modules/skunicode/include/SkUnicode_icu4x.h`

## 概述

`SkUnicode_icu4x.h` 声明了基于 ICU4X 库的 `SkUnicode` 实现的工厂函数。ICU4X 是 Unicode Consortium 开发的新一代国际化库，使用 Rust 编写，旨在提供更小的二进制体积和更好的内存安全性。该头文件仅包含一个工厂函数 `Make()`，返回 `SkUnicode` 的 ICU4X 实现实例。

ICU4X 是传统 ICU (International Components for Unicode) 的现代替代方案，它保留了 ICU 的全面 Unicode 功能覆盖，同时通过 Rust 的内存安全保证和模块化设计解决了传统 ICU 的体积和安全性问题。

## 架构位置

该文件位于 `skunicode` 模块的公共接口层，是 `SkUnicode` 抽象接口的后端实现之一。在 Skia 的 Unicode 后端架构中：

```
SkShaper / SkParagraph (使用方)
       |
   SkUnicode (抽象接口)
       |
   +---+---+----------+-----------+
   |       |          |           |
 ICU4X  libgrapheme  Client     Bidi
```

`SkUnicodes::ICU4X::Make()` 是创建 ICU4X 后端的唯一入口。用户通过调用此工厂函数获取 `SkUnicode` 实例，然后通过统一接口使用 Unicode 功能。在功能完整性方面，ICU4X 后端是最全面的选择，支持 `SkUnicode` 接口中定义的所有操作。

## 主要类与结构体

该文件不定义任何新的类或结构体。它仅在 `SkUnicodes::ICU4X` 嵌套命名空间中声明一个工厂函数。具体的实现类定义在对应的 `.cpp` 文件中，对用户完全隐藏。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `sk_sp<SkUnicode> SkUnicodes::ICU4X::Make()` | 创建 ICU4X 后端的 SkUnicode 实例 |

```cpp
namespace SkUnicodes::ICU4X {
SKUNICODE_API sk_sp<SkUnicode> Make();
}
```

- **返回值**: `sk_sp<SkUnicode>` — 引用计数管理的 SkUnicode 实例。如果 ICU4X 初始化失败，可能返回 `nullptr`
- **SKUNICODE_API**: DLL 导出/导入宏，支持动态库构建场景
- **无参数**: 不需要任何配置参数，ICU4X 使用内置或编译时配置的数据

## 内部实现细节

该文件仅为声明文件，实际实现在对应的 `.cpp` 文件中。工厂函数创建的实例将实现 `SkUnicode` 接口的所有纯虚方法，包括：

- **双向文本分析**: `getBidiRegions()`、`makeBidiIterator()` — 实现 UAX #9 算法
- **行分割**: 通过 `makeBreakIterator(BreakType::kLines)` — 实现 UAX #14 算法
- **词分割**: `getWords()`、`getUtf8Words()` — 实现 UAX #29 词边界算法
- **字素簇分割**: 通过 `makeBreakIterator(BreakType::kGraphemes)` — 实现 UAX #29 字素簇算法
- **句子分割**: `getSentences()` — 实现 UAX #29 句子边界算法
- **字符属性查询**: `isControl()`、`isWhitespace()`、`isEmoji()` 等
- **大小写转换**: `toUpper()`（标记为弃用）
- **编码转换**: UTF-8/UTF-16 互转

### 头文件结构
```cpp
#ifndef SkUnicode_icu4x_DEFINED
#define SkUnicode_icu4x_DEFINED

#include "modules/skunicode/include/SkUnicode.h"
#include <memory>

namespace SkUnicodes::ICU4X {
SKUNICODE_API sk_sp<SkUnicode> Make();
}

#endif
```

## 依赖关系

- **直接依赖**: `SkUnicode.h`（基类定义）、`<memory>`（`std::unique_ptr` 等智能指针支持）
- **运行时依赖**: ICU4X 库（Rust 编写的国际化库，通过 C FFI 接口调用）
- **编译选项**: 需要在构建系统（GN/Bazel）中启用 ICU4X 支持并链接 ICU4X 的 C 绑定库
- **数据依赖**: ICU4X 需要 Unicode 数据文件（可编译时嵌入或运行时加载）

## 设计模式与设计决策

- **抽象工厂模式**: 使用命名空间级别的 `Make()` 函数作为工厂方法，完全隐藏具体实现类。调用方只需要包含此头文件即可创建实例，无需了解内部实现细节
- **后端可插拔**: 与 `SkUnicodes::Libgrapheme::Make()`、`SkUnicodes::Client::Make()`、`SkUnicodes::Bidi::Make()` 并列，允许在编译时或运行时选择 Unicode 后端。所有后端返回相同类型 `sk_sp<SkUnicode>`
- **引用计数生命周期**: 返回 `sk_sp<SkUnicode>` 保证内存安全的共享所有权，调用方无需手动管理实例生命周期
- **DLL 兼容性**: `SKUNICODE_API` 宏在不同平台上展开为适当的导出/导入指令，支持 Skia 作为动态库使用
- **嵌套命名空间**: 使用 C++17 的嵌套命名空间语法 `SkUnicodes::ICU4X`，提供清晰的命名层次

## 性能考量

- **ICU4X 设计优势**: ICU4X 的设计目标包括小二进制体积和低内存占用，适合嵌入式和移动端场景
- **按需数据加载**: 相比传统 ICU (C/C++ 版本) 需要预加载大量数据，ICU4X 支持更灵活的数据加载策略
- **Rust FFI 开销**: ICU4X 通过 C FFI 接口调用 Rust 实现，存在少量的跨语言调用开销，但对于文本处理操作来说可忽略不计
- **工厂函数开销**: `Make()` 函数调用开销可忽略，通常仅在应用初始化时调用一次
- **功能最全面**: 在所有后端中功能覆盖最完整，适合需要全面 Unicode 支持的应用

## 相关文件

- `modules/skunicode/include/SkUnicode.h` — `SkUnicode` 抽象基类，定义了所有后端必须实现的接口
- `modules/skunicode/include/SkUnicode_libgrapheme.h` — libgrapheme 后端，更轻量但功能较少
- `modules/skunicode/include/SkUnicode_client.h` — 客户端提供数据的后端，无外部依赖
- `modules/skunicode/include/SkUnicode_bidi.h` — 仅双向文本支持的后端，功能最精简
- `modules/skunicode/src/SkUnicode_icu4x.cpp` — ICU4X 后端的具体实现
