# SkOrderedFontMgr

> 源文件: include/utils/SkOrderedFontMgr.h, src/utils/SkOrderedFontMgr.cpp

## 概述

`SkOrderedFontMgr` 是 Skia 图形库中的有序字体管理器,用于聚合多个字体管理器并按顺序访问它们。该类继承自 `SkFontMgr`,实现了一个复合字体管理器,当接收到字体查找或匹配请求时,会依次访问列表中的所有子字体管理器,直到找到匹配的字体。

该模块的核心特性是只支持查询和匹配操作,而明确拒绝所有从数据、流或文件创建字体的操作(所有 `Make*` 方法都返回 `nullptr`)。这种设计使其适用于需要组合多个字体源但不直接加载字体数据的场景,如跨平台字体回退系统、字体聚合器等。

## 架构位置

`SkOrderedFontMgr` 位于 Skia 的实用工具层,作为字体管理器的组合包装器:

```
应用层 / 文本渲染引擎
   ↓
SkOrderedFontMgr (工具层 - include/utils, src/utils)
   ↓
SkFontMgr (基类 - include/core)
   ↓
├── 平台字体管理器 1 (macOS, Windows, Linux 等)
├── 平台字体管理器 2
└── 自定义字体管理器 N
```

典型使用场景:
- 多平台字体回退系统
- 组合系统字体和嵌入字体
- 字体源的优先级排序
- 测试和模拟环境

## 主要类与结构体

### SkOrderedFontMgr

有序字体管理器,按顺序访问多个子字体管理器。

**继承关系**:
```
SkRefCnt
   ↑
SkFontMgr
   ↑
SkOrderedFontMgr
```

**关键成员变量**:

| 变量名 | 类型 | 说明 |
|--------|------|------|
| fList | std::vector<sk_sp<SkFontMgr>> | 子字体管理器列表,按添加顺序访问 |

## 公共 API 函数

### 构造函数与析构函数

```cpp
SkOrderedFontMgr();
~SkOrderedFontMgr() override;
```

默认构造函数创建空的字体管理器列表。析构函数释放所有子字体管理器的引用。

### append

```cpp
void append(sk_sp<SkFontMgr> fm);
```

向列表末尾添加一个字体管理器。添加顺序决定了查询时的访问顺序。

**参数**:
- `fm`: 要添加的子字体管理器智能指针

**示例**:
```cpp
auto orderedFontMgr = sk_make_sp<SkOrderedFontMgr>();
orderedFontMgr->append(SkFontMgr_New_Custom_Empty());
orderedFontMgr->append(SkFontMgr::RefDefault());
```

## 内部实现细节

### 字体家族统计与访问

```cpp
int SkOrderedFontMgr::onCountFamilies() const {
    int count = 0;
    for (const auto& fm : fList) {
        count += fm->countFamilies();
    }
    return count;
}
```

累加所有子字体管理器的字体家族数量。

```cpp
void SkOrderedFontMgr::onGetFamilyName(int index, SkString* familyName) const {
    for (const auto& fm : fList) {
        const int count = fm->countFamilies();
        if (index < count) {
            return fm->getFamilyName(index, familyName);
        }
        index -= count;
    }
}
```

通过索引偏移定位到正确的子字体管理器和家族。

### 创建字体样式集

```cpp
sk_sp<SkFontStyleSet> SkOrderedFontMgr::onCreateStyleSet(int index) const {
    for (const auto& fm : fList) {
        const int count = fm->countFamilies();
        if (index < count) {
            return fm->createStyleSet(index);
        }
        index -= count;
    }
    return nullptr;
}
```

使用索引减法遍历列表,将全局索引转换为子管理器的局部索引。

### 字体家族匹配

```cpp
sk_sp<SkFontStyleSet> SkOrderedFontMgr::onMatchFamily(const char familyName[]) const {
    for (const auto& fm : fList) {
        const auto fs = fm->matchFamily(familyName);
        if (fs->count() > 0) {
            return fs;
        }
    }
    return nullptr;
}
```

按顺序查询每个子字体管理器,返回第一个非空的样式集。这实现了优先级机制:先添加的字体管理器优先级更高。

### 字体样式匹配

```cpp
sk_sp<SkTypeface> SkOrderedFontMgr::onMatchFamilyStyle(
    const char family[], const SkFontStyle& style) const {
    for (const auto& fm : fList) {
        if (auto tf = fm->matchFamilyStyle(family, style)) {
            return tf;
        }
    }
    return nullptr;
}
```

遍历所有子字体管理器,返回第一个成功匹配的字体。

### 字符匹配

```cpp
sk_sp<SkTypeface> SkOrderedFontMgr::onMatchFamilyStyleCharacter(
    const char familyName[], const SkFontStyle& style,
    const char* bcp47[], int bcp47Count,
    SkUnichar uni) const {
    for (const auto& fm : fList) {
        if (auto tf = fm->matchFamilyStyleCharacter(
                familyName, style, bcp47, bcp47Count, uni)) {
            return tf;
        }
    }
    return nullptr;
}
```

查找支持特定 Unicode 字符的字体,用于字体回退机制。

### 旧版字体匹配

