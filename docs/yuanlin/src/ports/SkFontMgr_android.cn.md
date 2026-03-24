# SkFontMgr_android

> 源文件: include/ports/SkFontMgr_android.h, src/ports/SkFontMgr_android.cpp

## 概述

`SkFontMgr_android` 是 Skia 图形库为 Android 平台提供的字体管理器实现。该模块通过解析 Android 系统的 `fonts.xml` 配置文件来管理系统字体和自定义字体，支持字体回退、语言标签匹配、字符覆盖检测和字体变体（如紧凑型/优雅型）。

该实现是 Android 平台上传统的字体管理方式，与较新的 `SkFontMgr_android_ndk` 相比，它直接解析 XML 配置而不依赖 Android NDK Font API，因此可以在更低版本的 Android 系统上使用。

## 架构位置

```
skia/
├── include/
│   └── ports/
│       └── SkFontMgr_android.h       # 公共接口
└── src/
    └── ports/
        ├── SkFontMgr_android.cpp      # 主实现
        ├── SkFontMgr_android_parser.h # XML 解析器（依赖）
        └── SkTypeface_proxy.h         # 代理字体类型（依赖）
```

该模块位于 `ports` 层，为 Android 平台提供字体管理抽象，是跨平台字体系统的一部分。

## 主要类与结构体

### SkFontMgr_Android_CustomFonts

自定义字体配置结构体。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fSystemFontUse` | SystemFontUse | 系统字体使用策略（枚举） |
| `fBasePath` | const char* | 解析相对路径的基础路径 |
| `fFontsXml` | const char* | 自定义字体配置文件路径 |
| `fFallbackFontsXml` | const char* | 回退字体配置文件路径（旧版） |
| `fIsolated` | bool | 是否在初始化时获取所有系统 I/O 资源 |

**SystemFontUse 枚举值:**

| 枚举值 | 说明 |
|--------|------|
| `kOnlyCustom` | 仅使用自定义字体（符合 NDK 规范） |
| `kPreferCustom` | 优先使用自定义字体，然后是系统字体 |
| `kPreferSystem` | 优先使用系统字体，然后是自定义字体 |

### SkTypeface_AndroidSystem

Android 系统字体的代理实现。

**继承关系:**
- 继承自 `SkTypeface_proxy`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fFamilyName` | SkString | 字体族名称 |
| `fLang` | STArray<4, SkLanguage, true> | 支持的语言标签列表 |
| `fVariantStyle` | FontVariant | 字体变体类型（紧凑/优雅） |

### SkFontStyleSet_Android

Android 字体样式集合。

