# SkUnicode_bidi.cpp

> 源文件: `modules/skunicode/src/SkUnicode_bidi.cpp`

## 概述

`SkUnicode_bidi.cpp` 实现了一个轻量级的 `SkUnicode` 后端，专注于 Unicode 双向文本（Bidi）处理功能。该实现继承自 `SkUnicodeHardCodedCharProperties`，仅完整实现了 Bidi 相关操作（双向迭代器创建、Bidi 区域提取、视觉重排序），而将其他 Unicode 功能（如断行、分词、大小写转换等）标记为未实现。这种设计使得对于仅需要 Bidi 支持的应用场景，可以避免引入完整 ICU 库的体积开销。

## 架构位置

该文件位于 `modules/skunicode/src/` 目录下，是 SkUnicode 模块的后端实现之一。在 SkUnicode 的多后端架构中，`SkUnicode_bidi` 是最轻量的选择，位于 ICU 完整后端和完全无 Unicode 支持之间。它通过 `SkBidiSubsetFactory` 使用 ICU 子集来提供 Bidi 功能，适用于二进制大小敏感但需要正确处理阿拉伯语、希伯来语等双向文本的场景。

## 主要类与结构体

### `SkUnicode_bidi`
```cpp
class SkUnicode_bidi : public SkUnicodeHardCodedCharProperties
```
- **继承**: `SkUnicodeHardCodedCharProperties`（提供硬编码的字符属性查询，如 `isSpace()`、`isWhitespace()` 等）
- **职责**: 实现 `SkUnicode` 接口，提供 Bidi 相关功能，其余功能返回失败或 nullptr。
- **成员变量**:
  - `fBidiFact`: `sk_sp<SkBidiFactory>` 类型，初始化为 `SkBidiSubsetFactory` 实例，负责实际的 Bidi 操作。

## 公共 API 函数

### 已实现的 Bidi 功能

#### `makeBidiIterator(const uint16_t[], int, Direction)`
```cpp
std::unique_ptr<SkBidiIterator> makeBidiIterator(const uint16_t text[], int count,
                                                  SkBidiIterator::Direction dir) override;
```
- **功能**: 为 UTF-16 文本创建双向文本迭代器。迭代器用于逐段遍历文本中的 Bidi 级别。
- **实现**: 委托给内部 `fBidiFact->MakeIterator()`，传入文本缓冲区、代码单元数量和默认方向。

#### `getBidiRegions(const char[], int, TextDirection, std::vector<BidiRegion>*)`
```cpp
bool getBidiRegions(const char utf8[], int utf8Units, TextDirection dir,
                    std::vector<BidiRegion>* results) override;
```
- **功能**: 从 UTF-8 文本中提取 Bidi 区域信息，标记每段文本的方向（LTR/RTL）。
- **实现**: 委托给 `fBidiFact->ExtractBidi()`。

#### `reorderVisual(const BidiLevel[], int, int32_t[])`
```cpp
void reorderVisual(const BidiLevel runLevels[], int levelsCount,
                   int32_t logicalFromVisual[]) override;
```
- **功能**: 将逻辑顺序的 Bidi 级别数组重排为视觉显示顺序。
- **实现**: 在级别数非零时委托给 `fBidiFact->bidi_reorderVisual()`，空输入直接返回以避免 ICU 断言失败。

#### `computeCodeUnitFlags(char16_t[], int, bool, TArray<CodeUnitFlags, true>*)`
```cpp
bool computeCodeUnitFlags(char16_t utf16[], int utf16Units, bool replaceTabs,
                          TArray<SkUnicode::CodeUnitFlags, true>* results) override;
```
- **功能**: 为 UTF-16 文本计算每个代码单元的属性标志。
- **实现**: 遍历每个字符，使用硬编码属性检测空格、空白、控制字符和表意文字。

### 未实现的功能（返回失败/nullptr）

