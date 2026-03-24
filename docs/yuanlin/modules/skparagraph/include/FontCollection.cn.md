# FontCollection

> 源文件: [modules/skparagraph/include/FontCollection.h](../../../../modules/skparagraph/include/FontCollection.h)

## 概述

`FontCollection` 是 Skia 段落排版模块的字体管理中心，负责管理多个字体管理器（`SkFontMgr`）、执行字体查找与匹配、处理字体回退（fallback）以及维护段落缓存。它支持四种字体管理器角色：Asset（资产字体）、Dynamic（动态字体）、Test（测试字体）和 Default（默认/回退字体），并按优先级顺序查找字体。`FontCollection` 同时拥有 `ParagraphCache` 实例，将字体管理与段落缓存统一生命周期。

## 架构位置

```
skia::textlayout 命名空间
  FontCollection (SkRefCnt)  ← 本文件定义
    ├── 被 ParagraphBuilder::make() 接受
    ├── 被 Paragraph 内部引用
    ├── 拥有 ParagraphCache 实例
    └── 管理多个 SkFontMgr:
          ├── fAssetFontManager (优先级 1)
          ├── fDynamicFontManager (优先级 2)
          ├── fTestFontManager (优先级 3)
          └── fDefaultFontManager (优先级 4, 回退)
```

`FontCollection` 是排版系统的字体基础设施层，为段落构建和布局提供字体查找服务。

## 主要类与结构体

### FontCollection
- 继承自 `SkRefCnt`，支持引用计数的共享所有权
- 管理四个字体管理器槽位
- 维护字体查找缓存（`FaceCache`）和段落缓存（`ParagraphCache`）
- 控制字体回退的启用/禁用

### FontCollection::FaceCache（内部结构体）
- 前向声明，通过 `std::unique_ptr` 持有
- 缓存字体查找结果，避免重复匹配

## 公共 API 函数

### 字体管理器配置
```cpp
size_t getFontManagersCount() const;
```
返回已注册的字体管理器数量。

```cpp
void setAssetFontManager(sk_sp<SkFontMgr> fontManager);
void setDynamicFontManager(sk_sp<SkFontMgr> fontManager);
void setTestFontManager(sk_sp<SkFontMgr> fontManager);
void setDefaultFontManager(sk_sp<SkFontMgr> fontManager);
void setDefaultFontManager(sk_sp<SkFontMgr> fontManager, const char defaultFamilyName[]);
void setDefaultFontManager(sk_sp<SkFontMgr> fontManager, const std::vector<SkString>& defaultFamilyNames);
```
设置各角色的字体管理器。默认字体管理器有三个重载：无名称、单个名称、多个名称。

```cpp
sk_sp<SkFontMgr> getFallbackManager() const;
```
获取回退字体管理器（即默认字体管理器）。

### 字体查找
```cpp
std::vector<sk_sp<SkTypeface>> findTypefaces(
    const std::vector<SkString>& familyNames, SkFontStyle fontStyle);
std::vector<sk_sp<SkTypeface>> findTypefaces(
    const std::vector<SkString>& familyNames, SkFontStyle fontStyle,
    const std::optional<FontArguments>& fontArgs);
```
根据字体族名称列表和样式查找字体面。第二个重载额外支持字体参数（变体轴、调色板）。返回所有匹配的 typeface 列表。

### 字体回退
```cpp
sk_sp<SkTypeface> defaultFallback(SkUnichar unicode,
    const std::vector<SkString>& families,
    SkFontStyle fontStyle, const SkString& locale,
    const std::optional<FontArguments>& fontArgs);
```
为指定的 Unicode 字符查找回退字体，考虑字体族偏好、样式和区域设置。

```cpp
sk_sp<SkTypeface> defaultEmojiFallback(SkUnichar emojiStart,
    SkFontStyle fontStyle, const SkString& locale);
```
专用的 Emoji 回退查找。

```cpp
sk_sp<SkTypeface> defaultFallback();
```
获取默认回退字体面（无特定字符要求）。

