# CowboySlide 牛仔 SVG 动画演示

> 源文件: `tools/viewer/CowboySlide.cpp`

## 概述

此文件实现了 Skia Viewer 中的 `AnimatedSVGSlide` 演示，加载并动画展示一个牛仔（Cowboy）SVG 资源文件。该 Slide 演示了 Skia SVG 模块的渲染和动画能力，通过循环播放缩放进入、水平滚动和缩放退出三种动画状态来展示 SVG 在不同变换条件下的渲染效果。整个实现依赖 `SK_ENABLE_SVG` 编译标志。

## 架构位置

- 所属模块：`tools/viewer/`（Skia Viewer 工具）
- 角色：SVG 渲染和动画演示 Slide
- 编译条件：`SK_ENABLE_SVG`（需要启用 SVG 模块）

## 主要类与结构体

### `AnimatedSVGSlide`
- 继承自 `Slide`
- 名称：`"SampleCowboy"`

**状态枚举：**
- `kZoomIn`：缩放进入状态
- `kScroll`：水平滚动状态
- `kZoomOut`：缩放退出状态

**核心字段：**
- `fDom`：`sk_sp<SkSVGDOM>` SVG DOM 对象
- `fResource`：SVG 资源文件路径（`"Cowboy.svg"`）
- `fState`：当前动画状态
- `fAnimationLoop`：动画循环计数器（每状态 5 次迭代）
- `fDelta`：动画参数增量值

## 公共 API 函数

| 方法 | 描述 |
|------|------|
| `load(w, h)` | 加载 SVG 资源并创建 DOM 对象 |
| `draw(canvas)` | 根据当前动画状态绘制 SVG |
| `resize(w, h)` | 更新 SVG 容器大小 |
| `animate(nanos)` | 推进动画状态机 |

## 内部实现细节

### SVG 加载
- 使用 `GetResourceAsData` 从 Skia 资源目录加载 SVG 数据
- 通过 `SkSVGDOM::Builder` 构建 SVG DOM，配置字体管理器和文本 shaping 工厂
- 使用 `ToolUtils::TestFontMgr()` 和 `SkShapers::BestAvailable()` 确保 SVG 文本正确渲染

### 动画状态机
- **kZoomIn**：delta 从 1 递增 0.2，应用为均匀缩放
- **kScroll**：delta 作为水平偏移量，前半段向右（+80）后半段向左（-80）
- **kZoomOut**：delta 从 2 递增 0.2，应用为均匀缩放
- 每个状态持续 5 帧（`kAnimationIterations`），然后切换到下一个状态

### 画布变换
- 基础缩放 3x 并裁剪到 400x400 区域
- 在此基础上叠加动画状态的变换

## 依赖关系

- Skia SVG 模块：`SkSVGDOM`、`SkSVGNode`
- Skia 核心：`SkCanvas`、`SkRect`、`SkStream`
- 文本处理：`SkShapers::BestAvailable()`（skshaper 模块）
- 资源系统：`tools/Resources.h`
- 编译条件：`SK_ENABLE_SVG`

## 设计模式与设计决策

- **状态机模式**：使用枚举和计数器实现简单的动画状态机
- **条件编译**：整个文件包裹在 `#if defined(SK_ENABLE_SVG)` 中，仅在 SVG 模块可用时编译
- **Builder 模式**：SVG DOM 的创建使用 Builder 模式配置多个参数

## 性能考量

- 每帧重新渲染整个 SVG DOM，对复杂 SVG 可能有性能影响
- 3x 基础缩放增加了渲染面积，测试 SVG 在放大条件下的质量和性能
- 动画状态的快速变换测试 Skia 矩阵变换的效率
- kScroll 状态中 delta 的大幅变化可能触发大范围的重绘

## 相关文件

- `modules/svg/include/SkSVGDOM.h` - SVG DOM 接口
- `modules/skshaper/` - 文本 shaping 模块
- `resources/Cowboy.svg` - SVG 资源文件
- `tools/viewer/Slide.h` - Slide 基类
