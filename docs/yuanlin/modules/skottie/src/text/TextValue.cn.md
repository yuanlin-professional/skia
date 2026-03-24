# TextValue

> 源文件
> - `modules/skottie/src/text/TextValue.h`
> - `modules/skottie/src/text/TextValue.cpp`

## 概述

`TextValue` 模块定义了 Skottie 文本值的结构和解析逻辑,封装了文本图层的所有属性,包括文本内容、字体、样式、布局、对齐方式和渲染参数。该模块负责从 Lottie JSON 解析文本属性,并转换为 `TextPropertyValue` 结构,供文本塑形器和渲染器使用。

`TextValue` 是 Skottie 文本系统的核心数据模型,连接 JSON 数据和文本渲染管线。它支持丰富的文本功能,包括段落排版、自动调整大小、方向控制、颜色/描边、以及多种对齐和换行策略。

## 架构位置

`TextValue` 位于 Skottie 文本系统的数据层:

```
Skottie 文本系统
├── TextValue ← 本模块 (文本数据模型)
│   └── TextPropertyValue (类型别名)
├── TextAdapter (文本适配器)
│   └── 使用 TextValue 进行塑形和渲染
├── TextShaper (文本塑形器)
│   └── 接收 TextPropertyValue 参数
└── TextAnimator (文本动画器)
```

数据流程:
1. 从 JSON 解析 TextValue
2. TextAdapter 监听 TextValue 变化
3. TextShaper 根据 TextValue 塑形文本
4. 渲染器应用 TextValue 样式

## 主要类与结构体

### TextValue (类型别名)

```cpp
typedef TextPropertyValue TextValue;
```

`TextValue` 是 `TextPropertyValue` 的别名,定义在 `include/skottie/SkottieProperty.h`:

```cpp
struct TextPropertyValue {
    SkString fText;                        // 文本内容
    sk_sp<SkTypeface> fTypeface;           // 字体
    SkString fFontFamily;                  // 字体族名
    float fTextSize;                       // 文本大小
    float fLineHeight;                     // 行高
    float fLineShift;                      // 行偏移
    float fAscent;                         // 上升高度
    SkRect fBox;                           // 文本框
    SkTextUtils::Align fHAlign;            // 水平对齐
    Shaper::VAlign fVAlign;                // 垂直对齐
    Shaper::ResizePolicy fResize;          // 调整大小策略
    Shaper::LinebreakPolicy fLineBreak;    // 换行策略
    Shaper::Direction fDirection;          // 文本方向
    Shaper::Capitalization fCapitalization;// 大写化
    size_t fMaxLines;                      // 最大行数
    float fMinTextSize;                    // 最小文本大小
    float fMaxTextSize;                    // 最大文本大小
    SkColor fFillColor;                    // 填充颜色
    SkColor fStrokeColor;                  // 描边颜色
    float fStrokeWidth;                    // 描边宽度
    SkPaint::Join fStrokeJoin;             // 描边连接
    TextPaintOrder fPaintOrder;            // 绘制顺序
    bool fHasFill;                         // 是否有填充
    bool fHasStroke;                       // 是否有描边
};
```

## 公共 API 函数

### Parse

```cpp
bool Parse(const skjson::Value& jv,
          const internal::AnimationBuilder& abuilder,
          TextValue* v);
```

从 JSON 解析文本值的核心函数。

**JSON 格式**:
```json
{
  "f": "Arial",          // 字体名称
  "t": "Hello",          // 文本内容
  "s": 24,               // 文本大小
  "lh": 28.8,            // 行高
  "j": 0,                // 水平对齐 (0:左 1:右 2:居中)
  "ls": 0,               // 行偏移
  "sz": [100, 50],       // 文本框大小
  "ps": [10, 20],        // 文本框位置
  "d": 0,                // 方向 (0:LTR 1:RTL)
  "rs": 0,               // 调整大小策略 (0:无 1:缩放 2:缩小)
  "mf": 12,              // 最小字体大小
  "xf": 48,              // 最大字体大小
  "xl": 3,               // 最大行数
  "m": 0,                // 文本模式 (0:点 1:段落)
  "ca": 0,               // 大写化 (0:无 1:大写)
  "vj": 0,               // 垂直对齐 (0-5:多种模式)
  "fc": [1,0,0],         // 填充颜色
  "sc": [0,1,0],         // 描边颜色
  "sw": 2,               // 描边宽度
  "of": true,            // 绘制顺序 (true:填充在前)
  "lj": 1                // 描边连接 (1:斜接 2:圆角 3:斜角)
}
```

