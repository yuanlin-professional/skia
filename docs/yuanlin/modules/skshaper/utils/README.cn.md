# skshaper/utils - 文本整形工具辅助

## 概述

`utils/` 目录包含 skshaper 模块的实用工具类。核心文件 `FactoryHelpers.h` 提供了整形器工厂的便捷创建函数,帮助客户端根据编译配置自动选择最佳的整形后端,而无需手动编写条件编译代码。

该文件的关键设计理念是"最佳可用"(Best Available)--- 根据客户端编译时链接的模块,自动选择功能最完整的整形后端。优先级顺序为:HarfBuzz > CoreText > Primitive。

## 目录结构

```
utils/
|-- BUILD.bazel          # Bazel 构建规则
|-- FactoryHelpers.h     # 工厂辅助: BestAvailable, HarfbuzzFactory, CoreTextFactory
```

## 关键类与函数

### FactoryHelpers.h

**BestAvailableUnicode()** - 获取最佳可用的 Unicode 实现:

```cpp
static inline sk_sp<SkUnicode> BestAvailableUnicode() {
    // 优先级: ICU > ICU4X > Libgrapheme
    sk_sp<SkUnicode> uc;
    uc = SkUnicodes::ICU::Make();       // 优先使用完整 ICU
    if (!uc) uc = SkUnicodes::ICU4X::Make();  // 其次 ICU4X
    if (!uc) uc = SkUnicodes::Libgrapheme::Make(); // 最后 libgrapheme
    return uc;
}
```

**HarfbuzzFactory** - HarfBuzz 整形器工厂:

```cpp
class HarfbuzzFactory final : public SkShapers::Factory {
    explicit HarfbuzzFactory(sk_sp<SkUnicode> uc = nullptr);
    // 使用 SkShapers::HB::ShaperDrivenWrapper 创建整形器
    // 使用 SkShapers::unicode::BidiRunIterator 创建 BiDi 迭代器
    // 使用 SkShapers::HB::ScriptRunIterator 创建脚本迭代器
    SkUnicode* getUnicode() override;  // 提供 SkUnicode 访问
};
```

**CoreTextFactory** - CoreText 整形器工厂:

```cpp
class CoreTextFactory final : public SkShapers::Factory {
    // 使用 SkShapers::CT::CoreText 创建整形器
    // BiDi/Script 迭代器使用 Trivial 实现(CoreText内部处理)
    SkUnicode* getUnicode() override { return nullptr; }
};
```

**BestAvailable()** - 获取最佳可用工厂:

```cpp
inline sk_sp<Factory> BestAvailable() {
    // 优先级: HarfBuzz + Unicode > CoreText > Primitive
    #if defined(SK_SHAPER_HARFBUZZ_AVAILABLE) && defined(SK_SHAPER_UNICODE_AVAILABLE)
        return sk_make_sp<HarfbuzzFactory>();
    #elif defined(SK_SHAPER_CORETEXT_AVAILABLE)
        return sk_make_sp<CoreTextFactory>();
    #else
        return Primitive::Factory();
    #endif
}
```

## 依赖关系

```
utils/
  |-- modules/skshaper/include/SkShaper.h (SkShaper接口)
  |-- modules/skshaper/include/SkShaper_factory.h (Factory抽象)
  |-- modules/skshaper/include/SkShaper_harfbuzz.h (条件包含)
  |-- modules/skshaper/include/SkShaper_skunicode.h (条件包含)
  |-- modules/skshaper/include/SkShaper_coretext.h (条件包含)
  |-- modules/skunicode/include/SkUnicode.h (条件包含)
  |-- modules/skunicode/include/SkUnicode_icu.h (条件包含)
  |-- modules/skunicode/include/SkUnicode_icu4x.h (条件包含)
  |-- modules/skunicode/include/SkUnicode_libgrapheme.h (条件包含)
```

## 设计模式分析

### 编译时策略选择
`BestAvailable()` 利用预处理宏在编译时选择整形后端,这是一种编译时策略模式。客户端只需调用 `SkShapers::BestAvailable()` 即可获得最佳配置,无需了解底层后端细节。

### inline 头文件实现
所有函数都以 `inline` 或类内定义的形式实现在头文件中,因为选择逻辑必须在**客户端**的编译上下文中评估(客户端的预处理宏决定了哪些后端可用)。

### 优雅降级
从 HarfBuzz(完整功能)到 CoreText(平台特定)再到 Primitive(基本功能)的优先级链确保了在任何构建配置下都有可用的整形器。

## 数据流

```
客户端代码
  |
  +-- auto factory = SkShapers::BestAvailable()
  |     |
  |     +-- [编译时检测可用后端]
  |     +-- 返回: HarfbuzzFactory / CoreTextFactory / PrimitiveFactory
  |
  +-- auto shaper = factory->makeShaper(fontMgr)
  +-- auto bidi = factory->makeBidiRunIterator(utf8, len, level)
  +-- auto script = factory->makeScriptRunIterator(utf8, len, tag)
  +-- auto unicode = factory->getUnicode()
  |
  +-- shaper->shape(...)
```

## 相关文档与参考

- **使用者**: `modules/skparagraph/` - 段落排版模块通过工厂创建整形器
- **工厂接口**: `modules/skshaper/include/SkShaper_factory.h` - Factory 抽象定义
- **整形后端**: `modules/skshaper/src/` - 各后端实现
- **Unicode 后端**: `modules/skunicode/include/` - Unicode 实现选择
