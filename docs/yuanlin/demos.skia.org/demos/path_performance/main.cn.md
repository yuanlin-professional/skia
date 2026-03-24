# main.js - 路径性能测试主线程

> 源文件: `demos.skia.org/demos/path_performance/main.js`

## 概述

路径渲染性能对比演示的主线程控制逻辑,支持 SVG、Path2D 和 CanvasKit 三种渲染方法的切换和帧率监控。SVG 渲染在主线程执行,其余两种在 Worker 线程执行。

## 架构位置

路径性能演示的主控制层。

## 公共 API 函数

- **`svgToPathStringAndFillColorPairs()`**: 从 SVG DOM 提取路径和颜色数据
- **`fpsFromFramesInfo()`**: 计算平均帧率
- **`switchRenderMethodCallback()`**: 生成渲染方法切换回调函数

## 内部实现细节

加载 SVG 后提取所有 `<path>` 元素的 `d` 和 `fill` 属性,将数据分发给 Worker。SVG 渲染通过 CSS transform 实现动画,Path2D 和 CanvasKit 通过 OffscreenCanvas 在 Worker 中渲染。

## 依赖关系

- worker.js, shared.js

## 设计模式与设计决策

三种渲染方法使用统一的性能测量机制,便于公平对比。

## 性能考量

SVG 渲染受限于主线程,Path2D 和 CanvasKit 在 Worker 中不受主线程影响。

## 相关文件

- `demos.skia.org/demos/path_performance/worker.js`, `shared.js`