**解析步骤**:

1. **必需字段验证**:
```cpp
const skjson::StringValue* font_name = (*jtxt)["f"];
const skjson::StringValue* text = (*jtxt)["t"];
const skjson::NumberValue* text_size = (*jtxt)["s"];
const skjson::NumberValue* line_height = (*jtxt)["lh"];
if (!font_name || !text || !text_size || !line_height) {
    return false;
}
```

2. **字体查找**:
```cpp
const auto* font = abuilder.findFont(
    SkString(font_name->begin(), font_name->size()));
if (!font) {
    abuilder.log(Logger::Level::kError, nullptr,
        "Unknown font: \"%s\".", font_name->begin());
    return false;
}
```

3. **基础属性**:
```cpp
v->fText.set(text->begin(), text->size());
v->fTextSize = **text_size;
v->fLineHeight = **line_height;
v->fTypeface = font->fTypeface;
v->fFontFamily = font->fFamily;
v->fAscent = font->fAscentPct * -0.01f * v->fTextSize;
v->fLineShift = ParseDefault((*jtxt)["ls"], 0.0f);
```

4. **水平对齐**:
```cpp
static constexpr SkTextUtils::Align gAlignMap[] = {
    SkTextUtils::kLeft_Align,   // 'j': 0
    SkTextUtils::kRight_Align,  // 'j': 1
    SkTextUtils::kCenter_Align  // 'j': 2
};
v->fHAlign = gAlignMap[std::min<size_t>(
    ParseDefault<size_t>((*jtxt)["j"], 0),
    std::size(gAlignMap) - 1)];
```

5. **文本框**:
```cpp
// 大小
if (const skjson::ArrayValue* jsz = (*jtxt)["sz"]) {
    if (jsz->size() == 2) {
        v->fBox.setWH(ParseDefault<SkScalar>((*jsz)[0], 0),
                      ParseDefault<SkScalar>((*jsz)[1], 0));
    }
}

// 位置
if (const skjson::ArrayValue* jps = (*jtxt)["ps"]) {
    if (jps->size() == 2) {
        v->fBox.offset(ParseDefault<SkScalar>((*jps)[0], 0),
                       ParseDefault<SkScalar>((*jps)[1], 0));
    }
}
```

6. **文本方向**:
```cpp
static constexpr Shaper::Direction gDirectionMap[] = {
    Shaper::Direction::kLTR,  // 'd': 0
    Shaper::Direction::kRTL,  // 'd': 1
};
v->fDirection = gDirectionMap[std::min(
    ParseDefault<size_t>((*jtxt)["d"], 0),
    std::size(gDirectionMap) - 1)];
```

7. **调整大小策略**:
```cpp
static constexpr Shaper::ResizePolicy gResizeMap[] = {
    Shaper::ResizePolicy::kNone,            // 'rs': 0
    Shaper::ResizePolicy::kScaleToFit,      // 'rs': 1
    Shaper::ResizePolicy::kDownscaleToFit,  // 'rs': 2
};
v->fResize = gResizeMap[...];
```

8. **换行策略**:
```cpp
v->fLineBreak = v->fBox.isEmpty()
    ? Shaper::LinebreakPolicy::kExplicit    // 点模式
    : Shaper::LinebreakPolicy::kParagraph;  // 段落模式
```

9. **垂直对齐**:
```cpp
static constexpr Shaper::VAlign gVAlignMap[] = {
    Shaper::VAlign::kHybridTop,     // 'vj': 0
    Shaper::VAlign::kHybridCenter,  // 'vj': 1
    Shaper::VAlign::kHybridBottom,  // 'vj': 2
    Shaper::VAlign::kVisualTop,     // 'vj': 3
    Shaper::VAlign::kVisualCenter,  // 'vj': 4
    Shaper::VAlign::kVisualBottom,  // 'vj': 5
};
```