- `makeBidiIterator(const char[], int, Direction)` -- UTF-8 版本的 Bidi 迭代器（需要先进行 UTF-8 到 UTF-16 的编码转换，该实现选择不支持）
- `makeBreakIterator()` -- 断行/分词迭代器（需要完整的 ICU 断行数据）
- `getUtf8Words()` -- UTF-8 文本的分词功能
- `getSentences()` -- 句子边界分割
- `computeCodeUnitFlags(char[], int, bool, ...)` -- UTF-8 版本的标志计算
- `getWords()` -- 通用分词功能
- `toUpper()` -- 大写转换（需要 ICU 的区域感知大小写映射数据）

### 工厂函数

#### `SkUnicodes::Bidi::Make()`
```cpp
namespace SkUnicodes::Bidi {
    sk_sp<SkUnicode> Make();
}
```
- **功能**: 创建并返回 `SkUnicode_bidi` 实例。

## 内部实现细节

- **ICU 子集使用**: 通过 `SkBidiSubsetFactory` 使用 ICU 的 Bidi 子集功能，而非完整 ICU 库，显著减小二进制体积。子集仅包含 `ubidi.h` 相关的 Bidi 算法实现，不包含断行、分词等其他 ICU 功能。
- **硬编码字符属性**: 继承自 `SkUnicodeHardCodedCharProperties`，使用内置的查找表而非 ICU 的 `u_isspace()` 等函数来判断字符属性，避免额外的 ICU 数据依赖。硬编码属性覆盖了 ASCII 范围内的常用字符，对于非 ASCII 字符可能不够准确。
- **UTF-16 代码单元标志计算**: `computeCodeUnitFlags` 的 UTF-16 版本是唯一完整实现的标志计算方法，分配 `utf16Units + 1` 大小的数组（多一个用于末尾哨兵），逐字符检测以下四种属性标志：
  - `kPartOfIntraWordBreak`: 通过 `isSpace()` 检测空格字符
  - `kPartOfWhiteSpaceBreak`: 通过 `isWhitespace()` 检测空白字符
  - `kControl`: 通过 `isControl()` 检测控制字符
  - `kIdeographic`: 通过 `isIdeographic()` 检测表意文字（CJK 等）
- **空输入保护**: `reorderVisual` 中对空输入（`levelsCount == 0`）做了早期返回，避免 ICU 库内部的断言失败。这是一个防御性编程实践。
- **未实现方法的调试输出**: 所有未实现的方法在 DEBUG 构建中通过 `SkDEBUGF` 输出提示消息，帮助开发者识别功能缺失。Release 构建中这些输出被编译器优化掉。
- **UTF-8 到 UTF-16 的不对称实现**: Bidi 迭代器仅实现了 UTF-16 版本，因为 ICU 的 Bidi 算法原生操作 UTF-16 数据。UTF-8 版本需要先进行编码转换，该实现选择不支持以保持简洁。

## 依赖关系

- **`modules/skunicode/include/SkUnicode.h`**: `SkUnicode` 基类接口
- **`modules/skunicode/include/SkUnicode_bidi.h`**: 对应的公共头文件
- **`modules/skunicode/src/SkBidiFactory_icu_subset.h`**: ICU 子集 Bidi 工厂
- **`modules/skunicode/src/SkUnicode_hardcoded.h`**: 硬编码字符属性基类
- **`modules/skunicode/src/SkUnicode_icu_bidi.h`**: ICU Bidi 接口封装
- **ICU 头文件**: `<unicode/ubidi.h>`, `<unicode/ubrk.h>`, `<unicode/uchar.h>` 等，用于底层 Bidi 操作
- **`src/base/SkUTF.h`**: UTF 编码工具
- **`src/base/SkBitmaskEnum.h`**: 枚举位掩码运算

## 设计模式与设计决策

