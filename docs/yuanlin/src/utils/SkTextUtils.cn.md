# SkTextUtils

> 源文件: include/utils/SkTextUtils.h, src/utils/SkTextUtils.cpp

## 概述

`SkTextUtils` 是 Skia 图形库中的文本绘制工具类,提供了一组高级文本绘制和路径转换功能。该模块在标准 `SkCanvas` 文本 API 的基础上增加了文本对齐功能,支持左对齐、居中对齐和右对齐,简化了常见文本布局任务的实现。

核心功能包括:带对齐方式的文本绘制(支持多种文本编码)和将文本转换为路径对象。该模块作为便捷工具层,封装了底层的文本排版和测量逻辑,为应用层提供更易用的 API,广泛应用于 UI 文本渲染、标签绘制、图表注释等场景。

## 架构位置

`SkTextUtils` 位于 Skia 的实用工具层,作为文本绘制的高级封装:

```
应用层 / UI 框架
   ↓
SkTextUtils (工具层 - include/utils, src/utils)
   ↓
├── SkCanvas (画布接口)
├── SkFont (字体对象)
├── SkTextBlob (文本 blob)
└── SkFontPriv (字体私有工具)
```

使用场景:
- 对齐文本标签的绘制
- 图表和图形注释
- UI 控件文本渲染
- 文本效果和轮廓生成

## 主要类与结构体

### SkTextUtils

纯静态工具类,提供文本绘制和路径转换方法。

**继承关系**: 无继承关系,纯静态工具类

**关键成员变量**: 无(所有方法为静态方法)

### Align (枚举)

文本对齐方式枚举。

| 枚举值 | 值 | 说明 |
|--------|-----|------|
| kLeft_Align | 0 | 左对齐(默认) |
| kCenter_Align | 1 | 居中对齐 |
| kRight_Align | 2 | 右对齐 |

## 公共 API 函数

### Draw - 绘制对齐文本

```cpp
static void Draw(SkCanvas* canvas, const void* text, size_t size,
                 SkTextEncoding encoding,
                 SkScalar x, SkScalar y,
                 const SkFont& font, const SkPaint& paint,
                 Align align = kLeft_Align);
```

在指定位置绘制文本,支持对齐方式。

**参数**:
- `canvas`: 目标画布
- `text`: 文本数据指针
- `size`: 文本数据字节数
- `encoding`: 文本编码类型(UTF-8, UTF-16, UTF-32, GlyphID)
- `x, y`: 绘制位置(对齐基准点)
- `font`: 字体对象
- `paint`: 绘制属性
- `align`: 对齐方式(默认左对齐)

**对齐语义**:
- `kLeft_Align`: `(x, y)` 为文本起始点
- `kCenter_Align`: `(x, y)` 为文本中心点
- `kRight_Align`: `(x, y)` 为文本结束点

**示例**:
```cpp
SkFont font;
font.setSize(24);
SkPaint paint;
paint.setColor(SK_ColorBLACK);

const char* text = "Hello World";
SkTextUtils::Draw(canvas, text, strlen(text),
                  SkTextEncoding::kUTF8,
                  100, 100, font, paint,
                  SkTextUtils::kCenter_Align);
```

### DrawString - 绘制字符串

```cpp
static void DrawString(SkCanvas* canvas, const char text[],
                       SkScalar x, SkScalar y,
                       const SkFont& font, const SkPaint& paint,
                       Align align = kLeft_Align);
```

便捷方法,绘制 C 风格字符串(UTF-8 编码)。内部调用 `Draw` 方法,自动计算字符串长度。

**示例**:
```cpp
SkTextUtils::DrawString(canvas, "Hello World", 100, 100,
                        font, paint,
                        SkTextUtils::kCenter_Align);
```

### GetPath - 文本转路径

```cpp
static void GetPath(const void* text, size_t length,
                    SkTextEncoding encoding,
                    SkScalar x, SkScalar y,
                    const SkFont& font, SkPath* path);
```

将文本转换为路径对象,用于文本轮廓、描边、裁剪等效果。

**参数**:
- `text`: 文本数据
- `length`: 字节长度
- `encoding`: 文本编码
- `x, y`: 起始位置
- `font`: 字体对象
- `path`: 输出路径对象(累加,不清空)

**注意**: 该方法没有对齐参数,始终从 `(x, y)` 开始布局文本。

**示例**:
```cpp
SkPath path;
SkFont font;
font.setSize(48);

SkTextUtils::GetPath("TEXT", 4, SkTextEncoding::kUTF8,
                     0, 0, font, &path);

// 现在可以对路径应用各种效果
paint.setStyle(SkPaint::kStroke_Style);
paint.setStrokeWidth(2);
canvas->drawPath(path, paint);
```

