# SkFontMetrics

> 源文件: `include/core/SkFontMetrics.h`

## 概述

SkFontMetrics 结构体封装了字体的度量信息(metrics),包括基线偏移、行间距、字符宽度、下划线和删除线参数等排版关键数据。这些度量值遵循 Skia 的 y 轴向下坐标系统,为文本布局、行高计算和装饰线绘制提供精确的几何参数。

## 架构位置

SkFontMetrics 位于 Skia 核心层 (`include/core`),属于字体子系统的度量数据层。它被 SkFont、SkTextBlob、文本布局引擎以及文本绘制代码广泛使用,是连接字体数据和文本渲染几何的桥梁。

## 结构体定义

### SkFontMetrics

**职责**: 存储字体的排版度量参数,提供度量值的查询和验证方法。

**关键成员变量**:
| 变量名 | 类型 | 说明 |
|--------|------|------|
| fFlags | uint32_t | 标志位,指示哪些度量值有效 |
| fTop | SkScalar | 任何字形边界框的最大上边界(通常为负值) |
| fAscent | SkScalar | 基线上方保留空间(通常为负值) |
| fDescent | SkScalar | 基线下方保留空间(通常为正值) |
| fBottom | SkScalar | 任何字形边界框的最大下边界(通常为正值) |
| fLeading | SkScalar | 行间距附加空间(通常为正值或零) |
| fAvgCharWidth | SkScalar | 平均字符宽度(未知为零) |
| fMaxCharWidth | SkScalar | 最大字符宽度(未知为零) |
| fXMin | SkScalar | 字形边界框最左边界(通常为负值) |
| fXMax | SkScalar | 字形边界框最右边界(通常为正值) |
| fXHeight | SkScalar | 小写 'x' 的高度(未知为零,通常为负值) |
| fCapHeight | SkScalar | 大写字母高度(未知为零,通常为负值) |
| fUnderlineThickness | SkScalar | 下划线粗细 |
| fUnderlinePosition | SkScalar | 下划线距基线距离(通常为正值) |
| fStrikeoutThickness | SkScalar | 删除线粗细 |
| fStrikeoutPosition | SkScalar | 删除线距基线距离(通常为负值) |

### FontMetricsFlags 枚举

**职责**: 标识度量值的有效性。

| 枚举值 | 位掩码 | 说明 |
|--------|--------|------|
| kUnderlineThicknessIsValid_Flag | 1 << 0 | fUnderlineThickness 有效 |
| kUnderlinePositionIsValid_Flag | 1 << 1 | fUnderlinePosition 有效 |
| kStrikeoutThicknessIsValid_Flag | 1 << 2 | fStrikeoutThickness 有效 |
| kStrikeoutPositionIsValid_Flag | 1 << 3 | fStrikeoutPosition 有效 |
| kBoundsInvalid_Flag | 1 << 4 | fTop/fBottom/fXMin/fXMax 无效 |

## 公共 API 函数

### 比较运算符

#### `bool operator==(const SkFontMetrics& that) const`
- **功能**: 判断两个度量结构是否完全相等
- **返回值**: 所有字段相等返回 true
- **用途**: 字体缓存的相等性检查

### 度量验证方法

#### `bool hasUnderlineThickness(SkScalar* thickness) const`
- **功能**: 检查下划线粗细是否有效并获取值
- **参数**: `thickness` - 输出参数,接收粗细值
- **返回值**: 有效返回 true 且设置 thickness,否则返回 false
- **用途**: 绘制下划线前验证参数

#### `bool hasUnderlinePosition(SkScalar* position) const`
- **功能**: 检查下划线位置是否有效并获取值
- **参数**: `position` - 输出参数,接收位置值
- **返回值**: 有效返回 true 且设置 position,否则返回 false

#### `bool hasStrikeoutThickness(SkScalar* thickness) const`
- **功能**: 检查删除线粗细是否有效并获取值
- **参数**: `thickness` - 输出参数,接收粗细值
- **返回值**: 有效返回 true 且设置 thickness,否则返回 false

#### `bool hasStrikeoutPosition(SkScalar* position) const`
- **功能**: 检查删除线位置是否有效并获取值
- **参数**: `position` - 输出参数,接收位置值
- **返回值**: 有效返回 true 且设置 position,否则返回 false

#### `bool hasBounds() const`
- **功能**: 检查边界度量值(fTop/fBottom/fXMin/fXMax)是否有效
- **返回值**: 边界有效返回 true
- **说明**: 可变字体时边界可能标记为无效(因字形轮廓可变)

## 度量值详解

### 垂直度量(Y 轴)

#### 基线相关
```
           fTop ◄────────────┐ (最高点,负值)
                             │
         fAscent ◄──────┐    │ (推荐上边界,负值)
                        │    │
    ─────────────────基线────┤─────► Y=0
                        │    │
        fDescent ◄──────┘    │ (推荐下边界,正值)
                             │
         fBottom ◄────────────┘ (最低点,正值)

        fLeading ◄──────┐ (行间距,正值)
                        │
    ─────────────────下一行基线───────►
```

