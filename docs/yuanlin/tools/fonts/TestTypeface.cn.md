# TestTypeface

> 源文件: tools/fonts/TestTypeface.h, tools/fonts/TestTypeface.cpp

## 概述

`TestTypeface` 是 Skia 提供的测试专用字体实现,用于在单元测试和自动化测试中提供可预测、跨平台一致的字体渲染结果。该类实现了完整的 `SkTypeface` 接口,但使用预定义的字形路径数据而非真实的字体文件,确保测试结果不受系统字体差异的影响。

该实现包含三个预定义的字体家族(monospace、sans-serif、serif),每个家族包含四种样式(Normal、Bold、Italic、BoldItalic),支持 ASCII 可打印字符范围(0x20-0x7E)。所有字形数据在编译时生成并硬编码在源文件中,使测试环境完全可复现。

## 架构位置

该类位于 Skia 工具层的字体测试支持模块:

```
skia/
  tools/
    fonts/
      TestTypeface.h               # 类声明
      TestTypeface.cpp             # 类实现
      test_font_monospace.inc      # 预生成的 monospace 字体数据
      test_font_sans_serif.inc     # 预生成的 sans-serif 字体数据
      test_font_serif.inc          # 预生成的 serif 字体数据
      test_font_index.inc          # 字体索引和元数据
      create_test_font.cpp         # 字体数据生成工具
```

在架构层次中:
- **上层**: 测试代码、TestFontMgr
- **本层**: TestTypeface(字体实现)
- **下层**: SkTypeface(抽象基类)、SkScalerContext(字形缩放)

## 主要类与结构体

### SkTestFontData

```cpp
struct SkTestFontData {
    const SkScalar* fPoints;              // 字形路径点坐标数组
    const unsigned char* fVerbs;          // 路径动词数组
    const SkUnichar* fCharCodes;          // 字符编码数组
    const size_t fCharCodesCount;         // 字符数量
    const SkFixed* fWidths;               // 字形宽度数组(定点数)
    const SkFontMetrics& fMetrics;        // 字体度量信息
    const char* fName;                    // 字体名称
    SkFontStyle fStyle;                   // 字体样式
};
```

存储单个字体的所有静态数据,所有指针指向编译期常量数组。

### SkTestFont

```cpp
class SkTestFont : public SkRefCnt {
public:
    SkTestFont(const SkTestFontData& data);
    ~SkTestFont() override;

    SkGlyphID glyphForUnichar(SkUnichar charCode) const;
    void init(const SkScalar* pts, const unsigned char* verbs);

private:
    const SkUnichar* fCharCodes;          // 字符编码表
    const size_t fCharCodesCount;         // 字符数量
    const SkFixed* fWidths;               // 字形宽度
    const SkFontMetrics& fMetrics;        // 度量信息
    const char* fName;                    // 字体名称
    SkPath* fPaths;                       // 字形路径数组(动态构建)
};
```

封装单个测试字体的数据和方法,从静态数据构建字形路径。

### TestTypeface

```cpp
class TestTypeface : public SkTypeface {
public:
    struct List {
        struct Family {
            struct Face {
                sk_sp<SkTypeface> typeface;
                const char* name;
                bool isDefault;
            };
            std::vector<Face> faces;
            const char* name;
        };
        std::vector<Family> families;
    };

    static const List& Typefaces();  // 获取所有测试字体
    SkVector getAdvance(SkGlyphID) const;
    void getFontMetrics(SkFontMetrics* metrics);
    SkPath getPath(SkGlyphID glyph);

    struct Register { Register(); };  // 自动注册

protected:
    // SkTypeface 接口实现
    std::unique_ptr<SkScalerContext> onCreateScalerContext(
        const SkScalerContextEffects&, const SkDescriptor*) const override;
    void onFilterRec(SkScalerContextRec* rec) const override;
    void onCharsToGlyphs(SkSpan<const SkUnichar>, SkSpan<SkGlyphID>) const override;
    int onCountGlyphs() const override;
    int onGetUPEM() const override { return 2048; }
    // ... 其他虚函数实现

private:
    static constexpr SkTypeface::FactoryId FactoryId = SkSetFourByteTag('t','e','s','t');
    static sk_sp<SkTypeface> MakeFromStream(std::unique_ptr<SkStreamAsset>,
                                           const SkFontArguments&);
    TestTypeface(sk_sp<SkTestFont>, const SkFontStyle& style);

    sk_sp<SkTestFont> fTestFont;
};
```

