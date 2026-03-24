# test_pdfs - PDF 渲染比较测试工具

> 源文件: `tools/test_pdfs.py`

## 概述

`test_pdfs.py` 将 SKP 文件渲染为 PDF,然后与预期的 PDF 文件进行比较。支持处理单个文件或目录,可指定渲染和 diff 输出目录。

## 架构位置

属于 Skia 的 PDF 渲染质量验证工具链。

## 公共 API 函数

- **`Main(args)`**: 解析参数并调用 `test_rendering.TestRenderSkps()`

## 内部实现细节

- 使用 `render_pdfs` 工具将 SKP 渲染为 PDF
- 通过 `test_rendering` 模块比较输出与预期

## 依赖关系

- `test_rendering` 模块
- `render_pdfs` 二进制工具

## 性能考量

依赖外部渲染工具,性能取决于 SKP 复杂度。

## 相关文件

- `tools/test_rendering.py` - 渲染比较框架
