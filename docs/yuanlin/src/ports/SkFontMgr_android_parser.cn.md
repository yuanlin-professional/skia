# SkFontMgr_android_parser

> 源文件
> - src/ports/SkFontMgr_android_parser.h
> - src/ports/SkFontMgr_android_parser.cpp

## 概述

`SkFontMgr_android_parser` 是 Skia 字体管理系统中专门为 Android 平台设计的字体配置文件解析器。该模块负责解析 Android 系统的字体配置 XML 文件，提取字体家族、字体文件、语言支持、字体变体等信息，并将这些信息组织成 Skia 可以使用的数据结构。它支持多个 Android 版本的字体配置格式，包括 Android 4.x（JellyBean）和 Android 5.0+（Lollipop）的不同配置方案。

该解析器处理的配置文件包括：
- `/system/etc/fonts.xml` (Android 5.0+)
- `/system/etc/system_fonts.xml` (Android 4.x)
- `/system/etc/fallback_fonts.xml` (Android 4.x fallback)
- `/vendor/etc/fallback_fonts.xml` (Vendor fallback)
- 各种语言特定的 fallback 字体文件

## 架构位置

`SkFontMgr_android_parser` 位于 Skia 的平台适配层（ports）中，专门服务于 Android 平台的字体管理。它在 Skia 字体系统架构中的位置如下：

```
SkFontMgr (抽象接口)
    ↓
SkFontMgr_Android (Android 实现)
    ↓
SkFontMgr_Android_Parser (本模块 - XML 解析)
    ↓
Android 系统字体配置文件 (XML)
```

该模块作为底层解析器，为 Android 字体管理器提供配置数据，使上层能够根据用户请求匹配和加载正确的字体文件。

## 主要类与结构体

### SkLanguage
表示人类书写语言的类，用于文本绘制操作中确定在绘制具有变体的字符（如汉字衍生字符）时使用哪个字形。

**主要成员：**
- `fTag`: BCP 47 语言标识符
- `getTag()`: 获取 BCP 47 语言标识符
- `getParent()`: 执行 BCP 47 回退，返回更通用的语言

### FontFileInfo
描述单个字体文件的信息结构体（可平凡移动）。

**主要成员：**
- `fFileName`: 字体文件名
- `fIndex`: 字体集合中的索引（用于 TTC 文件）
- `fWeight`: 字体粗细（100-900）
- `fStyle`: 字体样式（自动/正常/斜体）
- `fVariationDesignPosition`: 可变字体的轴坐标数组
- `fTypeface`: 缓存的 SkTypeface 指针（可变）

### FontFamily
表示一个字体家族，包含多个字体文件和元数据。

**主要成员：**
- `fNames`: 字体家族名称数组（可能有多个别名）
- `fFonts`: 字体文件信息数组
- `fLanguages`: 支持的语言列表
- `fallbackFamilies`: 嵌套的 fallback 家族映射
- `fVariant`: 字体变体（默认/紧凑/优雅）
- `fOrder`: 解析顺序（内部使用）
- `fIsFallbackFont`: 是否为 fallback 字体
- `fFallbackFor`: fallback 目标家族名称
- `fBasePath`: 字体文件基础路径

### FontVariants (枚举)
定义 Android 字体变体类型：
- `kDefault_FontVariant = 0x01`: 默认变体
- `kCompact_FontVariant = 0x02`: 紧凑变体（用于 UI）
- `kElegant_FontVariant = 0x04`: 优雅变体

### TagHandler
XML 标签处理器结构体，定义了处理特定 XML 标签的回调函数。

**主要成员：**
- `start`: 标签开始时调用
- `end`: 标签结束时调用
- `tag`: 遇到嵌套标签时调用
- `chars`: 字符数据处理器

### FamilyData
表示当前解析状态的结构体。

**主要成员：**
- `fParser`: expat XML 解析器实例
- `fFamilies`: 字体家族集合（输出结果）
- `fCurrentFamily`: 当前正在创建的家族
- `fCurrentFontInfo`: 当前正在创建的字体信息
- `fVersion`: 配置文件版本号
- `fBasePath`: 当前基础路径
- `fIsFallback`: 是否为 fallback 文件
- `fFilename`: 当前解析的文件名
- `fDepth`: 当前元素深度
- `fSkip`: 跳过深度（用于忽略未知标签）
- `fHandler`: 标签处理器栈

## 公共 API 函数

