# src/pdf - Skia PDF 文档生成后端

## 概述

`src/pdf` 目录是 Skia 图形库中完整的 PDF 文档生成后端实现。该模块将 Skia 的通用 2D 绘图操作（如路径绘制、文本渲染、图像合成等）转换为符合 PDF 规范的输出流，生成标准的 PDF 文件。整个模块包含约 47 个源文件（`.cpp` 和 `.h`），总计超过 40,000 行代码，是 Skia 中最复杂的文档输出后端之一。

该模块的核心设计思想是通过 `SkPDFDevice`（PDF 绘图设备）拦截 Skia Canvas 的所有绘图指令，将它们转换为 PDF 页面内容流（Content Stream）。`SkPDFDocument` 作为顶层协调者，管理整个 PDF 文件的结构，包括页面对象、交叉引用表、资源字典和字体子集化等。所有 PDF 对象通过 `SkPDFIndirectReference`（间接引用）进行统一编号和去重，确保输出的 PDF 文件尽可能紧凑。

该模块支持丰富的 PDF 功能特性，包括但不限于：Type1/TrueType/CFF/CID 等多种字体格式的嵌入与子集化、线性渐变和径向渐变着色器、图像 XObject（支持 JPEG 和 Deflate 压缩）、图形状态字典、透明度与混合模式、Form XObject、结构化标签（Tagged PDF / PDF/A-2b 合规性）、文档元数据与 XMP、命名目标与超链接注释等。

在性能方面，该模块支持通过 `SkExecutor` 进行多线程压缩处理，并通过广泛的对象规范化（canonicalization）机制来去重字体、图像、着色器和图形状态资源，最大限度减少输出 PDF 的文件大小和内存占用。

## 架构图

```
+------------------------------------------------------------------+
|                        用户 API 层                                |
|  SkPDF::MakeDocument()  ->  SkDocument (include/core)            |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
|                     SkPDFDocument (文档管理)                       |
|  - 页面生命周期管理 (onBeginPage/onEndPage/onClose)                |
|  - 对象编号分配 (reserveRef / emit)                               |
|  - 资源规范化缓存 (字体/图像/着色器/图形状态)                       |
|  - 交叉引用表 (SkPDFOffsetMap)                                    |
|  - 结构化标签 (SkPDFStructTree)                                   |
|  - 元数据 (SkPDFMetadata + SkUUID)                                |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
|                     SkPDFDevice (页面绘图设备)                     |
|  - 继承自 SkClipStackDevice                                      |
|  - 绘图操作转换: drawRect/drawPath/drawImageRect/drawGlyphRun    |
|  - 内容流生成 (fContent: SkDynamicMemoryWStream)                  |
|  - 图形栈状态管理 (SkPDFGraphicStackState)                        |
|  - 标记内容管理 (MarkedContentManager)                            |
|  - 资源字典生成 (makeResourceDict)                                |
+------------------------------------------------------------------+
          |              |               |              |
          v              v               v              v
+-------------+ +---------------+ +-------------+ +------------------+
| 字体子系统   | | 图像子系统     | | 着色器子系统 | | 图形状态子系统    |
| SkPDFFont   | | SkPDFBitmap   | | SkPDFShader | | SkPDFGraphicState|
| SkPDFStrike | | SkKeyedImage  | | SkPDFGrad.. | | SkPDFGraphicStack|
| SkPDFGlyph  | | SkBitmapKey   | | ShaderKey   | | State            |
| SkPDFType1  | | SkPDFIccProf  | |             | |                  |
| SkPDFSubset | |               | |             | |                  |
+-------------+ +---------------+ +-------------+ +------------------+
          |              |               |              |
          v              v               v              v
+------------------------------------------------------------------+
|                    PDF 基础类型层                                  |
|  SkPDFObject / SkPDFArray / SkPDFDict / SkPDFUnion               |
|  SkPDFIndirectReference / SkPDFStreamOut                          |
|  SkPDFResourceDict / SkPDFFormXObject                            |
+------------------------------------------------------------------+
                               |
                               v
+------------------------------------------------------------------+
|                    输出与压缩层                                    |
|  SkDeflateWStream (zlib Deflate 压缩)                             |
|  SkWStream (输出流)                                               |
+------------------------------------------------------------------+
```

