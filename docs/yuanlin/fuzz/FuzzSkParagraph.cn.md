# SkParagraph 模糊测试

> 源文件: `fuzz/FuzzSkParagraph.cpp`

## 概述

此文件对 Skia 的 SkParagraph 文本排版模块进行模糊测试。它随机生成段落样式、文本内容（ASCII、Unicode、Zalgo 组合字符）并执行布局和绘制，以发现文本处理中的崩溃和异常。

## 架构位置

位于模糊测试框架 (`fuzz/`) 中，针对 `modules/skparagraph/` 模块。

## 主要类与结构体

### `ResourceFontCollection`
- 继承自 `FontCollection`，从资源目录加载字体
- 使用 `TypefaceFontProvider` 注册字体

## 公共 API 函数

- `DEF_FUZZ(SkParagraph, fuzz)` - 构建随机段落并排版绘制

### 辅助函数
- `AddASCIIText` - 添加随机 ASCII 文本
- `AddUnicodeText` - 添加随机 Unicode 文本
- `AddZalgoText` - 添加 Zalgo（叠加组合字符）文本
- `AddStyle` / `RemoveStyle` - 添加/移除文本样式
- `BuildParagraphStyle` - 构建随机段落样式

## 内部实现细节

- 最大文本长度 255 字节，最多 4 次文本添加
- Canvas 大小 250x250
- Zalgo 文本使用上方、中间、下方三组 Unicode 组合字符
- 段落样式随机化：文本方向、对齐、最大行数、省略号、行高等
- 使用 HarfBuzz 进行文本塑形

## 依赖关系

- `modules/skparagraph/` - SkParagraph 模块
- `modules/skshaper/` - 文本塑形器
- `tools/Resources.h` - 字体资源

## 设计模式与设计决策

**分层随机化**：样式和文本内容分别随机化，组合产生更多覆盖路径。

## 性能考量

Canvas 和文本大小受限以保持模糊测试吞吐量。

## 相关文件

- `modules/skparagraph/` - SkParagraph 模块源码
