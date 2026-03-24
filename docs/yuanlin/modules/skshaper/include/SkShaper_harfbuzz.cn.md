# SkShaper_harfbuzz - HarfBuzz 文本塑形接口

> 源文件: `modules/skshaper/include/SkShaper_harfbuzz.h`

## 概述

SkShaper_harfbuzz.h 声明了基于 HarfBuzz 排版引擎的文本塑形器创建函数和脚本运行迭代器。HarfBuzz 是功能最完整的塑形后端，支持复杂文字（阿拉伯语、天城体等）的连字、字形替换和 GSUB/GPOS 表处理。该头文件提供了三种不同换行策略的塑形器变体。

## 架构位置

位于 `SkShapers::HB` 命名空间，是 skshaper 模块中最重要的后端实现接口。它依赖 HarfBuzz 库和 SkUnicode 接口进行文本塑形和 Unicode 属性查询。

## 主要类与结构体

无独立类定义。所有功能通过命名空间级函数提供。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `ShaperDrivenWrapper(unicode, fallback)` | 创建塑形驱动换行的塑形器（逐段塑形后判断换行） |
| `ShapeThenWrap(unicode, fallback)` | 创建先塑形后换行的塑形器（完整塑形后根据宽度换行） |
| `ShapeDontWrapOrReorder(unicode, fallback)` | 创建不换行不重排的塑形器（保持输入顺序） |
| `ScriptRunIterator(utf8, utf8Bytes)` | 创建脚本运行迭代器（自动检测脚本） |
| `ScriptRunIterator(utf8, utf8Bytes, script)` | 创建脚本运行迭代器（指定默认脚本） |
| `PurgeCaches()` | 清除 HarfBuzz 字体面缓存 |

## 内部实现细节

三种塑形策略的区别：
- **ShaperDrivenWrapper**: 边塑形边换行，适合交互式文本编辑，可在塑形过程中利用安全断行点
- **ShapeThenWrap**: 先完成所有塑形，再根据字形宽度进行换行，适合静态排版
- **ShapeDontWrapOrReorder**: 不进行换行和 BiDi 重排，所有文本作为单行输出

## 依赖关系

- **SkShaper**: 塑形器基类
- **SkUnicode**: Unicode 处理（BiDi、行断行等）
- **SkFontMgr**: 字体回退
- **HarfBuzz 库**: 底层文本塑形引擎

## 设计模式与设计决策

1. **策略模式**: 三种塑形器变体实现不同的换行策略，共享 HarfBuzz 塑形核心。
2. **缓存管理**: `PurgeCaches()` 提供显式的缓存清理入口，用于内存压力场景。
3. **可选默认脚本**: ScriptRunIterator 支持自动检测和手动指定两种模式。

## 性能考量

- HarfBuzz 字体面（HBFace）创建较重（需要 sanitize），通过 LRU 缓存（100 条目）复用
- `PurgeCaches()` 应在字体变更或内存压力时调用

## 相关文件

- `modules/skshaper/src/SkShaper_harfbuzz.cpp` - 完整实现
- `modules/skshaper/include/SkShaper.h` - SkShaper 基类
- `modules/skshaper/include/SkShaper_skunicode.h` - Unicode BiDi 迭代器接口

## 使用示例

```cpp
// 创建 Unicode 和字体管理器
auto unicode = SkUnicodes::ICU::Make();
auto fontMgr = SkFontMgr::RefDefault();

// 创建塑形驱动换行器（最常用）
auto shaper = SkShapers::HB::ShaperDrivenWrapper(unicode, fontMgr);

// 创建脚本运行迭代器
auto scriptIter = SkShapers::HB::ScriptRunIterator(utf8, utf8Bytes);

// 使用指定默认脚本
auto scriptIter2 = SkShapers::HB::ScriptRunIterator(
    utf8, utf8Bytes, SkSetFourByteTag('L','a','t','n'));

// 清除缓存
SkShapers::HB::PurgeCaches();
```

## 使用注意事项

1. 所有工厂函数需要非空的 `sk_sp<SkUnicode>` 参数
2. fontMgr 参数可为 nullptr，此时使用 `SkFontMgr::RefEmpty()`
3. HarfBuzz 缓存为全局共享，`PurgeCaches()` 影响所有塑形器实例
4. ScriptRunIterator 使用 HarfBuzz 内置的 Unicode 脚本数据库
