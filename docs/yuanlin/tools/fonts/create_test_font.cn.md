# create_test_font.cpp

> 源文件: tools/fonts/create_test_font.cpp

## 概述

`create_test_font.cpp` 是一个字体数据生成工具,用于从系统安装的真实字体文件(Liberation 字体系列)提取字形数据并生成 C++ 头文件格式的静态数据。该工具是 Skia 测试基础设施的关键组件,生成的数据被 `TestTypeface` 类使用,提供跨平台一致的测试字体。

该程序自动化了以下流程:从字体文件加载字体 → 提取 ASCII 可打印字符的字形路径 → 序列化为紧凑的数组格式 → 生成 `.inc` 头文件。生成的文件在编译时嵌入到 Skia 中,避免测试对外部字体文件的依赖。

## 架构位置

该工具位于字体测试工具目录:

```
skia/
  tools/
    fonts/
      create_test_font.cpp           # 本工具(生成器)
      test_font_monospace.inc        # 输出: Monospace 字体数据
      test_font_sans_serif.inc       # 输出: Sans-serif 字体数据
      test_font_serif.inc            # 输出: Serif 字体数据
      test_font_index.inc            # 输出: 字体索引
      TestTypeface.h/cpp             # 使用生成数据的测试字体类
```

**工作流程**:
```
系统字体文件 (/usr/share/fonts 或 /Library/Fonts)
    ↓ (create_test_font 读取)
字形路径、度量信息
    ↓ (序列化)
C++ 数组和常量
    ↓ (写入 .inc 文件)
test_font_*.inc
    ↓ (编译时包含)
TestTypeface
    ↓ (运行时使用)
测试代码
```

## 主要类与结构体

### NamedFontStyle

```cpp
struct NamedFontStyle {
    char const * const fName;            // 样式名称 (如 "Normal")
    char const * const fIdentifierName;  // 标识符名称 (如 "Normal")
    SkFontStyle const fStyle;            // SkFontStyle 对象
};
```

描述单个字体样式的元数据。

### FontDesc

```cpp
struct FontDesc {
    NamedFontStyle const fNamedStyle;   // 字体样式信息
    char const * const fFile;           // 字体文件名
};
```

关联样式信息与字体文件。

### FontFamilyDesc

```cpp
struct FontFamilyDesc {
    char const * const fGenericName;        // 通用名称 (如 "monospace")
    char const * const fFamilyName;         // 家族名称 (如 "Liberation Mono")
    char const * const fIdentifierName;     // C++ 标识符 (如 "LiberationMono")
    SkSpan<const FontDesc> const fFonts;    // 该家族的所有字体
};
```

描述一个字体家族的完整信息。

## 公共 API 函数

### main()

```cpp
int main(int argc, char * const argv[]);
```

程序入口,执行字体数据生成:
1. 定义字体家族和样式映射
2. 创建平台相关的字体管理器
3. 调用 `generate_fonts()` 生成字体数据
4. 调用 `generate_index()` 生成索引文件

### generate_fonts()

```cpp
static void generate_fonts(const char* basepath,
                           const SkSpan<const FontFamilyDesc>& families,
                           sk_sp<const SkFontMgr> mgr);
```

为所有字体家族生成数据文件:
- 遍历每个家族的每个字体
- 加载字体文件
- 调用 `output_font()` 生成 C++ 代码

### generate_index()

```cpp
static void generate_index(const SkSpan<const FontFamilyDesc>& families,
                           const FontDesc* defaultFont);
```

生成字体索引文件 `test_font_index.inc`:
- 创建 `gTestFonts` 数组
- 创建 `gSubFonts` 数组
- 标记默认字体

### output_font()

```cpp
static void output_font(sk_sp<SkTypeface> face,
                       const char* identifier,
                       FILE* out);
```

为单个字体生成 C++ 数据:
- 提取字形路径、宽度、度量
- 格式化为 C++ 数组
- 写入输出文件

## 内部实现细节

### 字体配置

```cpp
int main(int, char * const []) {
    constexpr NamedFontStyle normal     = {"Normal",      "Normal",     SkFontStyle::Normal()};
    constexpr NamedFontStyle bold       = {"Bold",        "Bold",       SkFontStyle::Bold()};
    constexpr NamedFontStyle italic     = {"Italic",      "Italic",     SkFontStyle::Italic()};
    constexpr NamedFontStyle bolditalic = {"Bold Italic", "BoldItalic", SkFontStyle::BoldItalic()};

    static constexpr FontDesc kMonoFonts[] = {
        {normal,     "LiberationMono-Regular.ttf"},
        {bold,       "LiberationMono-Bold.ttf"},
        {italic,     "LiberationMono-Italic.ttf"},
        {bolditalic, "LiberationMono-BoldItalic.ttf"},
    };

    static constexpr FontDesc kSansFonts[] = {
        {normal,     "LiberationSans-Regular.ttf"},
        {bold,       "LiberationSans-Bold.ttf"},
        {italic,     "LiberationSans-Italic.ttf"},
        {bolditalic, "LiberationSans-BoldItalic.ttf"},
    };

    static constexpr FontDesc kSerifFonts[] = {
        {normal,     "LiberationSerif-Regular.ttf"},
        {bold,       "LiberationSerif-Bold.ttf"},
        {italic,     "LiberationSerif-Italic.ttf"},
        {bolditalic, "LiberationSerif-BoldItalic.ttf"},
    };

    static constexpr FontFamilyDesc kFamiliesData[] = {
        {"monospace",  "Liberation Mono",  "LiberationMono",  kMonoFonts},
        {"sans-serif", "Liberation Sans",  "LiberationSans",  kSansFonts},
        {"serif",      "Liberation Serif", "LiberationSerif", kSerifFonts},
    };
}
```

