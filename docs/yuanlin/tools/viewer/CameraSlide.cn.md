# CameraSlide

> 源文件: `tools/viewer/CameraSlide.cpp`

## 概述

CameraSlide 是一个 3D 摄像机效果演示幻灯片，使用 `Sk3DView` API 在圆角矩形上展示图片纹理的 3D 旋转动画。当矩形翻转到背面时自动切换到下一张图片。

## 架构位置

属于 `tools/viewer` 模块，演示 Skia 的 3D 视图变换 API。

## 主要类与结构体

### CameraSlide
- 继承自 `Slide`
- `fShaders`: 图片着色器数组（mandrill、dog、gamut 三张图片）
- `fRX/fRY`: 当前 X/Y 轴旋转角度
- `fFrontFace`: 当前是否显示正面

## 公共 API 函数

- `load()`: 加载三张图片资源并创建着色器
- `draw(SkCanvas*)`: 应用 3D 旋转并绘制纹理圆角矩形
- `animate(double)`: 以 90 度/秒的速度绕 Y 轴旋转

## 内部实现细节

使用 `Sk3DView` 实现 3D 变换：通过 `dotWithNormal(0,0,1)` 检测正/反面，翻面时切换 `fShaderIndex` 以显示下一张图片。图片映射到 300x300 区域（-150 到 150），使用线性过滤采样。

## 依赖关系

- `include/utils/SkCamera.h`: Sk3DView 3D 视图
- `tools/timer/TimeUtils.h`: 时间工具

## 设计模式与设计决策

- **自动翻面检测**: 利用法线点积判断正/背面，实现自然的图片切换效果

## 性能考量

- 单个圆角矩形绘制，开销极小

## 相关文件

- `include/utils/SkCamera.h`: 3D 摄像机 API
- `tools/viewer/Slide.h`: Slide 基类
