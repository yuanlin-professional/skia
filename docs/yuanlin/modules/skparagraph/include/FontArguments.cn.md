# FontArguments

> 源文件: [modules/skparagraph/include/FontArguments.h](../../../../modules/skparagraph/include/FontArguments.h)

## 概述

`FontArguments` 是 Skia 段落排版模块中对 `SkFontArguments` 的可拷贝封装类。`SkFontArguments` 本身是一个仅持有数据指针（非拥有型）的轻量级结构，不支持安全拷贝。`FontArguments` 通过内部存储变体轴坐标和调色板覆盖数据的完整副本，使其成为可安全拷贝、移动和比较的值类型，适合在 `TextStyle` 中作为可选字体参数长期持有。

## 架构位置

```
skia::textlayout 命名空间
  TextStyle
    └── std::optional<FontArguments>  ← 本文件定义
          └── 用于 FontCollection::findTypefaces() 查找字体变体

SkFontArguments (Skia 核心)
    └── FontArguments (skparagraph 封装) ← 值语义副本
```

`FontArguments` 是 `SkFontArguments` 和 `TextStyle` 之间的桥接层。

## 主要类与结构体

### FontArguments
- 可拷贝的字体参数封装类
- 成员变量：
  - `fCollectionIndex`（`int`）- 字体集合索引（TTC/OTC 中的字体索引）
  - `fCoordinates`（`vector<VariationPosition::Coordinate>`）- 变体轴坐标值
  - `fPaletteIndex`（`int`）- 调色板索引
  - `fPaletteOverrides`（`vector<Palette::Override>`）- 调色板覆盖项

## 公共 API 函数

### 构造函数
```cpp
FontArguments(const SkFontArguments&);
FontArguments(const FontArguments&) = default;
FontArguments(FontArguments&&) = default;
```
从 `SkFontArguments` 构造（拷贝数据）。支持拷贝和移动构造。默认构造函数被删除（`= delete`），必须从 `SkFontArguments` 创建。

### 赋值运算符
```cpp
FontArguments& operator=(const FontArguments&) = default;
FontArguments& operator=(FontArguments&&) = default;
```
支持拷贝和移动赋值。

### `CloneTypeface`
```cpp
sk_sp<SkTypeface> CloneTypeface(const sk_sp<SkTypeface>& typeface) const;
```
使用当前字体参数克隆一个字体面（typeface），应用变体轴设置和调色板覆盖。这是参数实际生效的核心方法。

### 比较运算符
```cpp
friend bool operator==(const FontArguments& a, const FontArguments& b);
friend bool operator!=(const FontArguments& a, const FontArguments& b);
```
支持相等性比较，用于缓存键和样式匹配。

### std::hash 特化
```cpp
namespace std {
    template<> struct hash<skia::textlayout::FontArguments> {
        size_t operator()(const skia::textlayout::FontArguments& args) const;
    };
}
```
提供标准库哈希支持，允许 `FontArguments` 用作 `std::unordered_map` 的键。

## 内部实现细节

### 数据所有权

`SkFontArguments` 中的 `VariationPosition` 和 `Palette` 仅持有指向外部数据的指针（非拥有型）。`FontArguments` 的构造函数将这些指针指向的数据完整拷贝到内部的 `std::vector` 中，确保数据的生命周期独立于原始 `SkFontArguments`。

### 友元声明

将 `operator==`、`operator!=` 和 `std::hash<FontArguments>` 声明为友元，允许这些函数访问私有成员变量，避免暴露 getter 方法。

### 默认构造删除

`FontArguments() = delete` 确保对象必须从有意义的 `SkFontArguments` 数据构造，避免意外创建空对象。

## 依赖关系

- **Skia 核心**: `SkFontArguments`（源数据类型）、`SkTypeface`（字体面）
- **标准库**: `<functional>`（hash 特化）、`<vector>`

## 设计模式与设计决策

1. **值语义封装**: 将非拥有型的 `SkFontArguments` 封装为拥有型的 `FontArguments`，解决了生命周期管理问题。

2. **显式构造**: 删除默认构造函数，强制从 `SkFontArguments` 构造，确保语义正确性。

3. **哈希支持**: 通过 `std::hash` 特化支持将 `FontArguments` 用作哈希容器的键，这在字体缓存中非常有用（避免为相同参数的字体重复创建 typeface）。

4. **最小接口原则**: 仅暴露 `CloneTypeface` 和比较/哈希操作，不提供对内部数据的直接访问，保持了封装性。

## 性能考量

- 构造时拷贝变体轴坐标和调色板覆盖，对于典型场景（少量变体轴）开销极小。
- `CloneTypeface` 涉及字体面克隆，是相对昂贵的操作，应通过缓存避免重复调用。
- `std::hash` 特化使得基于哈希的字体缓存成为可能，将 typeface 查找降低为 O(1)。
- 比较运算符需要比较 vector 内容，但变体轴数量通常很少（<10）。

## 相关文件

- `include/core/SkFontArguments.h` - 原始字体参数类型
- `include/core/SkTypeface.h` - 字体面类型
- `modules/skparagraph/include/TextStyle.h` - 使用 `optional<FontArguments>` 的文本样式
- `modules/skparagraph/include/FontCollection.h` - 使用 FontArguments 查找字体
- `modules/skparagraph/src/FontArguments.cpp` - 实现文件
