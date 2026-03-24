# SkFontMgr_custom

> 源文件
> - src/ports/SkFontMgr_custom.h
> - src/ports/SkFontMgr_custom.cpp

## 概述

`SkFontMgr_custom` 是 Skia 字体管理系统的自定义实现基类，为嵌入式系统、自定义字体加载场景提供了灵活的字体管理框架。该模块允许应用程序通过实现 `SystemFontLoader` 接口来自定义字体的加载源，可以从文件系统、内存、网络或任何其他数据源加载字体。

该模块的核心特点是：
- **可扩展的加载机制**：通过 `SystemFontLoader` 接口支持多种字体来源
- **完整的字体家族管理**：维护字体家族及其样式集合
- **基于 FreeType 的渲染**：所有 typeface 实现都继承自 `SkTypeface_FreeType`
- **默认字体回退**：自动选择合适的默认字体家族
- **内存和文件加载**：支持从文件路径、内存流、数据块加载字体

该模块是 Android 嵌入式字体管理器、目录字体管理器、空字体管理器等具体实现的基础。

## 架构位置

`SkFontMgr_custom` 在 Skia 字体系统架构中的位置：

```
SkFontMgr (抽象基类)
    ↓
SkFontMgr_Custom (自定义管理器基类 - 本模块)
    ↓
┌───────────────┬──────────────────┬─────────────────┐
│               │                  │                 │
SkFontMgr_      SkFontMgr_Custom_ SkFontMgr_Custom_ SkFontMgr_Custom_
Android         Directory         Embedded          Empty
(Android系统)   (目录扫描)        (嵌入式数据)     (空实现)
```

字体样式集和 Typeface 层次：
```
SkFontStyleSet (抽象基类)
    ↓
SkFontStyleSet_Custom (本模块)
    ↓
SkTypeface (抽象基类)
    ↓
SkTypeface_FreeType (FreeType基类)
    ↓
┌─────────────────┬──────────────────┬─────────────────┐
│                 │                  │                 │
SkTypeface_Custom SkTypeface_File    SkTypeface_Empty
(基类)           (文件加载)         (空typeface)
```

## 主要类与结构体

### SkTypeface_Custom
所有自定义字体管理器的 typeface 基类，继承自 `SkTypeface_FreeType`。

**主要成员：**
- `fIsSysFont`: 是否为系统字体
- `fFamilyName`: 字体家族名称
- `fIndex`: TTC 文件中的字体索引

**核心方法：**
- `isSysFont()`: 判断是否为系统字体
- `getIndex()`: 获取字体索引
- `onGetFamilyName()`: 获取家族名称（虚函数）
- `onGetFontDescriptor()`: 获取字体描述符（虚函数）

### SkTypeface_Empty
空 typeface 实现，用作最后的回退 typeface。

**特点：**
- 不包含任何字形数据
- `onOpenStream()` 返回 nullptr
- `onMakeClone()` 返回自身引用
- `onMakeFontData()` 返回 nullptr
- 用于防止字体系统完全失败

### SkTypeface_File
从文件系统加载字体的 typeface 实现。

**主要成员：**
- `fPath`: 字体文件路径

**核心方法：**
- `onOpenStream()`: 打开字体文件流
- `onMakeClone()`: 克隆 typeface（支持可变字体参数）
- `onMakeFontData()`: 创建字体数据对象

### SkFontStyleSet_Custom
自定义字体样式集，管理同一家族的多个字体样式（如 Regular、Bold、Italic）。

**主要成员：**
- `fStyles`: 字体样式数组（`TArray<sk_sp<SkTypeface>>`）
- `fFamilyName`: 家族名称

**核心方法：**
- `appendTypeface()`: 添加 typeface（仅在初始化阶段调用）
- `count()`: 返回样式数量
- `getStyle()`: 获取指定索引的样式信息
- `createTypeface()`: 创建指定索引的 typeface
- `matchStyle()`: 根据样式模式匹配最接近的 typeface
- `getFamilyName()`: 获取家族名称

