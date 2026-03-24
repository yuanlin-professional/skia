# SkUnicodeHardCodedCharProperties

> 源文件: modules/skunicode/src/SkUnicode_hardcoded.h, modules/skunicode/src/SkUnicode_hardcoded.cpp

## 概述

`SkUnicodeHardCodedCharProperties` 是一个硬编码的 Unicode 字符属性实现类,提供基本的字符分类功能而无需依赖外部 Unicode 库。该类继承自 `SkUnicode` 接口,通过静态定义的字符范围和查找表来判断字符属性,为 Skia 提供轻量级的 Unicode 支持。

这个实现主要用于不需要完整 Unicode 支持或者需要减小二进制大小的场景,它提供了基本的字符分类方法,包括控制字符、空白字符、表意文字等的识别。

## 架构位置

该类位于 Skia 的 Unicode 模块 (skunicode) 中,是 Unicode 支持层的备用实现:

```
skia/
├── modules/
│   └── skunicode/              # Unicode 处理模块
│       ├── include/
│       │   └── SkUnicode.h     # Unicode 接口定义
│       └── src/
│           ├── SkUnicode_hardcoded.h    # 硬编码实现头文件
│           ├── SkUnicode_hardcoded.cpp  # 硬编码实现源文件
│           ├── SkUnicode_icu.cpp        # ICU 完整实现
│           └── SkUnicode_icu4x.cpp      # ICU4X 实现
```

该类作为轻量级替代方案,与 ICU 等完整实现并存,允许应用根据需求选择合适的实现。

## 主要类与结构体

### SkUnicodeHardCodedCharProperties

```cpp
class SKUNICODE_API SkUnicodeHardCodedCharProperties : public SkUnicode
```

**核心成员方法:**
- `isControl()` - 检查是否为控制字符
- `isWhitespace()` - 检查是否为空白字符
- `isSpace()` - 检查是否为空格字符
- `isTabulation()` - 检查是否为制表符
- `isHardBreak()` - 检查是否为硬换行符
- `isEmoji()` - 检查是否为 Emoji 字符
- `isEmojiComponent()` - 检查是否为 Emoji 组件
- `isEmojiModifierBase()` - 检查是否为 Emoji 修饰基础
- `isEmojiModifier()` - 检查是否为 Emoji 修饰符
- `isRegionalIndicator()` - 检查是否为区域指示符
- `isIdeographic()` - 检查是否为表意文字

## 公共 API 函数

### isControl(SkUnichar utf8)

判断字符是否为控制字符。

```cpp
bool isControl(SkUnichar utf8) override;
```

**实现逻辑:**
- 检查字符是否在 ASCII 控制范围 (0x00-0x1F)
- 检查字符是否在扩展控制范围 (0x7F-0x9F)
- 检查字符是否在零宽度连接符范围 (0x200D-0x200F)
- 检查字符是否在双向文本控制范围 (0x202A-0x202E)

### isWhitespace(SkUnichar unichar)

判断字符是否为空白字符,使用硬编码的 21 个空白字符列表。

```cpp
bool isWhitespace(SkUnichar unichar) override;
```

**硬编码的空白字符包括:**
- 基本空白符:制表符(0x0009)、换行(0x000A)、垂直制表(0x000B)、换页(0x000C)、回车(0x000D)、空格(0x0020)
- Unicode 空白符:Ogham 空格标记(0x1680)、各种宽度的空格(0x2000-0x200A)
- 段落分隔符:行分隔符(0x2028)、段落分隔符(0x2029)
- 数学空格:中等数学空格(0x205F)、表意空格(0x3000)

### isSpace(SkUnichar unichar)

判断字符是否为空格字符,比 `isWhitespace()` 包含更多字符(25 个)。

```cpp
bool isSpace(SkUnichar unichar) override;
```

**额外包含的字符:**
- 下一行符号(0x0085)
- 不间断空格(0x00A0)
- 图形空格(0x2007)
- 窄不间断空格(0x202F)

### isTabulation(SkUnichar utf8)

简单检查字符是否为制表符。

```cpp
bool isTabulation(SkUnichar utf8) override;
```

返回 `utf8 == '\t'`。

### isHardBreak(SkUnichar utf8)

检查字符是否为硬换行符。

```cpp
bool isHardBreak(SkUnichar utf8) override;
```

识别两种硬换行:
- `\n` (换行符)
- `\u2028` (行分隔符)

### isIdeographic(SkUnichar unichar)

判断字符是否为表意文字,使用硬编码的 Unicode 范围。