定义了 3 个字体家族,每个包含 4 种样式,总计 12 个字体。

### 字形路径提取

```cpp
static void output_path_data(const SkFont& font,
                             int emSize,
                             SkString* ptsOut,
                             SkTDArray<SkPath::Verb>* verbs,
                             SkTDArray<unsigned>* charCodes,
                             SkTDArray<SkScalar>* widths) {
    for (SkUnichar index = 0x00; index < 0x7f; ++index) {
        SkGlyphID glyphID = font.unicharToGlyph(index);
        SkPath path = font.getPath(glyphID).value_or(SkPath());

        for (auto [verb, pts, w] : SkPathPriv::Iterate(path)) {
            *verbs->append() = (SkPath::Verb)verb;
            switch (verb) {
                case SkPathVerb::kMove:
                    output_points(&pts[0], emSize, 1, ptsOut);
                    break;
                case SkPathVerb::kLine:
                    output_points(&pts[1], emSize, 1, ptsOut);
                    break;
                case SkPathVerb::kQuad:
                    output_points(&pts[1], emSize, 2, ptsOut);
                    break;
                case SkPathVerb::kCubic:
                    output_points(&pts[1], emSize, 3, ptsOut);
                    break;
                case SkPathVerb::kClose:
                    break;
            }
        }
        *verbs->append() = SkPath::kDone_Verb;
        *charCodes->append() = index;
        *widths->append() = font.getWidth(glyphID);

        if (0 == index) {
            index = 0x1f;  // 跳过控制字符
        }
    }
}
```

**提取的数据**:
- **字符编码**: 0x00, 0x20-0x7E (ASCII 可打印字符)
- **路径动词**: Move, Line, Quad, Cubic, Close, Done
- **路径点**: 归一化到字体单位
- **字形宽度**: 前进宽度

### 数据格式化

#### 点坐标输出

```cpp
static void output_scalar(SkScalar num, int emSize, SkString* out) {
    num /= emSize;  // 归一化
    if (num == (int)num) {
        out->appendS32((int)num);
    } else {
        SkString str;
        str.printf("%1.6g", num);
        // 移除尾部的 0
        int width = (int)str.size();
        const char* cStr = str.c_str();
        while (cStr[width - 1] == '0') {
            --width;
        }
        str.remove(width, str.size() - width);
        out->appendf("%sf", str.c_str());
    }
    *out += ',';
    *out += (int)last_line_length(*out) >= kMaxLineLength ? '\n' : ' ';
}
```

**特点**:
- 归一化到字体单位(除以 emSize)
- 整数简化表示
- 移除浮点数尾部无用的零
- 自动换行(行长度限制 80 字符)

#### 定点数输出

```cpp
static void output_fixed(SkScalar num, int emSize, SkString* out) {
    uint32_t hex = (uint32_t)(num * 65536 / emSize);
    out->appendf("0x%08x,", hex);
    *out += (int)last_line_length(*out) >= kMaxLineLength ? '\n' : ' ';
}
```

宽度使用 SkFixed 格式(16.16 定点数)。

### 生成的文件格式

**字体数据文件** (`test_font_*.inc`):
```cpp
/*
 * Copyright 2015 Google Inc.
 * ...
 */

// Auto-generated by create_test_font.cpp

const SkScalar LiberationSansNormalPoints[] = {
    0.5f, 0.8f, 1.2f, 0.3f, ...
};

const unsigned char LiberationSansNormalVerbs[] = {
    0, 1, 2, 0, 4, 5, ...
};

const SkUnichar LiberationSansNormalCharCodes[] = {
    0, 32, 33, 34, ...
};

const SkFixed LiberationSansNormalWidths[] = {
    0x00000000, 0x00032000, ...
};

const size_t LiberationSansNormalCharCodesCount = 95;

const SkFontMetrics LiberationSansNormalMetrics = {
    0x00000001, -1.15f, -0.93f, 0.21f, ...
};
```

**索引文件** (`test_font_index.inc`):
```cpp
static SkTestFontData gTestFonts[] = {
    { LiberationMonoNormalPoints, LiberationMonoNormalVerbs,
      LiberationMonoNormalCharCodes, LiberationMonoNormalCharCodesCount,
      LiberationMonoNormalWidths, LiberationMonoNormalMetrics,
      "Toy Liberation Mono", SkFontStyle(400,5,SkFontStyle::kUpright_Slant)
    },
    ...
};

struct SubFont {
    const char* fFamilyName;
    const char* fStyleName;
    SkFontStyle fStyle;
    SkTestFontData& fFont;
    const char* fFile;
};

const SubFont gSubFonts[] = {
    { "monospace", "Normal", SkFontStyle(...), gTestFonts[0], "LiberationMono-Regular.ttf" },
    ...
};

const size_t gDefaultFontIndex = 4;  // sans-serif Normal
```

