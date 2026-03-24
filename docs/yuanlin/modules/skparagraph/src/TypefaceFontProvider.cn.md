# TypefaceFontProvider - 自定义字体提供器

> 源文件: `modules/skparagraph/src/TypefaceFontProvider.cpp`

## 概述

TypefaceFontProvider 是 SkFontMgr 的一个具体实现，允许应用程序通过编程方式注册和管理自定义字体。它维护一个按字体族名索引的字体集合，支持按名称查找字体族、按样式匹配字体。该类与 TypefaceFontStyleSet 配合使用，后者封装了同一字体族下不同样式变体的集合。

## 架构位置

TypefaceFontProvider 位于 `skia::textlayout` 命名空间内，是 SkFontMgr 抽象接口的具体实现。它通常作为 FontCollection 的 Asset 或 Dynamic 字体管理器使用，使应用程序能将自定义字体（如内嵌的 TTF/OTF 文件）注册到段落排版系统中。

**层级**: `FontCollection` -> `TypefaceFontProvider` (as SkFontMgr) -> `TypefaceFontStyleSet` -> `SkTypeface`

## 主要类与结构体

### `TypefaceFontProvider`
继承自 SkFontMgr，实现字体注册和查找功能。
- `fRegisteredFamilies`: `std::unordered_map` 存储字体族名到 TypefaceFontStyleSet 的映射
- `fFamilyNames`: `std::vector<std::string>` 维护字体族名的有序列表

### `TypefaceFontStyleSet`
继承自 SkFontStyleSet，封装同一字体族下的多个字体样式。
- `fFamilyName`: 字体族名
- `fStyles`: 字体面列表

## 公共 API 函数

### TypefaceFontProvider

| 函数 | 说明 |
|------|------|
| `registerTypeface(sk_sp<SkTypeface>)` | 注册字体，自动从 typeface 读取族名 |
| `registerTypeface(sk_sp<SkTypeface>, const SkString&)` | 注册字体并指定族名 |
| `onCountFamilies()` | 返回已注册的字体族数量 |
| `onGetFamilyName(int, SkString*)` | 按索引获取字体族名 |
| `onMatchFamily(const char[])` | 按名称查找字体样式集 |
| `onCreateStyleSet(int)` | 按索引创建字体样式集 |
| `onMatchFamilyStyle(const char[], const SkFontStyle&)` | 按族名和样式查找字体 |
| `onLegacyMakeTypeface(const char[], SkFontStyle)` | 兼容旧版接口的字体查找 |

### TypefaceFontStyleSet

| 函数 | 说明 |
|------|------|
| `count()` | 返回样式集中的字体数量 |
| `getStyle(int, SkFontStyle*, SkString*)` | 获取指定索引的样式信息 |
| `createTypeface(int)` | 创建指定索引的字体面 |
| `matchStyle(const SkFontStyle&)` | 使用 CSS3 规则匹配最接近的样式 |
| `appendTypeface(sk_sp<SkTypeface>)` | 添加新的字体面到样式集 |

## 内部实现细节

### 字体注册流程
1. 若 typeface 为空或族名为空，返回 0（注册失败）
2. 在 `fRegisteredFamilies` 中查找该族名
3. 若不存在，创建新的 TypefaceFontStyleSet 并添加到映射和名称列表中
4. 若已存在，将 typeface 追加到已有的样式集中
5. 返回 1 表示注册成功

### 旧版字体查找（`onLegacyMakeTypeface`）
1. 若提供了族名，先尝试 `matchFamilyStyle`
2. 若未找到或未提供族名，回退到第一个已注册的字体族
3. 使用 `matchStyle` 从默认族中选择最接近的样式

### 样式匹配
TypefaceFontStyleSet 的 `matchStyle` 直接委托给 `matchStyleCSS3`（继承自 SkFontStyleSet 基类），按照 CSS3 字体匹配规范选择最佳匹配。

## 使用示例

