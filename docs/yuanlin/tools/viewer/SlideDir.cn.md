# SlideDir - 幻灯片目录浏览器

> 源文件:
> - [tools/viewer/SlideDir.h](../../../tools/viewer/SlideDir.h)
> - [tools/viewer/SlideDir.cpp](../../../tools/viewer/SlideDir.cpp)

## 概述

SlideDir 是 Skia Viewer 中的幻灯片目录浏览组件，以网格布局展示多个 Slide 的缩略图。支持鼠标交互选择和焦点控制，使用 sksg（Skia Scene Graph）进行动画和场景管理。默认 4 列网格布局。

## 架构位置

位于 `tools/viewer/` 目录下，是 Viewer 应用的 UI 组件。继承 Slide 基类，组合管理多个子 Slide，实现类似文件浏览器的网格视图。

## 主要类与结构体

### `SlideDir`
继承 `Slide`，管理子 Slide 的网格展示。
- `fSlides` - 子 Slide 数组
- `fFocusController` - 焦点控制器（选中放大）
- `fColumns` - 列数
- `fRecs` - 每个 Slide 的布局记录
- `fScene` / `fRoot` - sksg 场景图

### `Rec`（内部）
单个 Slide 的布局记录。

### `FocusController`（内部）
管理 Slide 选中和焦点动画。

### `Animator`（内部）
sksg 动画控制器。

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `SlideDir(name, slides, columns)` | 构造网格目录 |
| `load/unload(winWidth, winHeight)` | 加载/卸载子 Slide |
| `draw(SkCanvas*)` | 绘制网格视图 |
| `animate(double)` | 更新动画 |
| `onChar/onMouse(...)` | 处理交互输入 |

## 内部实现细节

- 使用 sksg::Scene 管理渲染树。
- 鼠标事件通过 `findCell()` 定位到网格单元格。
- 焦点控制器管理选中 Slide 的放大/缩小动画。

## 依赖关系

- **Skia 核心**：SkCanvas、SkPoint、SkSize
- **sksg 模块**：Scene、Group
- **Viewer**：Slide 基类、TimeUtils

## 设计模式与设计决策

- **组合模式**：SlideDir 本身是 Slide，同时包含多个子 Slide。
- **场景图驱动**：使用 sksg 管理变换和动画。

## 性能考量

- 仅绘制可见区域的缩略图。
- 动画通过 sksg::Scene 统一调度。

## 相关文件

- `tools/viewer/Slide.h` - Slide 基类
- `modules/sksg/` - Skia Scene Graph 模块
