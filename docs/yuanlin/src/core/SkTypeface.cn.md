# SkTypeface

> 源文件: include/core/SkTypeface.h, src/core/SkTypeface.cpp

## 概述

`SkTypeface` 是 Skia 字体系统的核心抽象类,代表一个字体及其固有样式属性(粗细、宽度、倾斜)。它封装了字体的元数据、字形访问、表数据查询等功能,是文本渲染管线的基础组件。`SkTypeface` 对象是不可变的,可以安全地在多线程间共享。该类支持字体序列化、变体字体、字距调整等高级特性。

## 架构位置

`SkTypeface` 位于 Skia 核心 API 层,是字体系统的顶层抽象:

- **上游**: `SkFontMgr`(字体管理器)、平台字体工厂
- **下游**: `SkScalerContext`(字形生成)、`SkFont`(文本绘制)
- **实现**: FreeType、CoreText、DirectWrite、Fontations 等平台特定后端
- **扩展**: `SkTypefaceProxy`(远程字体)、`SkEmptyTypeface`(空字体)

## 主要类与结构体

### SkTypeface

**继承关系**:
```
SkRefCnt
    └── SkWeakRefCnt
            └── SkTypeface
```

**关键成员变量**:

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fUniqueID` | `SkTypefaceID` | 全局唯一标识符 |
| `fStyle` | `SkFontStyle` | 字体样式(粗细、宽度、倾斜) |
| `fBounds` | `SkRect` | 字体边界框(延迟计算) |
| `fBoundsOnce` | `SkOnce` | 边界框计算控制 |
| `fIsFixedPitch` | `bool` | 是否等宽字体 |

### SkEmptyTypeface

内置的空字体实现,不包含任何字形:

```cpp
class SkEmptyTypeface : public SkTypeface {
    static sk_sp<SkTypeface> Make();
    int onCountGlyphs() const override { return 0; }
    // 所有操作返回默认值或空结果
};
```

### LocalizedStrings

用于迭代本地化字体名称:

```cpp
class LocalizedStrings {
    virtual bool next(LocalizedString* localizedString) = 0;
    void unref() { delete this; }
};
```

## 公共 API 函数

### 基本属性

| 函数签名 | 功能描述 |
|---------|---------|
| `SkFontStyle fontStyle() const` | 获取字体样式 |
| `bool isBold() const` | 是否粗体(weight ≥ 600) |
| `bool isItalic() const` | 是否斜体 |
| `bool isFixedPitch() const` | 是否等宽字体 |
| `SkTypefaceID uniqueID() const` | 获取唯一 ID |
| `int countGlyphs() const` | 获取字形数量 |
| `int getUnitsPerEm() const` | 获取 EM 单位 |

### 变体字体支持

| 函数签名 | 功能描述 |
|---------|---------|
| `int getVariationDesignPosition(...)` | 获取变体坐标 |
| `int getVariationDesignParameters(...)` | 获取变体轴参数 |
| `sk_sp<SkTypeface> makeClone(const SkFontArguments&)` | 创建变体实例 |

### 字符到字形映射

| 函数签名 | 功能描述 |
|---------|---------|
| `void unicharsToGlyphs(SkSpan<const SkUnichar>, SkSpan<SkGlyphID>)` | Unicode 转字形 ID |
| `SkGlyphID unicharToGlyph(SkUnichar)` | 单字符转字形 ID |
| `size_t textToGlyphs(const void*, size_t, SkTextEncoding, SkSpan<SkGlyphID>)` | 文本转字形 ID |

### 字距调整

| 函数签名 | 功能描述 |
|---------|---------|
| `bool getKerningPairAdjustments(SkSpan<const SkGlyphID>, SkSpan<int32_t>)` | 获取字距调整值 |

### 字体表访问

| 函数签名 | 功能描述 |
|---------|---------|
| `int countTables() const` | 获取表数量 |
| `int readTableTags(SkSpan<SkFontTableTag>)` | 读取表标签 |
| `size_t getTableSize(SkFontTableTag)` | 获取表大小 |
| `size_t getTableData(SkFontTableTag, size_t, size_t, void*)` | 读取表数据 |
| `sk_sp<SkData> copyTableData(SkFontTableTag)` | 复制整个表 |

### 序列化

| 函数签名 | 功能描述 |
|---------|---------|
| `bool serialize(SkWStream*, SerializeBehavior)` | 序列化到流 |
| `sk_sp<SkData> serialize(SerializeBehavior)` | 序列化到数据 |
| `static sk_sp<SkTypeface> MakeDeserialize(SkStream*, sk_sp<SkFontMgr>)` | 反序列化 |

### 字体名称

| 函数签名 | 功能描述 |
|---------|---------|
| `void getFamilyName(SkString*)` | 获取字族名 |
| `bool getPostScriptName(SkString*)` | 获取 PostScript 名 |
| `int getResourceName(SkString*)` | 获取资源名(文件路径) |
| `LocalizedStrings* createFamilyNameIterator()` | 创建本地化名称迭代器 |

### 字体数据

| 函数签名 | 功能描述 |
|---------|---------|
| `std::unique_ptr<SkStreamAsset> openStream(int* ttcIndex)` | 打开字体数据流 |
| `std::unique_ptr<SkStreamAsset> openExistingStream(int*)` | 打开已有流(优化版) |
| `SkRect getBounds() const` | 获取字体边界框 |

### 工厂方法

| 函数签名 | 功能描述 |
|---------|---------|
| `static sk_sp<SkTypeface> MakeEmpty()` | 创建空字体 |
| `static bool Equal(const SkTypeface*, const SkTypeface*)` | 比较两个字体 |
| `static void Register(FactoryId, MakeFunc)` | 注册自定义工厂 |

## 内部实现细节

### 字体工厂注册机制

Skia 支持多个字体后端,通过工厂注册实现:

```cpp
std::vector<DecoderProc>* decoders() {
    static SkNoDestructor<std::vector<DecoderProc>> decoders{{
        { SkEmptyTypeface::FactoryId, SkEmptyTypeface::MakeFromStream },
        { SkCustomTypefaceBuilder::FactoryId, SkCustomTypefaceBuilder::MakeFromStream },
#ifdef SK_TYPEFACE_FACTORY_CORETEXT
        { SkTypeface_Mac::FactoryId, SkTypeface_Mac::MakeFromStream },
#endif
        // ... 其他后端
    }};
    return decoders.get();
}
```

每个后端提供:
- 唯一的 `FactoryId`(4 字节标签)
- 从流创建字体的工厂函数

### 序列化行为

三种序列化模式:

```cpp
enum class SerializeBehavior {
    kDoIncludeData,        // 总是包含字体数据
    kDontIncludeData,      // 从不包含字体数据
    kIncludeDataIfLocal,   // 仅本地字体包含数据
};
```

**序列化内容**:
- 工厂 ID
- 字族名称
- 字体样式
- 可选:字体数据流
- 可选:变体坐标

### 反序列化流程

```cpp
sk_sp<SkTypeface> SkTypeface::MakeDeserialize(SkStream* stream,
                                               sk_sp<SkFontMgr> lastResortMgr) {
    SkFontDescriptor desc;
    if (!SkFontDescriptor::Deserialize(stream, &desc)) {
        return nullptr;
    }

    if (desc.hasStream()) {
        // 查找匹配的工厂
        for (const DecoderProc& proc : *decoders()) {
            if (proc.id == desc.getFactoryId()) {
                return proc.makeFromStream(desc.detachStream(),
                                          desc.getFontArguments());
            }
        }
        // 降级到 lastResortMgr
        if (lastResortMgr) {
            return lastResortMgr->makeFromStream(...);
        }
    }
    // 按名称查找
    if (lastResortMgr) {
        return lastResortMgr->legacyMakeTypeface(desc.getFamilyName(),
                                                  desc.getStyle());
    }
    return SkEmptyTypeface::Make();
}
```

### 字符编码转换

支持多种文本编码:

```cpp
class SkConvertToUTF32 {
public:
    const SkUnichar* convert(const void* text, size_t byteLength,
                            SkTextEncoding encoding) {
        switch (encoding) {
            case SkTextEncoding::kUTF8:
                // 转换 UTF-8
                break;
            case SkTextEncoding::kUTF16:
                // 转换 UTF-16
                break;
            case SkTextEncoding::kUTF32:
                return (const SkUnichar*)text;  // 无需转换
            case SkTextEncoding::kGlyphID:
                // 直接使用字形 ID
                break;
        }
    }
};
```

### 字距调整实现

```cpp
bool SkTypeface::getKerningPairAdjustments(SkSpan<const SkGlyphID> glyphs,
                                           SkSpan<int32_t> adjustments) const {
    // 空 span 调用用于查询是否支持字距
    if (glyphs.size() <= 1 || adjustments.empty()) {
        return this->onGetKerningPairAdjustments({}, {});
    }

    const size_t n = std::min(glyphs.size() - 1, adjustments.size());
    return this->onGetKerningPairAdjustments(glyphs.first(n + 1),
                                            adjustments.first(n));
}
```

- N 个字形产生 N-1 个调整值
- 空调用判断字体是否支持字距
- 调整值单位为"设计单位"

### 边界框计算

```cpp
SkRect SkTypeface::getBounds() const {
    fBoundsOnce([this] {
        if (!this->onComputeBounds(&fBounds)) {
            fBounds.setEmpty();
        }
    });
    return fBounds;
}
```

- 使用 `SkOnce` 保证仅计算一次
- 延迟计算,仅在需要时执行
- 线程安全

**计算方法**:
```cpp
bool SkTypeface::onComputeBounds(SkRect* bounds) const {
    const SkScalar textSize = 2048;  // 使用大尺寸提高精度
    const SkScalar invTextSize = 1 / textSize;

    SkFont font;
    font.setTypeface(sk_ref_sp(const_cast<SkTypeface*>(this)));
    font.setSize(textSize);
    font.setLinearMetrics(true);

    // 创建缩放上下文并获取度量
    std::unique_ptr<SkScalerContext> ctx = ...;
    SkFontMetrics fm;
    ctx->getFontMetrics(&fm);

    // 缩放回 1pt 单位
    bounds->setLTRB(fm.fXMin * invTextSize, fm.fTop * invTextSize,
                    fm.fXMax * invTextSize, fm.fBottom * invTextSize);
    return true;
}
```

### 高级排版元数据

```cpp
std::unique_ptr<SkAdvancedTypefaceMetrics> SkTypeface::getAdvancedMetrics() const {
    std::unique_ptr<SkAdvancedTypefaceMetrics> result = this->onGetAdvancedMetrics();

    // 添加 PostScript 名称
    if (result && result->fPostScriptName.isEmpty()) {
        if (!this->getPostScriptName(&result->fPostScriptName)) {
            this->getFamilyName(&result->fPostScriptName);
        }
    }

    // 检查 OS/2 表的嵌入权限
    if (result && (result->fType == kTrueType_Font || result->fType == kCFF_Font)) {
        SkOTTableOS2::Version::V2::Type::Field fsType;
        constexpr SkFontTableTag os2Tag = SkTEndian_SwapBE32(SkOTTableOS2::TAG);
        if (this->getTableData(os2Tag, ..., &fsType) == sizeof(fsType)) {
            if (fsType.Restricted && !(fsType.PreviewPrint || fsType.Editable)) {
                result->fFlags |= kNotEmbeddable_FontFlag;
            }
            if (fsType.NoSubsetting) {
                result->fFlags |= kNotSubsettable_FontFlag;
            }
        }
    }
    return result;
}
```

用于 PDF 生成,提供字体类型、嵌入权限等信息。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|-----|------|
| `SkFontStyle` | 字体样式表示 |
| `SkFontArguments` | 变体字体参数 |
| `SkFontDescriptor` | 序列化描述符 |
| `SkScalerContext` | 字形生成上下文 |
| `SkTypefaceCache` | 字体缓存和 ID 生成 |
| `SkStream` | 字体数据流 |

### 被依赖的模块

| 模块 | 关系 |
|-----|------|
| `SkFont` | 使用字体进行文本度量和绘制 |
| `SkPaint` | 传统文本绘制接口 |
| `SkFontMgr` | 创建和管理字体 |
| `SkTextBlob` | 文本块使用字体信息 |
| PDF 后端 | 字体嵌入和子集化 |

## 设计模式与设计决策

### 设计模式

1. **模板方法模式**: 公共方法调用虚函数实现
2. **工厂模式**: 字体工厂注册和反序列化
3. **策略模式**: 不同后端实现不同策略
4. **单例模式**: 空字体使用单例
5. **延迟初始化**: 边界框按需计算

### 设计决策

**为什么字体对象不可变?**
- 允许多线程共享
- 简化缓存管理
- 变体通过 `makeClone()` 创建新对象

**为什么使用弱引用计数?**
```cpp
class SK_API SkTypeface : public SkWeakRefCnt
```
- 字形缓存持有弱引用
- 应用释放字体后可被缓存清理
- 避免循环引用

**为什么需要空字体?**
- 提供无效字体的安全替代
- 避免空指针检查
- 反序列化失败时的降级方案

**工厂 ID 设计**
```cpp
using FactoryId = SkFourByteTag;
static constexpr FactoryId FactoryId = SkSetFourByteTag('e','m','t','y');
```
- 4 字节人类可读标识符
- 用于序列化格式版本控制
- 支持多后端共存

**字距调整接口设计**
- 空 span 调用判断支持性
- 返回布尔值表示是否应用
- 某些字体不支持字距(如位图字体)

**边界框计算策略**
- 使用大尺寸(2048pt)提高精度
- 缩放回 1pt 单位
- 基于字体度量而非遍历所有字形

## 性能考量

### 优化策略

1. **延迟计算**: 边界框仅在需要时计算
2. **缓存**: 通过 `SkTypefaceCache` 避免重复创建
3. **弱引用**: 允许未使用字体被回收
4. **流优化**: `openExistingStream()` 避免重建流

### 性能特性

**字符到字形转换**:
```cpp
SkGlyphID SkTypeface::unicharToGlyph(SkUnichar uni) const {
    SkGlyphID glyphs[1] = { 0 };
    this->onCharsToGlyphs({&uni, 1}, glyphs);
    return glyphs[0];
}
```
- 单字符转换也通过批量接口
- 后端可优化批量处理

**表数据访问**:
- `getTableSize()` 避免分配内存
- `copyTableData()` 返回不可变数据
- 支持部分读取

### 内存管理

- 字体数据通常内存映射,不占用堆内存
- 序列化可选包含数据,控制内存使用
- 字形缓存与字体生命周期分离

## 相关文件

| 文件路径 | 关系说明 |
|---------|---------|
| `include/core/SkFont.h` | 现代文本 API |
| `include/core/SkFontMgr.h` | 字体管理器 |
| `include/core/SkFontStyle.h` | 字体样式 |
| `include/core/SkFontArguments.h` | 变体字体参数 |
| `src/core/SkScalerContext.h` | 字形生成上下文 |
| `src/core/SkTypefaceCache.h` | 字体缓存 |
| `src/core/SkFontDescriptor.h` | 序列化描述符 |
| `src/ports/SkTypeface_FreeType.h` | FreeType 实现 |
| `src/ports/SkTypeface_mac_ct.h` | CoreText 实现 |
| `src/ports/SkTypeface_win_dw.h` | DirectWrite 实现 |
