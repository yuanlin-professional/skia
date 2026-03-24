# textapi_utils.js - CanvasKit 文本编辑器工具库

> 源文件: `demos.skia.org/demos/textedit/textapi_utils.js`

## 概述

一个功能完整的富文本编辑器工具库,基于 CanvasKit (Skia 的 WebAssembly 版本)实现。提供了文本光标、鼠标交互、文本选择、样式管理和段落布局等功能。这是 Skia 文本 API 的交互式演示。

## 架构位置

属于 Skia Web 演示层,展示了 CanvasKit ParagraphBuilder.ShapeText API 的实际应用场景。

## 主要类与结构体

- **`MakeCursor()`**: 创建光标对象,支持闪烁和路径选择高亮
- **`MakeMouse()`**: 鼠标状态跟踪器,记录按下/移动/释放位置
- **`MakeStyle(length)`**: 文本样式对象,支持字体、大小、颜色、粗体、斜体、波浪效果
- **`MakeEditor(text, style, cursor, width)`**: 完整的文本编辑器对象

## 公共 API 函数

编辑器核心方法:
- **`setIndex/setIndices`**: 设置光标位置或选择范围
- **`moveDX/moveDY`**: 水平/垂直移动光标
- **`insert(charcode)`**: 插入文本
- **`deleteSelection(direction)`**: 删除选中文本或前/后字符
- **`draw(canvas, shaders)`**: 渲染编辑器内容
- **`applyStyleToRange/applyStyleToSelection`**: 应用样式到文本范围

辅助函数:
- **`runs_x_to_index`**: 将 x 坐标转换为文本索引
- **`lines_pos_to_index`**: 将 (x,y) 位置转换为文本索引
- **`lines_indices_to_path`**: 为选择范围生成路径

## 内部实现细节

文本布局通过 `CanvasKit.ParagraphBuilder.ShapeText` 实现,返回按行组织的运行(run)数据,每个 run 包含字形、位置和偏移量。样式系统维护一个样式数组,每个样式关联一个文本长度。编辑操作需要同步更新文本内容和样式数组。绘制时将 run 和 style 范围的交集逐段绘制。

## 依赖关系

- CanvasKit WebAssembly 库
- CanvasKit.ParagraphBuilder.ShapeText API
- CanvasKit.Path, Paint, Font 等绑定

## 设计模式与设计决策

- 文本-样式分离: 文本内容和样式信息独立管理
- 懒重建: 仅在文本/样式变更后重新调用 ShapeText
- 选择即路径: 文本选择区域通过 SkPath 绘制

## 性能考量

- ShapeText 在每次文本变更时调用,避免不必要的重新布局
- 波浪效果通过逐字符位移实现,创建临时 Float32Array
- 光标闪烁使用时间戳检查而非定时器

## 相关文件

- `demos.skia.org/demos/textedit/spiralshader.js`
