# skparagraph/gm - 段落排版 Golden Master 测试

## 概述

`gm/` 目录包含 skparagraph 模块的 Golden Master (GM) 测试。GM 测试是 Skia 的视觉回归测试机制,通过生成参考图像并与后续运行结果进行像素级比对,确保段落排版和渲染的视觉正确性不会在代码变更中退化。

GM 测试与单元测试互补:单元测试验证 API 行为的逻辑正确性,而 GM 测试验证最终渲染输出的视觉正确性。这对于文本排版尤为重要,因为微小的度量变化可能导致可见的视觉差异,例如行间距变化、基线偏移或字形位置微调。

文本渲染的视觉正确性验证比数值验证更为直观和全面。一个像素级别的渲染比对可以同时捕获字体度量、字形选择、装饰绘制、颜色混合等多个维度的问题。

## 架构图

```
+-------------------------------------------+
|           Skia GM 测试框架                 |
|  (skiagm::GM 基类 / DM 测试驱动)          |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|          simple_gm.cpp (测试实现)          |
|  onOnceBeforeDraw() | onDraw(SkCanvas*)   |
+-------------------+-----------------------+
                    |
                    v
+-------------------------------------------+
|       段落排版 + 渲染管线                   |
|  ParagraphBuilder -> Paragraph -> Canvas   |
+-------------------------------------------+
                    |
                    v
+-------------------------------------------+
|           Gold 图像比对服务                 |
|  参考图像存储 | 像素级比对 | 差异报告      |
+-------------------------------------------+
```

## 目录结构

```
gm/
|-- BUILD.bazel          # Bazel 构建规则
|-- simple_gm.cpp        # 简单段落渲染GM测试
```

## 关键类与函数

### simple_gm.cpp

该文件注册了基本的段落渲染 GM 测试:

- 创建简单的段落文本并进行排版和绘制
- 验证基本的文本对齐、样式渲染、换行等功能的视觉输出
- 使用 Skia 的 GM 框架(`skiagm::GM`)自动管理测试生命周期

```cpp
// 典型 GM 测试流程:
// 1. 创建 FontCollection 和 ParagraphBuilder
// 2. 添加文本和样式(字体、颜色、装饰等)
// 3. Build() 构建段落对象
// 4. layout(width) 执行排版
// 5. paint(canvas, x, y) 绘制到 GM 画布
// 6. GM 框架自动捕获画布内容并与参考图像比对
```

### 测试覆盖的视觉特性

| 视觉特性 | 验证内容 |
|----------|----------|
| 字形渲染 | 字形的正确选择和位置 |
| 行布局 | 行高、行间距、基线对齐 |
| 文本对齐 | 左/右/居中/两端对齐的视觉效果 |
| 装饰线 | 下划线、删除线的位置和样式 |
| 背景色 | 文本背景矩形的绘制 |
| 阴影 | 文本阴影的模糊和偏移 |

## 依赖关系

```
gm/
  |-- modules/skparagraph/include/ (Paragraph, ParagraphBuilder等)
  |-- Skia GM 框架 (gm/gm.h)
  |-- SkCanvas (绘制目标)
  |-- modules/skshaper/ (文本整形)
  |-- modules/skunicode/ (Unicode支持)
  |-- resources/ (测试字体)
```

## 设计模式分析

GM 测试采用 Skia 的标准 GM 框架模式:
- 继承 `skiagm::GM` 基类
- 重写 `onDraw(SkCanvas*)` 方法执行绘制
- 框架自动捕获画布内容并与参考图像比对

### 参考图像管理
- 参考图像存储在 Skia 的 Gold (图像比对服务) 中
- 每次提交时 CI 自动运行 GM 测试并上传结果
- 视觉差异需要人工审核确认(triage)
- 确认后的新图像成为新的参考基准

### 确定性保障
GM 测试使用 `TestFontCollection` 或内置测试字体,确保在不同平台上产生一致的渲染结果。避免使用系统字体以消除平台差异。

## 数据流

```
DM (Skia 测试驱动)
  |
  +-- 枚举所有注册的 GM 测试
  +-- 为每个 GM 创建渲染目标 (SkSurface: GPU 或 CPU)
  |
  +-- simple_gm::onDraw(canvas)
  |     |-- 创建 FontCollection (测试字体)
  |     |-- 创建 ParagraphBuilder
  |     |-- 配置样式, 添加文本
  |     |-- Build() -> Paragraph
  |     |-- layout(width)
  |     |-- paint(canvas, x, y)
  |
  +-- 框架捕获画布像素 -> PNG 图像
  +-- 上传到 Gold 服务
  +-- 与参考图像 (gold.skia.org) 比对
  +-- 报告差异(如有)
```

## 相关文档与参考

- **Skia GM 框架**: `gm/gm.h` - GM 测试基类
- **Skia Gold**: https://gold.skia.org - 视觉测试比对服务
- **DM 测试驱动**: `dm/` - Skia 的测试执行器
- **单元测试**: `modules/skparagraph/tests/` - API 逻辑测试
- **演示**: `modules/skparagraph/slides/` - 交互式段落演示
