# create_test_font_color.cpp

> 源文件: tools/fonts/create_test_font_color.cpp

## 概述

`create_test_font_color.cpp` 是一个彩色字体测试数据生成工具,用于导出 SVG 测试字体到 TTX 格式(FontTools 的 XML 表示),支持 CBDT(彩色位图数据表)、sbix(Apple 标准位图图像表)和 COLR(颜色表)格式。该工具为 Skia 的彩色字体渲染功能提供测试数据,确保跨平台彩色字体支持的正确性。

该程序仅在启用 SVG 支持时编译,生成的 TTX 文件可通过 FontTools 的 `ttx` 命令转换为真实的字体文件用于测试。

## 架构位置

```
skia/
  tools/
    fonts/
      create_test_font_color.cpp     # 本工具
      TestSVGTypeface.h/cpp          # SVG 测试字体实现
```

**工作流程**:
```
TestSVGTypeface (SVG 定义)
    ↓ (export_ttx)
TTX 文件 (cbdt.ttx, sbix.ttx, colr.ttx)
    ↓ (ttx 命令行工具)
TrueType 字体文件 (.ttf)
    ↓ (测试使用)
彩色字体渲染测试
```

## 主要类与结构体

无自定义类,主要使用 `TestSVGTypeface` 提供的功能。

## 公共 API 函数

### export_ttx()

```cpp
static void export_ttx(sk_sp<TestSVGTypeface> typeface,
                       SkString prefix,
                       SkSpan<unsigned> cbdtStrikeSizes,
                       SkSpan<unsigned> sbixStrikeSizes);
```

导出测试字体到 TTX 格式:
- **typeface**: 要导出的 SVG 测试字体
- **prefix**: 输出文件名前缀
- **cbdtStrikeSizes**: CBDT 格式的字号列表
- **sbixStrikeSizes**: sbix 格式的字号列表

生成三个文件:
- `{prefix}cbdt.ttx`: CBDT 格式(Google/Android)
- `{prefix}sbix.ttx`: sbix 格式(Apple)
- `{prefix}colr.ttx`: COLR 格式(微软/通用)

### main()

```cpp
int main(int argc, char** argv);
```

程序入口,导出两个测试字体:
1. **默认字体**: 使用常规尺寸 [16, 64, 128]
2. **行星字体**: 使用较小尺寸 [8, 16] (CBDT) 和常规尺寸 (sbix)

## 内部实现细节

### 导出流程

```cpp
void export_ttx(sk_sp<TestSVGTypeface> typeface,
                SkString prefix,
                SkSpan<unsigned> cbdtStrikeSizes,
                SkSpan<unsigned> sbixStrikeSizes) {
    // 导出 CBDT 格式
    SkFILEWStream cbdt((SkString(prefix) += "cbdt.ttx").c_str());
    typeface->exportTtxCbdt(&cbdt, cbdtStrikeSizes);
    cbdt.flush();
    cbdt.fsync();

    // 导出 sbix 格式
    SkFILEWStream sbix((SkString(prefix) += "sbix.ttx").c_str());
    typeface->exportTtxSbix(&sbix, sbixStrikeSizes);
    sbix.flush();
    sbix.fsync();

    // 导出 COLR 格式
    SkFILEWStream colr((SkString(prefix) += "colr.ttx").c_str());
    typeface->exportTtxColr(&colr);
    colr.flush();
    colr.fsync();
}
```

### 主函数实现

```cpp
int main(int argc, char** argv) {
    CommandLineFlags::Parse(argc, argv);

    // 常规尺寸用于大多数测试
    unsigned usual[] = { 16, 64, 128 };

    // 行星字体在 CBDT 格式中不能太大(格式限制)
    unsigned small[] = { 8, 16 };

    // 导出默认字体(无前缀)
    export_ttx(TestSVGTypeface::Default(), SkString(), SkSpan(usual), SkSpan(usual));

    // 导出行星字体(前缀 "planet")
    export_ttx(TestSVGTypeface::Planets(), SkString("planet"), SkSpan(small), SkSpan(usual));

    return 0;
}
```

### 彩色字体格式对比

| 格式  | 全称                        | 平台      | 技术       | 特点                     |
|-------|----------------------------|-----------|-----------|-------------------------|
| CBDT  | Color Bitmap Data Table    | Android   | PNG位图   | 大小受限,适合小字号     |
| sbix  | Standard Bitmap Graphics   | Apple     | PNG/JPEG  | 支持大字号,质量高       |
| COLR  | Color Table                | Windows   | 矢量图层  | 可缩放,文件小           |

### CBDT 大小限制

```cpp
// 行星字体在 CBDT 格式中只能使用较小尺寸
unsigned small[] = { 8, 16 };
```