```cpp
sk_sp<SkTypeface> SkOrderedFontMgr::onLegacyMakeTypeface(
    const char family[], SkFontStyle style) const {
    for (const auto& fm : fList) {
        if (auto tf = fm->matchFamilyStyle(family, style)) {
            return fm->legacyMakeTypeface(family, style);
        }
    }
    return nullptr;
}
```

先匹配,再调用子管理器的旧版创建方法。注意这里先检查是否能匹配,确保返回的字体来自支持该家族的管理器。

### 明确失败的创建方法

所有从数据创建字体的方法都返回 `nullptr`:

```cpp
sk_sp<SkTypeface> SkOrderedFontMgr::onMakeFromData(
    sk_sp<SkData>, int ttcIndex) const {
    return nullptr;
}

sk_sp<SkTypeface> SkOrderedFontMgr::onMakeFromStreamIndex(
    std::unique_ptr<SkStreamAsset>, int ttcIndex) const {
    return nullptr;
}

sk_sp<SkTypeface> SkOrderedFontMgr::onMakeFromStreamArgs(
    std::unique_ptr<SkStreamAsset>, const SkFontArguments&) const {
    return nullptr;
}

sk_sp<SkTypeface> SkOrderedFontMgr::onMakeFromFile(
    const char path[], int ttcIndex) const {
    return nullptr;
}
```

这是明确的设计决策:该类仅用于聚合和查询,不负责字体加载。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFontMgr | 基类,定义字体管理器接口 |
| SkFontStyleSet | 字体样式集接口 |
| SkTypeface | 字体对象 |
| SkFontStyle | 字体样式(粗细、宽度、斜体等) |
| SkRefCnt | 引用计数基类 |
| std::vector | 存储子字体管理器列表 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| 跨平台字体系统 | 组合不同平台的字体管理器 |
| 字体回退链 | 构建多层次的字体查找机制 |
| 测试框架 | 模拟多种字体环境 |
| 嵌入式系统 | 组合内置字体和系统字体 |

## 设计模式与设计决策

### 组合模式 (Composite Pattern)

`SkOrderedFontMgr` 是组合模式的典型应用:

- **Component**: `SkFontMgr` 接口
- **Composite**: `SkOrderedFontMgr` 聚合多个 `SkFontMgr`
- **Leaf**: 各种具体字体管理器(平台特定实现)

**优点**:
- 客户端统一对待单个和组合字体管理器
- 易于添加新的字体源
- 支持任意层次的嵌套

### 责任链模式 (Chain of Responsibility)

查询方法遵循责任链模式:

```cpp
for (const auto& fm : fList) {
    if (auto result = fm->matchFamily(familyName)) {
        return result;  // 第一个成功的处理者
    }
}
return nullptr;  // 无人处理
```

每个子字体管理器都有机会处理请求,第一个成功的管理器终止链。

### 明确的能力限制

设计明确限制了创建能力:

**原因**:
1. **语义不明确**: 如果支持 `MakeFromData`,应该将字体添加到哪个子管理器?
2. **职责单一**: 该类专注于聚合和查询,不负责字体加载
3. **强制正确使用**: 迫使用户明确选择字体管理器进行加载

### 索引转换策略

全局索引到局部索引的转换使用减法:

```cpp
index -= count;
```

这种策略简单高效,每个管理器"消耗"一部分索引范围。

**时间复杂度**: O(n),n 为子管理器数量
**优化空间**: 可预计算累积索引,但增加了复杂度

### 短路求值优化

匹配方法在找到结果后立即返回:

```cpp
if (auto tf = fm->matchFamilyStyle(family, style)) {
    return tf;  // 短路
}
```

避免无谓的查询,特别是当后续管理器查询成本较高时。

## 性能考量

### 顺序访问的开销

- **最好情况**: 第一个管理器匹配,O(1)
- **最坏情况**: 遍历所有管理器未匹配,O(n)
- **优化建议**: 将最常用的字体管理器放在列表前面

### 家族计数的线性成本

```cpp
int count = 0;
for (const auto& fm : fList) {
    count += fm->countFamilies();
}
```

每次调用 `countFamilies` 都需要遍历所有子管理器。如果频繁调用,可以缓存结果。

### 智能指针的引用计数

`sk_sp<SkFontMgr>` 在复制时增加引用计数:

```cpp
for (const auto& fm : fList)  // 拷贝 sk_sp
```

引用计数操作有原子操作开销,但通过 `const auto&` 最小化拷贝次数。

### 无缓存机制

该类不缓存查询结果:
- 每次查询都遍历列表
- 适合查询频率低或字体集合变化的场景
- 高频查询场景可在上层添加缓存

### 空样式集的短路

```cpp
if (fs->count() > 0) {
    return fs;
}
```

只有非空样式集才返回,避免返回无用的空集。但这需要每个管理器都执行完整查询,可能包含磁盘 I/O 等开销。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| include/utils/SkOrderedFontMgr.h | 公共 API 头文件 |
| src/utils/SkOrderedFontMgr.cpp | 实现文件 |
| include/core/SkFontMgr.h | 基类接口 |
| include/core/SkTypeface.h | 字体对象 |
| include/core/SkFontStyle.h | 字体样式 |
| src/ports/SkFontMgr_*.cpp | 各平台字体管理器实现 |
