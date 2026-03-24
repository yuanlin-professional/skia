# FactoryHelpers - 塑形器工厂便利类

> 源文件: `modules/skshaper/utils/FactoryHelpers.h`

## 概述

FactoryHelpers.h 提供了 SkShapers::Factory 接口的具体实现类（HarfbuzzFactory、CoreTextFactory）和一个自动选择最佳可用塑形后端的便利函数（BestAvailable）。该文件设计为纯头文件实现（header-only），所有代码通过 inline 函数和类定义在编译时由客户端直接包含，确保客户端的编译环境决定可用的后端。

## 架构位置

FactoryHelpers.h 是 skshaper 模块的顶层便利层，位于具体后端头文件（SkShaper_harfbuzz.h、SkShaper_coretext.h、SkShaper_skunicode.h）之上。它汇聚所有条件编译信息，为客户端提供一站式的工厂创建。

**选择链**: `BestAvailable()` -> HarfbuzzFactory > CoreTextFactory > Primitive::Factory()

## 主要类与结构体

### `SkShapers::HarfbuzzFactory`
Factory 的 HarfBuzz 实现，在 `SK_SHAPER_HARFBUZZ_AVAILABLE` 和 `SK_SHAPER_UNICODE_AVAILABLE` 时可用：
- 构造函数接受可选的 `sk_sp<SkUnicode>`，默认通过 `BestAvailableUnicode()` 获取
- `makeShaper`: 创建 `ShaperDrivenWrapper`
- `makeBidiRunIterator`: 创建 `SkShapers::unicode::BidiRunIterator`
- `makeScriptRunIterator`: 创建 `SkShapers::HB::ScriptRunIterator`
- `getUnicode`: 返回内部 SkUnicode 实例

### `SkShapers::CoreTextFactory`
Factory 的 CoreText 实现，在 `SK_SHAPER_CORETEXT_AVAILABLE` 时可用：
- `makeShaper`: 创建 `SkShapers::CT::CoreText()`
- `makeBidiRunIterator` / `makeScriptRunIterator`: 返回 Trivial 迭代器（CoreText 内部处理）
- `getUnicode`: 返回 nullptr（不使用外部 Unicode）

### 辅助函数

#### `BestAvailableUnicode()`
按优先级尝试创建 SkUnicode 实例：
1. ICU（`SK_UNICODE_ICU_IMPLEMENTATION`）
2. ICU4X（`SK_UNICODE_ICU4X_IMPLEMENTATION`）
3. libgrapheme（`SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION`）

#### `BestAvailable()`
按优先级创建最佳可用工厂：
1. HarfBuzz + Unicode（最完整）
2. CoreText（Apple 平台原生）
3. Primitive（最基础）

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SkShapers::BestAvailableUnicode()` | 获取最佳 Unicode 实现 |
| `SkShapers::BestAvailable()` | 获取最佳塑形工厂 |

## 内部实现细节

### 纯头文件设计
文件中所有函数和类都是 `inline` 或类内定义的，这是因为可用后端取决于客户端的编译环境。如果放在 .cpp 中编译，则无法获取客户端的编译宏定义。

### 条件编译层次
```
SK_SHAPER_UNICODE_AVAILABLE
  ├── SK_UNICODE_ICU_IMPLEMENTATION
  ├── SK_UNICODE_ICU4X_IMPLEMENTATION
  └── SK_UNICODE_LIBGRAPHEME_IMPLEMENTATION
  └── SK_SHAPER_HARFBUZZ_AVAILABLE
       └── HarfbuzzFactory

SK_SHAPER_CORETEXT_AVAILABLE
  └── CoreTextFactory