## 目录结构

```
src/pdf/
|
|-- BUILD.bazel                        # Bazel 构建配置，定义 pdf 库及其依赖
|
|-- [文档与页面管理]
|   |-- SkPDFDocument.cpp              # SkPDFDocument 实现：页面生命周期、对象序列化、文件结构输出
|   |-- SkPDFDocumentPriv.h            # SkPDFDocument 私有头文件：类定义、规范化缓存声明
|   |-- SkPDFDevice.cpp                # SkPDFDevice 实现：所有绘图操作到 PDF 内容流的转换 (77K)
|   |-- SkPDFDevice.h                  # SkPDFDevice 声明：继承 SkClipStackDevice
|   |-- SkDocument_PDF_None.cpp        # 无 PDF 支持时的空实现存根
|
|-- [PDF 基础类型]
|   |-- SkPDFTypes.cpp / .h            # PDF 核心对象类型：SkPDFObject、SkPDFArray、SkPDFDict
|   |-- SkPDFUnion.h                   # SkPDFUnion：非虚拟化 PDF 原语 (Int/Bool/Scalar/Name/String)
|   |-- SkPDFUtils.cpp / .h            # PDF 工具函数：路径输出、颜色转换、矩阵序列化
|   |-- SkPDFResourceDict.cpp / .h     # PDF 资源字典创建：ExtGState/Pattern/XObject/Font
|   |-- SkPDFFormXObject.cpp / .h      # Form XObject 创建：自包含图形对象
|
|-- [字体子系统]
|   |-- SkPDFFont.cpp / .h             # 字体管理：SkPDFFont 和 SkPDFStrike 类，字体类型判断和编码
|   |-- SkPDFType1Font.cpp / .h        # Type1 字体发射：PostScript Type1 字体嵌入
|   |-- SkPDFSubsetFont.cpp / .h       # 字体子集化：使用 HarfBuzz 进行字体裁剪
|   |-- SkPDFGlyphUse.h                # 字形使用位图：跟踪每个字体使用了哪些字形
|   |-- SkPDFMakeCIDGlyphWidthsArray.cpp / .h  # CID 字形宽度数组：PDF W 数组生成
|   |-- SkPDFMakeToUnicodeCmap.cpp / .h # ToUnicode CMap：字形到 Unicode 的映射表
|   |-- SkClusterator.cpp / .h         # 字形簇迭代器：处理 HarfBuzz 的 m-to-n 字形-字符映射
|
|-- [图像子系统]
|   |-- SkPDFBitmap.cpp / .h           # 图像序列化：SkImage 到 Image XObject 的转换
|   |-- SkKeyedImage.cpp / .h          # 带键图像：结合 SkImage 和 SkBitmapKey 的去重包装
|   |-- SkBitmapKey.h                  # 位图键：用于图像去重的 {子集矩形, ID} 结构
|
|-- [着色器子系统]
|   |-- SkPDFShader.cpp / .h           # 图像着色器：SkShader 到 PDF Pattern 的转换
|   |-- SkPDFGradientShader.cpp / .h   # 渐变着色器：线性/径向/锥形/扫描渐变到 PDF 着色函数
|
|-- [图形状态]
|   |-- SkPDFGraphicState.cpp / .h     # 图形状态字典：SkPaint 到 ExtGState 的转换（规范化）
|   |-- SkPDFGraphicStackState.cpp / .h # 图形栈状态：跟踪 CTM、裁剪、颜色等绘图状态变化
|
|-- [结构化标签与元数据]
|   |-- SkPDFTag.cpp / .h              # 结构树：Tagged PDF 支持 (StructTreeRoot, StructElem, MCID)
|   |-- SkPDFMetadata.cpp / .h         # 文档元数据：Info 字典、XMP、UUID
|   |-- SkUUID.h                       # UUID 结构体：128 位唯一标识符
|
|-- [压缩]
|   |-- SkDeflate.cpp / .h             # Deflate 压缩流：基于 zlib 的 PDF 流压缩
```

