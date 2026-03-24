# GrYUVtoRGBEffect

> 源文件: `src/gpu/ganesh/effects/GrYUVtoRGBEffect.h`, `src/gpu/ganesh/effects/GrYUVtoRGBEffect.cpp`

## 概述

`GrYUVtoRGBEffect` 是一个片段处理器，实现 YUV 到 RGB 颜色空间的转换。它支持多平面 YUV 纹理（最多 4 个平面），处理子采样（chroma subsampling）、YCbCr 颜色空间矩阵转换、坐标对齐（snapping）以及子集/域裁剪。该效果广泛用于视频帧和 YUVA 图像的 GPU 渲染。

## 架构位置

位于 Ganesh 片段处理器效果层。它将多个 `GrTextureEffect` 作为子处理器，每个对应一个 YUV 平面，然后在片段着色器中组合通道值并应用颜色空间转换矩阵。

## 主要类与结构体

### `GrYUVtoRGBEffect`
- 继承自 `GrFragmentProcessor`
- 存储 `YUVALocations`（每个 YUVA 通道在哪个平面的哪个通道）
- 存储 `SkYUVColorSpace` 和 `fSnap[2]`（是否对齐到像素中心）

## 公共 API 函数

### `Make()`
工厂方法，从 `GrYUVATextureProxies` 创建效果。处理子采样平面的坐标缩放、边界颜色计算、线性滤波的 snap 模式（模拟 libjpeg 的 fancy upsampling），以及子集/域约束。

### `clone()`
通过拷贝构造函数创建副本。

## 内部实现细节

### 子采样处理
- 对于子采样平面（ssx > 1 或 ssy > 1），坐标乘以缩放因子
- 当原始采样为最近邻时，子采样平面切换到线性滤波并启用 snap（模拟 fancy upsampling）
- snap 将坐标对齐到 `floor(coord) + 0.5`，在像素中心采样

### 颜色空间转换
- 在片段着色器中通过 3x3 矩阵和 3 维平移向量实现
- Identity 颜色空间跳过矩阵运算
- 矩阵通过 `SkColorMatrix_YUV2RGB()` 生成，提取 3x3 子矩阵和第 5 列作为 translate

### 通道提取
- 遍历每个平面，确定哪些 YUVA 通道来自该平面
- 动态生成 swizzle 代码，如 `color.rg = (planeResult).ba;`

### Key 编码
- 将平面/通道映射、颜色空间（是否为 Identity）、snap 标志编码到 32 位 key 中

## 依赖关系

- **GrFragmentProcessor** - 基类
- **GrTextureEffect** - 每个 YUV 平面使用一个 TextureEffect 子处理器
- **GrMatrixEffect** - 包装局部坐标矩阵
- **SkYUVAInfo / GrYUVATextureProxies** - YUV 图像信息和纹理代理
- **SkYUVMath** - YUV/RGB 颜色矩阵生成

## 设计模式与设计决策

1. **子处理器组合**: 每个平面作为独立的 TextureEffect 子处理器，通过 FP 树组合
2. **Fancy Upsampling 模拟**: 通过 snap + 线性滤波模拟 libjpeg 的子采样插值行为
3. **边界颜色**: 在 ClampToBorder 模式下，将 RGB 边界颜色转换到 YUV 空间

## 性能考量

- 子采样平面的 snap 操作需要额外的 floor 运算
- 颜色空间转换在 Identity 模式下完全跳过
- 子处理器的 `Explicit` 采样模式允许 snap 坐标直接传递

## 相关文件

- `src/gpu/ganesh/effects/GrTextureEffect.h` - 纹理效果
- `src/gpu/ganesh/effects/GrMatrixEffect.h` - 矩阵效果
- `src/gpu/ganesh/GrYUVATextureProxies.h` - YUVA 纹理代理
- `include/core/SkYUVAInfo.h` - YUV 信息描述
