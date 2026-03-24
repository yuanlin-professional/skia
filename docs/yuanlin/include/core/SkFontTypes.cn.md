# SkFontTypes

> 源文件: `include/core/SkFontTypes.h`

## 概述

SkFontTypes 定义了 Skia 字体系统的两个核心枚举类型:文本编码方式(SkTextEncoding)和字体微调模式(SkFontHinting)。这些类型在文本渲染管线中控制字符到字形的转换以及字形轮廓的栅格化质量,是 Skia 跨平台文本渲染的基础配置接口。

## 架构位置

该文件位于 Skia 核心层 (`include/core`),属于字体子系统的类型定义层。这些枚举被 SkFont、SkTextBlob、SkCanvas 等高层 API 使用,同时被底层字形缓存和光栅化引擎依赖。它们定义了文本处理的两个关键决策点:输入解析和输出优化。

## 枚举定义

### SkTextEncoding

**职责**: 定义文本字符串的编码格式,决定如何将字节序列解释为字符或字形索引。

| 枚举值 | 字节宽度 | 说明 |
|--------|---------|------|
| kUTF8 | 可变(1-4字节) | UTF-8 编码或纯 ASCII,兼容 C 字符串 |
| kUTF16 | 2字节 | UTF-16 编码,表示大部分 Unicode 字符 |
| kUTF32 | 4字节 | UTF-32 编码,可表示所有 Unicode 字符 |
| kGlyphID | 2字节 | 字形索引直接编码,跳过字符到字形映射 |

#### 编码详解

**kUTF8**:
- **兼容性**: ASCII 字符占 1 字节,与传统 C 字符串兼容
- **变长编码**: Unicode 字符占 1-4 字节
- **常见用途**: 跨平台文本交换,C++ 字符串字面量
- **示例**: "Hello世界" → 'H'(1字节) + '世'(3字节)

**kUTF16**:
- **固定宽度**(BMP): 基本多文种平面字符占 2 字节
- **代理对**: 补充平面字符需要 4 字节(代理对)
- **常见用途**: Windows API,Java/C# 字符串
- **示例**: "A😀" → 0x0041(2字节) + 0xD83D+0xDE00(4字节)

**kUTF32**:
- **真正固定**: 所有 Unicode 码点占 4 字节
- **简单索引**: 可直接通过数组下标访问字符
- **空间开销**: 占用空间是 UTF-8 的 2-4 倍
- **常见用途**: 内部处理,Unicode 算法实现

**kGlyphID**:
- **直接索引**: 绕过字符映射,直接指定字形 ID
- **性能优化**: 避免重复的字符到字形转换
- **字体相关**: 字形 ID 仅在特定字体中有效
- **常见用途**: 文本布局引擎,预处理后的文本

### SkFontHinting

**职责**: 控制字形轮廓调整程度,以改善低分辨率屏幕上的显示效果。

| 枚举值 | 调整程度 | 说明 |
|--------|---------|------|
| kNone | 无调整 | 保持原始轮廓,适用于高 DPI 或打印 |
| kSlight | 轻微调整 | 最小化修改以改善对比度,保留设计意图 |
| kNormal | 常规调整 | 标准微调,平衡清晰度和形状保真度 |
| kFull | 最大调整 | 激进修改轮廓以获得最佳像素对齐 |

#### 微调模式详解

**kNone (无微调)**:
- **保真度**: 完全保留字体设计师的原始曲线
- **适用场景**:
  - 高分辨率屏幕(>200 PPI)
  - 打印输出
  - 旋转或变换文本
- **缺点**: 低分辨率下可能模糊

**kSlight (轻微微调)**:
- **策略**: 仅调整关键控制点,保持曲线平滑
- **适用场景**:
  - 中等 DPI(100-150 PPI)
  - 抗锯齿渲染
  - 需要保持字形优雅外观
- **macOS/iOS 默认**: 符合 Apple 设计哲学

**kNormal (常规微调)**:
- **策略**: 对齐主要笔画到像素网格
- **适用场景**:
  - 标准桌面显示器(96 DPI)
  - 小字号文本(10-14pt)
  - 用户界面文本
- **Windows/Linux 默认**: 平衡清晰度和形状

**kFull (完全微调)**:
- **策略**: 使用字体内嵌指令(TrueType hints)完全重构字形
- **适用场景**:
  - 极低分辨率(72-96 DPI)
  - 禁用抗锯齿
  - 极小字号(<10pt)
- **副作用**: 可能显著改变字形形状

## 使用示例

### 设置文本编码
```cpp
SkFont font;
SkPaint paint;

// UTF-8 字符串
const char* utf8Text = "Hello 世界";
canvas->drawString(utf8Text, x, y, font, paint); // 默认 UTF-8

// 直接使用字形 ID
SkFont glyphFont;
uint16_t glyphIDs[] = {42, 105, 233}; // 预先计算的字形索引
SkTextBlob* blob = SkTextBlob::MakeFromText(
    glyphIDs, sizeof(glyphIDs), font, SkTextEncoding::kGlyphID);
canvas->drawTextBlob(blob, x, y, paint);
```

### 配置字体微调
```cpp
SkFont font;

// 高分辨率设备:禁用微调
font.setHinting(SkFontHinting::kNone);

// 标准桌面:常规微调
font.setHinting(SkFontHinting::kNormal);

// 低分辨率优化
if (deviceDPI < 100) {
    font.setHinting(SkFontHinting::kFull);
}
```

