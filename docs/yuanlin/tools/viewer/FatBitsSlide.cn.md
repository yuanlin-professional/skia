# FatBitsSlide 像素放大镜演示

> 源文件: `tools/viewer/FatBitsSlide.cpp`

## 概述

此文件实现了 Skia Viewer 中的 `FatBits`（胖像素）演示工具，它是一个像素级别的渲染可视化器。通过高倍放大（默认 64 倍）显示 Skia 绘制的单个像素，使用户能够直观地观察抗锯齿算法、描边宽度、像素对齐和裁剪等底层渲染行为。这是 Skia 开发者调试和验证栅格化算法的重要工具。

## 架构位置

- 所属模块：`tools/viewer/`（Skia Viewer 工具）
- 角色：像素级渲染调试和可视化工具
- 基类：`ClickHandlerSlide`（支持拖拽交互）

## 主要类与结构体

### `FatBits`
核心渲染引擎类，执行像素级放大绘制。

**核心字段：**
- `fAA`：抗锯齿开关
- `fStyle`：描边风格（hairline / stroke）
- `fGrid`：像素网格对齐开关
- `fShowSkeleton`：线框骨架显示开关
- `fUseClip`：裁剪区域开关
- `fRectAsOval`：矩形作为椭圆绘制
- `fUseTriangle`：三角形模式
- `fStrokeCap`：描边端点样式
- `fStrokeWidth`：描边宽度
- `fZoom`：放大倍数
- `fMinSurface` / `fMaxSurface`：原始尺寸和放大尺寸的离屏 Surface
- `fShader0` / `fShader1`：棋盘格/白色背景着色器

### `IndexClick`
自定义 Click 类，携带被拖拽控制点的索引。

### `DrawLineSlide`
- 继承自 `ClickHandlerSlide`
- 名称：`"FatBits"`
- 默认放大倍数 64x，画布尺寸 48x32 像素
- 3 个可拖拽控制点
- 支持丰富的键盘快捷键交互

## 公共 API 函数

### FatBits 方法
| 方法 | 描述 |
|------|------|
| `setWHZ(w, h, zoom)` | 设置画布尺寸和放大倍数 |
| `drawBG(canvas)` | 绘制背景（棋盘格或白色） |
| `drawFG(canvas)` | 绘制前景（像素中心点和裁剪框） |
| `drawLine(canvas, pts)` | 绘制并放大显示线段 |
| `drawRect(canvas, pts)` | 绘制并放大显示矩形 |
| `drawTriangle(canvas, pts)` | 绘制并放大显示三角形 |
| `setAA(aa)` / `getAA()` | 抗锯齿控制 |
| `setGrid(g)` / `getGrid()` | 网格对齐控制 |
| `setStyle(s)` / `getStyle()` | 描边风格控制 |
| `setUseClip(uc)` | 裁剪区域控制 |
| `toggleRectAsOval()` | 矩形/椭圆切换 |
| `togglePixelColors()` | 背景颜色切换 |

### DrawLineSlide 快捷键
| 键 | 功能 |
|----|------|
| `a` | 切换抗锯齿 |
| `s` | 切换 hairline/stroke 模式 |
| `c` | 切换裁剪区域 |
| `r` | 切换矩形模式 |
| `o` | 切换椭圆模式 |
| `x` | 切换网格对齐 |
| `k` | 循环切换端点样式 |
| `w` | 切换线框骨架 |
| `g` | 切换背景颜色 |
| `t` | 切换三角形模式 |
| `-`/`=` | 调整描边宽度 (0.125 步长) |

## 内部实现细节

### 双缓冲放大机制
1. 在 `fMinSurface`（原始尺寸）上以正常分辨率绘制图形
2. 使用 `fMatrix`（缩放矩阵）将 `fMinSurface` 内容复制到 `fMaxSurface`（放大尺寸）
3. 在放大的表面上使用 `SkBlendMode::kClear` 绘制像素网格线
4. 在放大的表面上叠加线框骨架
5. 将最终的 `fMaxSurface` 绘制到目标画布

### 网格对齐
`apply_grid` 函数将坐标四舍五入到半像素网格（grid=2），模拟子像素对齐

### 线框骨架绘制
- 线段模式：在描边模式下使用 `FillPathWithPaint` 生成描边轮廓，与原始线段一起绘制
- 矩形模式：绘制矩形或椭圆路径的线框
- 三角形模式：绘制三角形多边形的线框

### 裁剪区域
默认裁剪矩形为 (2,2)-(11,8)，在前景绘制时显示为浅灰色边框

## 依赖关系

- Skia 核心：`SkCanvas`、`SkSurface`、`SkPaint`、`SkPath`、`SkMatrix`、`SkShader`
- Skia 工具：`SkPathUtils::FillPathWithPaint`（路径描边转填充）
- Skia 内部：`SkPointPriv`（点操作）
- Viewer 框架：`ClickHandlerSlide`、`Slide`
- 字体工具：`FontToolUtils`

## 设计模式与设计决策

- **双缓冲放大**：先在小表面绘制再放大显示，确保看到的是真实的像素级渲染结果
- **MVC 分离**：`FatBits` 类负责渲染逻辑（Model + View），`DrawLineSlide` 负责用户交互（Controller）
- **索引式点击**：通过 `IndexClick` 携带控制点索引，实现精确的拖拽交互
- **键盘驱动**：大量的键盘快捷键提供快速的参数切换，适合开发者调试工作流

## 性能考量

- 双缓冲放大涉及额外的 Surface 分配和像素复制
- 网格线使用 kClear 混合模式逐行绘制，像素数量与放大倍数平方成正比
- 前景的像素中心点绘制涉及 W*H 次 `drawPoint` 调用
- 放大倍数为 64 时，48x32 像素的原始画布产生 3072x2048 像素的放大视图

## 相关文件

- `tools/viewer/ClickHandlerSlide.h` - 可交互 Slide 基类
- `include/core/SkPathUtils.h` - 路径描边转填充工具
- `src/core/SkPointPriv.h` - 点操作内部 API
