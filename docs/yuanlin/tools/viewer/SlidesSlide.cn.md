# SlidesSlide 演示幻灯片集合

> 源文件: `tools/viewer/SlidesSlide.cpp`

## 概述

此文件实现了 Skia Viewer 中的 `SlidesSlide` 演示幻灯片，它是一个综合性的 Skia 绘图演示集合，包含三个独立的演示场景：路径特效（PathEffect）、渐变着色器（Gradient）和网格绘制（Mesh/Vertices）。用户可以通过点击切换不同的演示场景。此文件同时也是 Skia 各种 2D 绘图 API 的教学示例。

## 架构位置

- 所属模块：`tools/viewer/`（Skia Viewer 可视化工具）
- 角色：Viewer 中的一个 Slide 实现，展示 Skia 核心绘图功能
- 基类：`ClickHandlerSlide`（支持点击交互的 Slide 基类）

## 主要类与结构体

### `SlidesSlide`
- 继承自 `ClickHandlerSlide`
- 名称：`"Slides"`
- 通过 `fIndex` 在三个演示场景间切换
- `load()` 时预渲染所有场景为 PNG 文件
- `draw()` 时调用当前场景的绘制函数

### `GradData`
渐变数据结构体，包含颜色数组、位置数组和颜色数量，提供 `grad()` 方法生成 `SkGradient` 对象。

### `Rec`
顶点数据记录类，存储顶点模式、顶点坐标和纹理坐标。

### 函数类型定义
- `SlideProc`：`void (*)(SkCanvas*)` - 幻灯片绘制函数指针
- `PE_Proc`：`void (*)(SkPaint*)` - 路径特效设置函数指针
- `GradMaker`：渐变着色器创建函数指针

## 公共 API 函数

### 路径特效演示函数
| 函数 | 描述 |
|------|------|
| `compose_pe(paint)` | 添加 CornerPathEffect 组合效果 |
| `hair_pe(paint)` | 设置零宽度（hairline）描边 |
| `hair2_pe(paint)` | 零宽度描边 + 圆角组合 |
| `stroke_pe(paint)` | 12pt 描边 + 圆角组合 |
| `dash_pe(paint)` | 虚线效果 + 组合 |
| `one_d_pe(paint)` | 1D 路径效果（沿路径放置形状） |
| `fill_pe(paint)` | 纯填充（清除路径效果） |
| `discrete_pe(paint)` | 离散路径效果（抖动） |
| `tile_pe(paint)` | 2D 路径效果（平铺圆形） |

### 渐变演示函数
| 函数 | 描述 |
|------|------|
| `MakeLinear(pts, data, tm)` | 创建线性渐变着色器 |
| `MakeRadial(pts, data, tm)` | 创建径向渐变着色器 |
| `MakeSweep(pts, data, tm)` | 创建扫描渐变着色器 |
| `Make2Conical(pts, data, tm)` | 创建双锥形渐变着色器 |

### 网格演示函数
| 函数 | 描述 |
|------|------|
| `make_tris(rec)` | 生成随机三角形顶点 |
| `make_fan(rec, w, h)` | 生成三角形扇形顶点 |
| `make_strip(rec, w, h)` | 生成三角形条带顶点 |
| `make_shader0(size)` | 从图片创建纹理着色器 |
| `make_shader1(size)` | 创建线性渐变着色器 |

### 场景绘制函数
| 函数 | 描述 |
|------|------|
| `patheffect_slide(canvas)` | 绘制路径特效演示 |
| `gradient_slide(canvas)` | 绘制渐变着色器演示 |
| `mesh_slide(canvas)` | 绘制顶点/网格演示 |

## 内部实现细节

### 路径特效场景
- 使用 5 条折线路径展示不同的路径特效组合
- 同时在椭圆+内嵌矩形路径上展示填充、离散和平铺效果
- 路径特效通过 `MakeCompose` 组合多种效果

### 渐变场景
- 展示 5 种渐变数据配置 x 4 种渐变类型的矩阵
- 渐变数据包含 2-5 种颜色的组合，带或不带自定义位置
- 使用 `SkTileMode::kClamp` 作为标准平铺模式

### 网格场景
- 展示 3 种顶点模式：三角形、扇形、条带
- 每种模式分别用无着色器、纹理着色器、渐变着色器绘制
- 使用 `SkVertices::MakeCopy` 构建顶点对象

### 预渲染
`load()` 方法将所有场景预渲染为 1024x768 的 PNG 文件保存到 `/skimages/` 目录。

## 依赖关系

- Skia 核心：`SkCanvas`、`SkPaint`、`SkPath`、`SkVertices`、`SkShader`
- 路径特效：`Sk1DPathEffect`、`Sk2DPathEffect`、`SkCornerPathEffect`、`SkDashPathEffect`、`SkDiscretePathEffect`
- 渐变：`SkGradient`、`SkShaders::LinearGradient/RadialGradient/SweepGradient`
- Viewer 框架：`ClickHandlerSlide`
- 工具：`EncodeUtils`、`DecodeUtils`

## 设计模式与设计决策

- **函数指针表驱动**：通过 `gProc` 数组和函数指针实现场景切换，简洁高效
- **组合模式**：路径特效通过 `MakeCompose` 组合多种效果，展示 Skia 的效果组合能力
- **工厂函数模式**：渐变创建使用工厂函数数组，便于扩展新的渐变类型

## 性能考量

- 预渲染为 PNG 避免了运行时重复绘制所有场景的开销
- 路径特效的组合链增加了路径处理的复杂度
- 顶点绘制使用 `MakeCopy` 每帧复制数据，非性能最优但适合演示

## 相关文件

- `tools/viewer/ClickHandlerSlide.h` - 可点击 Slide 基类
- `tools/viewer/Slide.h` - Slide 基类
- `include/effects/` - 各种路径特效头文件
