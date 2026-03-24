# skunicode/src - Unicode 支持实现

## 概述

`src/` 目录包含 skunicode 模块所有 Unicode 后端的具体实现代码。这里实现了五种 Unicode 后端:ICU(内置和运行时两种加载模式)、ICU4X、libgrapheme、Client 和 Bidi,以及共享的硬编码字符属性基类和通用静态方法。

ICU 后端是功能最完整的实现,支持所有 Unicode 分析功能。它有两种变体:builtin(静态链接 ICU 数据)和 runtime(运行时动态加载 ICU 共享库)。ICU 的 BiDi 功能被单独封装,允许在精简构建中仅使用 BiDi 分析而不引入完整的 ICU 依赖。

`SkUnicodeHardCodedCharProperties` 是一个重要的基类,它通过 Unicode 码点范围的硬编码查表实现了字符属性分类(如 isControl、isWhitespace、isEmoji 等),不依赖任何外部库。多个后端继承此类以获得零开销的字符分类能力。

## 架构图

```
+------------------------------------------------------------------+
|               SkUnicodeHardCodedCharProperties                    |
|  (硬编码字符属性基类 - 不依赖外部库)                               |
|  isControl / isWhitespace / isEmoji / isIdeographic 等            |
+-------+-------+-------+-------+-------+--------------------------+
        |       |       |       |       |
        v       v       v       v       v
+------+ +------+ +------+ +------+ +------+
|ICU   | |ICU4X | |libgr | |Client| |Bidi  |
|后端  | |后端  | |后端  | |后端  | |后端  |
+--+---+ +------+ +------+ +------+ +--+---+
   |                                    |
   +--+--+                        +-----+----+
   |     |                        |          |
   v     v                        v          v
+------+ +-------+          +---------+ +---------+
|builtin| |runtime|          |icu_full | |icu_subset|
|(静态) | |(动态) |          |BiDi工厂 | |BiDi工厂 |
+------+ +-------+          +---------+ +---------+
   |        |                     |          |
   v        v                     v          v
+------------------+         +-----------------+
| ICU 库           |         | ICU BiDi 子集   |
| (完整Unicode数据)|         | (仅 ubidi)      |
+------------------+         +-----------------+
```

## 目录结构

```
src/
|-- BUILD.bazel                      # Bazel 构建规则
|-- SkUnicode.cpp                    # 通用静态方法(标志位检测/编码转换/extractBidi)
|-- SkUnicode_hardcoded.cpp          # 硬编码字符属性实现
|-- SkUnicode_hardcoded.h            # 硬编码字符属性基类
|-- SkUnicode_icu.cpp                # ICU 通用实现(共享于builtin和runtime)
|-- SkUnicode_icupriv.h              # ICU 内部辅助(函数指针类型定义)
|-- SkUnicode_icu_builtin.cpp        # ICU 静态链接版(直接调用ICU函数)
|-- SkUnicode_icu_runtime.cpp        # ICU 运行时加载版(dlopen/dlsym)
|-- SkUnicode_icu_bidi.cpp           # ICU BiDi 功能封装
|-- SkUnicode_icu_bidi.h             # ICU BiDi 头文件
|-- SkBidiFactory_icu_full.cpp       # 完整ICU BiDi工厂(链接完整ICU)
|-- SkBidiFactory_icu_full.h         # 完整ICU BiDi工厂头文件
|-- SkBidiFactory_icu_subset.cpp     # 精简ICU BiDi工厂(仅链接ubidi)
|-- SkBidiFactory_icu_subset.h       # 精简ICU BiDi工厂头文件
|-- SkUnicode_icu4x.cpp              # ICU4X 后端实现
|-- SkUnicode_libgrapheme.cpp        # libgrapheme 后端实现
|-- SkUnicode_client.cpp             # Client 后端实现(使用预计算数据)
|-- SkUnicode_bidi.cpp               # Bidi 后端实现(仅BiDi支持)
```

## 关键类与函数

### SkUnicode.cpp - 通用静态方法

```cpp
// 标志位检测辅助
static bool hasTabulationFlag(CodeUnitFlags flags);
static bool hasHardLineBreakFlag(CodeUnitFlags flags);
static bool hasSoftLineBreakFlag(CodeUnitFlags flags);
static bool hasGraphemeStartFlag(CodeUnitFlags flags);
static bool hasControlFlag(CodeUnitFlags flags);
static bool hasPartOfWhiteSpaceBreakFlag(CodeUnitFlags flags);

// 编码转换
static SkString convertUtf16ToUtf8(const char16_t*, int);
static std::u16string convertUtf8ToUtf16(const char*, int);

// BiDi 提取(使用 makeBidiIterator)
static bool extractBidi(const char utf8[], int utf8Units,
                        TextDirection dir, std::vector<BidiRegion>* regions);
```

### SkUnicode_hardcoded.cpp/h - 硬编码字符属性

