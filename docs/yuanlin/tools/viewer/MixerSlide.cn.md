# MixerSlide 颜色滤镜混合演示

> 源文件: `tools/viewer/MixerSlide.cpp`

## 概述

此文件实现了 Skia Viewer 中的 `MixerSlide` 演示，展示了 `SkColorFilters::Lerp` 颜色滤镜线性插值功能。它将两个颜色滤镜（灰度矩阵滤镜和绿色 Screen 混合滤镜）以可变权重进行混合，通过动画效果直观展示插值过程。每行显示三张图片：原始滤镜效果、插值结果和目标滤镜效果，混合权重在 0 和 1 之间自动振荡。

## 架构位置

- 所属模块：`tools/viewer/`（Skia Viewer 工具）
- 角色：颜色滤镜 API 的交互式演示
- 基类：`ClickHandlerSlide`

## 主要类与结构体

### `MixerSlide`
- 继承自 `ClickHandlerSlide`
- 名称：`"Mixer"`

**核心字段：**
- `fImg`：测试图片（mandrill_256.png）
- `fCF0`：灰度矩阵颜色滤镜
- `fCF1`：绿色 Screen 混合颜色滤镜
- `fWeight`：当前插值权重（0 到 1）
- `fDW`：权重变化步长（0.02）
- `fRect`：可拖拽区域

### 全局灰度矩阵 `gMat`
5x4 颜色变换矩阵，将 RGB 映射为灰度值（0.3R + 0.6G + 0.1B），Alpha 保持不变。

## 公共 API 函数

| 方法 | 描述 |
|------|------|
| `draw(canvas)` | 绘制三行颜色滤镜混合对比图 |
| `onFindClickHandler(x, y, modi)` | 检测是否点击在拖拽区域内 |
| `onClick(click)` | 处理拖拽偏移 |

### 私有方法
| 方法 | 描述 |
|------|------|
| `dodraw(canvas, cf0, cf1, gap)` | 绘制一行：原始、混合、目标三张图片 |

## 内部实现细节

### 颜色滤镜配置
- `fCF0`：灰度矩阵滤镜，使用标准亮度系数（0.3, 0.6, 0.1）
- `fCF1`：`SkColorFilters::Blend(0xFF44CC88, SkBlendMode::kScreen)`，绿色调 Screen 混合

### 绘制布局
三行展示，每行三张图片：
1. 第一行：nullptr -> fCF1（展示从无滤镜到绿色滤镜的过渡）
2. 第二行：fCF0 -> nullptr（展示从灰度到无滤镜的过渡）
3. 第三行：fCF0 -> fCF1（展示从灰度到绿色的过渡）

### 动画机制
- `fWeight` 在 0 和 1 之间以 0.02 步长振荡
- 中间图片的水平位置随 `fWeight` 线性移动，产生滑动效果
- 使用 `SkColorFilters::Lerp(fWeight, cf0, cf1)` 计算混合滤镜

### 延迟初始化
资源（图片和滤镜）在首次 `draw()` 调用时初始化，而非构造函数中。

## 依赖关系

- Skia 核心：`SkCanvas`、`SkImage`、`SkPaint`、`SkColorFilter`、`SkShader`
- 颜色滤镜：`SkColorFilters::Matrix`、`SkColorFilters::Blend`、`SkColorFilters::Lerp`
- 渐变：`SkGradient`
- 工具：`DecodeUtils`、`Resources`
- Viewer 框架：`ClickHandlerSlide`

## 设计模式与设计决策

- **延迟初始化**：资源在首次使用时加载，避免构造函数中的文件 I/O
- **动画振荡**：简单的权重反弹机制（`fDW = -fDW`）产生来回过渡效果
- **对比展示**：三列布局（原始-混合-目标）提供直观的视觉对比

## 性能考量

- 每帧绘制 9 张图片（3 行 x 3 列），对图片绘制性能有一定要求
- `SkColorFilters::Lerp` 在每帧以新权重创建新的颜色滤镜对象
- 使用 `SkSamplingOptions()` 默认采样，不会启用高质量缩放
- 图片固定为 256x256（mandrill），渲染负载适中

## 相关文件

- `include/core/SkColorFilter.h` - 颜色滤镜 API
- `resources/images/mandrill_256.png` - 测试图片
- `tools/viewer/ClickHandlerSlide.h` - Slide 基类