### SkFontMgr_Android_Parser::GetSystemFontFamilies()
```cpp
void GetSystemFontFamilies(std::vector<std::unique_ptr<FontFamily>>& fontFamilies);
```
解析系统字体配置文件并将结果追加到 `fontFamilies` 中。自动检测 Android 版本并选择合适的配置文件。

**处理流程：**
1. 尝试解析 LMP (Android 5.0+) 格式的 `/system/etc/fonts.xml`
2. 如果失败，回退到旧格式 `/system/etc/system_fonts.xml`
3. 如果版本 < 21，追加 fallback 字体和 vendor 字体

### SkFontMgr_Android_Parser::GetCustomFontFamilies()
```cpp
void GetCustomFontFamilies(std::vector<std::unique_ptr<FontFamily>>& fontFamilies,
                           const SkString& basePath,
                           const char* fontsXml,
                           const char* fallbackFontsXml,
                           const char* langFallbackFontsDir = nullptr);
```
解析自定义字体配置文件并将结果追加到 `fontFamilies` 中。允许指定自定义路径和配置文件。

**参数：**
- `fontFamilies`: 输出的字体家族向量
- `basePath`: 字体文件的基础路径
- `fontsXml`: 主字体配置文件路径
- `fallbackFontsXml`: fallback 字体配置文件路径
- `langFallbackFontsDir`: 语言特定 fallback 字体目录

## 内部实现细节

### XML 解析架构

该模块使用 expat XML 解析器，采用了双层命名空间设计来处理不同版本的 Android 字体配置格式：

1. **lmpParser 命名空间**：处理 Android 5.0+ (API 21+) 格式
   - `familySetHandler`: 处理 `<familyset>` 根标签
   - `familyHandler`: 处理 `<family>` 标签
   - `fontHandler`: 处理 `<font>` 标签
   - `axisHandler`: 处理 `<axis>` 标签（可变字体轴）
   - `aliasHandler`: 处理 `<alias>` 标签（字体别名）

2. **jbParser 命名空间**：处理 Android 4.x (JellyBean) 格式
   - `familySetHandler`: 处理 `<familyset>` 根标签
   - `familyHandler`: 处理 `<family>` 标签
   - `nameSetHandler`: 处理 `<nameset>` 标签
   - `nameHandler`: 处理 `<name>` 标签
   - `fileSetHandler`: 处理 `<fileset>` 标签
   - `fileHandler`: 处理 `<file>` 标签

### 版本检测机制

解析器根据 `<familyset>` 标签的 `version` 属性自动选择解析器：
- `version >= 21`: 使用 lmpParser
- `version < 21` 或未指定: 使用 jbParser

### 字符串解析模板函数

#### parse_non_negative_integer()
```cpp
template <typename T> bool parse_non_negative_integer(const char* s, T* value)
```
解析非负整数字符串，检查溢出。实现了安全的整数解析逻辑，避免溢出攻击。

#### parse_fixed()
```cpp
template <int N, typename T> bool parse_fixed(const char* s, T* value)
```
解析定点数字符串，支持负数和小数点。用于解析可变字体轴的样式值（如 wght=400.5）。

**算法特点：**
- 支持格式：`-?((:digit:+(.:digit:+)?)|(.:digit:+))`
- 检查溢出
- 低位舍入（当前实现为截断）
- 需要偏移量 N 来保留符号位和 4 位整数

### Fallback 字体处理

模块支持多层 fallback 机制：

1. **系统 fallback**：从 `/system/etc/fallback_fonts.xml` 加载
2. **Vendor fallback**：从 `/vendor/etc/fallback_fonts.xml` 加载
3. **语言特定 fallback**：从 `fallback_fonts-<locale>.xml` 加载
4. **字体级别 fallback**：通过 `fallbackFor` 属性指定

Vendor fallback 字体按照 `order` 属性插入到正确位置，实现了灵活的字体优先级控制。

### 语言支持

支持 BCP 47 语言标签，包括：
- 多个语言标签（空格分隔）
- 语言回退机制（如 zh-Hans-CN → zh-Hans → zh）
- 语言特定字体配置文件

### 字体变体处理

Android 区分三种字体变体：
- **默认变体**：通用文本渲染
- **紧凑变体**：用于 UI，字符间距更紧密
- **优雅变体**：更美观的字形，适合大尺寸文本

### 安全措施

