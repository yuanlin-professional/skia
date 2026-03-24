# SkEmbossMask - 浮雕遮罩生成

> 源文件: `src/effects/SkEmbossMask.h`, `src/effects/SkEmbossMask.cpp`

## 概述

SkEmbossMask 提供一个静态方法 `Emboss`，用于将 alpha 遮罩转换为 3D 浮雕效果。它根据指定的光照方向计算每个像素的漫反射和镜面反射分量，生成乘法平面（multiply）和加法平面（additive）用于后续的颜色混合。

该类是 SkEmbossMaskFilter 的内部实现细节，负责实际的逐像素光照计算。

## 架构位置

```
SkEmbossMaskFilter
  └── SkEmbossMask::Emboss() (静态方法)
```

## 主要类与结构体

### SkEmbossMask
仅包含一个静态方法，无实例状态。

## 公共 API 函数

```cpp
static void Emboss(SkMaskBuilder* mask, const SkEmbossMaskFilter::Light& light);
```

输入: k3D_Format 的遮罩（包含 alpha、multiply、additive 三个平面）
输出: 填充 multiply 和 additive 平面

## 内部实现细节

### 光照计算
对每个像素：
1. 从 alpha 平面计算法线分量 nx、ny（使用前后/上下差分）
2. kDelta=32 作为法线 Z 分量的固定值
3. 计算光照点积 `numer = lx*nx + ly*ny + lz*kDelta`
4. 如果点积为正（面向光源）：
   - 漫反射: `dot = numer / sqrt(nx*nx + ny*ny + kDelta*kDelta)`
   - multiply = ambient + dot（夹紧到 255）
5. 镜面反射计算:
   - `hilite = (2*dot - lz_dot8) * lz_dot8`
   - 对 hilite 进行 specular 指数次幂运算（通过循环乘法实现）
   - additive = hilite^specular

### 辅助函数
- `nonzero_to_one(x)` — 非零转 1（无分支实现）
- `neq_to_one(x, max)` — x!=max 转 1
- `neq_to_mask(x, max)` — x!=max 转全 1 掩码
- `div255(x)` — 快速 x/255 近似

### 边界处理
使用 `nonzero_to_one` 和 `neq_to_one` 处理图像边缘的差分计算，避免越界访问。

## 依赖关系

- `SkEmbossMaskFilter::Light` — 光照参数
- `SkMaskBuilder` — 遮罩数据结构
- `SkFixed` — 定点数运算
- `SkSqrt32` — 整数平方根

## 设计模式与设计决策

1. **纯函数设计**: 无状态类，单一静态方法
2. **无分支优化**: 边界检查使用位运算替代条件分支
3. **定点数运算**: 使用 SkFixed (16.16) 进行光照计算

## 性能考量

- 逐像素计算，O(width * height)
- SkSqrt32 是主要开销（每像素一次整数平方根）
- 镜面反射的幂运算通过循环实现（specular >> 4 次迭代）
- 无分支的边界处理减少了分支预测失误

## 相关文件

- `src/effects/SkEmbossMaskFilter.h` — 浮雕遮罩滤镜
- `src/core/SkMask.h` — 遮罩数据结构（k3D_Format）
