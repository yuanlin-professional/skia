# ImageFilterDAGSlide - 图像滤镜 DAG 可视化幻灯片

> 源文件: `tools/viewer/ImageFilterDAGSlide.cpp`

## 概述

ImageFilterDAGSlide.cpp 实现了一个可视化工具，将 Skia 图像滤镜的有向无环图（DAG）以树形结构渲染到画布上。每个节点显示滤镜的实际渲染结果、输入/输出边界框（红/绿/蓝色框线）以及层尺寸信息，帮助开发者理解和调试复杂的图像滤镜管线。

## 架构位置

位于 `tools/viewer/` 目录，属于 Viewer 的开发调试工具幻灯片。

## 主要类与结构体

### `FilterNode`
表示 DAG 中的一个节点。存储滤镜指针、输入子节点列表、深度、内容矩形、映射矩阵，以及缓存的未提示/提示层边界和输出边界。

### `ImageFilterDAGSlide`
构建一个多层 DAG（Merge <- ColorFilter/Blur <- Blur/DropShadow/Offset），调用 `draw_dag` 可视化。

## 公共 API 函数

继承 Slide 接口。`getDimensions()` 返回与滤镜内容匹配的尺寸。

## 内部实现细节

- 使用 `skif::Mapping::decomposeCTM` 分解变换矩阵
- 区分三种边界：hinted（红色，使用内容提示）、unhinted（绿色，无提示）、output（蓝色）
- 递归绘制 DAG 树，每个节点在独立 Surface 上渲染
- 显示 Param->Layer 和 Layer->Device 变换矩阵

## 依赖关系

- `src/core/SkImageFilter_Base.h` - 滤镜内部 API
- `src/core/SkSpecialImage.h` - 特殊图像
- `include/effects/SkImageFilters.h` - 标准滤镜集

## 设计模式与设计决策

- **递归可视化**: 树形结构自然映射为递归渲染
- **调试优先**: 为图像滤镜开发者提供内部状态的直观展示

## 性能考量

每个节点创建独立 Surface 并渲染，仅用于调试目的。

## 相关文件

- `src/core/SkImageFilter_Base.h` - 图像滤镜内部实现