### SkFontMgr_Custom
自定义字体管理器，管理所有字体家族。

**主要成员：**
- `fFamilies`: 字体家族集合（`TArray<sk_sp<SkFontStyleSet_Custom>>`）
- `fDefaultFamily`: 默认字体家族
- `fScanner`: 字体扫描器（用于解析字体文件元数据）

**核心方法：**
- `onCountFamilies()`: 返回家族数量
- `onGetFamilyName()`: 获取指定索引的家族名称
- `onCreateStyleSet()`: 创建样式集
- `onMatchFamily()`: 根据名称匹配家族
- `onMatchFamilyStyle()`: 根据名称和样式匹配 typeface
- `onMatchFamilyStyleCharacter()`: 根据字符匹配 typeface（未实现）
- `onMakeFromData()`: 从数据创建 typeface
- `onMakeFromStreamIndex()`: 从流创建 typeface
- `onMakeFromStreamArgs()`: 从流和参数创建 typeface
- `onMakeFromFile()`: 从文件创建 typeface
- `onLegacyMakeTypeface()`: 传统方式创建 typeface（支持默认回退）

### SystemFontLoader
抽象接口，定义系统字体加载策略。

**核心方法：**
```cpp
virtual void loadSystemFonts(const SkFontScanner*, Families*) const = 0;
```

**实现示例：**
- **DirectoryLoader**：扫描指定目录加载字体文件
- **EmbeddedLoader**：从嵌入式数据加载字体
- **EmptyLoader**：不加载任何字体（空实现）

## 公共 API 函数

### SkTypeface_Custom 构造函数
```cpp
SkTypeface_Custom(const SkFontStyle& style, bool isFixedPitch,
                  bool sysFont, SkString familyName, int index);
```
创建自定义 typeface。

**参数：**
- `style`: 字体样式（粗细、宽度、倾斜）
- `isFixedPitch`: 是否为等宽字体
- `sysFont`: 是否为系统字体
- `familyName`: 家族名称
- `index`: TTC 文件中的索引（0 表示单字体文件）

### SkTypeface_File 构造函数
```cpp
SkTypeface_File(const SkFontStyle& style, bool isFixedPitch, bool sysFont,
                SkString familyName, const char path[], int index);
```
创建基于文件的 typeface。

**参数：**
- `path`: 字体文件路径

### SkFontStyleSet_Custom::appendTypeface()
```cpp
void appendTypeface(sk_sp<SkTypeface> typeface);
```
向样式集添加 typeface。**仅应在初始化阶段调用**。

### SkFontStyleSet_Custom::matchStyle()
```cpp
sk_sp<SkTypeface> matchStyle(const SkFontStyle& pattern);
```
根据样式模式匹配最接近的 typeface。使用 CSS3 字体匹配算法（`matchStyleCSS3`）。

**匹配优先级：**
1. 字体粗细（weight）
2. 字体宽度（width）
3. 字体倾斜（slant）

### SkFontMgr_Custom 构造函数
```cpp
explicit SkFontMgr_Custom(const SystemFontLoader& loader);
```
创建自定义字体管理器。

**初始化流程：**
1. 创建 FreeType 字体扫描器
2. 调用 `loader.loadSystemFonts()` 加载字体
3. 尝试选择默认字体（按优先级：Arial、Verdana、Times New Roman、Droid Sans、DejaVu Serif）
4. 如果没有找到默认字体，使用第一个加载的家族

### SkFontMgr_Custom::onMatchFamily()
```cpp
sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const;
```
根据家族名称进行精确匹配。使用线性搜索，名称区分大小写。

### SkFontMgr_Custom::onLegacyMakeTypeface()
```cpp
sk_sp<SkTypeface> onLegacyMakeTypeface(const char familyName[], SkFontStyle style) const;
```
传统方式创建 typeface，支持自动回退到默认家族。

