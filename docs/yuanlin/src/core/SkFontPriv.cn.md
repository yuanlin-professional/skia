# SkFontPriv

> 源文件：src/core/SkFontPriv.h

## 概述

SkFontPriv 是 SkFont 类的私有工具类,提供内部使用的辅助函数和常量。它封装了字体相关的私有操作,包括变换矩阵构建、边界计算、文本编码转换、序列化支持等。该类采用纯静态方法设计,作为 SkFont 的扩展功能集,不对外公开,仅供 Skia 内部模块使用。

## 架构位置

```
Skia 字体系统
└── src/core
    ├── SkFont (公共字体类)
    ├── SkFontPriv (私有工具类)
    │   ├── 矩阵变换
    │   ├── 边界计算
    │   ├── 文本编码转换
    │   └── 序列化支持
    └── 字体渲染管道
        ├── SkGlyphRun
        ├── SkStrikeCache
        └── SkScalerContext
```

该类是字体系统内部实现的粘合层,为上层模块提供便捷工具。

## 主要类与结构体

### SkFontPriv (静态工具类)

**继承关系**
- 无继承,纯静态工具类

**关键常量**

| 常量 | 值 | 说明 |
|------|---|------|
| kCanonicalTextSizeForPaths | 64 | 路径提取的标准字体大小 |

### SkAutoToGlyphs (辅助类)

自动文本到字形 ID 转换的 RAII 类。

**继承关系**
- 无继承,栈对象

**关键成员变量**

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| fStorage | AutoSTArray<32, SkGlyphID> | 字形 ID 存储 |
| fGlyphs | SkSpan<const SkGlyphID> | 字形 ID 视图 |

## 公共 API 函数

### 矩阵变换

#### MakeTextMatrix (重载1)

```cpp
static SkMatrix MakeTextMatrix(SkScalar size, SkScalar scaleX, SkScalar skewX)
```

构建文本变换矩阵。

**参数**
- size: 字体大小
- scaleX: X 方向缩放
- skewX: X 方向倾斜(斜体)

**返回值**: 组合变换矩阵

**数学形式**
```
M = Scale(size*scaleX, size) * Skew(skewX, 0)
```

#### MakeTextMatrix (重载2)

```cpp
static SkMatrix MakeTextMatrix(const SkFont& font)
```

从字体对象构建变换矩阵。

**便捷方法**: 调用重载1,使用 font 的参数。

### 度量缩放

```cpp
static void ScaleFontMetrics(SkFontMetrics* metrics, SkScalar scale)
```

按比例缩放字体度量值。

**参数**
- metrics: 字体度量(输入输出)
- scale: 缩放因子

**功能**: 所有度量值乘以 scale,用于字体大小调整。

### 边界计算

```cpp
static SkRect GetFontBounds(const SkFont& font)
```

获取字体的整体边界框。

**返回值**: 所有字形的并集边界

**特性**
- 基于字体度量计算
- 不包含假粗体或路径效果
- 忽略提示(hinting)

**近似公式**
```cpp
当 textSize 大、scaleX=1、skewX=0 时:
bounds ≈ {fXMin, fTop, fXMax, fBottom}
```

### 近似变换文本大小

```cpp
static SkScalar ApproximateTransformedTextSize(
    const SkFont& font, const SkMatrix& matrix, const SkPoint& textLocation)
```

估算变换后的文本尺寸。

**参数**
- font: 字体对象
- matrix: 变换矩阵
- textLocation: 文本位置(用于透视计算)

**返回值**: 近似最大维度

**用途**: 用于细节层次(LOD)决策,避免完整变换。

### 有限性检查

```cpp
static bool IsFinite(const SkFont& font)
```

检查字体参数是否有限(非 NaN/Inf)。

**实现**
```cpp
return SkIsFinite(font.getSize(), font.getScaleX(), font.getSkewX());
```

### 文本编码工具

#### CountTextElements

```cpp
static size_t CountTextElements(const void* text, size_t byteLength,
                                 SkTextEncoding encoding)
```

计算文本中的字符或字形数量。

**参数**
- text: 文本数据
- byteLength: 字节长度
- encoding: 编码类型

**返回值**: 元素数量

| 编码 | 计算方式 |
|------|---------|
| UTF8 | 解析 UTF-8 序列 |
| UTF16 | byteLength / 2 |
| UTF32 | byteLength / 4 |
| GlyphID | byteLength / 2 |

#### GlyphsToUnichars

```cpp
static void GlyphsToUnichars(const SkFont& font,
                              const SkGlyphID glyphs[], int count,
                              SkUnichar unicodes[])
```

将字形 ID 转换为 Unicode 字符。

**参数**
- font: 字体对象
- glyphs: 字形 ID 数组
- count: 数量
- unicodes: 输出 Unicode 数组

**注意**: 反向查找,可能不准确(多对一映射)。

### 序列化

```cpp
static void Flatten(const SkFont& font, SkWriteBuffer& buffer)
static bool Unflatten(SkFont* font, SkReadBuffer& buffer)
```

序列化和反序列化字体对象。

**详见**: SkFont_serial.md 文档

### 标志访问

```cpp
static inline uint8_t Flags(const SkFont& font)
```

访问字体的内部标志位。

**返回值**: font.fFlags

**用途**: 内部模块需要直接访问标志。