**继承关系:**
- 继承自 `SkFontStyleSet`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fStyles` | TArray<sk_sp<SkTypeface_AndroidSystem>> | 样式列表 |
| `fFallbackFor` | SkString | 作为哪个字体族的回退 |

### SkFontMgr_Android

Android 字体管理器的核心实现类。

**继承关系:**
- 继承自 `SkFontMgr`

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `fScanner` | std::unique_ptr<SkFontScanner> | 字体扫描器 |
| `fStyleSets` | TArray<sk_sp<SkFontStyleSet_Android>> | 所有字体样式集 |
| `fDefaultStyleSet` | sk_sp<SkFontStyleSet> | 默认字体集 |
| `fNameToFamilyMap` | TArray<NameToFamily, true> | 命名字体族映射 |
| `fFallbackNameToFamilyMap` | TArray<NameToFamily, true> | 回退字体族映射 |

### NameToFamily

名称到字体族的映射结构。

**关键成员变量:**

| 变量名 | 类型 | 说明 |
|--------|------|------|
| `name` | SkString | 字体族名称 |
| `styleSet` | SkFontStyleSet_Android* | 对应的样式集 |

## 公共 API 函数

### SkFontMgr_New_Android

```cpp
SK_API sk_sp<SkFontMgr> SkFontMgr_New_Android(
    const SkFontMgr_Android_CustomFonts* custom,
    std::unique_ptr<SkFontScanner> scanner
);
```

创建 Android 字体管理器。

**参数:**
- `custom`: 自定义字体配置，如果为 `nullptr` 则仅使用系统字体
- `scanner`: 字体扫描器实例，用于解析字体文件

**返回值:**
- `SkFontMgr` 实例的智能指针

**加载顺序:**
1. 如果 `custom != nullptr` 且 `fSystemFontUse != kPreferSystem`：加载自定义字体
2. 如果 `custom == nullptr` 或 `fSystemFontUse != kOnlyCustom`：加载系统字体
3. 如果 `custom != nullptr` 且 `fSystemFontUse == kPreferSystem`：再次加载自定义字体

## 内部实现细节

### 字体族构建流程

1. **解析 XML**: 通过 `SkFontMgr_Android_Parser` 解析 `fonts.xml` 或自定义配置
2. **创建样式集**: 为每个字体族创建 `SkFontStyleSet_Android`
3. **扫描字体**: 使用 `SkFontScanner` 扫描每个字体文件
4. **创建代理**: 创建 `SkTypeface_AndroidSystem` 代理实例
5. **构建映射**: 建立名称到字体族的映射表

### 字体文件缓存

使用 `StreamForPathCache` (即 `THashMap<SkString, std::unique_ptr<SkStreamAsset>>`) 缓存字体文件流，避免重复打开同一文件：

```cpp
std::unique_ptr<SkStreamAsset>* streamPtr = streamForPath.find(pathName);
if (!streamPtr) {
    streamPtr = streamForPath.set(pathName, SkStream::MakeFromFile(pathName.c_str()));
}
```

### 字体变体处理

Android 字体支持两种变体：
- **kCompact_FontVariant**: 紧凑型，保持在上升/下降范围内
- **kElegant_FontVariant**: 优雅型，非压缩样式

默认变体是两者的组合：
```cpp
uint32_t variant = family.fVariant;
if (kDefault_FontVariant == variant) {
    variant = kCompact_FontVariant | kElegant_FontVariant;
}
```

### 字符和语言匹配策略

`onMatchFamilyStyleCharacter` 实现复杂的五级回退策略：

1. **命名字体匹配**: 查找与请求的 `familyName` 匹配的命名字体
2. **回退字体匹配（指定族）**: 查找 `fallback-for` 属性匹配 `familyName` 的回退字体
3. **回退字体匹配（空族）**: 查找 `fallback-for` 为空的回退字体
4. **命名字体匹配（任意）**: 查找所有命名字体（不限 `familyName`）
5. **回退字体匹配（任意）**: 查找所有回退字体（不限 `fallback-for`）

每一级都需要匹配：
- 字体样式（通过 CSS3 匹配算法）
- 语言标签（如果指定）
- 字体变体（优雅型/紧凑型）
- 字符覆盖（通过 `unicharToGlyph`）

### 语言标签匹配

使用 `SkLanguage` 类解析 BCP-47 语言标签，支持从具体到一般的渐进式匹配：

```cpp
SkLanguage lang(bcp47[bcp47Index]);
while (!lang.getTag().isEmpty()) {
    matchingTypeface = find(currentFamilyName, lang.getTag(), elegant);
    if (matchingTypeface) {
        return matchingTypeface;
    }
    lang = lang.getParent();  // zh-Hans-CN -> zh-Hans -> zh -> ""
}
```

### 字体样式计算

从 XML 配置和字体文件中综合确定字体样式：

```cpp
int weight = fontFile.fWeight != 0 ? fontFile.fWeight : fontStyle.weight();
SkFontStyle::Slant slant = fontStyle.slant();
switch (fontFile.fStyle) {
    case FontFileInfo::Style::kAuto: slant = fontStyle.slant(); break;
    case FontFileInfo::Style::kNormal: slant = SkFontStyle::kUpright_Slant; break;
    case FontFileInfo::Style::kItalic: slant = SkFontStyle::kItalic_Slant; break;
}
fontStyle = SkFontStyle(weight, fontStyle.width(), slant);
```

### 回退字体命名

对于没有名称的回退字体，自动生成名称：

```cpp
if (family.fNames.empty()) {
    SkString& fallbackName = family.fNames.push_back();
    fallbackName.printf("%.2x##fallback", (uint32_t)familyIndex);
}
```

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| `SkFontScanner` | 扫描和解析字体文件 |
| `SkFontMgr_android_parser` | 解析 Android fonts.xml 配置 |
| `SkTypeface_proxy` | 字体代理基类 |
| `SkTypefaceCache` | 字体实例缓存 |
| `SkTHash` | 哈希表实现 |
| `SkStream` | 字体文件流 |

### 被依赖的模块

| 模块 | 用途 |
|------|------|
| Skia 字体管理层 | 作为 Android 平台的字体管理器 |
| Android 应用 | 通过 `SkFontMgr_New_Android` 创建实例 |

## 设计模式与设计决策

### 工厂模式

通过 `SkFontMgr_New_Android` 工厂函数创建字体管理器，隐藏实现细节。

### 代理模式

`SkTypeface_AndroidSystem` 继承 `SkTypeface_proxy`，将字体操作委托给底层的真实字体实例，同时添加 Android 特定的元数据（语言、变体）。

### 策略模式

通过 `SkFontScanner` 抽象接口，允许注入不同的字体扫描策略。

### 模板方法模式

`find_family_style_character` 模板函数使用 `Matcher` 函数指针定义匹配策略，允许复用相同的查找逻辑但使用不同的匹配规则。

### 缓存策略

- **StreamForPathCache**: 文件流缓存，避免重复打开文件
- **字体实例共享**: 同一字体文件的多个别名共享同一个 `SkFontStyleSet_Android` 实例

### 渐进式匹配

语言标签和字体族匹配都采用从具体到一般的渐进式策略，提高匹配成功率。

## 性能考量

### 初始化性能

- 解析 XML 配置文件
- 扫描所有配置的字体文件
- 构建名称到字体族的映射

优化策略：
- 使用 `streamForPath` 缓存避免重复文件 I/O
- 延迟加载字体实例（仅在需要时创建）
- `isolated` 模式可选择在初始化时加载所有资源

### 查找性能

- 名称匹配：线性搜索 `fNameToFamilyMap` 和 `fFallbackNameToFamilyMap`（O(n)）
- 字符匹配：可能遍历所有字体和样式（最坏 O(n*m)）

优化策略：
- 大小写不敏感匹配使用预计算的小写名称
- 优先搜索命名字体和指定回退族

### 内存使用

- 所有字体样式集保存在内存中
- 字体文件流可能被缓存
- 每个字体族可能有多个别名条目

### 线程安全

该实现不提供内部线程同步，需要外部保证线程安全，或者为每个线程创建独立的字体管理器实例。

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `include/ports/SkFontMgr_android.h` | 公共 API 头文件 |
| `src/ports/SkFontMgr_android.cpp` | 主实现文件 |
| `src/ports/SkFontMgr_android_parser.h` | Android fonts.xml 解析器 |
| `src/ports/SkFontMgr_android_parser.cpp` | 解析器实现 |
| `src/ports/SkTypeface_proxy.h` | 字体代理基类 |
| `include/core/SkFontMgr.h` | 字体管理器基类 |
| `include/core/SkFontScanner.h` | 字体扫描器接口 |
| `src/core/SkTypefaceCache.h` | 字体实例缓存 |