### SkTestScalerContext

```cpp
class SkTestScalerContext : public SkScalerContext {
public:
    SkTestScalerContext(TestTypeface& face,
                        const SkScalerContextEffects& effects,
                        const SkDescriptor* desc);

protected:
    GlyphMetrics generateMetrics(const SkGlyph&, SkArenaAlloc*) override;
    void generateImage(const SkGlyph&, void* imageBuffer) override;
    std::optional<GeneratedPath> generatePath(const SkGlyph&) override;
    void generateFontMetrics(SkFontMetrics*) override;

private:
    const SkMatrix fMatrix;  // 字形变换矩阵
};
```

为 TestTypeface 提供字形缩放和光栅化支持。

## 公共 API 函数

### Typefaces()

```cpp
static const List& Typefaces();
```

返回所有可用测试字体的列表:
```cpp
const TestTypeface::List& list = TestTypeface::Typefaces();
for (const auto& family : list.families) {
    printf("Family: %s\n", family.name);
    for (const auto& face : family.faces) {
        printf("  Face: %s (default: %d)\n", face.name, face.isDefault);
    }
}
```

输出:
```
Family: monospace
  Face: Normal (default: 0)
  Face: Bold (default: 0)
  Face: Italic (default: 0)
  Face: Bold Italic (default: 0)
Family: sans-serif
  Face: Normal (default: 1)  // 默认字体
  ...
Family: serif
  ...
```

### getAdvance()

```cpp
SkVector getAdvance(SkGlyphID glyphID) const;
```

获取字形的前进宽度:
- 输入: 字形 ID
- 返回: 二维向量,x 分量为宽度,y 为 0
- 使用预定义的定点宽度数据

### getFontMetrics()

```cpp
void getFontMetrics(SkFontMetrics* metrics);
```

获取字体度量信息,包括:
- `fTop`, `fAscent`, `fDescent`, `fBottom`: 基线相关度量
- `fLeading`: 行间距
- `fAvgCharWidth`, `fMaxCharWidth`: 字符宽度统计
- `fXHeight`, `fCapHeight`: 大小写高度
- `fUnderlineThickness`, `fUnderlinePosition`: 下划线
- `fStrikeoutThickness`, `fStrikeoutPosition`: 删除线

### getPath()

```cpp
SkPath getPath(SkGlyphID glyph);
```

获取字形的路径表示:
- 返回预定义的 SkPath 对象
- 路径数据在初始化时从静态数组构建
- 超出范围的字形 ID 返回索引 0 的路径

## 内部实现细节

### 字体数据结构

预生成的字体数据包含:

```cpp
// 示例: LiberationSansNormal
const SkScalar LiberationSansNormalPoints[] = {
    0.5f, 0.8f,  // 点坐标对
    1.2f, 0.3f,
    // ... 数千个点
};

const unsigned char LiberationSansNormalVerbs[] = {
    SkPath::kMove_Verb,   // 移动到新位置
    SkPath::kLine_Verb,   // 直线
    SkPath::kQuad_Verb,   // 二次贝塞尔
    SkPath::kCubic_Verb,  // 三次贝塞尔
    SkPath::kClose_Verb,  // 闭合路径
    SkPath::kDone_Verb,   // 字形结束
    // ... 每个字形一个序列
};

const SkUnichar LiberationSansNormalCharCodes[] = {
    0x00, 0x20, 0x21, 0x22, ..., 0x7E  // ASCII 可打印字符
};

const SkFixed LiberationSansNormalWidths[] = {
    0x00000000,  // 字形 0 宽度
    0x00032000,  // 字形 1 宽度(定点数格式)
    // ...
};

const SkFontMetrics LiberationSansNormalMetrics = {
    0x00000001,  // flags
    -1.15f,      // fTop
    -0.93f,      // fAscent
    0.21f,       // fDescent
    // ...
};
```

### 字形路径构建

