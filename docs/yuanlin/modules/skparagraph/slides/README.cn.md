# skparagraph/slides - 段落排版交互式演示

## 概述

`slides/` 目录包含 skparagraph 模块的交互式演示代码。这些幻灯片(Slide)通过 Skia 的 Viewer 应用程序运行,提供了段落排版各种功能的实时可视化展示。开发者可以通过这些演示直观地观察和调试文本排版行为。

幻灯片展示了 skparagraph 模块的丰富功能,包括多样式文本、双向文本、字体回退、占位符、文本装饰、对齐模式、省略号处理等。这些演示同时也是功能验证的重要辅助工具。

交互式演示对于文本排版引擎的开发尤其有价值,因为很多排版问题(如字体回退视觉效果、BiDi 文本方向、装饰线位置)需要通过视觉观察才能有效判断正确性。

## 架构图

```
+-------------------------------------------+
|           Skia Viewer 应用                 |
|  (tools/viewer/Viewer.cpp)                |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|         ParagraphSlide (幻灯片)            |
|  draw(SkCanvas*) | 交互事件处理            |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|           段落排版管线                      |
|  ParagraphBuilder -> Paragraph            |
|  layout -> paint -> 查询API可视化          |
+-------------------------------------------+
```

## 目录结构

```
slides/
|-- BUILD.bazel              # Bazel 构建规则
|-- ParagraphSlide.cpp       # 段落功能演示幻灯片集合
```

## 关键类与函数

### ParagraphSlide.cpp

该文件包含多个段落排版演示场景,每个场景展示特定的排版功能:

| 演示类别 | 展示内容 |
|----------|----------|
| 基础排版 | 简单文本的布局和渲染 |
| 多样式文本 | 不同字体、颜色、大小的混合排版 |
| 文本装饰 | 下划线、上划线、删除线(实线/虚线/波浪线) |
| 双向文本 | LTR/RTL 混合文本的正确排版 |
| 文本对齐 | 左对齐/右对齐/居中/两端对齐 |
| 省略号 | 超出最大行数时的省略号截断 |
| 占位符 | 行内占位符(inline widget)的排版 |
| 字体回退 | 缺失字形的自动字体回退 |
| 选区高亮 | getRectsForRange 返回的选区矩形可视化 |
| 命中测试 | getGlyphPositionAtCoordinate 的鼠标命中测试 |
| 支柱样式 | StrutStyle 对行高的影响 |
| 阴影效果 | TextShadow 的视觉展示 |

### 典型幻灯片结构

```cpp
class ParagraphXxxSlide : public Slide {
    void draw(SkCanvas* canvas) override {
        // 1. 创建 FontCollection 和 ParagraphBuilder
        // 2. 配置 ParagraphStyle (对齐/方向/最大行数)
        // 3. 配置 TextStyle (字体/颜色/装饰)
        // 4. 添加文本: pushStyle -> addText -> pop
        // 5. Build() 并 layout(width)
        // 6. paint(canvas, x, y)
        // 7. (可选) 绘制辅助信息:
        //    - 选区高亮框 (getRectsForRange)
        //    - 基线参考线
        //    - 行边界标注
        //    - 光标位置指示
    }
};
```

### 交互功能

部分幻灯片支持用户交互:
- **鼠标点击**: 触发命中测试,显示点击位置对应的字符索引
- **鼠标拖拽**: 模拟文本选择,可视化选区矩形
- **键盘输入**: 动态修改文本内容,观察重新排版效果
- **滑块控制**: 调整排版宽度、字体大小等参数

## 依赖关系

```
slides/
  |-- modules/skparagraph/include/ (完整段落API)
  |-- Skia Viewer 框架 (tools/viewer/Slide.h)
  |-- SkCanvas (绘制目标)
  |-- SkPaint (辅助绘制)
  |-- modules/skshaper/ (文本整形)
  |-- modules/skunicode/ (Unicode支持)
  |-- resources/ (测试字体资源)
```

## 设计模式分析

幻灯片采用 Skia Viewer 的 `Slide` 框架:
- 每个幻灯片是一个 `Slide` 子类
- 通过 `draw(SkCanvas*)` 渲染内容
- 通过 `onMouse()` / `onKey()` 处理用户交互
- Viewer 应用提供幻灯片切换和参数调整 UI

### 实时渲染循环
Viewer 应用使用 GPU 加速渲染,每帧调用 `draw()`,允许实时观察排版参数变化的效果。这种即时反馈对于调试排版问题非常高效。

## 数据流

```
Skia Viewer 应用
  |
  +-- 启动: 注册所有 ParagraphSlide
  +-- 用户选择幻灯片
  |
  +-- 渲染循环 (每帧):
  |   +-- draw(canvas)
  |   |     |
  |   |     +-- 创建段落 (或复用已创建的段落)
  |   |     +-- layout(width) (宽度可能受用户控制)
  |   |     +-- paint(canvas, x, y)
  |   |     +-- 绘制辅助可视化信息
  |   |
  |   +-- 处理用户交互事件
  |   +-- (如有变化) 标记重新绘制
  |
  +-- 用户切换到下一个幻灯片
```

## 相关文档与参考

- **Viewer 应用**: `tools/viewer/` - Skia 的交互式查看器
- **Slide 基类**: `tools/viewer/Slide.h` - 幻灯片接口定义
- **运行方式**: 编译 viewer 后使用 `--slide ParagraphXxx` 参数选择幻灯片
- **GM 测试**: `modules/skparagraph/gm/` - 自动化视觉测试
- **单元测试**: `modules/skparagraph/tests/` - API 功能测试