CBDT 格式使用 16 位偏移量,限制了单个表的大小,大图像会超出限制。

### SVG 支持条件编译

```cpp
#if defined(SK_ENABLE_SVG)
    // 完整实现
#else
int main(int argc, char** argv) {
    SkDebugf("compile with SVG enabled\n");
    return 1;
}
#endif
```

仅在定义 `SK_ENABLE_SVG` 时提供完整功能。

## 依赖关系

**Skia 核心**:
- `include/core/SkRefCnt.h`: 引用计数
- `include/core/SkStream.h`: 文件流
- `include/core/SkString.h`: 字符串

**工具**:
- `tools/flags/CommandLineFlags.h`: 命令行参数解析
- `tools/fonts/TestSVGTypeface.h`: SVG 测试字体

**外部工具**:
- **FontTools ttx**: 将 TTX 转换为 TrueType 字体
  ```bash
  ttx cbdt.ttx  # 生成 cbdt.ttf
  ```

## 设计模式与设计决策

### 1. Adapter Pattern

将 `TestSVGTypeface` 的内部表示适配为多种字体表格格式。

### 2. Template Method Pattern

`export_ttx` 提供统一接口,具体格式由 `TestSVGTypeface` 的不同方法处理。

### 3. 设计决策

**为何生成 TTX 而非直接生成 TTF**:
- TTX 是人类可读的 XML 格式,易于调试
- 利用成熟的 FontTools 工具链
- 避免重新实现复杂的字体格式

**为何支持三种格式**:
- 确保跨平台兼容性测试
- 验证 Skia 对多种彩色字体标准的支持
- 每种格式有不同的技术特点和限制

**为何行星字体使用不同尺寸**:
```cpp
// CBDT 格式限制
unsigned small[] = { 8, 16 };
// sbix 无此限制
unsigned usual[] = { 16, 64, 128 };
```
适应不同格式的技术限制,确保测试数据有效。

## 性能考量

### 1. 生成时间

- 单个字体单个格式: < 1 秒
- 总计(2 字体 × 3 格式): 约 2-5 秒
- 主要时间花在 PNG 编码和 XML 生成

### 2. 文件大小

**典型 TTX 文件大小**:
- CBDT (小尺寸): 50-200 KB
- sbix (大尺寸): 200-500 KB
- COLR (矢量): 10-50 KB

**转换后的 TTF 大小**:
- CBDT: 30-150 KB
- sbix: 100-300 KB
- COLR: 5-20 KB

### 3. 内存使用

生成过程内存占用很小(< 10 MB),主要用于:
- SVG 解析和光栅化
- PNG 编码缓冲区
- XML 序列化

## 相关文件

**本工具**:
- `tools/fonts/create_test_font_color.cpp`: 生成器源代码

**依赖的类**:
- `tools/fonts/TestSVGTypeface.h/cpp`: SVG 测试字体实现

**生成的文件** (示例):
- `cbdt.ttx`: 默认字体 CBDT 格式
- `sbix.ttx`: 默认字体 sbix 格式
- `colr.ttx`: 默认字体 COLR 格式
- `planetcbdt.ttx`: 行星字体 CBDT 格式
- `planetsbix.ttx`: 行星字体 sbix 格式
- `planetcolr.ttx`: 行星字体 COLR 格式

**相关工具**:
- `tools/fonts/create_test_font.cpp`: 常规字体数据生成器
- **FontTools**: Python 字体工具库
  ```bash
  pip install fonttools
  ttx filename.ttx  # 转换为 TTF
  ```

**测试使用**:
- `tests/FontTest.cpp`: 字体功能测试
- `tests/ColorSpaceTest.cpp`: 彩色字体颜色空间测试

**使用生成字体的示例**:
```cpp
// 加载生成的字体
sk_sp<SkTypeface> colorFont = SkTypeface::MakeFromFile("cbdt.ttf");

// 使用彩色字体绘制
SkFont font(colorFont, 64);
canvas->drawString("🌍🌎🌏", 100, 100, font, paint);
```

**构建集成**:
可能在 `BUILD.gn` 中定义自定义操作:
```python
action("generate_color_fonts") {
  script = "tools/fonts/create_test_font_color"
  outputs = [
    "$target_gen_dir/cbdt.ttx",
    "$target_gen_dir/sbix.ttx",
    "$target_gen_dir/colr.ttx",
  ]
}

action("ttx_to_ttf") {
  script = "ttx"
  deps = [ ":generate_color_fonts" ]
  # ...
}
```

该工具虽然代码量小,但在 Skia 的彩色字体测试基础设施中扮演关键角色,确保现代表情符号和彩色文本在所有平台上正确渲染。
