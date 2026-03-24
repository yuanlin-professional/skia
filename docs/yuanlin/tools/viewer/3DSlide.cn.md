# 3D - 三维立方体交互演示

> 源文件: `tools/viewer/3DSlide.cpp`

## 概述

3DSlide.cpp 实现了多个 3D 交互演示：ThreeDSlide（基础3D相机）、CubeBaseSlide（可旋转立方体框架）、Bump3DSlide（法线贴图光照立方体）和 SkottieCubeSlide（Skottie动画纹理立方体）。使用 VSphere 虚拟球体实现直觉的旋转交互，RotateAnimator 提供带惯性衰减的旋转动画。

## 架构位置

位于 `tools/viewer/` 目录，属于 Skia Viewer 应用程序的演示/测试幻灯片集合。

## 主要类与结构体

VSphere - 虚拟球体数学（computeUnitV3/computeRotation）。RotateAnimator - 惯性旋转（指数衰减）。ThreeDSlide - 透视相机配置。Bump3DSlide - SkRuntimeEffect 着色器实现法线贴图光照。

## 公共 API 函数

继承 Slide 或 ClickHandlerSlide 接口：`load()`, `draw()`, `animate()`, `onChar()`, `onFindClickHandler()` 等。

## 内部实现细节

详见概述和主要类描述中的实现说明。

## 依赖关系

- `tools/viewer/Slide.h` 或 `tools/viewer/ClickHandlerSlide.h` - 基类
- Skia 核心绘图 API（SkCanvas, SkPaint, SkPath 等）
- 部分幻灯片依赖 GPU 特定功能或第三方库

## 设计模式与设计决策

- 遵循 Viewer 幻灯片框架，通过 DEF_SLIDE 宏注册
- 交互式幻灯片使用 ClickHandlerSlide 的命中测试和拖拽机制
- 动画幻灯片覆写 animate() 方法实现基于时间的更新

## 性能考量

各幻灯片侧重于特定 Skia 功能的展示和测试，部分专门用于压力测试（如 MegaStroke、ManyRects、Chart）。

## 相关文件

- `tools/viewer/Slide.h` - Slide 基类定义
- `tools/viewer/ClickHandlerSlide.h` - 可交互幻灯片基类
