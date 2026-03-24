# SkFontMgr_fontations_empty

> 源文件
> - src/ports/SkFontMgr_fontations_empty.cpp

## 概述

`SkFontMgr_fontations_empty` 是基于 Fontations 渲染后端的空字体管理器实现。Fontations 是 Skia 的新一代字体渲染引擎，使用 Rust 编写。该模块提供了一个不包含任何预加载字体的最小化字体管理器，主要用于测试场景，允许从数据、流或文件动态创建字体实例。

核心特点：
- **空字体列表**：不预加载任何系统字体
- **Fontations 渲染**：使用 Rust 实现的 Fontations 引擎
- **动态字体加载**：支持从多种数据源创建 typeface
- **测试工具**：作为 FontToolUtils 中 TestFontMgr 的基础
- **最小化实现**：所有查询方法返回空结果

该模块是 Fontations 字体管理器系列的基础组件，用于需要完全控制字体加载的场景。

## 架构位置

```
SkFontMgr (抽象基类)
    ↓
SkFontMgr_Fontations_Empty (本模块)
    ↓
SkTypeface_Fontations (Rust 渲染后端)
    ↓
Fontations Library (Rust)
    ↓
字体文件 (TrueType, OpenType, WOFF2, etc.)
```

与 FreeType 路径对比：
```
FreeType 路径:
SkFontMgr_Custom → SkTypeface_FreeType → FreeType Library

Fontations 路径:
SkFontMgr_Fontations → SkTypeface_Fontations → Fontations Library (Rust)
```

## 主要类与结构体

### SkFontMgr_Fontations_Empty
Fontations 空字体管理器类，继承自 `SkFontMgr`。

**设计特点：**
- 匿名命名空间：仅在编译单元内部可见
- 所有查询方法返回空结果或 nullptr
- 支持从数据源创建 typeface

**核心方法：**
- `onCountFamilies()`: 返回 0（无家族）
- `onGetFamilyName()`: 空实现
- `onCreateStyleSet()`: 返回空样式集
- `onMatchFamily()`: 返回空样式集
- `onMatchFamilyStyle()`: 返回 nullptr
- `onMatchFamilyStyleCharacter()`: 返回 nullptr（不支持字符回退）
- `onMakeFromData()`: 从数据创建 typeface
- `onMakeFromStreamIndex()`: 从流和索引创建 typeface
- `onMakeFromStreamArgs()`: 从流和参数创建 typeface
- `onMakeFromFile()`: 从文件创建 typeface
- `onLegacyMakeTypeface()`: 返回 nullptr（无默认字体）

## 公共 API 函数

### SkFontMgr_New_Fontations_Empty()
```cpp
sk_sp<SkFontMgr> SkFontMgr_New_Fontations_Empty();
```
创建 Fontations 空字体管理器。

**返回值：** 字体管理器智能指针

**使用场景：**
- 单元测试
- 集成测试
- 需要完全控制字体加载的应用
- 性能基准测试

**使用示例：**
```cpp
sk_sp<SkFontMgr> fontMgr = SkFontMgr_New_Fontations_Empty();

// 从文件加载字体
sk_sp<SkTypeface> typeface = fontMgr->makeFromFile("font.ttf", 0);

// 从数据加载字体
sk_sp<SkData> data = SkData::MakeFromFileName("font.otf");
sk_sp<SkTypeface> typeface2 = fontMgr->makeFromData(data, 0);
```

## 内部实现细节

### 查询方法的空实现

所有字体查询方法返回空结果：

```cpp
int onCountFamilies() const override { return 0; }

void onGetFamilyName(int index, SkString* familyName) const override {}

sk_sp<SkFontStyleSet> onCreateStyleSet(int index) const override {
    return SkFontStyleSet::CreateEmpty();
}

sk_sp<SkFontStyleSet> onMatchFamily(const char familyName[]) const override {
    return SkFontStyleSet::CreateEmpty();
}
```

这确保了查询操作不会崩溃，但也不会返回任何有用的结果。

### 字体创建方法

#### onMakeFromData()
```cpp
sk_sp<SkTypeface> onMakeFromData(sk_sp<SkData> data, int ttcIndex) const override {
    return this->makeFromStream(std::make_unique<SkMemoryStream>(std::move(data)), ttcIndex);
}
```
将数据包装为内存流，然后调用 `makeFromStream()`。

#### onMakeFromStreamIndex()
```cpp
sk_sp<SkTypeface> onMakeFromStreamIndex(std::unique_ptr<SkStreamAsset> stream,
                                        int ttcIndex) const override {
    return this->makeFromStream(std::move(stream),
                                SkFontArguments().setCollectionIndex(ttcIndex));
}
```
将 TTC 索引转换为 `SkFontArguments`，然后调用 `makeFromStream()`。