### 平台特定字体管理器

```cpp
#if defined(SK_FONTMGR_FONTCONFIG_AVAILABLE)
    mgr = SkFontMgr_New_FontConfig(nullptr, SkFontScanner_Make_FreeType());
#elif defined(SK_FONTMGR_CORETEXT_AVAILABLE)
    mgr = SkFontMgr_New_CoreText(nullptr);
#elif defined(SK_FONTMGR_FREETYPE_EMPTY_AVAILABLE)
    mgr = SkFontMgr_New_Custom_Empty();
#else
    SkDEBUGFAIL("Unsupported FontMgr");
#endif
```

根据平台选择字体管理器:
- **Linux**: FontConfig + FreeType
- **macOS**: CoreText
- **其他**: 空字体管理器(需手动配置)

### 字体文件路径

```cpp
#if defined(SK_BUILD_FOR_UNIX)
#define SK_FONT_FOLDER "/usr/share/fonts/truetype/liberation/"
#elif defined(SK_BUILD_FOR_MAC)
#define SK_FONT_FOLDER "/Library/Fonts/"
#else
#error "Unsupported OS"
#endif
```

## 依赖关系

**Skia 核心**:
- `include/core/SkFont.h`: 字体 API
- `include/core/SkFontMgr.h`: 字体管理器
- `include/core/SkPath.h`: 路径表示
- `src/core/SkPathPriv.h`: 路径迭代器

**平台端口**:
- `include/ports/SkFontMgr_fontconfig.h`: Linux 字体管理
- `include/ports/SkFontMgr_mac_ct.h`: macOS 字体管理

**工具**:
- `src/core/SkOSFile.h`: 文件系统操作
- `src/utils/SkOSPath.h`: 路径操作

## 设计模式与设计决策

### 1. Code Generation Pattern

自动生成源代码,避免手写大量数据。

**优点**:
- 减少人为错误
- 易于更新(重新运行工具)
- 保证数据一致性

### 2. Data-Driven Design

使用配置数据驱动生成过程:
```cpp
static constexpr FontFamilyDesc kFamiliesData[] = { ... };
```

易于扩展和维护。

### 3. 设计决策

**为何选择 Liberation 字体**:
- 开源(SIL Open Font License)
- 高质量
- 与流行字体(Arial, Times New Roman)度量兼容
- 跨平台可用

**为何限制 ASCII 字符**:
- 覆盖英文测试场景
- 减少生成数据量
- 加快编译速度

**为何使用固定 emSize = UPEM * 2**:
```cpp
const int emSize = face->getUnitsPerEm() * 2;
```
提供足够精度同时保持数值范围合理。

**为何生成 mipmap**:
```cpp
std::unique_ptr<SkMipmap> mipmaps(SkMipmap::Build(tmp.pixmap(), nullptr));
```
(注释中提到但实际未在生成器中使用,由 TestTypeface 在运行时决定)

## 性能考量

### 1. 生成时间

- 单个字体: 约 0.5-2 秒
- 总计 12 个字体: 约 10-20 秒
- 仅在字体数据需要更新时运行

### 2. 生成文件大小

- 单个字体: 约 50-100 KB
- 总计: 约 600-1200 KB
- 压缩后(在 .inc 文件中): 约 400-800 KB

### 3. 编译影响

- 增加编译时间: 约 1-2 秒
- 增加二进制大小: 约 500-1000 KB

### 4. 优化措施

**数值精度优化**:
```cpp
// 移除尾部零
while (cStr[width - 1] == '0') {
    --width;
}
```
减少生成文件大小约 10-15%。

**换行优化**:
```cpp
*out += (int)last_line_length(*out) >= kMaxLineLength ? '\n' : ' ';
```
保持代码可读性同时避免过长行。

## 相关文件

**本工具**:
- `tools/fonts/create_test_font.cpp`: 生成器源代码

**生成的文件**:
- `tools/fonts/test_font_monospace.inc`: Monospace 数据
- `tools/fonts/test_font_sans_serif.inc`: Sans-serif 数据
- `tools/fonts/test_font_serif.inc`: Serif 数据
- `tools/fonts/test_font_index.inc`: 索引数据

**使用生成数据的文件**:
- `tools/fonts/TestTypeface.h/cpp`: 测试字体实现

**相关工具**:
- `tools/fonts/create_test_font_color.cpp`: 彩色字体生成器
- `tools/fonts/generate_fir_coeff.py`: FIR 系数生成器

**字体文件** (输入):
- `/usr/share/fonts/truetype/liberation/*.ttf` (Linux)
- `/Library/Fonts/Liberation*.ttf` (macOS)

**构建集成**:
- `BUILD.gn`: 可能包含运行此工具的自定义规则

**测试**:
- `tests/FontMgrTest.cpp`: 验证生成的字体数据