## 关键类与函数

### SkPDFDocument (`SkPDFDocumentPriv.h` / `SkPDFDocument.cpp`)

`SkPDFDocument` 是整个 PDF 后端的顶层管理类，继承自 `SkDocument`。它是 PDF 文件生命周期的唯一所有者。

```cpp
class SkPDFDocument : public SkDocument {
public:
    SkPDFDocument(SkWStream*, SkPDF::Metadata);

    // 页面生命周期
    SkCanvas* onBeginPage(SkScalar width, SkScalar height) override;
    void onEndPage() override;
    void onClose(SkWStream*) override;

    // 对象序列化：将 PDF 对象写入输出流并记录偏移量
    SkPDFIndirectReference emit(const SkPDFObject&, SkPDFIndirectReference);
    SkPDFIndirectReference emit(const SkPDFObject& o);

    // 流式对象输出
    template <typename T>
    void emitStream(const SkPDFDict& dict, T writeStream, SkPDFIndirectReference ref);

    // 对象编号预留（用于前向引用）
    SkPDFIndirectReference reserveRef();

    // 字体子集标签生成
    SkString nextFontSubsetTag();
};
```

关键的规范化缓存（用于对象去重）：
- `fImageShaderMap` - 图像着色器去重
- `fGradientPatternMap` - 渐变着色器去重
- `fPDFBitmapMap` - 位图图像去重
- `fICCProfileMap` - ICC 颜色配置文件去重
- `fTypefaceMetrics` - 字体度量缓存
- `fStrikes` - 字体 Strike 缓存（按 SkDescriptor 键控）
- `fStrokeGSMap` / `fFillGSMap` - 描边/填充图形状态去重

### SkPDFDevice (`SkPDFDevice.h` / `SkPDFDevice.cpp`)

`SkPDFDevice` 是 PDF 页面的绘图设备，继承自 `SkClipStackDevice`。每个 PDF 页面对应一个 `SkPDFDevice` 实例。这是最大的单一文件（77KB），负责将所有 Skia 绘图操作转换为 PDF 内容流。

```cpp
class SkPDFDevice final : public SkClipStackDevice {
public:
    SkPDFDevice(SkISize pageSize, SkPDFDocument* document,
                const SkMatrix& initialTransform = SkMatrix::I());

    // 核心绘图操作
    void drawPaint(const SkPaint& paint) override;
    void drawRect(const SkRect& r, const SkPaint& paint) override;
    void drawPath(const SkPath& origpath, const SkPaint& paint) override;
    void drawImageRect(const SkImage*, const SkRect* src, const SkRect& dst,
                       const SkSamplingOptions&, const SkPaint&,
                       SkCanvas::SrcRectConstraint) override;

    // 页面内容输出
    std::unique_ptr<SkPDFDict> makeResourceDict();
    std::unique_ptr<SkStreamAsset> content();

private:
    // 资源引用集合（跟踪本页使用了哪些资源）
    skia_private::THashSet<SkPDFIndirectReference> fGraphicStateResources;
    skia_private::THashSet<SkPDFIndirectReference> fXObjectResources;
    skia_private::THashSet<SkPDFIndirectReference> fShaderResources;
    skia_private::THashSet<SkPDFIndirectReference> fFontResources;

    // 内容流
    SkDynamicMemoryWStream fContent;
    SkPDFGraphicStackState fActiveStackState;

    // 标记内容管理器（Tagged PDF）
    MarkedContentManager fMarkManager;
};
```

### SkPDFFont 与 SkPDFStrike (`SkPDFFont.h`)