#### onMakeFromStreamArgs()
```cpp
sk_sp<SkTypeface> onMakeFromStreamArgs(std::unique_ptr<SkStreamAsset> stream,
                                       const SkFontArguments& args) const override {
    return SkTypeface_Fontations::MakeFromStream(std::move(stream), args);
}
```
直接委托给 `SkTypeface_Fontations::MakeFromStream()`，这是实际的 Fontations typeface 工厂方法。

#### onMakeFromFile()
```cpp
sk_sp<SkTypeface> onMakeFromFile(const char path[], int ttcIndex) const override {
    std::unique_ptr<SkStreamAsset> stream = SkStream::MakeFromFile(path);
    return stream ? this->makeFromStream(std::move(stream), ttcIndex) : nullptr;
}
```
打开文件流，然后调用 `makeFromStream()`。如果文件打开失败，返回 nullptr。

### 回退方法

```cpp
sk_sp<SkTypeface> onMatchFamilyStyleCharacter(
    const char familyName[], const SkFontStyle&,
    const char* bcp47[], int bcp47Count,
    SkUnichar character) const override {
    return nullptr;
}

sk_sp<SkTypeface> onLegacyMakeTypeface(const char familyName[],
                                       SkFontStyle style) const override {
    return nullptr;
}
```

这两个方法在空管理器中无法实现，因为没有可回退的字体。

### Fontations 与 FreeType 的区别

| 特性 | FreeType | Fontations |
|------|----------|------------|
| **实现语言** | C | Rust |
| **内存安全** | 手动管理 | 自动管理 |
| **性能** | 成熟优化 | 新兴优化 |
| **可变字体** | 支持 | 完整支持 |
| **COLRv1** | 支持 | 更好支持 |
| **WOFF2** | 需要额外库 | 原生支持 |
| **代码大小** | 较大 | 较小 |

## 依赖关系

### Skia 内部依赖
| 模块 | 用途 |
|------|------|
| `SkFontMgr` | 字体管理器抽象基类 |
| `SkTypeface_Fontations` | Fontations typeface 实现 |
| `SkFontStyle` | 字体样式定义 |
| `SkFontArguments` | 字体参数（TTC 索引、轴坐标等） |
| `SkStream` | 流接口 |
| `SkData` | 数据容器 |
| `SkMemoryStream` | 内存流实现 |
| `SkFontStyleSet` | 字体样式集基类 |

### 外部依赖
| 库 | 用途 |
|---|-----|
| **Fontations** | Rust 字体解析和渲染库 |
| `read-fonts` | 字体表解析 |
| `skrifa` | 字形渲染 |
| `fontations_ffi` | C++ 到 Rust 的 FFI 绑定 |

## 设计模式与设计决策

### 1. 空对象模式（Null Object Pattern）
整个类是空对象模式的实现，提供了完整的接口但不包含任何字体数据。

### 2. 工厂模式（Factory Pattern）
`SkFontMgr_New_Fontations_Empty()` 工厂函数隐藏了类的具体实现（匿名命名空间）。

### 3. 委托模式（Delegation Pattern）
所有 `makeFrom*` 方法最终委托给 `SkTypeface_Fontations::MakeFromStream()`。

### 4. 适配器模式（Adapter Pattern）
将不同的输入格式（数据、文件、流+索引）适配为统一的流+参数接口。

### 5. 最小化实现原则
仅实现创建功能，查询功能全部返回空结果，保持代码简洁。

### 6. 测试优先设计
专门为测试场景设计，允许测试代码完全控制字体加载。

## 性能考量

### 1. 零启动开销
不预加载任何字体，构造函数立即返回：
```cpp
SkFontMgr_Fontations_Empty() = default;
```

### 2. 按需加载
所有字体都是按需加载，只有显式调用 `makeFrom*` 时才解析字体。

### 3. 内存占用
- 管理器对象：约 16 字节（虚函数表指针 + 引用计数）
- 无额外字体数据

### 4. Fontations 性能特点
- **Rust 内存安全**：零成本抽象，无 GC 开销
- **现代优化**：利用 SIMD 和并发优化
- **增量解析**：只解析需要的字体表

### 5. 与 FreeType 性能对比
- **启动时间**：相当（都是按需加载）
- **首次渲染**：Fontations 稍慢（新代码路径）
- **后续渲染**：相当
- **可变字体**：Fontations 更快

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| `src/ports/SkTypeface_fontations_priv.h` | Fontations typeface 私有实现 |
| `include/ports/SkFontMgr_Fontations.h` | Fontations 字体管理器公共 API |
| `src/ports/fontations/src/ffi.rs` | Rust FFI 绑定 |
| `src/ports/fontations/src/base.rs` | Fontations 基础实现 |
| `include/core/SkFontMgr.h` | 字体管理器抽象基类 |
| `src/ports/SkFontMgr_custom_empty.cpp` | FreeType 空字体管理器（对比） |
| `tools/fonts/FontToolUtils.cpp` | TestFontMgr 实现 |
