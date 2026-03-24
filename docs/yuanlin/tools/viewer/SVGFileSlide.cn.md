# SVGFileSlide

> 源文件: `tools/viewer/SVGFileSlide.cpp`

## 概述

SVGFileSlide 是一个 SVG 文件渲染幻灯片，使用 Skia 的 SVG 模块（`SkSVGDOM`）加载和渲染 SVG 文件。仅在启用 `SK_ENABLE_SVG` 编译标志时可用。

## 架构位置

属于 `tools/viewer` 模块，是 Skia SVG 渲染能力的展示入口。通过工厂函数 `CreateSampleSVGFileSlide` 从文件路径创建。

## 主要类与结构体

### SVGFileSlide
- 继承自 `Slide`
- `fDom`: `SkSVGDOM` SVG 文档对象
- `fPath`: SVG 文件路径
- 名称格式: `[文件名]`

## 公共 API 函数

- `load(SkScalar w, SkScalar h)`: 从文件流解析 SVG DOM
- `draw(SkCanvas*)`: 调用 `fDom->render(canvas)` 渲染
- `resize(SkScalar w, SkScalar h)`: 更新容器尺寸

### 工厂函数
- `CreateSampleSVGFileSlide(const SkString& filename)`: 创建 SVGFileSlide 实例

## 内部实现细节

使用 `SkSVGDOM::Builder` 配置字体管理器（`TestFontMgr`）和文本塑形工厂（`SkShapers::BestAvailable()`），然后解析 SVG 文件流。容器尺寸跟随窗口大小变化。

## 依赖关系

- `modules/svg/include/SkSVGDOM.h`: SVG DOM 解析器
- `modules/skshaper/utils/FactoryHelpers.h`: 文本塑形工厂
- `src/utils/SkOSPath.h`: 文件路径工具

## 设计模式与设计决策

- **条件编译**: 整个文件包裹在 `SK_ENABLE_SVG` 条件中
- **工厂创建**: 使用独立工厂函数而非 `DEF_SLIDE` 宏，支持动态文件加载

## 性能考量

- SVG 解析在 `load` 时一次性完成
- 每帧调用 `render` 遍历 DOM 树

## 相关文件

- `modules/svg/include/SkSVGDOM.h`: SVG DOM 实现
- `tools/viewer/Slide.h`: Slide 基类
