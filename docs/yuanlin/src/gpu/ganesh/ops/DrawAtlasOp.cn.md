# DrawAtlasOp

> 源文件
> - src/gpu/ganesh/ops/DrawAtlasOp.h

## 概述

`DrawAtlasOp` 是 Skia Ganesh GPU 后端的图集绘制操作，用于高效渲染多个精灵（sprites）或纹理矩形。该操作通过实例化渲染技术，在单个 draw call 中绘制大量使用相同纹理图集的对象，广泛应用于 UI 元素、粒子系统、2D 游戏等场景。

该操作支持 2D 旋转缩放变换（RSTransform）、可选的颜色调制、抗锯齿等特性，是 `SkCanvas::drawAtlas` API 的 GPU 实现。

## 架构位置

```
Skia GPU 渲染架构:
├── SkCanvas API
│   └── drawAtlas() → 创建 DrawAtlasOp
├── GrOp 操作层
│   └── DrawAtlasOp ← 本类
├── 实例化渲染
│   └── 多个精灵一次绘制
└── 纹理图集
    └── 共享纹理资源
```

## 主要类与结构体

### DrawAtlasOp 命名空间

提供图集绘制操作的工厂方法。

## 公共 API 函数

### 工厂方法

```cpp
GrOp::Owner Make(GrRecordingContext*, GrPaint&&,
                 const SkMatrix& viewMatrix, GrAAType,
                 int spriteCount, const SkRSXform* xforms,
                 const SkRect* rects, const SkColor* colors)
```
创建图集绘制操作。参数说明：
- `viewMatrix`：视图变换矩阵
- `GrAAType`：抗锯齿类型
- `spriteCount`：精灵数量
- `xforms`：每个精灵的旋转缩放变换（RSXform）
- `rects`：纹理图集中的矩形区域
- `colors`：可选的颜色调制数组（可为 null）

## 内部实现细节

### SkRSXform 变换

`SkRSXform` 表示 2D 旋转缩放平移变换：
```cpp
struct SkRSXform {
    float fSCos;  // scale * cos(rotation)
    float fSSin;  // scale * sin(rotation)
    float fTx;    // translation x
    float fTy;    // translation y
};
```

这种表示比完整的 `SkMatrix` 更紧凑，适合实例化渲染。

### 实例化渲染

每个精灵作为一个实例：
1. **顶点数据**：四边形的 4 个顶点（位置和纹理坐标）
2. **实例数据**：RSXform 和颜色（通过实例属性传递）
3. **GPU 绘制**：单个 drawInstanced 调用渲染所有精灵

### 纹理坐标计算

对于每个精灵：
1. 从 `rects` 数组获取图集中的矩形
2. 计算归一化纹理坐标（0.0-1.0）
3. 应用 RSXform 变换到四边形顶点
4. 传递给几何处理器

### 颜色调制

可选的颜色调制功能：
- **提供 colors 数组**：每个精灵独立颜色
- **null colors**：使用 paint 的颜色
- **片段着色器**：颜色与纹理采样值相乘

### 抗锯齿支持

根据 `GrAAType` 参数：
- **kNone**：无抗锯齿
- **kCoverage**：覆盖率抗锯齿（边缘渐变）
- **kMSAA**：多重采样抗锯齿

### 几何处理器

专用的几何处理器处理图集绘制：
- 输入：顶点位置、实例 RSXform、实例颜色
- 输出：变换后的位置、纹理坐标、调制颜色
- 着色器：应用 RSXform、插值纹理坐标

### 批处理优化

相同图集纹理的 DrawAtlasOp 可以合并：
- 共享纹理绑定
- 累积实例数据
- 减少 draw call 数量

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `GrOp` | 继承 | 操作基类 |
| `GrPaint` | 依赖 | 绘制参数和效果 |
| `SkRSXform` | 依赖 | 旋转缩放变换 |
| `GrRecordingContext` | 依赖 | 录制上下文 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `SkCanvas` | 使用 | `drawAtlas` API 创建此操作 |
| `SurfaceDrawContext` | 使用 | 添加操作到绘制上下文 |

## 设计模式与设计决策

### 1. 实例化渲染架构

使用 GPU 实例化技术：
- **优势**：单个 draw call 渲染多个对象
- **性能**：减少 CPU-GPU 通信
- **适用场景**：大量相似几何体

### 2. RSXform 紧凑表示

使用 4 个浮点数而非 9 个（完整矩阵）：
- **节省带宽**：减少实例数据传输
- **限制**：只支持旋转、缩放、平移（无倾斜）
- **权衡**：功能 vs 性能

### 3. 可选颜色调制

支持统一颜色和每实例颜色：
- **灵活性**：适应不同使用场景
- **优化**：无颜色变化时节省实例数据
- **实现**：通过 null 检查选择代码路径

### 4. 共享纹理图集

多个精灵共享单个纹理：
- **内存效率**：减少纹理数量
- **性能**：减少纹理绑定开销
- **管理**：需要图集打包和管理

## 性能考量

### 1. 实例化收益

单个 draw call 绘制所有精灵：
- 大幅减少 CPU 开销
- 减少驱动验证和状态设置
- GPU 并行处理实例

### 2. 实例数据大小

每个实例的数据量：
- **最小**：4 floats (RSXform)
- **带颜色**：4 floats + 1 uint (颜色)
- **优化**：保持实例数据紧凑

### 3. 纹理缓存局部性

图集布局影响性能：
- 相邻精灵使用相邻纹理区域
- 提高纹理缓存命中率
- 减少内存带宽

### 4. 批处理潜力

合并相同图集的操作：
- 减少状态切换
- 增加单次绘制的实例数
- 提高 GPU 利用率

### 5. 抗锯齿开销

根据场景选择抗锯齿：
- **kNone**：最快，像素对齐精灵
- **kCoverage**：中等，高质量边缘
- **kMSAA**：最慢，最高质量

### 6. 顶点缓冲区复用

四边形顶点可以共享：
- 所有实例使用相同的四边形模板
- 通过索引缓冲区重用
- 节省顶点内存

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/ops/GrOp.h` | 基类 | 操作基类 |
| `include/core/SkRSXform.h` | 依赖 | 旋转缩放变换 |
| `include/core/SkCanvas.h` | 使用者 | drawAtlas API |
| `src/gpu/ganesh/GrPaint.h` | 依赖 | 绘制参数 |
| `src/gpu/ganesh/SurfaceDrawContext.h` | 使用者 | 表面绘制上下文 |
