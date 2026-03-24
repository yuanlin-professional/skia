# TypefaceFontProvider

> 源文件: modules/skparagraph/include/TypefaceFontProvider.h

## 概述

`TypefaceFontProvider` 是 Skia 段落模块中的一个自定义字体管理器,继承自 `SkFontMgr`,用于在运行时动态注册和管理字体。它允许应用程序在不依赖系统字体管理器的情况下,手动控制可用的字体集合,这对于跨平台应用程序和需要自定义字体加载的场景特别有用。该类与 `TypefaceFontStyleSet` 配合使用,后者管理同一字体族的不同样式变体。

## 架构位置

`TypefaceFontProvider` 位于 Skia 的段落模块 (`modules/skparagraph`) 中,作为字体系统的一个可选实现层。它在架构中的位置:

```
段落布局系统
    ├── FontCollection (字体集合管理)
    │   └── TypefaceFontProvider (自定义字体提供者)
    │       └── TypefaceFontStyleSet (字体样式集)
    │           └── SkTypeface (具体字体实例)
    └── ParagraphBuilder (段落构建器)
```

该类位于字体抽象层,介于高层的 `FontCollection` 和底层的 `SkTypeface` 之间,提供了一个灵活的字体注册和查询机制。它是段落模块与 Skia 核心字体系统的桥梁,允许段落系统使用自定义的字体集合而不依赖平台特定的字体管理器。

## 主要类与结构体

### TypefaceFontStyleSet

```cpp
class TypefaceFontStyleSet : public SkFontStyleSet {
    int count() override;
    void getStyle(int index, SkFontStyle*, SkString* name) override;
    sk_sp<SkTypeface> createTypeface(int index) override;
    sk_sp<SkTypeface> matchStyle(const SkFontStyle& pattern) override;
    SkString getFamilyName() const;
    void appendTypeface(sk_sp<SkTypeface> typeface);
private:
    skia_private::TArray<sk_sp<SkTypeface>> fStyles;
    SkString fFamilyName;
    SkString fAlias;
};
```

`TypefaceFontStyleSet` 表示同一字体族的不同样式集合。它继承自 `SkFontStyleSet`,管理一个字体族(如 "Arial")的多个变体(Regular、Bold、Italic 等)。主要成员包括:
- `fStyles`: 存储该字体族的所有字体样式
- `fFamilyName`: 字体族名称
- `fAlias`: 字体族别名

### TypefaceFontProvider

```cpp
class TypefaceFontProvider : public SkFontMgr {
    size_t registerTypeface(sk_sp<SkTypeface> typeface);
    size_t registerTypeface(sk_sp<SkTypeface> typeface, const SkString& alias);
private:
    std::unordered_map<std::string, sk_sp<TypefaceFontStyleSet>> fRegisteredFamilies;
    skia_private::TArray<std::string> fFamilyNames;
};
```

核心字体管理器类,维护已注册字体的映射表:
- `fRegisteredFamilies`: 从字体族名称到样式集的映射
- `fFamilyNames`: 按注册顺序存储的字体族名称列表

## 公共 API 函数

### registerTypeface

```cpp
size_t registerTypeface(sk_sp<SkTypeface> typeface);
size_t registerTypeface(sk_sp<SkTypeface> typeface, const SkString& alias);
```

注册一个字体到提供者中。第一个版本使用字体自身的族名,第二个版本允许指定别名。返回注册后该字体族中样式的总数。这是用户与该类交互的主要接口,用于动态添加字体资源。

### onCountFamilies

```cpp
int onCountFamilies() const override;
```

返回已注册的字体族数量,覆盖 `SkFontMgr` 的虚函数。

### onGetFamilyName

```cpp
void onGetFamilyName(int index, SkString* familyName) const override;
```

获取指定索引处的字体族名称,用于枚举所有可用字体族。

### onMatchFamily

```cpp
sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const override;
```

根据字体族名称查找对应的样式集。这是字体查询的核心方法,允许按名称快速定位字体族。

### onCreateStyleSet

```cpp
sk_sp<SkFontStyleSet> onCreateStyleSet(int) const override;
```

根据索引创建样式集,用于枚举方式访问字体族。

### onMatchFamilyStyle

```cpp
sk_sp<SkTypeface> onMatchFamilyStyle(const char familyName[],
                                     const SkFontStyle& pattern) const override;
```

根据字体族名称和样式模式(如粗细、宽度、倾斜度)查找最匹配的字体。这是字体选择的关键方法,支持样式匹配算法。

### onLegacyMakeTypeface

```cpp
sk_sp<SkTypeface> onLegacyMakeTypeface(const char[], SkFontStyle) const override;
```

提供向后兼容的字体创建接口,支持旧版 API。

## 内部实现细节

### 字体注册机制