```cpp
class SkUnicodeHardCodedCharProperties : public SkUnicode {
    // 通过 Unicode 码点范围直接判断字符属性
    // 不依赖任何外部库,编译为简单的范围比较
    bool isControl(SkUnichar) override;        // 0x00-0x1F, 0x7F-0x9F 等
    bool isWhitespace(SkUnichar) override;     // 0x20, 0xA0, 0x2000-0x200A 等
    bool isSpace(SkUnichar) override;          // 0x20 (ASCII空格)
    bool isTabulation(SkUnichar) override;     // 0x09 (Tab)
    bool isHardBreak(SkUnichar) override;      // 0x0A (LF), 0x0D (CR) 等
    bool isEmoji(SkUnichar) override;          // Emoji 码点范围
    bool isEmojiComponent(SkUnichar) override; // ZWJ, VS16, 肤色修饰等
    bool isEmojiModifierBase(SkUnichar) override;
    bool isEmojiModifier(SkUnichar) override;  // 0x1F3FB-0x1F3FF (肤色)
    bool isRegionalIndicator(SkUnichar) override; // 0x1F1E6-0x1F1FF (国旗)
    bool isIdeographic(SkUnichar) override;    // CJK 统一汉字等
};
```

### SkUnicode_icu.cpp - ICU 后端通用实现

```cpp
// ICU 后端的共享实现,builtin 和 runtime 变体共用此文件
class SkUnicode_icu : public SkUnicodeHardCodedCharProperties {
    // 使用 ICU 的 ubrk (break iterator) 进行文本分割
    bool getWords(...) override;       // UBRK_WORD
    bool getUtf8Words(...) override;   // UBRK_WORD (UTF-8索引)
    bool getSentences(...) override;   // UBRK_SENTENCE
    bool computeCodeUnitFlags(...) override;  // 组合多种分析结果

    // 使用 ICU 的 ubidi 进行 BiDi 分析
    bool getBidiRegions(...) override;
    std::unique_ptr<SkBidiIterator> makeBidiIterator(...) override;

    // 使用 ICU 的 ubrk 创建断点迭代器
    std::unique_ptr<SkBreakIterator> makeBreakIterator(...) override;

    // 大小写转换
    SkString toUpper(const SkString&) override;        // u_strToUpper
    SkString toUpper(const SkString&, const char*) override;

    // BiDi 重排序
    void reorderVisual(const BidiLevel[], int, int32_t[]) override; // ubidi_reorderVisual
};
```

### SkUnicode_icu_builtin.cpp vs SkUnicode_icu_runtime.cpp

| 特性 | builtin (内置) | runtime (运行时) |
|------|---------------|-----------------|
| ICU 链接方式 | 静态链接 | dlopen/dlsym 动态加载 |
| 二进制大小 | 较大(包含 ICU 数据) | 较小(依赖系统 ICU) |
| 部署要求 | 自包含 | 需要系统安装 ICU |
| 函数调用 | 直接调用 | 通过函数指针调用 |
| 使用场景 | 嵌入式/自包含部署 | 系统已有 ICU 的场景 |

### SkUnicode_icu_bidi.cpp/h - ICU BiDi 封装

```cpp
// 将 ICU 的 ubidi API 封装为 SkBidiIterator 接口
// 支持两种 BiDi 工厂:
// - SkBidiFactory_icu_full: 链接完整 ICU(数据内置)
// - SkBidiFactory_icu_subset: 仅链接 ubidi 子集(最小依赖)
```

### SkUnicode_icu4x.cpp - ICU4X 后端

```cpp
// 使用 ICU4X (Rust 实现) 的 C FFI 绑定
// ICU4X 提供了现代的、模块化的 Unicode 实现
// 数据通过 compiled_data 特性编译到二进制中
// 支持: 文本分割、字符属性、BiDi
```

### SkUnicode_libgrapheme.cpp - libgrapheme 后端

```cpp
// 使用 libgrapheme (suckless 项目) 的轻量级 Unicode 分割
// 优势: 极小的代码和数据大小
// 支持: 字素簇分割、行断点、词边界
// 限制: 不支持完整的 BiDi(使用硬编码回退)
```

### SkUnicode_client.cpp - Client 后端

```cpp
// 使用客户端预计算的 Unicode 数据
// 适用于 Flutter Web 等场景:浏览器/JS 侧计算 Unicode 属性后传入
// 参数: 预计算的 words[], graphemeBreaks[], lineBreaks[]
// 优势: 无需链接任何 Unicode 库
// 限制: 不支持动态文本分析(仅使用预计算数据)
```

### SkUnicode_bidi.cpp - Bidi 后端

```cpp
// 仅提供 BiDi 分析功能的最小后端
// 适用于只需要双向文本支持的精简构建
// 字符属性使用硬编码基类
// 文本分割功能未实现或使用简单回退
```

## 依赖关系

