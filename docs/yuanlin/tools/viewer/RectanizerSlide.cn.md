# RectanizerSlide

> 源文件: `tools/viewer/RectanizerSlide.cpp`

## 概述

RectanizerSlide 是一个矩形装箱（bin packing）算法可视化工具，展示 GPU 纹理图集中 `RectanizerPow2` 和 `RectanizerSkyline` 两种矩形打包策略的实时填充过程。仅在 Ganesh 或 Graphite 编译模式下可用。

## 架构位置

属于 `tools/viewer` 模块，可视化 `src/gpu/Rectanizer*.h` 中定义的 GPU 纹理图集打包算法。

## 主要类与结构体

### RectanizerSlide
- 继承自 `Slide`
- 预生成三组各 200 个矩形:
  - `Rand`: 2-256 随机尺寸
  - `Pow2Rand`: 2-256 的 2 幂次尺寸
  - `SmallPow2`: 固定 128x128
- 两种打包器: `RectanizerPow2`, `RectanizerSkyline`

## 公共 API 函数

- `onChar(SkUnichar)`: 'j' 切换打包器，'h' 切换矩形集
- `draw(SkCanvas*)`: 逐帧添加矩形并可视化

## 内部实现细节

每帧尝试添加一个矩形到当前打包器（1024x1024 画布），显示已放置矩形（红色填充+黑色边框）。统计信息包括总面积、填充率、矩形数量。切换打包器或矩形集时自动重置。

## 依赖关系

- `src/gpu/RectanizerPow2.h`: 2 幂次打包器
- `src/gpu/RectanizerSkyline.h`: 天际线打包器

## 设计模式与设计决策

- **逐帧渐进**: 每帧添加一个矩形，动态展示打包过程
- **对比测试**: 三种输入集 x 两种算法的全覆盖

## 性能考量

- 天际线算法通常比 Pow2 算法有更高的填充率

## 相关文件

- `src/gpu/RectanizerPow2.h/cpp`: Pow2 实现
- `src/gpu/RectanizerSkyline.h/cpp`: Skyline 实现
