# SkShaper_factory - 文本塑形器工厂接口

> 源文件: `modules/skshaper/include/SkShaper_factory.h`

## 概述

SkShaper_factory.h 定义了 SkShapers::Factory 抽象工厂接口，为文本塑形器（SkShaper）及其关联的运行迭代器（BiDiRunIterator、ScriptRunIterator）提供统一的创建入口。该接口允许客户端在不直接依赖具体实现（HarfBuzz、CoreText、Primitive）的情况下创建适合当前环境的塑形组件。

## 架构位置

Factory 位于 `SkShapers` 命名空间内，是文本塑形模块的抽象工厂层。它被 FactoryHelpers.h 中的具体工厂类（HarfbuzzFactory、CoreTextFactory）实现，被 Skia 的高层文本渲染组件（如 skparagraph、Slide）使用。

**层级**: 客户端 -> `SkShapers::Factory` -> 具体工厂 -> `SkShaper` / 迭代器

## 主要类与结构体

### `SkShapers::Factory`（抽象基类）
继承自 SkRefCnt，定义了三个纯虚创建方法和一个 Unicode 访问器：
- `makeShaper(sk_sp<SkFontMgr>)`: 创建塑形器实例
- `makeBidiRunIterator(utf8, utf8Bytes, bidiLevel)`: 创建 BiDi 运行迭代器
- `makeScriptRunIterator(utf8, utf8Bytes, script)`: 创建脚本运行迭代器
- `getUnicode()`: 获取底层 SkUnicode 实例

## 公共 API 函数

| 命名空间 | 函数 | 说明 |
|----------|------|------|
| `SkShapers::Primitive` | `Factory()` | 创建原始（无复杂排版）工厂实例 |

## 内部实现细节

Factory 是纯接口类，无内部实现。具体实现由以下类提供：
- `HarfbuzzFactory`（FactoryHelpers.h）：基于 HarfBuzz + SkUnicode
- `CoreTextFactory`（FactoryHelpers.h）：基于 macOS/iOS CoreText
- Primitive Factory：最基础的字符到字形映射

## 依赖关系

- **SkShaper**: 塑形器基类及其嵌套迭代器类型
- **SkFontMgr**: 字体管理器（用于字体回退）
- **SkUnicode**: Unicode 处理接口
- **SkFourByteTag**: 脚本标签类型
- **SkRefCnt**: 引用计数基类

## 设计模式与设计决策

1. **抽象工厂模式**: 将塑形器和迭代器的创建统一到一个工厂接口，使客户端代码与具体实现解耦。
2. **引用计数管理**: 继承 SkRefCnt，工厂实例通过 `sk_sp` 智能指针管理生命周期。
3. **Unicode 访问**: `getUnicode()` 方法允许外部获取工厂内部使用的 Unicode 实例，避免重复创建。

## 性能考量

- Factory 实例通常为单例或少量实例，创建开销可忽略
- 工厂方法本身的开销取决于底层实现（HarfBuzz 初始化较重，Primitive 轻量）

## 相关文件

- `modules/skshaper/include/SkShaper.h` - SkShaper 基类定义
- `modules/skshaper/utils/FactoryHelpers.h` - 具体工厂实现
- `modules/skshaper/include/SkShaper_harfbuzz.h` - HarfBuzz 塑形接口
- `modules/skshaper/include/SkShaper_coretext.h` - CoreText 塑形接口

## 使用示例

```cpp
// 获取工厂（通常使用 FactoryHelpers.h 中的 BestAvailable）
auto factory = SkShapers::BestAvailable();

// 创建塑形器
auto shaper = factory->makeShaper(fontMgr);

// 创建运行迭代器
auto bidi = factory->makeBidiRunIterator(utf8, len, 0);
auto script = factory->makeScriptRunIterator(utf8, len, SkSetFourByteTag('L','a','t','n'));

// 获取 Unicode 实例（如果需要进行其他 Unicode 操作）
SkUnicode* unicode = factory->getUnicode();
```

## 使用注意事项

1. Factory 实例应通过 `sk_sp<Factory>` 管理生命周期
2. `getUnicode()` 在 CoreText 工厂中返回 nullptr
3. Primitive 工厂创建的迭代器功能有限
4. 工厂方法返回 `unique_ptr`，调用方获得所有权