1. **实体处理禁用**：通过 `xml_entity_decl_handler` 禁用 XML 实体处理，防止 CVE-2013-0340 漏洞
2. **溢出检查**：所有整数和定点数解析都进行溢出检查
3. **内存管理**：使用 Skia 的内存分配函数（sk_malloc_throw, sk_realloc_throw, sk_free）
4. **字符串修剪**：自动去除配置值的前后空白字符

## 依赖关系

### 外部依赖
- **expat**: XML 解析库
- **Android 系统**：依赖 `ANDROID_ROOT` 环境变量

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkFontMgr` | 字体管理器抽象接口 |
| `SkFontArguments` | 字体参数（变体轴坐标） |
| `SkTypeface` | 字体类型接口 |
| `SkString` | 字符串类 |
| `SkTArray` | 动态数组 |
| `SkTDArray` | 动态数组（旧版） |
| `SkTHash` | 哈希表 |
| `SkOSFile` | 文件系统操作 |
| `SkStream` | 文件流 |
| `SkFixed` | 定点数运算 |
| `SkMalloc` | 内存分配 |

## 设计模式与设计决策

### 1. 策略模式（Strategy Pattern）
使用 `TagHandler` 结构体定义标签处理策略，不同的 XML 标签有不同的处理器。这种设计使得添加新的标签类型变得容易。

### 2. 状态模式（State Pattern）
`FamilyData` 结构体维护解析状态，包括当前深度、跳过状态、处理器栈等。这使得递归的 XML 结构能够被正确解析。

### 3. 工厂模式（Factory Pattern）
`topLevelHandler` 根据版本号动态选择使用 lmpParser 或 jbParser，实现了解析器的工厂创建。

### 4. 模板方法模式（Template Method Pattern）
解析流程框架固定（start → chars → nested tags → end），但具体行为由各个 handler 的回调函数定义。

### 5. 向后兼容性设计
通过版本检测和多解析器支持，该模块能够处理从 Android 4.0 到最新版本的配置文件格式。这是关键的设计决策，确保了 Skia 在不同 Android 版本上的兼容性。

### 6. 延迟加载设计
`FontFileInfo` 中的 `fTypeface` 成员使用 mutable，允许延迟创建 SkTypeface 对象，优化了初始化性能。

### 7. 分层 Fallback 设计
支持多层 fallback 机制（系统、vendor、语言、字体级别），提供了灵活的字体回退策略。

## 性能考量

### 1. XML 缓冲策略
使用 `XML_GetBuffer()` 和 `XML_ParseBuffer()` 进行流式解析，避免一次性加载整个文件到内存：
```cpp
static const int bufferSize = 512 SkDEBUGCODE( - 507);
void* buffer = XML_GetBuffer(parser, bufferSize);
```

### 2. 字符串操作优化
- 使用 `memmove` 进行字符串修剪
- 使用 `memcmp` 进行字符串比较
- 宏 `MEMEQ` 简化了字符串比较代码

### 3. 内存分配策略
使用 Skia 的抛出式内存分配器（throw on failure），避免了大量的空指针检查。

### 4. 数组预分配
使用 `SkTArray` 的第二个模板参数（true）启用栈上小数组优化，减少小规模数据的堆分配。

### 5. 移动语义
大量使用 `std::move` 和 `std::unique_ptr`，避免不必要的字体家族数据复制。

### 6. 跳过未知标签
通过 `fSkip` 机制快速跳过不识别的标签，避免处理无用数据。

### 7. 条件编译
Debug 模式下使用小缓冲区（512 - 507 = 5 字节）来检测 `XML_CharacterDataHandler` 中的切片错误。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkFontMgr_android.cpp` | Android 字体管理器实现，使用本解析器 |
| `include/core/SkFontMgr.h` | 字体管理器抽象接口定义 |
| `include/core/SkTypeface.h` | 字体类型接口定义 |
| `include/core/SkFontArguments.h` | 字体参数定义（变体轴等） |
| `src/core/SkOSFile.h` | 跨平台文件操作接口 |
| `src/ports/SkFontHost_FreeType_common.h` | FreeType 通用功能（字体渲染） |
| `src/ports/SkFontMgr_custom.h` | 自定义字体管理器基类 |
| `/system/etc/fonts.xml` | Android 5.0+ 系统字体配置文件 |
| `/system/etc/system_fonts.xml` | Android 4.x 系统字体配置文件 |
| `/system/etc/fallback_fonts.xml` | Android 4.x fallback 字体配置 |