```cpp
void SkTestFont::init(const SkScalar* pts, const unsigned char* verbs) {
    fPaths = new SkPath[fCharCodesCount];
    for (unsigned index = 0; index < fCharCodesCount; ++index) {
        SkPathBuilder b;
        SkPath::Verb verb;
        while ((verb = (SkPath::Verb)*verbs++) != SkPath::kDone_Verb) {
            switch (verb) {
                case SkPath::kMove_Verb:
                    b.moveTo(pts[0], pts[1]);
                    pts += 2;
                    break;
                case SkPath::kLine_Verb:
                    b.lineTo(pts[0], pts[1]);
                    pts += 2;
                    break;
                case SkPath::kQuad_Verb:
                    b.quadTo(pts[0], pts[1], pts[2], pts[3]);
                    pts += 4;
                    break;
                case SkPath::kCubic_Verb:
                    b.cubicTo(pts[0], pts[1], pts[2], pts[3], pts[4], pts[5]);
                    pts += 6;
                    break;
                case SkPath::kClose_Verb:
                    b.close();
                    break;
            }
        }
        fPaths[index] = b.detach();
    }
}
```

从压缩的动词和点数据构建完整的字形路径。

### 字符到字形映射

```cpp
void TestTypeface::onCharsToGlyphs(SkSpan<const SkUnichar> uni,
                                   SkSpan<SkGlyphID> glyphs) const {
    SkASSERT(uni.size() == glyphs.size());
    for (size_t i = 0; i < uni.size(); ++i) {
        glyphs[i] = fTestFont->glyphForUnichar(uni[i]);
    }
}

SkGlyphID SkTestFont::glyphForUnichar(SkUnichar charCode) const {
    for (size_t index = 0; index < fCharCodesCount; ++index) {
        if (fCharCodes[index] == charCode) {
            return SkTo<SkGlyphID>(index);
        }
    }
    return 0;  // 未找到时返回 .notdef 字形
}
```

线性搜索字符编码表,时间复杂度 O(n),但由于字符集很小(~100 个字符),性能可接受。

### SkTestScalerContext 实现

```cpp
GlyphMetrics SkTestScalerContext::generateMetrics(const SkGlyph& glyph,
                                                   SkArenaAlloc*) {
    GlyphMetrics mx(glyph.maskFormat());

    // 获取前进宽度并应用变换
    SkPoint advance = this->getTestTypeface()->getAdvance(glyph.getGlyphID());
    mx.advance = fMatrix.mapPoint(advance);

    // 从路径计算边界
    mx.computeFromPath = true;
    return mx;
}

std::optional<GeneratedPath> SkTestScalerContext::generatePath(const SkGlyph& glyph) {
    return {{
        this->getTestTypeface()->getPath(glyph.getGlyphID()).makeTransform(fMatrix),
        false  // 不需要原始缩放信息
    }};
}
```

应用变换矩阵到字形路径,并从路径计算精确边界。

### 序列化支持

```cpp
std::unique_ptr<SkStreamAsset> TestTypeface::onOpenStream(int* ttcIndex) const {
    SkDynamicMemoryWStream wstream;
    wstream.write(gHeaderString, kHeaderSize);  // "SkTestTypeface01"

    SkString name;
    this->getFamilyName(&name);
    SkFontStyle style = this->fontStyle();

    wstream.writePackedUInt(name.size());
    wstream.write(name.c_str(), name.size());
    wstream.writeScalar(style.weight());
    wstream.writeScalar(style.width());
    wstream.writePackedUInt(style.slant());

    *ttcIndex = 0;
    return wstream.detachAsStream();
}
```

序列化为自定义格式,包含字体名称和样式信息,用于测试字体的序列化和反序列化。

### 自动注册机制

```cpp
TestTypeface::Register::Register() {
    SkTypeface::Register(TestTypeface::FactoryId, &TestTypeface::MakeFromStream);
}
static TestTypeface::Register registerer;  // 全局静态实例
```

程序启动时自动注册工厂函数,使 SkTypeface 反序列化系统能识别测试字体。

## 依赖关系

**核心依赖**:
- `include/core/SkTypeface.h`: 字体抽象基类
- `src/core/SkScalerContext.h`: 字形缩放上下文
- `include/core/SkPath.h`: 路径表示
- `include/core/SkFontMetrics.h`: 字体度量

