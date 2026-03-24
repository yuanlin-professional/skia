# CoverageMaskShape - 覆盖率遮罩形状

> 源文件: `src/gpu/graphite/geom/CoverageMaskShape.h`

## 概述

CoverageMaskShape 是 Skia Graphite 渲染后端中用于表示基于纹理覆盖率遮罩（Coverage Mask）的形状几何类型。与直接通过几何路径渲染不同，CoverageMaskShape 的逐像素覆盖率数据来源于预先渲染到纹理中的遮罩。此类型专门用于非字体字形的覆盖率遮罩场景（字体字形由 `SubRunData` 处理）。

覆盖率遮罩定义在一个介于最终设备空间和原始几何/着色局部空间之间的中间坐标空间中。对于图集和简单情况，此中间空间与最终设备空间像素对齐，仅需整数平移即可对齐遮罩。在复杂情况下，剩余变换可能包含旋转、倾斜甚至透视变换。

## 架构位置

```
Graphite 绘制管线
  -> Geometry (几何容器)
    -> CoverageMaskShape (覆盖率遮罩)
      -> TextureProxy (纹理代理)
      -> SkM44 (设备到局部空间变换)
```

CoverageMaskShape 是 `Geometry` 联合类型的一种变体，在绘制管线中作为一种独立的几何类型被处理。它连接了纹理系统（通过 TextureProxy）和坐标变换系统。

## 主要类与结构体

### `CoverageMaskShape`
- **职责**: 封装覆盖率遮罩纹理及其在设备空间中的位置和变换信息
- **禁用的操作**: 移动赋值运算符被删除（`operator=(CoverageMaskShape&&) = delete`），因为几何类型不受益于移动语义

### `MaskInfo` 结构体
- **fTextureOrigin** (`half2`): 遮罩在纹理中的左上角 UV 坐标（纹理相对整数坐标），包含形状的设备空间边界 + 1 像素 AA 边框
- **fMaskSize** (`half2`): 遮罩在设备坐标中的宽高，同样包含 1 像素 AA 边框

## 公共 API 函数

| 函数 | 说明 |
|------|------|
| `CoverageMaskShape(shape, proxy, deviceToLocal, maskInfo)` | 完整构造，传入形状、纹理代理、逆变换和遮罩信息 |
| `bounds()` | 返回遮罩空间的边界（从 0,0 到 maskSize） |
| `deviceToLocal()` | 返回设备到局部空间的逆矩阵（SkM44） |
| `textureOrigin()` | 返回纹理中遮罩的左上角 UV 坐标 |
| `maskSize()` | 返回遮罩的宽高 |
| `textureProxy()` | 返回纹理代理的原始指针 |
| `inverted()` | 是否使用反向填充规则 |

## 内部实现细节

### 坐标空间设计
CoverageMaskShape 存储 `fDeviceToLocal`（设备到局部空间的逆变换），用于在着色器中重建局部坐标以进行着色。`bounds()` 返回的边界是遮罩空间的边界（即 `[0, 0, maskWidth, maskHeight]`），与 DrawParams 中的 Clip 边界不同（特别是在反向填充时）。

### 纹理代理的生命周期管理
使用 `sk_sp<TextureProxy>` 持有纹理代理的强引用，确保在 CoverageMaskShape 生命周期内纹理不会被释放。源码注释表明未来可能改为原始指针，待纹理和 uniform 在 `Device::drawGeometry` 中提取后。

### half2 类型选择
使用 `skvx::half2`（16 位半精度浮点）存储纹理坐标和遮罩尺寸，在保持足够精度的同时减少内存占用。这对于可能大量存在的遮罩形状实例尤其重要。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/TextureProxy.h` | 纹理代理，持有遮罩纹理 |
| `src/gpu/graphite/geom/Rect.h` | bounds() 返回类型 |
| `src/gpu/graphite/geom/Shape.h` | 原始 Shape 类型（用于读取 inverted 状态） |
| `include/core/SkM44.h` | 4x4 矩阵，存储设备到局部空间变换 |
| `include/core/SkRefCnt.h` | sk_sp 智能指针 |
| `src/base/SkVx.h` | SIMD 向量类型 half2, int2 |

## 设计模式与设计决策

1. **逆矩阵存储**: 存储 `deviceToLocal`（逆矩阵）而非 `localToDevice`，因为着色器需要从设备坐标反推局部坐标来采样着色信息。这避免了在 GPU 端执行矩阵求逆。

2. **中间坐标空间**: 引入遮罩空间作为中间坐标空间，将复杂的变换分解为两步：遮罩渲染时处理部分变换，最终绘制时处理剩余变换（存储在 DrawParams 的 local-to-device 中）。

3. **值语义**: 支持拷贝构造和拷贝赋值，但禁用移动赋值（`operator=(CoverageMaskShape&&) = delete`），所有几何类型遵循相同的设计约定。

## 性能考量

1. **half2 存储**: 使用半精度浮点存储纹理坐标和尺寸，减少每实例内存占用，提升缓存利用率。
2. **纹理代理引用计数**: sk_sp 的引用计数操作有一定开销，但确保了安全的生命周期管理。
3. **bounds() 零开销**: bounds() 直接从 maskSize 构建 Rect，无需额外计算。

## 相关文件

- `src/gpu/graphite/geom/Geometry.h` - 包含 CoverageMaskShape 的几何容器
- `src/gpu/graphite/geom/SubRunData.h` - 字体字形的类似覆盖率遮罩机制
- `src/gpu/graphite/TextureProxy.h` - 纹理代理
- `src/gpu/graphite/geom/Shape.h` - 原始形状类型
- `src/gpu/graphite/Device.h` - 创建和使用 CoverageMaskShape 的设备类
