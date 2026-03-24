# ThinAASlide

> 源文件: `tools/viewer/ThinAASlide.cpp`

## 概述

ThinAASlide 是一个抗锯齿（Anti-Aliasing）算法对比演示幻灯片，专门针对亚像素宽度（0.1-1.0 像素）的细线和形状。它将同一形状在五种不同的 AA 策略下并排渲染，并提供 8 倍缩放视图和覆盖率可视化，帮助开发者比较不同 AA 方法在极细几何体上的表现。

## 架构位置

属于 `tools/viewer` 模块（`skiagm` 命名空间），是 Skia AA 算法质量评估的重要工具。

## 主要类与结构体

### ShapeRenderer（抽象基类）
- 定义 20x20 像素的渲染瓷砖
- 接口: `draw()`, `name()`, `toHairline()`

### RectRenderer / PathRenderer
- `RectRenderer`: 使用 `drawRect` 绘制填充矩形
- `PathRenderer`: 支持直线、折线、曲线路径，可配置深度和发丝线模式

### OffscreenShapeRenderer
- 包装其他渲染器在离屏缓冲区中渲染
- 支持超采样（4x/8x）和强制光栅化后端
- `prepareBuffer/redraw` 分离渲染和显示
- 调试模式将任何非零 alpha 转为纯绿色

### ThinAASlide
五组渲染器数组（每组 5 个形状）：
- `fNative`: 当前 GPU 后端 1x 采样
- `fRaster`: 强制光栅化 1x 采样
- `fHairline`: 发丝线模拟（alpha 乘以线宽）
- `fSS4`: 4x4 = 16 倍超采样
- `fSS16`: 8x8 = 64 倍超采样

## 公共 API 函数

- `load(SkScalar, SkScalar)`: 初始化所有渲染器
- `draw(SkCanvas*)`: 渲染五列对比视图
- `animate(double)`: 驱动平移/旋转动画
- `onChar(SkUnichar)`: 键盘控制（t=动画平移, r=动画旋转, -/+=线宽, 空格=旋转15度）

## 内部实现细节

### 动画状态机
使用 `AnimStage` 枚举驱动动画序列：
`MoveLeft -> MoveDown -> MoveRight -> MoveUp -> Rotate`

亚像素平移在 [-1, 1] 范围内循环，旋转以 15 度为步进。

### 显示布局
每个形状显示三部分：
1. 8x 缩放的渲染结果（大矩形）
2. 原始尺寸（左上角小矩形）
3. 覆盖率可视化（右侧小矩形，非零区域显示为纯绿色）

### 发丝线模拟
将线宽信息编码到 alpha 通道中，将描边宽度设为 0（发丝线），利用 alpha 值模拟覆盖率。

## 依赖关系

- `include/core/SkSurface.h`: 离屏渲染
- `include/core/SkColorFilter.h`: 覆盖率可视化滤镜
- `tools/fonts/FontToolUtils.h`: 字体工具

## 设计模式与设计决策

- **装饰器模式**: `OffscreenShapeRenderer` 包装 `ShapeRenderer`，添加超采样和调试功能
- **可扩展形状**: 通过 `ShapeRenderer` 抽象可以轻松添加新的测试形状
- **参考比较**: 64x 超采样作为"接近真实"的参考结果

## 性能考量

- 8x8 超采样需要 64 倍的渲染面积
- 强制光栅化确保在所有平台上获得一致的基准
- 每帧渲染 25 个离屏缓冲区（5 策略 * 5 形状）

## 相关文件

- `tools/viewer/Slide.h`: Slide 基类
- Skia AA 相关的管线代码