10. **颜色和描边**:
```cpp
v->fHasFill = parse_color((*jtxt)["fc"], &v->fFillColor);
v->fHasStroke = parse_color((*jtxt)["sc"], &v->fStrokeColor);

if (v->fHasStroke) {
    v->fStrokeWidth = ParseDefault((*jtxt)["sw"], 1.0f);
    v->fPaintOrder = ParseDefault((*jtxt)["of"], true)
        ? TextPaintOrder::kFillStroke
        : TextPaintOrder::kStrokeFill;

    static constexpr SkPaint::Join gJoins[] = {
        SkPaint::kMiter_Join,  // lj: 1
        SkPaint::kRound_Join,  // lj: 2
        SkPaint::kBevel_Join,  // lj: 3
    };
    v->fStrokeJoin = gJoins[...];
}
```

## 内部实现细节

### 字体查找

通过 `AnimationBuilder` 查找预注册的字体:

```cpp
const auto* font = abuilder.findFont(
    SkString(font_name->begin(), font_name->size()));
```

字体必须在 Lottie JSON 的 `fonts` 列表中定义。

### Ascent 计算

Ascent 根据字体的 ascent 百分比计算:

```cpp
v->fAscent = font->fAscentPct * -0.01f * v->fTextSize;
```

负值符合 Skia 的 `SkFontMetrics` 约定。

### 点模式 vs. 段落模式

根据文本框是否为空判断模式:

```cpp
v->fLineBreak = v->fBox.isEmpty()
    ? Shaper::LinebreakPolicy::kExplicit
    : Shaper::LinebreakPolicy::kParagraph;

v->fVAlign = v->fBox.isEmpty()
    ? Shaper::VAlign::kTopBaseline
    : Shaper::VAlign::kTop;
```

- **点模式**: 无文本框,基线对齐
- **段落模式**: 有文本框,顶部对齐

### 显式文本模式

支持显式文本模式覆盖:

```cpp
auto text_mode = ParseDefault((*jtxt)["m"], -1);
if (text_mode >= 0) {
    v->fLineBreak = (text_mode == 0)
        ? Shaper::LinebreakPolicy::kExplicit
        : Shaper::LinebreakPolicy::kParagraph;
}
```

注意: BM 不导出此属性,仅用于测试。

### 遗留属性支持

支持遗留的 `sk_rs` 和 `sk_vj` 属性:

```cpp
v->fResize = gResizeMap[std::min(
    std::max(ParseDefault<size_t>((*jtxt)["rs"], 0),
             ParseDefault<size_t>((*jtxt)["sk_rs"], 0)),
    std::size(gResizeMap) - 1)];
```

取两者的较大值,确保向后兼容。

### 颜色解析

使用 Lambda 函数解析颜色:

```cpp
const auto& parse_color = [](const skjson::ArrayValue* jcolor,
                              SkColor* c) {
    if (!jcolor) return false;

    ColorValue color_vec;
    if (!skottie::Parse(*jcolor,
                        static_cast<VectorValue*>(&color_vec))) {
        return false;
    }

    *c = color_vec;  // 隐式转换
    return true;
};
```

复用 `VectorValue` 解析逻辑,然后转换为 `SkColor`。

### 枚举映射

所有枚举使用静态映射表:

```cpp
static constexpr SkTextUtils::Align gAlignMap[] = { ... };
static constexpr Shaper::Direction gDirectionMap[] = { ... };
static constexpr Shaper::ResizePolicy gResizeMap[] = { ... };
static constexpr Shaper::VAlign gVAlignMap[] = { ... };
static constexpr SkPaint::Join gJoins[] = { ... };
static constexpr Shaper::Capitalization gCapMap[] = { ... };
```

使用 `std::min` 确保索引不越界,默认使用第一个值。

### 描边连接映射