字体子系统采用两级结构。`SkPDFStrike` 对应一个特定的 `SkFont + SkPaint` 组合（即一种渲染配置），而 `SkPDFFont` 则代表 PDF 文件中的一个字体资源对象。一个 Strike 可能包含多个 Font 对象（当字形 ID 超过 255 时，Type1 字体需要分片）。

```cpp
class SkPDFStrike : public SkRefCnt {
public:
    // 规范化创建，由 SkPDFDocument 所有
    static sk_sp<SkPDFStrike> Make(SkPDFDocument* doc, const SkFont&, const SkPaint&);

    // 获取字形对应的 PDF 字体资源
    SkPDFFont* getFontResource(const SkGlyph* glyph);
};

class SkPDFFont {
public:
    // 支持的字体类型：Type1, Type1CID, TrueType, CFF, Type3(位图字体)
    SkAdvancedTypefaceMetrics::FontType getType() const;

    // 多字节字形（TrueType/CFF/CID 字体支持超过 255 个字形）
    bool multiByteGlyphs() const;

    // 字形编码转换
    SkGlyphID glyphToPDFFontEncoding(SkGlyphID gid) const;

    // 发射字体子集到 PDF
    void emitSubset(SkPDFDocument*) const;

    // 检查字体是否允许嵌入
    static bool CanEmbedTypeface(const SkTypeface&, SkPDFDocument*);
};
```

### SkPDFObject / SkPDFArray / SkPDFDict (`SkPDFTypes.h`)

这些是 PDF 对象模型的核心基础类型，直接映射到 PDF 规范中的对象类型。

```cpp
// PDF 对象基类
class SkPDFObject {
public:
    virtual void emitObject(SkWStream* stream) const = 0;
};

// PDF 数组（最大长度 8191）
class SkPDFArray : public SkPDFObject {
    void appendInt(int32_t);
    void appendScalar(SkScalar);
    void appendName(const char[]);
    void appendRef(SkPDFIndirectReference);
    // ...
};

// PDF 字典
class SkPDFDict final : public SkPDFObject {
    void insertInt(const char key[], int32_t value);
    void insertName(const char key[], const char nameValue[]);
    void insertRef(const char key[], SkPDFIndirectReference);
    // ...
};
```

### SkPDFUnion (`SkPDFUnion.h`)

`SkPDFUnion` 是非虚拟化的 PDF 原语值类型实现，使用 C++ `union` 来高效存储 Int、Bool、Scalar、Name、String、Object 和 Ref 等多种值。它避免了为每个简单值都创建堆对象的开销。

```cpp
class SkPDFUnion {
public:
    static SkPDFUnion Int(int32_t);
    static SkPDFUnion Bool(bool);
    static SkPDFUnion Scalar(SkScalar);
    static SkPDFUnion Name(const char*);    // 不复制，适用于静态字符串
    static SkPDFUnion Name(SkString);       // 复制并转义
    static SkPDFUnion ByteString(const char*);
    static SkPDFUnion TextString(const char*);
    static SkPDFUnion Object(std::unique_ptr<SkPDFObject>);
    static SkPDFUnion Ref(SkPDFIndirectReference);

    void emitObject(SkWStream*) const;
};
```

### SkPDFIndirectReference (`SkPDFTypes.h`)

PDF 间接引用是整个对象系统的纽带。每个 PDF 对象都可以通过其编号被其他对象引用。

```cpp
struct SkPDFIndirectReference {
    int fValue = -1;
    explicit operator bool() const { return fValue >= 0; }
};
```

### SkPDFStructTree (`SkPDFTag.h`)

结构树用于支持 Tagged PDF（可访问性 PDF）。它维护了一个从元素 ID 到 `SkPDFStructElem` 的映射，支持标记内容序列（Marked-Content Sequence）和父树（Parent Tree）。