## 依赖关系

### 依赖的模块
该文件是独立的枚举定义,无外部依赖。

### 被依赖的模块
| 模块 | 用途 |
|------|------|
| SkFont | 字体对象,存储编码和微调设置 |
| SkTextBlob | 文本 Blob,需要知道输入编码 |
| SkCanvas | 绘图 API,drawString/drawTextBlob 使用编码 |
| SkGlyphCache | 字形缓存,根据微调模式缓存不同版本 |
| SkScalerContext | 字形缩放器,应用微调指令 |
| SkTypeface | 字体文件,包含微调指令数据 |

## 设计决策

### 编码类型选择

**为何支持多种编码**:
1. **平台兼容**: UTF-16(Windows)、UTF-8(Unix)、UTF-32(内部)
2. **性能优化**: kGlyphID 避免重复映射
3. **API 历史**: 兼容旧版 Skia API

**为何不统一为 UTF-8**:
- 某些平台原生 API 使用 UTF-16(Windows WCHAR)
- kGlyphID 在复杂文本布局中有显著性能优势
- UTF-32 简化内部 Unicode 算法实现

### 微调模式分级

**四级划分依据**:
- **kNone**: 纯数学缩放,无额外计算
- **kSlight**: 自动微调,无需字体指令
- **kNormal**: 基本 TrueType 指令
- **kFull**: 完整 TrueType/PostScript 指令

**与 FreeType 对应**:
| SkFontHinting | FreeType 模式 |
|---------------|---------------|
| kNone | FT_LOAD_NO_HINTING |
| kSlight | FT_LOAD_TARGET_LIGHT |
| kNormal | FT_LOAD_TARGET_NORMAL |
| kFull | FT_LOAD_TARGET_LCD |

## 性能考量

### 编码性能

**UTF-8 解码开销**:
- 变长编码需要字节扫描
- 分支预测友好(ASCII 快速路径)
- SIMD 优化可加速多字节字符

**kGlyphID 优势**:
```cpp
// 常规路径:每次绘制都需映射
UTF8 → Unicode码点 → 字形ID → 字形轮廓

// kGlyphID 路径:跳过映射
字形ID → 字形轮廓 (快 2-3 倍)
```

### 微调性能

**缓存策略**:
```cpp
// 字形缓存键包含微调模式
struct GlyphCacheKey {
    uint16_t glyphID;
    SkFontHinting hinting; // 不同微调模式缓存不同版本
    // ... 其他参数
};
```

**微调计算成本**:
- **kNone**: 几乎零成本
- **kSlight**: 10-20% 额外计算
- **kNormal**: 30-50% 额外计算
- **kFull**: 50-100% 额外计算(执行 TrueType 指令)

## 平台相关行为

### 编码默认值

| 平台 | API 默认编码 |
|------|-------------|
| Windows | UTF-16(WCHAR) |
| macOS/iOS | UTF-8(char*) |
| Android | UTF-8(Java String 转换) |
| Web | UTF-8(JavaScript String) |

### 微调默认值

| 平台 | 默认微调模式 | 原因 |
|------|-------------|------|
| macOS | kSlight | 保留字体设计美感 |
| Windows | kNormal | 优化 ClearType 渲染 |
| Linux | kNormal | FreeType 默认行为 |
| Android | kSlight/kNormal | 取决于设备 DPI |

### 子像素渲染交互

```cpp
// Windows ClearType
if (subpixelRendering && hinting == kFull) {
    // 使用 LCD 优化的微调指令
}

// macOS 子像素 AA
if (hinting == kSlight) {
    // 轻微微调 + 子像素抗锯齿
}
```

## 最佳实践

### 编码选择建议
- **用户输入文本**: 使用平台原生编码(Windows=UTF-16,其他=UTF-8)
- **静态 UI 文本**: UTF-8(紧凑且跨平台)
- **性能关键路径**: 预计算字形 ID 使用 kGlyphID
- **文本编辑器**: UTF-32(简化光标移动和索引)

### 微调选择建议
```cpp
SkFontHinting ChooseHinting(float dpi, float fontSize) {
    if (dpi > 200) {
        return SkFontHinting::kNone;  // 高 DPI 屏幕
    }
    if (fontSize < 10) {
        return SkFontHinting::kFull;   // 小字号需要强微调
    }
    if (fontSize > 20) {
        return SkFontHinting::kSlight; // 大字号保持形状
    }
    return SkFontHinting::kNormal;     // 标准情况
}
```

## 相关文件

| 文件 | 关系 |
|------|------|
| `include/core/SkFont.h` | 字体对象,使用这些枚举配置渲染行为 |
| `include/core/SkTextBlob.h` | 文本 Blob,存储编码类型 |
| `include/core/SkCanvas.h` | 绘图 API,文本绘制方法使用这些类型 |
| `src/core/SkGlyphCache.h` | 字形缓存,根据微调模式区分缓存项 |
| `src/core/SkScalerContext.h` | 字形缩放器,应用微调算法 |
| `include/core/SkFontStyle.h` | 字体风格定义(字重、字宽、斜体) |
| `include/core/SkFontMetrics.h` | 字体度量信息 |