**关键差异**:
- **fAscent/fDescent**: 推荐的行高空间,保证常见字符不重叠
- **fTop/fBottom**: 极端字形的实际边界(如带装饰的大写字母)
- **fLeading**: 行与行之间的额外间距

#### 字符高度
```
    ─────────────── fCapHeight (大写字母顶部,负值)
         H   x
    ─────────────── fXHeight (小写 x 顶部,负值)

    ─────────────── Y=0 (基线)
```

### 水平度量(X 轴)

```
fXMin ◄────────────────────────────► fXMax
      │                            │
      └─ 最左边的字形点              └─ 最右边的字形点

fAvgCharWidth: 平均宽度(统计值)
fMaxCharWidth: 最宽字符宽度
```

### 装饰线度量

#### 下划线
```
基线 ─────────────────
      ↓ fUnderlinePosition (正值,向下)
     ═══════════════ 下划线(粗细 = fUnderlineThickness)
```

#### 删除线
```
     ───────────────── 删除线(粗细 = fStrikeoutThickness)
      ↑ fStrikeoutPosition (负值,向上)
基线 ─────────────────
```

## 使用场景

### 获取字体度量
```cpp
SkFont font;
font.setSize(24);

SkFontMetrics metrics;
font.getMetrics(&metrics);

printf("行高: %.2f\n", metrics.fDescent - metrics.fAscent);
printf("基线上方: %.2f\n", -metrics.fAscent);
printf("基线下方: %.2f\n", metrics.fDescent);
```

### 计算行高
```cpp
SkScalar CalculateLineHeight(const SkFontMetrics& metrics) {
    // 标准行高 = ascent 到 descent + leading
    return (metrics.fDescent - metrics.fAscent) + metrics.fLeading;
}
```

### 绘制下划线
```cpp
void DrawUnderline(SkCanvas* canvas, SkScalar x, SkScalar y,
                   SkScalar width, const SkFontMetrics& metrics) {
    SkScalar thickness, position;
    if (metrics.hasUnderlineThickness(&thickness) &&
        metrics.hasUnderlinePosition(&position)) {
        SkPaint paint;
        paint.setStrokeWidth(thickness);

        SkScalar underlineY = y + position;
        canvas->drawLine(x, underlineY, x + width, underlineY, paint);
    } else {
        // 使用默认值:字号的 10%,基线下 1/10 字号
        SkScalar fontSize = ...;
        thickness = fontSize * 0.1f;
        position = fontSize * 0.1f;
        // ... 绘制
    }
}
```

### 垂直文本定位
```cpp
// 将文本垂直居中于给定矩形
SkScalar CenterTextVertically(const SkFontMetrics& metrics,
                              SkScalar rectHeight) {
    SkScalar textHeight = metrics.fDescent - metrics.fAscent;
    SkScalar offset = (rectHeight - textHeight) / 2;
    return offset - metrics.fAscent;  // 返回基线位置
}
```

### 计算文本边界框
```cpp
SkRect CalculateTightBounds(const SkFontMetrics& metrics,
                            SkScalar textWidth) {
    if (metrics.hasBounds()) {
        return SkRect::MakeLTRB(
            metrics.fXMin,
            metrics.fTop,
            textWidth + metrics.fXMax,
            metrics.fBottom
        );
    } else {
        // 使用 ascent/descent 近似
        return SkRect::MakeLTRB(
            0,
            metrics.fAscent,
            textWidth,
            metrics.fDescent
        );
    }
}
```

## 内部实现细节

### 坐标系约定
Skia 使用 y 轴向下坐标系:
- **负值**: 基线上方(fAscent, fTop, fCapHeight, fXHeight)
- **正值**: 基线下方(fDescent, fBottom, fUnderlinePosition)
- **零点**: 基线位置

### 标志位验证
```cpp
bool SkFontMetrics::hasUnderlineThickness(SkScalar* thickness) const {
    if (SkToBool(fFlags & kUnderlineThicknessIsValid_Flag)) {
        *thickness = fUnderlineThickness;
        return true;
    }
    return false;
}
```

### 可变字体的特殊处理
可变字体中字形轮廓可变,导致:
- fTop/fBottom 可能随轴值变化
- 设置 kBoundsInvalid_Flag 表示边界不可靠
- 调用者应使用 fAscent/fDescent 代替

## 依赖关系

### 依赖的模块
| 依赖 | 用途 |
|------|------|
| SkScalar.h | 浮点数类型定义 |
| SkTo.h | SkToBool 类型转换宏 |

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkFont | 通过 getMetrics 返回度量信息 |
| SkPaint | 文本绘制时使用度量计算位置 |
| SkTextBlob | 文本 Blob 布局需要度量参数 |
| 文本布局引擎 | HarfBuzz/ICU 集成时使用度量 |