**逻辑：**
1. 如果提供了家族名称，尝试匹配
2. 如果匹配失败或未提供名称，使用默认家族
3. 在选定的家族中匹配样式

## 内部实现细节

### 字体加载流程

#### 初始化阶段
```
SkFontMgr_Custom 构造
    ↓
创建 SkFontScanner_FreeType
    ↓
调用 SystemFontLoader::loadSystemFonts()
    ↓
扫描器解析字体文件
    ↓
创建 SkFontStyleSet_Custom 家族
    ↓
创建 SkTypeface_File 对象
    ↓
添加到 fFamilies
    ↓
选择默认家族
```

#### 字体匹配流程
```
用户请求字体 (familyName, style)
    ↓
onMatchFamily(familyName)
    ↓
线性搜索 fFamilies
    ↓
找到 SkFontStyleSet_Custom
    ↓
matchStyle(style)
    ↓
CSS3 匹配算法
    ↓
返回最接近的 SkTypeface
```

### 默认字体选择策略

构造函数尝试按以下优先级选择默认字体：
1. **Arial**: Windows 标准字体
2. **Verdana**: Web 安全字体
3. **Times New Roman**: 传统衬线字体
4. **Droid Sans**: Android 默认字体
5. **DejaVu Serif**: Linux 常用字体

如果都不存在，使用第一个加载的家族。这种策略确保了在不同平台上都能有合理的默认字体。

### 空 Typeface 的作用

`SkTypeface_Empty` 提供了一个"什么都不做"的 typeface，用于以下场景：
- 系统完全没有字体时的最后回退
- 测试和调试
- 防止空指针崩溃

它的所有流和数据方法都返回 nullptr，但对象本身是有效的。

### 文件 Typeface 的克隆机制

`SkTypeface_File::onMakeClone()` 支持克隆并修改字体参数（如可变字体轴）：

```cpp
sk_sp<SkTypeface> SkTypeface_File::onMakeClone(const SkFontArguments& args) const {
    SkFontStyle style = this->fontStyle();
    std::unique_ptr<SkFontData> data = this->cloneFontData(args, &style);
    // 创建新的 SkTypeface_FreeTypeStream
    return sk_make_sp<SkTypeface_FreeTypeStream>(...);
}
```

这允许从同一个字体文件创建多个具有不同参数的 typeface 实例。

### 样式匹配算法

`matchStyle()` 使用 `matchStyleCSS3()` 算法，遵循 CSS3 字体匹配规范：

**匹配步骤：**
1. 过滤字体宽度（优先精确匹配，然后是最接近的）
2. 过滤字体倾斜（Italic vs Upright vs Oblique）
3. 选择最接近目标粗细的字体

这确保了字体选择行为与 Web 标准一致。

### 字体数据创建

`onMakeFontData()` 创建 `SkFontData` 对象，包含：
- 字体流（`SkStreamAsset`）
- TTC 索引
- 轴数量（可变字体）
- 轴坐标数组
- 调色板索引和覆盖信息

这是字体渲染的基础数据结构。

## 依赖关系