**辅助依赖**:
- `src/core/SkFontDescriptor.h`: 字体描述符序列化
- `src/sfnt/SkOTUtils.h`: OpenType 工具
- `tools/fonts/test_font_*.inc`: 预生成的字体数据

**数据流**:
```
create_test_font.cpp (生成工具)
    ↓ (从真实字体提取)
test_font_*.inc (静态数据)
    ↓ (编译期嵌入)
SkTestFont (字形数据封装)
    ↓ (提供给)
TestTypeface (SkTypeface 实现)
    ↓ (被使用于)
测试代码
```

## 设计模式与设计决策

### 1. Singleton Pattern (变体)

```cpp
static const List& Typefaces() {
    static List list = []() -> List {
        // 构建字体列表
        return list;
    }();
    return list;
}
```

使用 C++11 的线程安全静态初始化,确保字体列表只构建一次。

### 2. Factory Pattern

```cpp
static sk_sp<SkTypeface> MakeFromStream(std::unique_ptr<SkStreamAsset> stream,
                                       const SkFontArguments&);
```

通过工厂函数创建字体实例,支持反序列化。

### 3. Template Method Pattern

SkTypeface 定义接口,TestTypeface 实现具体行为:
- `onCreateScalerContext()`: 创建缩放上下文
- `onCharsToGlyphs()`: 字符映射
- `onGetAdvancedMetrics()`: 度量信息

### 4. 设计决策

**为何使用硬编码数据**:
- 完全可复现的测试结果
- 无需依赖外部字体文件
- 跨平台一致性

**为何支持序列化**:
测试 Skia 的字体序列化和反序列化机制,确保在分布式渲染场景中的正确性。

**为何限制字符集**:
ASCII 可打印字符足以覆盖大多数测试场景,减少数据量和编译时间。

**为何使用线性搜索**:
字符集小(~100 个),哈希表或二分查找的开销不值得。

**为何固定 UPEM = 2048**:
标准化字体单位,简化测试和验证。

## 性能考量

### 1. 初始化性能

```cpp
void SkTestFont::init(const SkScalar* pts, const unsigned char* verbs)
```

首次访问时构建所有字形路径,时间复杂度 O(n×m),其中 n 是字形数量,m 是每个字形的平均路径复杂度。

**优化**: 路径数据在首次使用时构建,之后重用。

### 2. 字符查找性能

```cpp
SkGlyphID glyphForUnichar(SkUnichar charCode) const {
    for (size_t index = 0; index < fCharCodesCount; ++index) {
        if (fCharCodes[index] == charCode) {
            return SkTo<SkGlyphID>(index);
        }
    }
    return 0;
}
```

O(n) 查找,但 n ≈ 100,实际性能影响可忽略。

### 3. 内存占用

每个字体包含:
- 点坐标数组: ~1000-5000 个浮点数
- 动词数组: ~500-2000 个字节
- 字形路径: 运行时构建,约 50KB
- 总计: 每个字体约 100-200KB

12 个字体(3 家族 × 4 样式)总计约 1-2MB。

### 4. 缓存友好性

所有静态数据在编译时确定,位于只读数据段,具有良好的缓存局部性。

## 相关文件

**头文件**:
- `tools/fonts/TestTypeface.h`: 类声明

**实现文件**:
- `tools/fonts/TestTypeface.cpp`: 类实现

**数据文件**:
- `tools/fonts/test_font_monospace.inc`: Monospace 字体数据
- `tools/fonts/test_font_sans_serif.inc`: Sans-serif 字体数据
- `tools/fonts/test_font_serif.inc`: Serif 字体数据
- `tools/fonts/test_font_index.inc`: 字体索引

**生成工具**:
- `tools/fonts/create_test_font.cpp`: 从真实字体生成测试数据
- `tools/fonts/create_test_font_color.cpp`: 彩色字体生成

**相关工具**:
- `tools/fonts/TestFontMgr.h/cpp`: 测试字体管理器
- `tools/fonts/TestSVGTypeface.h/cpp`: SVG 测试字体

**测试文件**:
- `tests/FontMgrTest.cpp`: 字体管理器测试
- `tests/TypefaceTest.cpp`: 字体功能测试