## 设计决策

### 结构体而非类
选择 POD 结构体:
- 避免虚函数表开销
- 支持按值复制和比较
- 简化序列化

### 有效性标志
使用位标志而非 optional:
- 紧凑表示(单个 uint32_t)
- 批量查询效率高
- 与 C 字体库(FreeType)的 API 习惯一致

### 分离边界和行高
fTop/fBottom 与 fAscent/fDescent 分离:
- 满足不同布局需求(紧凑 vs 安全)
- 兼容 OpenType 规范(有两套度量表)

### 装饰线度量可选
下划线和删除线参数可能缺失:
- 位图字体通常不提供
- 允许运行时合成默认值

## 平台相关说明

### 度量来源

| 平台 | 垂直度量来源 | 水平度量来源 |
|------|-------------|-------------|
| FreeType | OS/2 表 sTypoAscender/Descender | hhea 表 advanceWidthMax |
| CoreText | CTFontGetAscent/Descent | CTFontGetBoundingBox |
| DirectWrite | DWRITE_FONT_METRICS | Advance widths |

### OpenType 表映射

| SkFontMetrics 字段 | OpenType 表字段 |
|-------------------|----------------|
| fAscent | OS/2.sTypoAscender (或 hhea.ascent) |
| fDescent | OS/2.sTypoDescender |
| fLeading | OS/2.sTypoLineGap |
| fUnderlinePosition | post.underlinePosition |
| fUnderlineThickness | post.underlineThickness |
| fXHeight | OS/2.sxHeight |
| fCapHeight | OS/2.sCapHeight |

### 平台差异
- **Windows**: 优先使用 USE_TYPO_METRICS 标志
- **macOS**: 可能调整度量以匹配 CoreText 行为
- **Web**: 与 CSS line-height 计算对齐

## 性能考量

### 缓存友好
结构体大小:
```cpp
sizeof(SkFontMetrics) = 4 + 15*4 = 64 字节 (对齐后)
```
适合栈分配和缓存行。

### 快速验证
标志位检查是单次位运算:
```cpp
if (metrics.fFlags & kUnderlineThicknessIsValid_Flag) {
    // O(1) 复杂度
}
```

### 避免重复获取
```cpp
// 好:一次获取,多次使用
SkFontMetrics metrics;
font.getMetrics(&metrics);
for (...) {
    SkScalar lineHeight = metrics.fDescent - metrics.fAscent;
}

// 差:重复获取
for (...) {
    SkFontMetrics metrics;
    font.getMetrics(&metrics);  // 多次调用
}
```

## 常见陷阱

### 符号混淆
```cpp
// 错误:fAscent 是负值!
SkScalar lineHeight = metrics.fAscent + metrics.fDescent;

// 正确:需要取差
SkScalar lineHeight = metrics.fDescent - metrics.fAscent;
```

### 边界无效
```cpp
// 危险:可变字体可能标记边界无效
if (metrics.hasBounds()) {
    // 安全使用 fTop/fBottom
} else {
    // 回退到 fAscent/fDescent
}
```

### 装饰线缺失
```cpp
SkScalar thickness;
if (!metrics.hasUnderlineThickness(&thickness)) {
    // 必须提供默认值!
    thickness = fontSize * 0.1f;
}
```

## 实际应用示例

### 多行文本布局
```cpp
void LayoutMultilineText(const std::vector<SkString>& lines,
                         const SkFont& font) {
    SkFontMetrics metrics;
    font.getMetrics(&metrics);

    SkScalar lineHeight = (metrics.fDescent - metrics.fAscent) + metrics.fLeading;
    SkScalar y = -metrics.fAscent;  // 第一行基线

    for (const auto& line : lines) {
        canvas->drawString(line, 0, y, font, paint);
        y += lineHeight;  // 下一行
    }
}
```

### 自定义装饰线
```cpp
void DrawCustomUnderline(SkCanvas* canvas, SkScalar x, SkScalar baselineY,
                         SkScalar width, const SkFont& font) {
    SkFontMetrics metrics;
    font.getMetrics(&metrics);

    SkScalar thickness = font.getSize() / 10;  // 字号的 10%
    SkScalar position;

    if (!metrics.hasUnderlinePosition(&position)) {
        position = font.getSize() / 8;  // 默认基线下 1/8 字号
    }

    SkPaint paint;
    paint.setStrokeWidth(thickness);
    paint.setColor(SK_ColorRED);

    canvas->drawLine(x, baselineY + position,
                     x + width, baselineY + position, paint);
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkFont.h` | 字体对象,通过 getMetrics 返回此结构 |
| `include/core/SkPaint.h` | 绘制参数,使用度量计算文本位置 |
| `include/core/SkTypeface.h` | 字体文件,提供原始度量数据 |
| `src/core/SkStrike.h` | 字形缓存,存储度量信息 |
| `src/core/SkScalerContext.h` | 字形缩放器,生成度量数据 |