```cpp
class SkPDFStructTree {
public:
    class Mark {
        int mcid() const;        // 标记内容标识符
        int elemId() const;      // 元素标识符
        SkString structType() const;  // 结构类型
        void accumulate(SkPoint);     // 累积位置信息
    };

    // 为结构元素创建标记
    Mark createMarkForElemId(int elemId, unsigned pageIndex,
                             SkPDFParentTreeKey& structParentsKey);

    // 发射结构树根节点
    SkPDFIndirectReference emitStructTreeRoot(SkPDFDocument* doc) const;

    // 生成大纲（书签）
    SkPDFIndirectReference makeOutline(SkPDFDocument* doc) const;
};
```

### SkPDFGraphicStackState (`SkPDFGraphicStackState.h`)

图形栈状态跟踪器管理 PDF 内容流中的 `q`/`Q`（保存/恢复）操作，跟踪当前变换矩阵、裁剪区域、颜色和着色器索引等状态。

```cpp
struct SkPDFGraphicStackState {
    struct Entry {
        SkMatrix fMatrix;
        uint32_t fClipStackGenID;
        SkColor4f fColor;
        SkScalar fTextScaleX;
        int fShaderIndex;
        int fGraphicStateIndex;
    };
    static constexpr int kMaxStackDepth = 2;

    void updateClip(const SkClipStack* clipStack, const SkIRect& bounds);
    void updateMatrix(const SkMatrix& matrix);
    void updateDrawingState(const Entry& state);
    void push();
    void pop();
    void drainStack();
};
```

### SkDeflateWStream (`SkDeflate.h`)

Deflate 压缩流包装器，基于 zlib 实现 PDF 流的压缩功能。

```cpp
class SkDeflateWStream final : public SkWStream {
public:
    // compressionLevel: 1=最快, 9=最高压缩, -1=默认
    SkDeflateWStream(SkWStream*, int compressionLevel, bool gzip = false);
    void finalize();  // 写入压缩流结尾标记
    bool write(const void*, size_t) override;
};
```

## 依赖关系

### 外部依赖

| 依赖库 | 用途 | 说明 |
|--------|------|------|
| **zlib** | Deflate 流压缩 | PDF 流数据压缩（`/FlateDecode` 过滤器） |
| **HarfBuzz** | 字体子集化 | 通过 `SK_PDF_USE_HARFBUZZ_SUBSET` 宏启用 |
| **skcms** | 颜色管理 | ICC 配置文件处理 |

### 内部依赖（Skia 模块）

| 模块 | 用途 |
|------|------|
| `//:core` | Skia 核心类型（SkCanvas, SkPaint, SkPath, SkImage 等） |
| `//src/core:core_priv` | 核心私有 API（SkClipStack, SkGlyph, SkAdvancedTypefaceMetrics 等） |
| `//:pathops` | 路径运算（用于裁剪路径的布尔操作） |
| `//src/codec:codec_support_priv` | 图像编解码支持 |
| `//src/encode:icc_support` | ICC 配置文件编码 |
| `//src/utils:clip_stack_utils` | 裁剪栈工具 |
| `//src/utils:float_to_decimal` | 浮点数到十进制字符串的精确转换 |

### 模块内部依赖关系

```
SkPDFDocument
    |-- SkPDFDevice (拥有页面设备)
    |   |-- SkPDFGraphicStackState (管理图形状态栈)
    |   |-- SkPDFTag::MarkedContentManager (管理标记内容)
    |   |-- SkPDFResourceDict (生成资源字典)
    |   |-- SkPDFFormXObject (创建 Form XObject)
    |   |-- SkPDFBitmap (序列化图像)
    |   |-- SkPDFShader + SkPDFGradientShader (着色器转换)
    |   |-- SkPDFGraphicState (图形状态字典)
    |   |-- SkPDFFont (字体资源获取)
    |   +-- SkClusterator (文本簇处理)
    |
    |-- SkPDFStructTree (结构化标签树)
    |-- SkPDFMetadata (元数据生成)
    |-- SkPDFOffsetMap (交叉引用表)
    |
    |-- 规范化缓存:
    |   |-- SkPDFStrike -> SkPDFFont (字体去重)
    |   |-- SkBitmapKey -> SkPDFBitmap (图像去重)
    |   |-- SkPDFImageShaderKey -> SkPDFShader (图像着色器去重)
    |   |-- SkPDFGradientShader::Key (渐变着色器去重)
    |   |-- SkPDFStrokeGraphicState / SkPDFFillGraphicState (图形状态去重)
    |   +-- SkPDFIccProfileKey (ICC 配置文件去重)
    |
    +-- SkPDFTypes (SkPDFObject / SkPDFArray / SkPDFDict / SkPDFUnion)
        +-- SkDeflateWStream (压缩输出)
```