- **策略模式 + 空对象模式**: 未实现的方法不抛异常，而是返回 `nullptr`/`false` 并输出调试信息，允许调用方优雅降级。这使得 SkUnicode_bidi 可以作为完整后端的替代品在功能受限的场景下使用。
- **组合优于继承**: Bidi 功能通过组合 `SkBidiFactory`（`fBidiFact` 成员）来实现，而非直接继承 ICU 的 Bidi 类，保持了灵活性。如果未来需要替换为其他 Bidi 算法实现（如 SheenBidi 或 Fribidi），只需替换工厂实例即可。
- **分层精简策略**: 与完整的 ICU 后端相比，该实现通过选择性地实现接口方法，在功能完整性和二进制体积之间取得平衡。这是 Skia 一贯的模块化设计哲学的体现。
- **工厂函数命名空间**: `SkUnicodes::Bidi::Make()` 使用嵌套命名空间，与 `SkUnicodes::ICU::Make()` 保持一致的 API 风格，方便用户在不同后端间切换。
- **调试信息的条件编译**: 未实现方法中的 `SkDEBUGF` 仅在 DEBUG 构建中输出，Release 构建中完全消除，不影响性能或二进制大小。

## 性能考量

- **轻量级实例化**: `SkBidiSubsetFactory` 的创建开销远小于完整 ICU 初始化。工厂对象在 `SkUnicode_bidi` 构造时以 `sk_make_sp` 创建，仅涉及少量内存分配。
- **硬编码字符属性**: 基于查找表的字符属性查询比 ICU 的通用查询更快（无需加载 ICU 数据文件），虽然覆盖范围有限于常见字符集。
- **代码单元标志的线性扫描**: `computeCodeUnitFlags` 对每个 UTF-16 代码单元执行 O(1) 的属性检测（四次位或操作），整体为 O(n) 复杂度。对于典型的文本长度（数百到数千字符），性能完全满足实时排版需求。
- **二进制体积优势**: 相比完整 ICU 后端可节省数兆字节的二进制体积，适合资源受限的部署场景。具体节省取决于 ICU 库的链接方式（静态链接节省最为显著）。
- **Bidi 算法本身的复杂度**: ICU Bidi 算法（Unicode Bidirectional Algorithm, UBA）的复杂度为 O(n)，其中 n 为文本长度。对于大多数文本，Bidi 处理不会成为性能瓶颈。
- **内存分配**: `computeCodeUnitFlags` 使用 `TArray::push_back_n` 一次性分配结果数组，避免了多次增长分配的开销。

## 相关文件

- `modules/skunicode/include/SkUnicode.h` -- 基类接口，定义了所有 Unicode 操作的虚函数签名
- `modules/skunicode/include/SkUnicode_bidi.h` -- Bidi 后端的公共头文件和工厂函数声明
- `modules/skunicode/include/SkUnicode_icu.h` -- ICU 完整后端工厂，功能全面但体积更大
- `modules/skunicode/src/SkUnicode.cpp` -- 基类通用方法实现（UTF 编码转换、标志查询等）
- `modules/skunicode/src/SkBidiFactory_icu_subset.h` -- ICU 子集 Bidi 工厂，封装了 ICU Bidi API 的子集
- `modules/skunicode/src/SkUnicode_hardcoded.h` -- 硬编码字符属性基类，提供 `isSpace()` 等基础属性查询
- `modules/skunicode/src/SkUnicode_icu_bidi.h` -- ICU Bidi 接口的 C++ 封装层

### 功能覆盖矩阵

| 功能 | SkUnicode_bidi | ICU 完整后端 |
|------|---------------|-------------|
| Bidi 迭代器 (UTF-16) | 已实现 | 已实现 |
| Bidi 迭代器 (UTF-8) | 未实现 | 已实现 |
| Bidi 区域提取 | 已实现 | 已实现 |
| 视觉重排序 | 已实现 | 已实现 |
| 代码单元标志 (UTF-16) | 已实现（基础） | 已实现（完整） |
| 代码单元标志 (UTF-8) | 未实现 | 已实现 |
| 断行迭代器 | 未实现 | 已实现 |
| 分词 | 未实现 | 已实现 |
| 句子分割 | 未实现 | 已实现 |
| 大小写转换 | 未实现 | 已实现 |