Lottie 使用 1-based 索引:

```cpp
v->fStrokeJoin = gJoins[std::min<size_t>(
    ParseDefault<size_t>((*jtxt)["lj"], 1) - 1,  // 减 1 转为 0-based
    std::size(gJoins) - 1)];
```

## 依赖关系

### 对外依赖

- **TextPropertyValue**: 公共 API 中的文本值结构
- **SkTypeface**: Skia 字体类型
- **SkTextUtils**: 文本对齐枚举
- **TextShaper**: 提供方向、对齐、换行等枚举
- **AnimationBuilder**: 提供字体查找和日志功能
- **skjson**: JSON 解析库

### 内部依赖

- **SkottieJson**: `Parse`、`ParseDefault` 解析工具
- **SkottieValue**: `VectorValue`、`ColorValue` 类型
- **SkottiePriv**: 私有工具函数

### 被依赖情况

- **TextAdapter**: 使用 `TextValue` 作为文本属性类型
- **AnimationBuilder**: 调用 `Parse` 解析文本图层
- **PropertyObserver**: 通过 `TextPropertyValue` 观察文本变化

## 设计模式与设计决策

### 查找表模式

所有枚举映射使用 `constexpr` 静态数组:

```cpp
static constexpr SkTextUtils::Align gAlignMap[] = { ... };
```

编译时计算,零运行时开销,支持边界检查。

### 类型别名

`TextValue` 是 `TextPropertyValue` 的别名:

```cpp
typedef TextPropertyValue TextValue;
```

内部使用简洁名称,对外提供完整类型。

### Lambda 辅助函数

使用 Lambda 封装重复逻辑:

```cpp
const auto& parse_color = [](const skjson::ArrayValue* jcolor,
                              SkColor* c) { ... };

v->fHasFill = parse_color((*jtxt)["fc"], &v->fFillColor);
v->fHasStroke = parse_color((*jtxt)["sc"], &v->fStrokeColor);
```

### 防御性编程

所有索引都经过边界检查:

```cpp
v->fHAlign = gAlignMap[std::min<size_t>(..., std::size(gAlignMap) - 1)];
```

### 向后兼容

支持遗留属性,确保旧动画正常工作:

```cpp
std::max(ParseDefault<size_t>((*jtxt)["rs"], 0),
         ParseDefault<size_t>((*jtxt)["sk_rs"], 0))
```

## 性能考量

### 静态映射表

所有枚举映射使用 `constexpr` 数组,无运行时初始化:

```cpp
static constexpr SkTextUtils::Align gAlignMap[] = { ... };
```

### 字符串最小化

直接使用 JSON 字符串指针,避免不必要的复制:

```cpp
v->fText.set(text->begin(), text->size());
```

### 早期验证

必需字段在开始就验证,快速失败:

```cpp
if (!font_name || !text || !text_size || !line_height) {
    return false;
}
```

### Lambda 内联

Lambda 函数通常会被编译器内联:

```cpp
const auto& parse_color = [](...)  { ... };
```

### 引用传递

使用引用避免复制:

```cpp
bool Parse(const skjson::Value& jv,
          const internal::AnimationBuilder& abuilder,
          TextValue* v);
```

## 相关文件

**头文件依赖**:
- `modules/skottie/include/SkottieProperty.h` - `TextPropertyValue` 定义
- `include/core/SkTypeface.h` - 字体类型
- `include/utils/SkTextUtils.h` - 文本工具
- `modules/skottie/include/TextShaper.h` - 塑形器枚举

**实现文件依赖**:
- `modules/skottie/src/SkottieJson.h` - JSON 解析工具
- `modules/skottie/src/SkottieValue.h` - `VectorValue`、`ColorValue`
- `modules/skottie/src/SkottiePriv.h` - 私有工具
- `modules/jsonreader/SkJSONReader.h` - JSON 读取器

**相关模块**:
- `modules/skottie/src/text/TextAdapter.h` - 文本适配器
- `modules/skottie/include/TextShaper.h` - 文本塑形器
- `modules/skottie/src/SkottiePriv.h` - 动画构建器