## 内部实现细节

### Draw 方法的对齐计算

```cpp
void SkTextUtils::Draw(SkCanvas* canvas, const void* text, size_t size,
                       SkTextEncoding encoding,
                       SkScalar x, SkScalar y, const SkFont& font,
                       const SkPaint& paint, Align align) {
    if (align != kLeft_Align) {
        SkScalar width = font.measureText(text, size, encoding);
        if (align == kCenter_Align) {
            width *= 0.5f;
        }
        x -= width;
    }

    canvas->drawTextBlob(
        SkTextBlob::MakeFromText(text, size, font, encoding),
        x, y, paint);
}
```

**实现逻辑**:
1. 如果不是左对齐,测量文本宽度
2. 居中对齐时,宽度乘以 0.5
3. 右对齐时,宽度保持不变
4. 调整 x 坐标:`x -= width`
5. 使用 `SkTextBlob` 绘制文本

**关键点**:
- 通过调整 x 坐标实现对齐,避免修改文本布局
- 使用 `SkTextBlob` 提高绘制性能(文本形状缓存)

### GetPath 方法的字形路径组合

```cpp
void SkTextUtils::GetPath(const void* text, size_t length,
                          SkTextEncoding encoding,
                          SkScalar x, SkScalar y,
                          const SkFont& font, SkPath* path) {
    SkAutoToGlyphs ag(font, text, length, encoding);
    AutoTArray<SkPoint> pos(ag.count());
    font.getPos(ag.glyphs(), pos, {x, y});

    struct Rec {
        SkPathBuilder fDst;
        const SkPoint* fPos;
    } rec = { {}, pos.get() };

    font.getPaths(ag.glyphs(), [](const SkPath* src, const SkMatrix& mx,
                                   void* ctx) {
        Rec* rec = (Rec*)ctx;
        if (src) {
            SkMatrix m(mx);
            m.postTranslate(rec->fPos->fX, rec->fPos->fY);
            rec->fDst.addPath(*src, m);
        }
        rec->fPos += 1;
    }, &rec);
    *path = rec.fDst.detach();
}
```

**实现步骤**:
1. **文本转字形**: `SkAutoToGlyphs` 将文本转换为字形 ID 数组
2. **计算位置**: `font.getPos()` 计算每个字形的绘制位置
3. **获取路径**: `font.getPaths()` 为每个字形获取轮廓路径
4. **变换组合**: 对每个字形路径应用位置偏移,累加到结果路径

**回调函数逻辑**:
- `src`: 字形的轮廓路径(可能为 nullptr,如空格)
- `mx`: 字形的基础变换矩阵
- `postTranslate`: 添加字形位置偏移
- `addPath`: 将变换后的路径添加到构建器

### SkAutoToGlyphs 的作用

```cpp
SkAutoToGlyphs ag(font, text, length, encoding);
```

`SkAutoToGlyphs` 是 RAII 风格的辅助类:
- 根据编码类型将文本转换为字形 ID
- 自动管理内存(栈或堆分配)
- 提供 `glyphs()` 和 `count()` 访问器

### 字形位置计算

```cpp
font.getPos(ag.glyphs(), pos, {x, y});
```

计算每个字形的绘制位置:
- 考虑字形前进宽度(advance)
- 应用字距调整(kerning)
- 起始位置为 `{x, y}`

结果存储在 `pos` 数组中,每个字形一个位置。

## 依赖关系

### 依赖的模块

| 模块 | 用途 |
|------|------|
| SkCanvas | 画布绘制接口 |
| SkFont | 字体对象,提供文本测量和字形查询 |
| SkPaint | 绘制属性 |
| SkTextBlob | 文本 blob,优化文本绘制 |
| SkPath | 路径对象 |
| SkPathBuilder | 路径构建器 |
| SkFontPriv | 字体私有工具(SkAutoToGlyphs) |
| SkMatrix | 变换矩阵 |

### 被依赖的模块

| 模块 | 使用方式 |
|------|----------|
| UI 框架 | 绘制对齐文本标签 |
| 图表库 | 绘制坐标轴标签和注释 |
| 矢量编辑器 | 文本转路径功能 |
| 示例和演示程序 | 简化文本绘制代码 |
| 测试框架 | 测试文本排版和对齐 |

## 设计模式与设计决策

### 静态工具类模式

所有方法都是静态的:

**优点**:
- 无需实例化
- 轻量级,无状态
- 清晰的工具性质

**权衡**:
- 不支持多态
- 难以模拟(单元测试)

### 便捷方法模式

`DrawString` 作为 `Draw` 的便捷包装:

```cpp
static void DrawString(SkCanvas* canvas, const char text[],
                       SkScalar x, SkScalar y,
                       const SkFont& font, const SkPaint& paint,
                       Align align = kLeft_Align) {
    Draw(canvas, text, strlen(text), SkTextEncoding::kUTF8,
         x, y, font, paint, align);
}
```

**优点**:
- 简化常见用例(C 字符串)
- 避免用户手动计算长度和指定编码
- 代码复用(内部调用 `Draw`)

### 坐标调整而非布局修改

对齐通过调整绘制坐标实现:

```cpp
x -= width;  // 向左偏移文本宽度
```

而非:
```cpp
// 修改文本布局或字形位置(更复杂)
```

**优点**:
- 简单高效
- 不影响字距调整等布局细节
- 与底层 API 无缝集成

### 累加式路径构建

`GetPath` 累加到现有路径:

```cpp
rec.fDst.addPath(*src, m);  // 添加,不替换
*path = rec.fDst.detach();   // 最后赋值
```

**优点**:
- 允许多次调用合并路径
- 符合 Skia 的路径操作习惯

**注意**: 如果需要替换路径,调用者应先清空:
```cpp
path.reset();
SkTextUtils::GetPath(..., &path);
```

### 回调函数处理字形路径

`font.getPaths()` 使用回调:

```cpp
font.getPaths(glyphs, [](const SkPath* src, const SkMatrix& mx, void* ctx) {
    // 处理每个字形路径
}, &rec);
```

**优点**:
- 避免一次性分配所有字形路径
- 支持流式处理
- 允许跳过无效字形(src == nullptr)

### 编码灵活性

`Draw` 和 `GetPath` 都支持多种编码:

- `SkTextEncoding::kUTF8`: 最常用
- `SkTextEncoding::kUTF16`: Windows 常用
- `SkTextEncoding::kUTF32`: 完整 Unicode
- `SkTextEncoding::kGlyphID`: 直接指定字形 ID

**好处**: 适应不同平台和数据源

## 性能考量

### 文本宽度测量

```cpp
SkScalar width = font.measureText(text, size, encoding);
```

对于非左对齐的情况,每次绘制都需要测量:

- **UTF-8/16/32**: 需要解析文本并查询字形前进宽度
- **GlyphID**: 直接查询,更快

**优化建议**: 如果同一文本重复绘制,缓存宽度。

### SkTextBlob 的使用

```cpp
canvas->drawTextBlob(SkTextBlob::MakeFromText(text, size, font, encoding),
                     x, y, paint);
```

`SkTextBlob` 缓存字形形状和位置:

- 避免重复的文本整形(shaping)
- GPU 后端可批量上传字形纹理
- 比直接 `drawText` 更高效

但每次调用都创建新 blob:
- 如果同一文本重复绘制,应缓存 `SkTextBlob` 对象

### GetPath 的开销

```cpp
font.getPaths(ag.glyphs(), callback, &rec);
```

获取字形路径涉及:

- 从字体文件解析轮廓
- 可能的 TrueType 提示(hinting)
- 路径点的生成

**开销较大**: 适合一次性或低频操作(如文本效果预处理)

**不适合**: 每帧实时绘制大量文本

### 内存分配

```cpp
AutoTArray<SkPoint> pos(ag.count());
```

`AutoTArray` 根据大小选择栈或堆分配:
- 小数组:栈分配(快速)
- 大数组:堆分配

对于短文本,完全在栈上完成,性能最优。

### 字形路径合并

```cpp
rec.fDst.addPath(*src, m);
```

每个字形路径都独立变换和添加:

- 对于复杂字形(如中文),路径可能包含数百个点
- 多个字形的路径合并可能产生非常大的路径对象

**优化**: 如果只需要绘制,使用 `drawTextBlob` 而非转路径。

## 相关文件

| 文件路径 | 说明 |
|----------|------|
| include/utils/SkTextUtils.h | 公共 API 头文件 |
| src/utils/SkTextUtils.cpp | 实现文件 |
| include/core/SkCanvas.h | 画布接口 |
| include/core/SkFont.h | 字体对象 |
| include/core/SkTextBlob.h | 文本 blob |
| include/core/SkPath.h | 路径对象 |
| include/core/SkPathBuilder.h | 路径构建器 |
| src/core/SkFontPriv.h | 字体私有工具 |