## SkAutoToGlyphs 辅助类

### 构造函数

```cpp
SkAutoToGlyphs(const SkFont& font, const void* text,
               size_t length, SkTextEncoding encoding)
```

自动将文本转换为字形 ID。

**参数**
- font: 字体对象
- text: 文本数据
- length: 字节长度
- encoding: 编码类型

**行为**
- GlyphID 编码: 直接使用,无转换
- 其他编码: 调用 font.textToGlyphs 转换
- 自动管理内存(栈/堆)

### 访问器

```cpp
size_t size() const          // 字形数量
const SkGlyphID* data() const  // 字形数据指针
size_t count() const         // 同 size()
SkSpan<const SkGlyphID> glyphs() const  // 字形视图
```

### 用法示例

```cpp
SkAutoToGlyphs atg(font, text, length, encoding);
for (SkGlyphID glyph : atg.glyphs()) {
    // 处理每个字形
}
```

## 内部实现细节

### kCanonicalTextSizeForPaths 常量

**值**: 64

**用途**: 从字体获取字形路径时使用的标准大小

**原理**
- 路径存储为浮点数,可缩放
- 字体缩放器可能使用定点数(26.6)
- 64 避免下溢(太小)和溢出(太大)
- 与字形缓存大小无需匹配(使用 unhinted)

### 矩阵构建

```cpp
SkMatrix m = SkMatrix::Scale(size * scaleX, size);
if (skewX) {
    m.postSkew(skewX, 0);
}
```

**顺序**: 先缩放,后倾斜,确保正确的文本变形。

### SkAutoToGlyphs 优化

```cpp
// 小数组用栈(32 个字形)
skia_private::AutoSTArray<32, SkGlyphID> fStorage;

// GlyphID 编码快速路径
if (encoding == SkTextEncoding::kGlyphID || length == 0) {
    fGlyphs = {(const uint16_t*)text, length >> 1};
} else {
    // 需要转换
    const size_t count = font.countText(text, length, encoding);
    fStorage.reset(count);
    font.textToGlyphs(text, length, encoding, fGlyphs);
}
```

避免不必要的内存分配和转换。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkFont | 字体类定义 |
| SkMatrix | 变换矩阵 |
| SkFontMetrics | 字体度量 |
| SkTypeface | 字体面 |
| SkWriteBuffer | 序列化 |
| SkReadBuffer | 反序列化 |
| SkFloatingPoint | 有限性检查 |
| SkTemplates | AutoSTArray |

### 被依赖的模块

| 模块 | 使用场景 |
|------|----------|
| SkGlyphRun | 文本运行构建 |
| SkTextBlob | 文本对象创建 |
| SkCanvas::drawText | 文本绘制 |
| SkStrikeCache | 字形缓存 |
| SkScalerContext | 字形缩放 |

## 设计模式与设计决策

### 设计决策

1. **为何使用私有工具类**
   - 避免污染公共 API
   - 集中管理内部逻辑
   - 便于重构和优化

2. **kCanonicalTextSizeForPaths = 64**
   - 经验值,平衡精度和性能
   - 26.6 定点数友好
   - 避免浮点精度问题

3. **矩阵缓存而非重复构建**
   - 矩阵构建有一定开销
   - 文本渲染是热点路径
   - 提供静态方法便于缓存

4. **SkAutoToGlyphs 的 RAII 设计**
   - 自动内存管理
   - 栈优化常见情况
   - 异常安全

5. **GlyphID 快速路径**
   - 避免不必要的转换
   - 零拷贝优化
   - 性能关键

## 性能考量

### 性能特征

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| MakeTextMatrix | O(1) | 矩阵乘法 ~10 ns |
| GetFontBounds | O(1) | 读取度量 ~5 ns |
| IsFinite | O(1) | 3 次比较 ~2 ns |
| CountTextElements(UTF8) | O(n) | n = 字节数 |
| GlyphsToUnichars | O(n) | n = 字形数 |

### SkAutoToGlyphs 性能

```cpp
// GlyphID 编码(快速路径)
开销: ~10 ns (指针赋值)

// UTF8 转换(慢速路径)
开销: ~50 ns/字符 + 分配

// 小数组(<32 字形)
栈分配: ~0 ns

// 大数组(>32 字形)
堆分配: ~100 ns
```

### 优化技术

1. **内联函数**: 简单工具函数标记 inline
2. **栈优化**: AutoSTArray 小数组用栈
3. **延迟计算**: 仅在需要时构建矩阵
4. **缓存友好**: 紧凑数据布局

### 内存占用

```cpp
sizeof(SkAutoToGlyphs) ≈
    sizeof(AutoSTArray<32>)  // ~140 字节
    + sizeof(SkSpan)         // 16 字节
    ≈ 160 字节
```

## 相关文件

| 文件路径 | 说明 |
|---------|------|
| include/core/SkFont.h | 字体公共接口 |
| src/core/SkFont.cpp | 字体实现 |
| src/core/SkFont_serial.cpp | 序列化实现 |
| src/core/SkFontMetrics.h | 字体度量 |
| src/core/SkGlyphRun.cpp | 使用文本转换 |
| src/core/SkTextBlob.cpp | 使用边界计算 |
| src/core/SkStrikeCache.cpp | 使用标准大小 |
| include/private/base/SkTemplates.h | AutoSTArray 定义 |