```
src/
  |-- include/ (SkUnicode.h 等公共接口)
  |-- Skia Core
  |   |-- SkRefCnt, SkString, SkSpan, SkTypes
  |   |-- SkTArray, SkTHash
  |   |-- SkUTF (src/base/SkUTF.h)
  |   |-- SkMutex (线程安全)
  |
  |-- ICU (SkUnicode_icu*.cpp)
  |   |-- unicode/uchar.h (字符属性)
  |   |-- unicode/ubidi.h (BiDi 算法)
  |   |-- unicode/ubrk.h (断点迭代)
  |   |-- unicode/utext.h (文本访问)
  |   |-- unicode/ustring.h (字符串操作)
  |
  |-- ICU4X (SkUnicode_icu4x.cpp)
  |   |-- ICU4X C FFI 绑定头文件
  |
  |-- libgrapheme (SkUnicode_libgrapheme.cpp)
  |   |-- grapheme.h
  |
  |-- 无外部依赖 (SkUnicode_client.cpp, SkUnicode_hardcoded.cpp)
```

## 设计模式分析

### 1. 继承层次结构

```
SkRefCnt
  |
  v
SkUnicode (抽象接口)
  |
  v
SkUnicodeHardCodedCharProperties (字符分类硬编码)
  |
  +-- SkUnicode_icu (ICU 完整实现)
  +-- SkUnicode_icu4x (ICU4X 实现)
  +-- SkUnicode_libgrapheme (libgrapheme 实现)
  +-- SkUnicode_client (Client 预计算)
  +-- SkUnicode_bidi (仅 BiDi)
```

### 2. 桥接模式 (Bridge Pattern)
ICU 后端的 builtin/runtime 变体使用了桥接模式:`SkUnicode_icu.cpp` 包含业务逻辑,通过 `SkUnicode_icupriv.h` 中定义的函数指针类型与 ICU 库交互。builtin 变体直接绑定 ICU 函数,runtime 变体通过 dlsym 动态获取函数指针。

### 3. 工厂方法模式
每个后端通过独立的工厂函数创建(`SkUnicodes::ICU::Make()` 等)。BiDi 功能额外提供了两级工厂:BiDi 工厂(icu_full/icu_subset)用于创建 BiDi 迭代器。

### 4. 组合模式
`computeCodeUnitFlags()` 方法组合了多种分析结果:
1. 使用 BreakIterator(kLines) 获取行断点
2. 使用 BreakIterator(kGraphemes) 获取字素簇
3. 使用 BreakIterator(kWords) 获取词边界
4. 使用字符分类函数标记特殊字符
5. 将所有信息合并到 `CodeUnitFlags[]` 数组中

## 数据流

```
SkUnicodes::XXX::Make()
  |
  +-- [ICU builtin 路径]
  |   直接使用 ICU 函数 -> SkUnicode_icu 实例
  |
  +-- [ICU runtime 路径]
  |   dlopen("libicuuc.so") -> 获取函数指针 -> SkUnicode_icu 实例
  |
  +-- [ICU4X 路径]
  |   创建 ICU4X data provider -> SkUnicode_icu4x 实例
  |
  +-- [libgrapheme 路径]
  |   无初始化 -> SkUnicode_libgrapheme 实例
  |
  +-- [Client 路径]
  |   接收预计算数据 -> SkUnicode_client 实例
  |
  v
computeCodeUnitFlags(utf8, replaceTabs, results[]) 执行流程:
  |
  +-- 初始化 results[] 为 kNoCodeUnitFlag
  |
  +-- 使用 makeBreakIterator(kLines) 遍历行断点
  |   for each 断点位置: results[pos] |= kSoftLineBreakBefore 或 kHardLineBreakBefore
  |
  +-- 使用 makeBreakIterator(kGraphemes) 遍历字素簇
  |   for each 字素簇起始: results[pos] |= kGraphemeStart
  |
  +-- 使用 makeBreakIterator(kWords) 遍历词边界
  |   for each 词边界: results[pos] |= kWordBreak
  |
  +-- 遍历每个代码单元:
  |   if isWhitespace(ch): results[pos] |= kPartOfWhiteSpaceBreak
  |   if isControl(ch): results[pos] |= kControl
  |   if isTabulation(ch): results[pos] |= kTabulation
  |   if isIdeographic(ch): results[pos] |= kIdeographic
  |   if isEmoji(ch): results[pos] |= kEmoji
  |   if replaceTabs && isTabulation(ch): 替换为空格
  |
  +-- 输出: results[] 完整标志位数组
```

## 相关文档与参考

- **公共接口**: `modules/skunicode/include/` - API 定义
- **测试**: `modules/skunicode/tests/SkUnicodeTest.cpp` - Unicode 功能测试
- **ICU 项目**: https://icu.unicode.org/
- **ICU4X 项目**: https://github.com/unicode-org/icu4x
- **libgrapheme**: https://libs.suckless.org/libgrapheme/
- **Unicode 算法**: UAX #9 (BiDi), UAX #14 (Line Breaking), UAX #29 (Text Segmentation)