### 外部依赖
| 模块 | 用途 |
|------|------|
| **FreeType** | 字体解析和渲染（通过 SkTypeface_FreeType） |

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkFontMgr` | 字体管理器抽象基类 |
| `SkFontStyleSet` | 字体样式集抽象基类 |
| `SkTypeface` | 字体类型抽象基类 |
| `SkTypeface_FreeType` | FreeType typeface 基类 |
| `SkFontScanner_FreeType` | FreeType 字体扫描器 |
| `SkFontStyle` | 字体样式描述 |
| `SkFontDescriptor` | 字体描述符 |
| `SkStream` | 流接口 |
| `SkData` | 数据容器 |
| `SkString` | 字符串类 |
| `SkTArray` | 动态数组 |
| `SkRefCnt` | 引用计数 |

## 设计模式与设计决策

### 1. 模板方法模式（Template Method Pattern）
`SkFontMgr_Custom` 定义了字体管理的框架（查询、匹配、创建），子类通过 `SystemFontLoader` 接口自定义加载逻辑。

### 2. 策略模式（Strategy Pattern）
`SystemFontLoader` 接口是策略模式的典型应用，允许运行时注入不同的字体加载策略：
- 从目录扫描
- 从嵌入式数据加载
- 从网络加载
- 空加载（测试用）

### 3. 工厂模式（Factory Pattern）
各种 `onMakeFrom*` 方法实现了工厂模式，根据不同的输入源创建 typeface。

### 4. 空对象模式（Null Object Pattern）
`SkTypeface_Empty` 是空对象模式的实现，提供了一个"什么都不做但不会崩溃"的对象。

### 5. 组合模式（Composite Pattern）
字体家族（`SkFontStyleSet_Custom`）包含多个字体样式（`SkTypeface`），形成了组合结构。

### 6. 面向接口编程
所有关键组件都继承自抽象基类（`SkFontMgr`、`SkFontStyleSet`、`SkTypeface`），提供了良好的扩展性。

### 7. 关注点分离
- **SkFontMgr_Custom**: 管理字体家族集合
- **SkFontStyleSet_Custom**: 管理单个家族的样式
- **SkTypeface_Custom/File/Empty**: 管理单个字体实例
- **SystemFontLoader**: 负责字体加载
- **SkFontScanner**: 负责字体元数据解析

### 8. 延迟加载
字体文件在创建 typeface 时不会立即加载，只有在实际需要渲染时才通过 `onOpenStream()` 打开。

### 9. 合理的默认值
自动选择常见的默认字体，确保在各种环境下都有可用的字体。

## 性能考量

### 1. 线性搜索字体家族
```cpp
for (int i = 0; i < fFamilies.size(); ++i) {
    if (fFamilies[i]->getFamilyName().equals(familyName)) {
        return fFamilies[i];
    }
}
```
**性能特点：**
- 时间复杂度 O(n)
- 对于少量家族（< 100）性能足够
- 如果需要优化，可以使用哈希表

### 2. 引用计数代替复制
使用 `sk_sp<SkTypeface>` 智能指针，避免了字体对象的深拷贝。

### 3. 预构建家族列表
在构造函数中一次性加载所有字体，避免了运行时扫描文件系统。

### 4. CSS3 匹配算法
`matchStyleCSS3()` 是优化的匹配算法，通常在常数时间内完成（样式数量有限）。

### 5. 流式加载字体
使用 `SkStreamAsset` 而非一次性加载整个文件到内存，节省内存。

### 6. 默认家族缓存
缓存 `fDefaultFamily`，避免每次回退都要搜索。

### 7. 移动语义
大量使用 `std::move` 转移所有权，避免字符串和对象复制。

### 8. 扫描器复用
共享一个 `fScanner` 实例用于解析所有字体，避免重复创建。

### 内存占用
- 每个家族：~100 字节（名称 + 指针）
- 每个 typeface：~200 字节（不包括字体文件数据）
- 100 个字体家族约占用 30KB 内存

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkFontMgr_custom_directory.cpp` | 基于目录扫描的字体管理器 |
| `src/ports/SkFontMgr_custom_embedded.cpp` | 基于嵌入式数据的字体管理器 |
| `src/ports/SkFontMgr_custom_empty.cpp` | 空字体管理器（测试用） |
| `src/ports/SkTypeface_FreeType.h` | FreeType typeface 基类 |
| `include/ports/SkFontScanner_FreeType.h` | FreeType 字体扫描器 |
| `include/core/SkFontMgr.h` | 字体管理器抽象基类 |
| `include/core/SkFontStyle.h` | 字体样式定义 |
| `include/core/SkTypeface.h` | Typeface 抽象基类 |
| `src/core/SkFontDescriptor.h` | 字体描述符 |
| `src/ports/SkFontMgr_android.cpp` | Android 字体管理器（使用类似架构） |
