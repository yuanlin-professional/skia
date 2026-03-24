# GrConvexPolyEffect

> 源文件: `src/gpu/ganesh/effects/GrConvexPolyEffect.h`, `src/gpu/ganesh/effects/GrConvexPolyEffect.cpp`

## 概述

`GrConvexPolyEffect` 是一个片段处理器，用于在设备空间中对凸多边形进行裁剪。它存储最多 8 条边的方程，在片段着色器中计算每个片段相对于这些边的位置，实现精确的硬裁剪或抗锯齿裁剪。通常作为覆盖率效果使用。

## 架构位置

位于 Ganesh 片段处理器效果层，主要被裁剪系统使用。当裁剪路径是简单的凸多边形时，该效果比模板缓冲区裁剪更高效。

## 主要类与结构体

### `GrConvexPolyEffect`
- 继承自 `GrFragmentProcessor`
- `kMaxEdges = 8` 最多支持 8 条边
- 存储边方程数组 `fEdges[3*kMaxEdges]`（每条边 3 个系数 a, b, c）
- 存储裁剪边类型 `fEdgeType`（AA/硬裁剪，正常/反转填充）

## 公共 API 函数

### `Make(edges)`
```cpp
static GrFPResult Make(std::unique_ptr<GrFragmentProcessor> inputFP,
                       GrClipEdgeType edgeType, int n, const float edges[]);
```
从边方程数组创建效果。边应形成凸多边形，前两个系数为单位向量。

### `Make(path)`
```cpp
static GrFPResult Make(std::unique_ptr<GrFragmentProcessor>, GrClipEdgeType, const SkPath&);
```
从凸路径创建效果。自动提取线段边、计算法线方向。仅支持线段组成的凸路径。

### `clone()`
通过拷贝构造函数创建副本。

## 内部实现细节

### 边方程处理
- 构造函数中对每条边的常数项偏移 0.5（`fEdges[3*i+2] += SK_ScalarHalf`），使像素中心位于边上时覆盖率为 50%（AA 模式）或 100%（非 AA 模式）
- 从路径提取边时，根据路径方向（CW/CCW）翻转法线方向
- 退化路径（方向不可计算）在反转填充时返回白色，正常填充时返回透明

### 着色器实现
- 使用 `edgeArray` uniform 数组传递边方程
- 对每条边计算 `edge = dot(float3(edgeCoeffs), sk_FragCoord.xy1)`
- AA 模式：`alpha *= saturate(edge)`（平滑过渡）
- 非 AA 模式：`alpha *= step(0.5, edge)`（硬边界）
- 反转填充：最终 `alpha = 1.0 - alpha`

### Key 编码
- `(fEdgeCount << 3) | edgeType` 编码到 32 位 key

## 依赖关系

- **GrFragmentProcessor** - 基类
- **GrClipEdgeType** - 裁剪边类型（AA/非 AA，正常/反转）
- **SkPath** - 从路径提取凸多边形边

## 设计模式与设计决策

1. **GrFPResult 返回模式**: 成功/失败用 `GrFPSuccess/GrFPFailure` 表达，失败时归还输入 FP
2. **设备空间裁剪**: 边方程在设备空间中指定，避免着色器中的变换运算
3. **边数限制**: 8 条边限制平衡了 uniform 使用量和裁剪灵活性
4. **0.5 偏移**: 确保边界像素获得正确的 50% 覆盖率

## 性能考量

- 每个片段需要 `n` 次点积运算（n 为边数），比模板裁剪更轻量
- uniform 数组避免了每帧的数据上传（仅在边变化时更新）
- 边数据变化检测通过 `std::equal` 比较避免不必要的 uniform 更新

## 相关文件

- `src/gpu/ganesh/GrFragmentProcessor.h` - 片段处理器基类
- `src/gpu/ganesh/GrClip.h` - 裁剪系统
- `include/private/gpu/ganesh/GrTypesPriv.h` - `GrClipEdgeType` 定义