典型的使用流程：
```cpp
auto provider = sk_make_sp<TypefaceFontProvider>();
// 注册自定义字体
auto typeface = SkTypeface::MakeFromFile("path/to/font.ttf");
provider->registerTypeface(typeface);
// 或者指定自定义族名
provider->registerTypeface(typeface, SkString("MyCustomFont"));
// 将 provider 设置为 FontCollection 的字体管理器
fontCollection->setAssetFontManager(provider);
```

### 与 SkFontMgr 的兼容性
TypefaceFontProvider 实现了 SkFontMgr 的以下虚方法：
- `onCountFamilies()` -> 返回已注册字体族数量
- `onGetFamilyName(index, name)` -> 按索引获取族名
- `onMatchFamily(name)` -> 按名称查找
- `onCreateStyleSet(index)` -> 按索引创建样式集
- `onMatchFamilyStyle(name, pattern)` -> 按族名和样式匹配
- `onLegacyMakeTypeface(name, style)` -> 旧版兼容接口

以下虚方法未实现（继承基类默认行为）：
- `onMatchFamilyStyleCharacter` -> 不支持按 Unicode 字符匹配
- `onMakeFromData` / `onMakeFromStreamIndex` -> 不支持从数据创建字体

### TypefaceFontStyleSet 的 CSS3 匹配
`matchStyle` 方法委托给基类的 `matchStyleCSS3`，按照 CSS3 字体匹配算法：
1. 首先按字体宽度过滤
2. 然后按倾斜度过滤
3. 最后按权重选择最接近的匹配

### 字体族名大小写处理
`fRegisteredFamilies` 使用 `std::string` 作为键，字体族名查找是大小写敏感的。调用方需要确保注册和查询时使用一致的大小写。

## 依赖关系

- **SkFontMgr**: 抽象字体管理器基类
- **SkFontStyleSet**: 抽象字体样式集基类
- **SkTypeface**: 字体面类型
- **SkFontDescriptor**: 字体描述符（头文件依赖）
- **SkString**: Skia 字符串类型

## 设计模式与设计决策

1. **SkFontMgr 实现模式**: 通过实现 SkFontMgr 的虚函数（`on*` 前缀方法），融入 Skia 的字体管理体系，可直接被 FontCollection 使用。
2. **灵活的注册机制**: 支持自动读取族名或手动指定族名两种注册方式，后者可用于给字体起别名。
3. **CSS3 匹配规范**: 样式匹配遵循 CSS3 规范，确保与 Web 排版行为一致。

## 性能考量

- **O(1) 字体族查找**: 使用 `std::unordered_map` 进行族名到样式集的映射
- **增量注册**: 同一族名下的新字体追加到已有样式集，无需重建
- **轻量级设计**: 不持有字体数据，仅引用 SkTypeface 的智能指针

## 相关文件

- `modules/skparagraph/include/TypefaceFontProvider.h` - 公共头文件
- `include/core/SkFontMgr.h` - SkFontMgr 抽象基类
- `include/core/SkTypeface.h` - SkTypeface 接口
- `src/core/SkFontDescriptor.h` - 字体描述符

## 使用注意事项

1. 注册的字体族名是大小写敏感的
2. 空族名或空 typeface 的注册将被忽略（返回 0）
3. 同一族名下可注册多个样式变体（如 Regular、Bold、Italic）
4. TypefaceFontProvider 不支持按 Unicode 字符匹配（`matchFamilyStyleCharacter` 未实现）
5. 字体注册后立即可用，无需额外初始化步骤
6. 该类通常用于嵌入式或测试场景，生产环境更多使用系统字体管理器

### 返回值约定
| 方法 | 成功返回 | 失败返回 |
|------|---------|---------|
| `registerTypeface(typeface)` | 1 | 0（typeface 为空） |
| `registerTypeface(typeface, name)` | 1 | 0（名称为空） |
| `onMatchFamily(name)` | SkFontStyleSet | nullptr |
| `onMatchFamilyStyle(name, style)` | SkTypeface | nullptr |
| `onLegacyMakeTypeface(name, style)` | SkTypeface | nullptr |
| `onCountFamilies()` | int (>= 0) | N/A |
| `onGetFamilyName(index, name)` | void | assert 失败 |
