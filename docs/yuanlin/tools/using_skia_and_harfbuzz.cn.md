# using_skia_and_harfbuzz - Skia + HarfBuzz PDF 生成示例

> 源文件: `tools/using_skia_and_harfbuzz.cpp`

## 概述

`using_skia_and_harfbuzz` 是一个示例程序,演示如何结合 Skia 和 HarfBuzz 将 stdin 的 UTF-8 文本转换为 PDF 文件。它使用 SkShaper (HarfBuzz 后端) 进行文本排版,SkPDF 生成 PDF 输出,支持自定义字体、页面尺寸、边距等参数。

## 架构位置

属于 Skia 示例和演示工具,展示 Skia 文本渲染和 PDF 生成的集成用法。

## 主要类与结构体

- **`BaseOption`/`Option<T>`**: 模板化的命令行选项系统
- **`DoubleOption`/`StringOption`**: double 和 string 类型的选项实现
- **`Config`**: 程序配置(页面尺寸、字体、边距、行间距等)
- **`Placement`**: 管理文本在 PDF 页面上的布局和渲染

## 公共 API 函数

- **`main()`**: 解析配置、创建 PDF、逐行排版写入
- **`Placement::WriteLine()`**: 使用 SkShaper 排版一行文本并渲染到 PDF
- **`MakePDFDocument()`**: 创建带元数据的 PDF 文档

## 内部实现细节

- 使用 `SkShapers::HB::ShaperDrivenWrapper` 进行 HarfBuzz 文本整形
- 支持双向文本(BiDi)、脚本检测和语言检测
- 自动分页: 当文本超出页面高度时创建新页面
- 支持 ICU Unicode 实现

## 依赖关系

- HarfBuzz - 文本整形引擎
- SkShaper 模块 - Skia 文本整形接口
- SkUnicode (ICU) - Unicode 支持
- SkPDF - PDF 生成

## 设计模式与设计决策

- **模块化选项系统**: 通过模板类实现类型安全的命令行解析
- **流式处理**: 逐行读取 stdin 并渲染,支持任意长度输入

## 性能考量

文本排版是主要开销。PDF 页面按需创建,避免预分配。

## 相关文件

- `modules/skshaper/` - SkShaper 模块
- `include/docs/SkPDFDocument.h` - PDF 文档接口