当调用 `registerTypeface` 时,实现会执行以下步骤:
1. 从 `SkTypeface` 中提取字体族名称
2. 检查该字体族是否已在 `fRegisteredFamilies` 中存在
3. 如果不存在,创建新的 `TypefaceFontStyleSet` 并添加到映射表
4. 如果存在,将字体添加到现有的样式集
5. 更新 `fFamilyNames` 列表以维护注册顺序
6. 返回该字体族中样式的总数

### 字体查找策略

字体查找采用两阶段策略:
1. **族名匹配**: 首先在 `fRegisteredFamilies` 中查找精确匹配的字体族名或别名
2. **样式匹配**: 在找到的样式集中,根据 `SkFontStyle` 参数(包括粗细、宽度、倾斜度)找到最接近的字体

对于不支持的操作(如从流或文件创建字体),实现直接返回 `nullptr`,因为该类仅管理预注册的字体。

### 内存管理

所有字体对象使用智能指针 `sk_sp<SkTypeface>` 管理,确保引用计数正确。`fRegisteredFamilies` 使用 `unordered_map` 提供 O(1) 的查找性能,而 `fFamilyNames` 使用 `TArray` 维护插入顺序,支持索引访问。

## 依赖关系

### 依赖的核心类型

- **SkFontMgr**: 基类,定义字体管理器接口
- **SkFontStyleSet**: `TypefaceFontStyleSet` 的基类
- **SkTypeface**: 字体实例的核心类型
- **SkFontStyle**: 描述字体样式的结构(粗细、宽度、倾斜度)
- **SkString**: Skia 的字符串类型

### 标准库依赖

- `std::unordered_map`: 用于快速字体族查找
- `std::vector` 和 `std::string`: 标准容器和字符串类型
- `skia_private::TArray`: Skia 的私有数组实现

### 模块间依赖

该类是段落模块的一部分,但依赖于 Skia 核心模块的字体系统。它通常与 `FontCollection` 类配合使用,后者是段落系统的字体管理入口点。

## 设计模式与设计决策

### 工厂模式

`TypefaceFontProvider` 作为字体对象的工厂,负责创建和返回 `SkTypeface` 实例。它将字体创建逻辑集中管理,客户端无需了解字体的实际来源。

### 策略模式

通过继承 `SkFontMgr`,该类实现了一种特定的字体管理策略——基于运行时注册的策略。这允许应用程序在不同平台上使用统一的接口,但底层实现可以灵活切换(系统字体管理器、自定义提供者等)。

### 组合模式

`TypefaceFontProvider` 和 `TypefaceFontStyleSet` 形成组合关系,前者管理字体族集合,后者管理单个字体族的样式集合。这种层次化设计简化了字体管理的复杂性。

### 设计决策

1. **选择注册模式**: 不支持从文件或流创建字体,所有相关方法返回 `nullptr`。这是明确的设计选择,将该类定位为纯注册型字体管理器,简化实现并避免文件 I/O 复杂性。

2. **支持别名机制**: `registerTypeface` 提供别名参数,允许为字体族设置多个名称,提高字体查找的灵活性(例如,可以为中文字体设置英文别名)。

3. **使用智能指针**: 所有字体对象使用 `sk_sp` 管理生命周期,避免内存泄漏并简化资源管理。

## 性能考量

### 查找性能

使用 `std::unordered_map` 存储字体族映射,提供 O(1) 的平均查找时间。这对于频繁的字体查询场景至关重要,因为段落布局过程可能涉及大量字体查找操作。

### 内存占用

每个注册的字体都会增加内存占用,因为 `sk_sp` 会保持对字体对象的引用。对于内存敏感的应用,应避免注册过多不必要的字体。

### 注册开销

字体注册操作涉及哈希表插入和数组追加,时间复杂度为 O(1)。但如果大量注册字体,应考虑批量注册并在应用启动时完成,避免运行时频繁注册。

### 线程安全

该类没有显式的线程同步机制。如果在多线程环境中使用,需要外部同步来保护 `fRegisteredFamilies` 和 `fFamilyNames` 的并发访问。通常的做法是在应用初始化阶段完成所有字体注册,之后仅进行只读访问。

## 相关文件

- `modules/skparagraph/src/TypefaceFontProvider.cpp`: 实现文件,包含所有方法的具体实现
- `modules/skparagraph/include/FontCollection.h`: 字体集合类,通常使用 `TypefaceFontProvider` 作为其字体源
- `include/core/SkFontMgr.h`: 基类定义,规定字体管理器接口
- `include/core/SkTypeface.h`: 字体对象的核心定义
- `include/core/SkFontStyle.h`: 字体样式描述符
- `modules/skparagraph/src/ParagraphBuilderImpl.cpp`: 段落构建器实现,间接使用该类进行字体查询