## 设计模式分析

### 1. 享元模式（Flyweight Pattern）

整个 PDF 后端的核心优化策略是对象规范化（canonicalization），即享元模式的体现。`SkPDFDocument` 维护了多个哈希表缓存，确保相同的 PDF 资源（字体、图像、着色器、图形状态）在文件中只出现一次：

```cpp
// SkPDFDocumentPriv.h 中的规范化缓存
skia_private::THashMap<SkBitmapKey, SkPDFIndirectReference> fPDFBitmapMap;
skia_private::THashMap<SkPDFStrokeGraphicState, SkPDFIndirectReference, ...> fStrokeGSMap;
skia_private::THashMap<SkPDFFillGraphicState, SkPDFIndirectReference, ...> fFillGSMap;
```

每个资源类型都定义了自己的键类型和哈希函数（如 `SkBitmapKey`、`SkPDFImageShaderKey`、`SkPDFGradientShader::Key`），使用 `SkForceDirectHash` 或自定义哈希实现高效查找。

### 2. 访问者模式（Visitor Pattern）的变体

`SkPDFDevice` 作为 `SkClipStackDevice` 的子类，实现了所有虚拟绘图方法。SkCanvas 的绘图操作通过虚函数分发到 `SkPDFDevice`，后者将其转换为 PDF 操作符并写入内容流：

```cpp
void drawRect(const SkRect& r, const SkPaint& paint) override;
void drawPath(const SkPath& origpath, const SkPaint& paint) override;
void drawImageRect(...) override;
void onDrawGlyphRunList(...) override;
```

### 3. 策略模式（Strategy Pattern）

字体处理根据字体类型采用不同的策略：
- `SkAdvancedTypefaceMetrics::kType1_Font` -> `SkPDFEmitType1Font()`
- `SkAdvancedTypefaceMetrics::kTrueType_Font` -> CID 字体 + TrueType 嵌入
- `SkAdvancedTypefaceMetrics::kCFF_Font` -> CID 字体 + CFF 嵌入
- Type3 字体 -> 位图字形路径

着色器处理也类似：
- 图像着色器 -> `SkPDFMakeShader()` -> 平铺图案
- 渐变着色器 -> `SkPDFGradientShader::Make()` -> PDF 着色函数

### 4. 组合模式（Composite Pattern）

PDF 对象模型使用组合模式：`SkPDFArray` 和 `SkPDFDict` 都继承自 `SkPDFObject`，而它们的内部又可以包含其他 `SkPDFObject`（通过 `SkPDFUnion`）。这允许构建任意嵌套的 PDF 对象图。

### 5. 工厂方法模式（Factory Method）

文档通过 `SkPDF::MakeDocument()` 工厂函数创建。各种 PDF 资源也通过工厂函数创建，如：
- `SkPDFMakeResourceDict()` - 资源字典
- `SkPDFMakeFormXObject()` - Form XObject
- `SkPDFMakeToUnicodeCmap()` - ToUnicode CMap
- `SkPDFMakeCIDGlyphWidthsArray()` - CID 字形宽度数组

### 6. 标记联合体模式（Tagged Union）

