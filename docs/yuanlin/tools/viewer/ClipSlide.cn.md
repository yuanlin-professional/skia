# ClipSlide

> 源文件: `tools/viewer/ClipSlide.cpp`

## 概述

ClipSlide.cpp 包含多个裁剪和半平面（Half-Plane）相关的演示幻灯片。`ClipSlide` 展示了圆角矩形裁剪下的文本、描边、发丝线和填充效果。三个 `HalfPlaneSlide` 变体展示了半平面裁剪路径的算法实现。`HalfPlaneCoonsSlide` 将 3D 透视变换与 Coons 面片渲染结合。

## 架构位置

属于 `tools/viewer` 模块，涵盖了从基础裁剪到高级透视裁剪的完整演示。共注册 5 个幻灯片。

## 主要类与结构体

### ClipSlide
在圆角矩形裁剪区域中绘制四种图元（AA/非AA 各一行）。

### SkHalfPlane
半平面结构体（Ax + By + C = 0）:
- `eval()`: 计算点到半平面的有符号距离
- `twoPts()`: 计算半平面上的两个点
- `test()`: 检测矩形与半平面的关系

### HalfPlaneSlide
使用 `SkEdgeClipper` 实现路径的半平面裁剪：将路径变换到半平面坐标系，对上半平面裁剪后变换回原坐标系。

### HalfPlaneSlide2
交互式四点透视变换，显示对应的四条半平面。

### CameraSlide（内部类）
3D 摄像机基类，使用 LookAt + Perspective 矩阵链：
`viewport * perspective * camera * translate * rotation * inv(viewport)`

### HalfPlaneSlide3
将 3D 透视变换与半平面 W=0 裁剪结合，使用 `SkPathPriv::PerspectiveClip`。

### HalfPlaneCoonsSlide
在 3D 透视变换下绘制可编辑的 12 点 Coons 面片，支持颜色/纹理模式切换。

## 公共 API 函数

各幻灯片的 `draw()`、`onChar()`、`onClick()` 等标准接口。

## 内部实现细节

### 半平面裁剪算法 (clip 函数)
1. 从两点构建坐标变换矩阵
2. 将路径变换到半平面对齐坐标系
3. 使用 `SkEdgeClipper::ClipPath` 对 y>0 的区域裁剪
4. 将裁剪后的路径变换回原坐标系

### 半平面计算
`compute_half_planes()` 从 3x3 变换矩阵推导出视口边界对应的四条半平面方程。

### 3D 摄像机系统
支持键盘控制旋转（8/2/4/6 键），平移（i/k 键），近远裁面调节（n/N/f/F 键）。

## 依赖关系

- `src/core/SkEdgeClipper.h`: 边缘裁剪器
- `src/core/SkPathPriv.h`: `PerspectiveClip` 路径裁剪
- `include/core/SkM44.h`: 4x4 矩阵
- `include/core/SkVertices.h`: Coons 面片绘制

## 设计模式与设计决策

- **渐进式复杂度**: 从简单裁剪到半平面到 3D 透视裁剪，逐步增加复杂度
- **继承复用**: `HalfPlaneSlide3` 和 `HalfPlaneCoonsSlide` 继承 `CameraSlide` 复用 3D 变换逻辑

## 性能考量

- 半平面裁剪涉及路径变换和逐段裁剪，复杂路径开销较大
- Coons 面片使用 TriangleStrip 顶点绘制

## 相关文件

- `src/core/SkEdgeClipper.h`: 边缘裁剪实现
- `include/core/SkM44.h`: 4x4 矩阵运算
