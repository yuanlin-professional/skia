# SkUnicode_icu.h

> 源文件: `modules/skunicode/include/SkUnicode_icu.h`

## 概述

`SkUnicode_icu.h` 是 SkUnicode 模块中基于 ICU (International Components for Unicode) 库的 Unicode 实现的工厂头文件。该文件定义了一个简洁的工厂函数，用于创建基于 ICU 后端的 `SkUnicode` 实例。ICU 是业界广泛使用的 Unicode 处理库，提供了完整的 Unicode 文本处理能力，包括双向文本、断行、字符属性查询等功能。

## 架构位置

该文件位于 `modules/skunicode/include/` 目录下，属于 SkUnicode 模块的公共头文件。在 Skia 的模块架构中，SkUnicode 是一个可插拔的 Unicode 支持层，为上层文本排版模块（如 Skottie 文本排版、SkParagraph）提供 Unicode 功能。ICU 后端是其中一个可选实现，提供最完整的 Unicode 支持。

## 主要类与结构体

该文件未定义任何类或结构体，仅在 `SkUnicodes::ICU` 命名空间中声明了一个工厂函数。

### 头文件保护宏

```cpp
#ifndef SkUnicode_icu_DEFINED
#define SkUnicode_icu_DEFINED
// ...
#endif //SkUnicode_icu_DEFINED
```
遵循 Skia 的标准头文件保护命名约定 `<FileName>_DEFINED`。

## 公共 API 函数

### `SkUnicodes::ICU::Make()`
```cpp
SKUNICODE_API sk_sp<SkUnicode> Make();
```
- **功能**: 创建并返回一个基于 ICU 库的 `SkUnicode` 实现实例。该实例提供完整的 Unicode 文本处理能力。
- **返回值**: `sk_sp<SkUnicode>` 智能指针，指向新创建的 ICU 后端 Unicode 实例。如果 ICU 库初始化失败，可能返回 `nullptr`。
- **导出属性**: 通过 `SKUNICODE_API` 宏标记为模块导出函数，可在动态库边界使用。
- **线程安全**: 创建的 `SkUnicode` 实例的线程安全性取决于底层 ICU 库的实现。通常 ICU 的只读操作是线程安全的。

## 内部实现细节

该头文件本身没有实现逻辑。实际的 ICU 后端实现位于对应的 `.cpp` 文件中，会链接 ICU 库并实现 `SkUnicode` 接口的所有虚函数，包括：

- **双向文本分析（Bidi）**: 使用 ICU 的 `ubidi.h` 进行双向文本级别计算和视觉重排。
- **断行计算**: 使用 ICU 的 `ubrk.h` 断行迭代器实现行断行和词断行。
- **字符属性查询**: 使用 ICU 的 `uchar.h` 查询字符的 Unicode 通用类别、脚本等属性。
- **大小写转换**: 使用 ICU 的 `ustring.h` 实现区域感知的大小写转换。
- **分词和句子分割**: 使用 ICU 的断行迭代器实现词和句子边界检测。
- **字位簇检测**: 通过 ICU 的字符迭代器确定字位簇（grapheme cluster）边界。

ICU 后端是 SkUnicode 所有后端中功能最完整的实现，能够处理所有 Unicode 文本场景，包括复杂脚本（如阿拉伯语、天城文、泰语等）的正确排版。

## 依赖关系

- **`include/core/SkRefCnt.h`**: 提供 `sk_sp` 智能指针支持，用于引用计数管理。`sk_sp` 是 Skia 的标准智能指针类型，通过侵入式引用计数实现自动内存管理。
- **`modules/skunicode/include/SkUnicode.h`**: 提供 `SkUnicode` 基类定义，声明了所有 Unicode 操作的虚函数接口，是该工厂函数返回类型的基础接口。
- **ICU 库**: 运行时依赖 ICU 动态库或静态库（`libicu`），通常包括 `libicuuc`（通用组件）和 `libicudata`（Unicode 数据）。ICU 库的版本需要与编译时使用的头文件版本匹配。
- **构建系统依赖**: 在 Skia 的构建系统中，ICU 后端的编译需要正确配置 ICU 库的头文件路径和链接选项。通过 `BUILD.gn` 或 `BUILD.bazel` 文件中的条件编译控制。

## 设计模式与设计决策

- **工厂模式**: 采用简洁的命名空间级工厂函数 `Make()`，遵循 Skia 的标准对象创建惯例。
- **后端可插拔设计**: SkUnicode 支持多种后端（ICU、ICU 子集、仅 Bidi 等），每个后端通过独立的工厂函数创建，允许应用程序根据需求和二进制大小约束选择合适的实现。
- **API 导出宏**: 使用 `SKUNICODE_API` 而非 `SK_API`，表明该模块有独立的动态库导出控制，支持作为独立共享库构建。

## 性能考量

- **二进制体积**: ICU 后端提供最完整的 Unicode 支持，但也是最重量级的选择。ICU 库本身体积较大（完整 ICU 数据文件可达数十兆字节），对于二进制大小敏感的场景（如移动端或 WebAssembly），应考虑使用 ICU 子集后端（`SkUnicodes::ICU_Subset`）或仅 Bidi 后端（`SkUnicodes::Bidi`）。
- **初始化开销**: ICU 库的首次初始化涉及内存映射 Unicode 数据文件，可能有数毫秒的开销。建议在应用启动阶段完成初始化，避免在性能敏感路径上首次调用。
- **工厂函数频率**: `Make()` 的调用频率通常很低（应用生命周期内调用一次），因此函数本身的性能不是关注点。创建的 `SkUnicode` 实例应被缓存复用。
- **后端选择建议**: 对于完整的文本排版场景（SkParagraph、复杂脚本支持），推荐使用 ICU 后端。对于仅需双向文本支持的场景（简单的 Lottie 动画文本），可以使用更轻量的 Bidi 后端。

## 相关文件

- `modules/skunicode/include/SkUnicode.h` -- `SkUnicode` 基类接口定义，声明了所有 Unicode 操作的虚函数
- `modules/skunicode/include/SkUnicode_bidi.h` -- 仅 Bidi 功能的轻量级 Unicode 后端工厂
- `modules/skunicode/src/SkUnicode_bidi.cpp` -- Bidi 后端的实现，使用 ICU 子集
- `modules/skunicode/src/SkUnicode.cpp` -- `SkUnicode` 基类的通用工具方法实现（UTF 编码转换等）
- `modules/skunicode/src/SkUnicode_hardcoded.h` -- 硬编码字符属性基类，被 Bidi 后端使用
- `modules/skottie/include/TextShaper.h` -- Skottie 文本排版器，SkUnicode 的主要消费者之一
- `modules/skparagraph/` -- SkParagraph 段落排版模块，SkUnicode 的另一个主要消费者

### 后端选择指南

| 后端 | 工厂函数 | 功能 | 二进制体积 | 适用场景 |
|------|---------|------|-----------|---------|
| ICU 完整版 | `SkUnicodes::ICU::Make()` | 全部 | 最大 | 完整文本排版 |
| ICU 子集 | (内部) | Bidi + 部分断行 | 中等 | 基本文本处理 |
| 仅 Bidi | `SkUnicodes::Bidi::Make()` | 仅 Bidi | 最小 | 双向文本支持 |
