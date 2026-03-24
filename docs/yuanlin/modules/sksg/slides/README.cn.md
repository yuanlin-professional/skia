# sksg/slides - 演示幻灯片

## 概述

`slides/` 目录包含基于 SkSG 构建的演示程序。这些演示程序展示了 SkSG 场景图作为独立渲染框架的能力,不依赖 Skottie 或 Lottie 格式。

## 目录结构

```
slides/
├── BUILD.bazel          # Bazel 构建配置
└── SVGPongSlide.cpp     # SVG Pong 游戏演示
```

## 关键文件

### SVGPongSlide.cpp

一个使用 SkSG 场景图实现的简单 Pong (乒乓) 游戏演示。该示例展示了:

1. **场景构建**: 使用 SkSG 节点构建游戏画面
   - `sksg::Rect` 用于球拍和球
   - `sksg::Color` 用于颜色
   - `sksg::Draw` 组合几何体和画笔
   - `sksg::Group` 组织场景结构
   - `sksg::TransformEffect` 实现移动

2. **动画更新**: 通过修改节点属性驱动游戏逻辑
   - 修改 `Rect` 的位置属性
   - 修改 `Transform` 的矩阵
   - 调用 `Scene::revalidate()` 更新
   - 调用 `Scene::render()` 渲染帧

3. **交互处理**: 响应用户输入控制球拍移动

该演示是 SkSG 作为通用保留模式渲染框架的良好实践参考,展示了如何在不使用 Lottie/Skottie 的情况下直接操作场景图节点。

## 依赖关系

```
slides/
  ├── sksg/include (Node, Group, Rect, Draw, Color, TransformEffect, Scene)
  ├── Skia Slide 框架
  └── include/core (SkCanvas)
```

## 相关文档与参考

- **sksg 主文档**: `docs/yuanlin/modules/sksg/README.md`
- **sksg 节点类型**: `docs/yuanlin/modules/sksg/include/README.md`
