# skparagraph/utils - 段落排版测试工具

## 概述

`utils/` 目录包含 skparagraph 模块的测试辅助工具类。核心组件是 `TestFontCollection`,它为单元测试和基准测试提供了一套确定性的字体集合,确保测试在不同平台和环境下产生一致的结果。

在文本排版测试中,字体的可用性和度量信息直接影响排版结果。使用 `TestFontCollection` 而非系统字体管理器,可以消除因操作系统、字体安装差异而导致的测试不确定性。

## 目录结构

```
utils/
|-- BUILD.bazel              # Bazel 构建规则
|-- TestFontCollection.cpp   # 测试字体集合实现
|-- TestFontCollection.h     # 测试字体集合头文件
```

## 关键类与函数

### TestFontCollection

`TestFontCollection` 继承自 `FontCollection`,配置了一组已知的测试字体:

```cpp
class TestFontCollection : public FontCollection {
public:
    TestFontCollection(const std::string& resourceDir, bool testOnly = true, bool loadFonts = true);
    // resourceDir: 字体资源目录路径(通常为 Skia 的 resources/fonts/)
    // testOnly: 若为true,仅使用测试字体;否则也加载系统字体
    // loadFonts: 是否立即加载字体
};
```

### 使用模式

```cpp
// 在测试中使用 TestFontCollection:
auto fontCollection = sk_make_sp<TestFontCollection>(resourceDir);

ParagraphStyle style;
auto builder = ParagraphBuilder::make(style, fontCollection, unicode);
builder->addText("Test text");
auto paragraph = builder->Build();
paragraph->layout(500);
```

### 测试字体集

`TestFontCollection` 通常加载以下类型的测试字体:
- **Ahem**: 特殊的测试字体,所有字形为正方形方块,便于精确验证尺寸
- **Roboto**: Google 的 Android 默认字体,用于常规 Latin 文本测试
- **Noto CJK**: 用于中日韩文本排版测试
- **Emoji 字体**: 用于 Emoji 相关排版测试

## 依赖关系

```
utils/
  |-- modules/skparagraph/include/FontCollection.h (继承基类)
  |-- modules/skparagraph/include/TypefaceFontProvider.h (字体注册)
  |-- Skia Core: SkFontMgr, SkTypeface, SkData
  |-- resources/ (测试字体文件: .ttf, .otf)
```

## 设计模式分析

### 测试夹具模式 (Test Fixture)
`TestFontCollection` 是典型的测试夹具,为测试提供受控的环境。通过统一的字体集合,消除了外部依赖带来的不确定性。

### 工厂方法模式
`TestFontCollection` 的构造过程实质是工厂方法,根据配置参数组装不同的字体管理器组合:
- 测试字体管理器(使用 `TypefaceFontProvider`)
- 默认字体管理器(可选的系统字体管理器)

## 数据流

```
TestFontCollection 初始化
  |
  +-- 扫描 resourceDir 目录
  +-- 加载 .ttf / .otf 字体文件
  +-- 创建 TypefaceFontProvider
  +-- 注册所有测试字体
  +-- 配置字体管理器链
  |
  v
提供给 ParagraphBuilder / ParagraphImpl
  |
  +-- findTypefaces(): 根据字体族名查找字体
  +-- defaultFallback(): 字形缺失时的字体回退
```

## 相关文档与参考

- **使用者**: `modules/skparagraph/tests/SkParagraphTest.cpp` - 单元测试
- **使用者**: `modules/skparagraph/bench/ParagraphBench.cpp` - 性能测试
- **字体管理**: `modules/skparagraph/include/FontCollection.h` - 字体集合接口
- **字体提供器**: `modules/skparagraph/include/TypefaceFontProvider.h` - 自定义字体注册
- **测试字体**: `resources/fonts/` - Skia 测试字体资源
- **字体度量**: `include/core/SkFontMetrics.h` - 字体度量数据结构