```cpp
bool isIdeographic(SkUnichar unichar) override;
```

**表意文字范围包括:**
- Hangul Jamo (4352-4607)
- CJK Radicals (11904-42191)
- Phags_Pa (43072-43135)
- Hangul Syllables (44032-55215)
- CJK Compatibility Ideographs (63744-64255)
- CJK Compatibility Forms (65072-65103)
- Katakana/Hangul Halfwidth (65381-65500)
- Supplementary Ideographic Plane (131072-196607)

### Emoji 相关方法

以下 Emoji 相关方法未实现,调用时会触发调试断言:

```cpp
bool isEmoji(SkUnichar unichar) override;
bool isEmojiComponent(SkUnichar utf8) override;
bool isEmojiModifier(SkUnichar utf8) override;
bool isEmojiModifierBase(SkUnichar utf8) override;
bool isRegionalIndicator(SkUnichar unichar) override;
```

## 内部实现细节

### 字符查找策略

该实现使用两种查找策略:

1. **静态数组 + 二分查找**:用于空白字符和空格字符
   ```cpp
   static constexpr std::array<SkUnichar, 21> whitespaces { ... };
   return std::find(whitespaces.begin(), whitespaces.end(), unichar) != whitespaces.end();
   ```

2. **范围检查**:用于表意文字
   ```cpp
   static constexpr std::array<std::pair<SkUnichar, SkUnichar>, 8> ranges {{ ... }};
   for (auto range : ranges) {
       if (range.first <= unichar && range.second > unichar) {
           return true;
       }
   }
   ```

### 性能优化

- 使用 `constexpr` 确保数据在编译时初始化
- 使用 `std::array` 而非动态分配,避免运行时开销
- 范围检查采用短路逻辑,找到匹配即返回

## 依赖关系

**直接依赖:**
- `include/core/SkTypes.h` - Skia 基础类型定义
- `modules/skunicode/include/SkUnicode.h` - Unicode 接口基类
- `src/base/SkUTF.h` - UTF 编码处理工具

**被依赖:**
- `SkUnicode_libgrapheme.cpp` - 继承此类实现字符属性
- `SkUnicode_client.cpp` - 继承此类实现字符属性
- `SkUnicode_icu4x.cpp` - 可能使用此类作为备用

## 设计模式与设计决策

### 继承模式

采用公共继承自 `SkUnicode`,实现接口的一个子集,允许在不需要完整 Unicode 支持时使用轻量级实现。

### 硬编码数据

**优点:**
- 无需外部 Unicode 数据库,减小二进制大小
- 运行时性能稳定,无需动态查询
- 编译时初始化,零启动成本

**缺点:**
- 不支持新的 Unicode 标准
- Emoji 支持缺失
- 功能有限,仅支持基本字符分类

### 部分实现策略

对于 Emoji 相关功能,采用断言失败的方式明确表示未实现,而非返回错误的结果。这种设计让调用者在开发阶段就能发现问题。

## 性能考量

### 时间复杂度

- `isControl()`: O(1) - 简单的范围检查
- `isWhitespace()`: O(n) - 线性查找,n=21
- `isSpace()`: O(n) - 线性查找,n=25
- `isIdeographic()`: O(n) - 范围查找,n=8
- `isTabulation()`: O(1) - 直接比较
- `isHardBreak()`: O(1) - 两次比较

### 空间复杂度

- 空白字符数组:21 × 4 字节 = 84 字节
- 空格字符数组:25 × 4 字节 = 100 字节
- 表意文字范围:8 × 8 字节 = 64 字节
- 总计:约 250 字节静态数据

### 优化特点

1. 所有数据都是编译时常量,存储在只读数据段
2. 不使用动态内存分配
3. 函数都很简单,易于内联优化
4. 适合嵌入式或对二进制大小敏感的场景

## 相关文件

**接口定义:**
- `/modules/skunicode/include/SkUnicode.h` - 基类接口

**其他实现:**
- `/modules/skunicode/src/SkUnicode_icu.cpp` - 基于 ICU 的完整实现
- `/modules/skunicode/src/SkUnicode_icu4x.cpp` - 基于 ICU4X 的实现
- `/modules/skunicode/src/SkUnicode_libgrapheme.cpp` - 基于 libgrapheme 的实现

**使用此类的文件:**
- `/modules/skunicode/src/SkUnicode_libgrapheme.cpp` - 继承字符属性实现
- `/modules/skunicode/src/SkUnicode_client.cpp` - 继承字符属性实现