`SkPDFUnion` 使用 C++ 原生 `union` 加枚举标记实现轻量级多态，避免了虚函数开销：

```cpp
class SkPDFUnion {
    union {
        int32_t fIntValue;
        bool fBoolValue;
        SkScalar fScalarValue;
        const char* fStaticString;
        SkString fSkString;
        PDFObject fObject;
    };
    enum class Type : char {
        kInt, kBool, kScalar, kName, kByteString, ...
    };
    Type fType;
};
```

### 7. 内部迭代器模式（Internal Iterator）

`SkClusterator` 实现了对 HarfBuzz 字形簇的内部迭代，将复杂的 m-to-n 字形-字符映射关系封装为简单的 `next()` 调用：

```cpp
class SkClusterator {
public:
    struct Cluster {
        const char* fUtf8Text;
        uint32_t fTextByteLength;
        uint32_t fGlyphIndex;
        uint32_t fGlyphCount;
    };
    Cluster next();
};
```

## 数据流

### 1. PDF 文档创建流程

```
用户代码:
  sk_sp<SkDocument> doc = SkPDF::MakeDocument(stream, metadata);
      |
      v
  SkPDFDocument 构造:
    - 创建 SkPDFStructTree (如果 metadata 包含结构元素树)
    - 生成 UUID (SkPDFMetadata::CreateUUID)
    - 写入 PDF 文件头 "%PDF-1.4"
    - 标记文档起始偏移 (fOffsetMap.markStartOfDocument)
```

### 2. 页面绘制流程

```
用户代码:
  SkCanvas* canvas = doc->beginPage(width, height);
      |
      v
  SkPDFDocument::onBeginPage():
    - 创建 SkPDFDevice (pageSize, initialTransform)
    - 将 fCanvas 绑定到 SkPDFDevice
    - 预留页面间接引用 (reserveRef)
      |
      v
  用户在 canvas 上绘图: canvas->drawRect(), drawText(), drawImage()...
      |
      v
  SkPDFDevice 拦截绘图调用:
    1. setUpContentEntry()
       - 检查裁剪是否为空
       - 处理混合模式
       - 如果需要透明度组合，创建临时设备
    2. 转换为 PDF 操作:
       - updateMatrix() -> "cm" 操作符
       - updateClip() -> "re W n" 裁剪操作
       - 写入绘图操作 (如 "re f" 画矩形, "m l S" 画线)
    3. finishContentEntry()
       - 处理混合模式后续步骤
      |
      v
  doc->endPage():
    - 调用 device->content() 获取内容流
    - 调用 device->makeResourceDict() 获取资源字典
    - 构建页面字典 {/Type /Page, /MediaBox, /Contents, /Resources}
    - emit() 序列化页面到输出流
```

### 3. 字体处理流程

```
SkPDFDevice::onDrawGlyphRunList()
    |
    v
internalDrawGlyphRun():
    |
    v
SkPDFStrike::Make(doc, font, paint)  // 规范化查找或创建
    |
    v
strike->getFontResource(glyph)  // 获取字形对应的字体资源
    |                              (Type1 字体可能按 255 字形分片)
    v
font->noteGlyphUsage(glyphID)   // 记录字形使用情况
    |
    v
[在 endPage/close 时]
font->emitSubset(doc):
    1. SkPDFSubsetFont() - 使用 HarfBuzz 子集化字体数据
    2. SkPDFMakeToUnicodeCmap() - 生成 ToUnicode 映射
    3. SkPDFMakeCIDGlyphWidthsArray() - 生成宽度数组
    4. 构建 Font 字典和 FontDescriptor
    5. doc->emit() 写入输出
```

### 4. 图像处理流程