(fallback) Primitive::Factory
```

### CoreTextFactory 的简化设计
CoreText 自行处理 BiDi 和脚本检测，因此 makeBidiRunIterator 和 makeScriptRunIterator 返回 Trivial 实现（参数为 0, 0），这些迭代器不会被实际使用。

## 依赖关系

- **SkShaper_factory.h**: Factory 抽象基类
- **SkShaper_harfbuzz.h**: HarfBuzz 塑形器创建函数
- **SkShaper_skunicode.h**: Unicode BiDi 迭代器
- **SkShaper_coretext.h**: CoreText 塑形器
- **SkUnicode_icu.h / SkUnicode_icu4x.h / SkUnicode_libgrapheme.h**: Unicode 后端

## 设计模式与设计决策

1. **策略选择器模式**: `BestAvailable()` 根据编译时可用的后端自动选择最佳策略。
2. **依赖注入**: HarfbuzzFactory 的构造函数接受可选的 SkUnicode，允许客户端指定特定的 Unicode 实现。
3. **编译时多态**: 通过条件编译宏而非运行时类型检测确定可用后端，零运行时开销。
4. **Header-only 库模式**: 所有代码在头文件中，确保客户端编译环境的宏定义正确传递。

## 性能考量

- BestAvailableUnicode 和 BestAvailable 通常在程序初始化时调用一次，不在热路径上
- HarfbuzzFactory 持有 SkUnicode 实例，避免每次创建塑形器时重新初始化 Unicode
- inline 函数允许编译器在客户端代码中进行内联优化

## 使用示例

### 获取最佳塑形工厂
```cpp
// 自动选择最佳后端
auto factory = SkShapers::BestAvailable();

// 创建塑形器
auto shaper = factory->makeShaper(fontMgr);

// 创建运行迭代器
auto bidiIter = factory->makeBidiRunIterator(utf8, len, 0);
auto scriptIter = factory->makeScriptRunIterator(utf8, len, script);
```

### 指定 Unicode 实现
```cpp
// 强制使用 ICU4X
auto uc = SkUnicodes::ICU4X::Make();
auto factory = sk_make_sp<SkShapers::HarfbuzzFactory>(uc);
```

### BestAvailable 的选择逻辑
在编译时，根据以下宏定义决定可用后端：
1. 如果同时定义了 `SK_SHAPER_HARFBUZZ_AVAILABLE` 和 `SK_SHAPER_UNICODE_AVAILABLE`：
   - 选择 HarfbuzzFactory，提供最完整的排版支持
   - 需要 HarfBuzz 库和至少一个 Unicode 实现
2. 否则如果定义了 `SK_SHAPER_CORETEXT_AVAILABLE`：
   - 选择 CoreTextFactory，使用 Apple 原生排版
   - 仅在 macOS/iOS 上可用
3. 否则：
   - 回退到 Primitive::Factory()，最基础的排版
   - 不支持复杂文字、BiDi 或高级换行

### HarfbuzzFactory 与 CoreTextFactory 的对比
| 特性 | HarfbuzzFactory | CoreTextFactory |
|------|----------------|-----------------|
| BiDi 支持 | SkUnicode (完整) | CoreText 内部 |
| 脚本检测 | HarfBuzz hb_unicode_script | CoreText 内部 |
| 复杂文字 | HarfBuzz GSUB/GPOS | CoreText 内部 |
| 字体回退 | SkFontMgr | CoreText 内部 |
| 平台 | 跨平台 | Apple 专用 |
| Unicode 依赖 | ICU/ICU4X/libgrapheme | 无 |

## 相关文件

- `modules/skshaper/include/SkShaper_factory.h` - Factory 抽象接口
- `modules/skshaper/include/SkShaper_harfbuzz.h` - HarfBuzz 接口
- `modules/skshaper/include/SkShaper_coretext.h` - CoreText 接口
- `modules/skunicode/include/SkUnicode.h` - Unicode 抽象接口

## 使用注意事项

1. `BestAvailable()` 在编译时确定，运行时无法切换后端
2. HarfbuzzFactory 的 SkUnicode 实例在工厂生命周期内共享
3. CoreTextFactory 的 BiDi/Script 迭代器返回 Trivial 实现，不提供实际功能
4. 如果客户端需要特定的 Unicode 实现，应显式传递给 HarfbuzzFactory 构造函数
5. BestAvailableUnicode 的选择优先级是 ICU > ICU4X > libgrapheme