### 回退控制
```cpp
void disableFontFallback();
void enableFontFallback();
bool fontFallbackEnabled();
```
控制字体回退功能的启用和禁用。

### 缓存管理
```cpp
ParagraphCache* getParagraphCache();
void clearCaches();
```
获取段落缓存指针和清除所有缓存（包括字体缓存和段落缓存）。

## 内部实现细节

### 字体管理器优先级

`getFontManagerOrder()` 私有方法返回字体管理器的有序列表，查找时按此顺序遍历：
1. Asset 字体管理器
2. Dynamic 字体管理器
3. Test 字体管理器
4. Default 字体管理器

### 字体匹配缓存

`FaceCache` 使用 Pimpl 模式隐藏实现，缓存 `(familyName, fontStyle)` 到 `sk_sp<SkTypeface>` 的映射，避免重复的字体匹配操作。

### 默认字体族名称

`fDefaultFamilyNames`（`vector<SkString>`）存储通过 `setDefaultFontManager` 设置的默认字体族名称。当所有指定的字体族都找不到时，使用这些名称作为最后回退。

### 引用计数

继承自 `SkRefCnt`，通过 `sk_sp<FontCollection>` 管理生命周期。`ParagraphBuilder` 和 `Paragraph` 都持有 `FontCollection` 的引用计数指针。

## 依赖关系

- **Skia 核心**: `SkFontMgr`、`SkRefCnt`、`SkSpan`、`SkTypeface`、`SkFontStyle`
- **skparagraph 模块**: `FontArguments`、`ParagraphCache`、`TextStyle`
- **标准库**: `<memory>`、`<optional>`、`<set>`、`<vector>`

## 设计模式与设计决策

1. **多级字体管理器**: 四种角色的字体管理器设计支持灵活的字体来源配置。Asset 用于嵌入的字体，Dynamic 用于运行时添加的字体，Test 用于测试，Default 作为最终回退。

2. **引用计数共享**: 继承 `SkRefCnt`，允许多个 `Paragraph` 和 `ParagraphBuilder` 安全共享同一个 `FontCollection` 实例。

3. **缓存统一管理**: `ParagraphCache` 嵌入在 `FontCollection` 中，确保字体集合变更时可以同时清除段落缓存。`clearCaches()` 提供一键清除所有缓存的接口。

4. **Pimpl 模式**: `FaceCache` 通过 `unique_ptr` 隐藏实现，减少头文件依赖，加速编译。

5. **Emoji 特殊处理**: `defaultEmojiFallback` 专门处理 Emoji 字符的回退，因为 Emoji 字体的查找逻辑（如需要彩色字体）与普通文本不同。

6. **字体回退可控**: 通过 `enableFontFallback()`/`disableFontFallback()` 允许客户端在确定字体完备时禁用回退查找，避免潜在的性能开销。

## 性能考量

- `findTypefaces` 通过 `FaceCache` 缓存查找结果，将重复查找降低为 O(1) 哈希查找。
- `defaultFallback` 涉及遍历字体管理器和匹配特定 Unicode 字符，可能较慢。结果应由调用方缓存。
- `clearCaches()` 会清除所有字体和段落缓存，调用后首次排版会较慢。
- `FontCollection` 的生命周期应尽可能长，避免频繁创建/销毁导致缓存失效。
- 字体管理器的顺序影响查找速度，将最常用的字体放在 Asset 管理器中可以加速查找。

## 相关文件

- `modules/skparagraph/include/ParagraphCache.h` - 段落缓存
- `modules/skparagraph/include/FontArguments.h` - 字体参数
- `modules/skparagraph/include/TextStyle.h` - 文本样式（包含字体配置）
- `modules/skparagraph/include/ParagraphBuilder.h` - 接受 FontCollection 的构建器
- `modules/skparagraph/src/FontCollection.cpp` - 实现文件
- `include/core/SkFontMgr.h` - Skia 字体管理器接口