```
SkPDFDevice::drawImageRect()
    |
    v
internalDrawImageRect():
    |
    v
SkKeyedImage(image) -> SkBitmapKey  // 提取去重键
    |
    v
doc->fPDFBitmapMap 查找           // 检查是否已序列化
    |                              (命中则直接使用已有引用)
    v [未命中]
SkPDFSerializeImage(img, doc, quality):
    1. 尝试 JPEG 编码 (如果 quality <= 100 且图像不透明)
    2. 否则使用 Deflate 压缩 (SkDeflateWStream)
    3. 处理 alpha 通道 (SMask)
    4. 附加 ICC 颜色配置文件 (如果有)
    5. 构建 Image XObject 字典 {/Type /XObject, /Subtype /Image, ...}
    6. doc->emit() 写入输出
```

### 5. PDF 文件关闭流程

```
doc->close()
    |
    v
SkPDFDocument::onClose():
    1. 等待所有并行任务完成 (waitForJobs)
    2. 发射所有延迟的字体子集 (emitSubset)
    3. 构建页面树 (Pages 字典)
    4. 构建命名目标列表
    5. 构建结构树 (如果是 Tagged PDF)
    6. 构建大纲 (如果配置了)
    7. 生成 XMP 元数据 (如果 fPDFA)
    8. 生成文档信息字典 (Info)
    9. 构建 Catalog 字典 {/Type /Catalog, /Pages, /MarkInfo, ...}
   10. 写入交叉引用表 (fOffsetMap.emitCrossReferenceTable)
   11. 写入文件尾部 (trailer + startxref + %%EOF)
```

## 相关文档与参考

### PDF 规范
- **PDF 32000-1:2008** - ISO 标准 PDF 1.7 规范，定义了所有 PDF 对象类型、内容流操作符和文件结构
- **PDF/A-2b (ISO 19005-2)** - PDF 长期存档格式标准，该模块通过 `fPDFA` 选项支持

### 公共 API 头文件
- `include/docs/SkPDFDocument.h` - 用户面向的 PDF API，包括 `SkPDF::Metadata`、`SkPDF::MakeDocument()`、`SkPDF::SetNodeId()` 等
- `include/core/SkDocument.h` - `SkDocument` 基类，定义 `beginPage()`/`endPage()`/`close()` 接口
- `include/core/SkCanvas.h` - Skia 画布 API，所有绘图操作的入口

### Skia 内部依赖
- `src/core/SkClipStackDevice.h` - `SkPDFDevice` 的基类，提供裁剪栈管理
- `src/core/SkAdvancedTypefaceMetrics.h` - 字体类型元数据，用于判断字体格式
- `src/core/SkStrikeSpec.h` - 字形光栅化规格
- `src/utils/SkFloatToDecimal.h` - 精确的浮点数转字符串（PDF 对数字精度有要求）

### 构建配置
- `src/pdf/BUILD.bazel` - Bazel 构建规则，定义了 `pdf` 目标及其所有源文件和依赖关系
- 关键构建宏：`SK_PDF_USE_HARFBUZZ_SUBSET`（启用 HarfBuzz 字体子集化）
- 关键运行时宏：`SK_PDF_MASK_QUALITY`（控制遮罩 JPEG 编码质量，默认 50）

### 使用示例

```cpp
#include "include/docs/SkPDFDocument.h"
#include "include/core/SkCanvas.h"
#include "include/core/SkStream.h"

void createPDF() {
    SkFILEWStream fileStream("output.pdf");

    SkPDF::Metadata metadata;
    metadata.fTitle = "示例文档";
    metadata.fAuthor = "Skia";
    metadata.fCompressionLevel = SkPDF::Metadata::CompressionLevel::Default;
    metadata.fEncodingQuality = 85;  // JPEG 质量

    auto doc = SkPDF::MakeDocument(&fileStream, metadata);

    // 第一页
    SkCanvas* canvas = doc->beginPage(612, 792);  // Letter 尺寸 (8.5 x 11 英寸)
    SkPaint paint;
    paint.setColor(SK_ColorBLACK);
    canvas->drawString("Hello PDF!", 72, 72, SkFont(), paint);
    doc->endPage();

    // 关闭文档，写入文件尾部
    doc->close();
}
```
