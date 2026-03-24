# GrAATriangulator

> 源文件
> - src/gpu/ganesh/geometry/GrAATriangulator.h
> - src/gpu/ganesh/geometry/GrAATriangulator.cpp

## 概述

`GrAATriangulator` 是带抗锯齿功能的路径三角化器，通过在路径边缘生成额外的覆盖几何来实现覆盖抗锯齿（Coverage AA）。该类扩展 `GrTriangulator` 基类，在内部三角形基础上添加外部边缘四边形，使用覆盖值（0.0 到 1.0）编码抗锯齿过渡。适用于复杂非凸路径的 GPU 绘制，生成的几何数据包含位置和覆盖属性，可直接提交到 GPU 渲染管线。

## 架构位置

- **模块层级**：`src/gpu/ganesh/geometry/` - Ganesh 几何处理
- **继承关系**：扩展 `GrTriangulator` 基类
- **使用者**：`PathInnerTriangulateOp`、AA 路径渲染器
- **输出**：顶点缓冲区（位置 + 覆盖值）+ 索引缓冲区

## 主要类与结构体

### GrAATriangulator

**静态工厂方法**：
```cpp
static int PathToAATriangles(const SkPath&, SkScalar tolerance, const SkRect& clipBounds,
                             GrEagerVertexAllocator*, bool* isLinear);
```

**功能**：
- 将路径三角化为带 AA 的几何
- `tolerance` - 曲线线性化容差
- `clipBounds` - 裁剪边界
- `isLinear` - 输出是否包含曲线

**输出格式**：
- 顶点：`{x, y, coverage}`（3 个 float）
- 索引：三角形列表

## 内部实现细节

### AA 边缘生成

**边缘四边形**：
- 内边缘顶点：覆盖值 = 1.0
- 外边缘顶点：覆盖值 = 0.0
- 宽度：0.5 像素（设备空间）

**法线计算**：
根据边缘方向计算外法线，沿法线外扩 0.5 像素生成外边缘。

### 覆盖计算

**规则**：
- 内部完全覆盖区域：coverage = 1.0
- 边缘过渡区域：coverage ∈ [0.0, 1.0]
- 外部未覆盖区域：coverage = 0.0

### 三角化流程

1. 调用 `GrTriangulator` 生成内部三角形
2. 识别轮廓边缘
3. 为每条边缘生成外扩四边形
4. 合并内部三角形和边缘几何
5. 生成索引缓冲区

## 设计模式与设计决策

### 扩展基类

复用 `GrTriangulator` 的复杂非凸三角化逻辑，仅添加 AA 边缘处理。

### 覆盖几何

使用几何覆盖而非多重采样，适用于无 MSAA 的场景，通过顶点属性传递覆盖值。

### 设备空间处理

AA 边缘宽度在设备空间固定（0.5px），确保一致的视觉效果。

## 性能考量

### 几何复杂度

AA 边缘使边数翻倍，顶点数增加，但避免 MSAA 的多倍片段处理开销。

### GPU 友好

输出直接适配 GPU 顶点格式，无需 CPU 后处理。

## 相关文件

- `src/gpu/ganesh/geometry/GrTriangulator.h/cpp` - 基类三角化器
- `src/gpu/ganesh/ops/PathInnerTriangulateOp.h/cpp` - 使用 AA 三角化的操作
- `src/gpu/ganesh/geometry/GrPathUtils.h` - 路径工具函数
