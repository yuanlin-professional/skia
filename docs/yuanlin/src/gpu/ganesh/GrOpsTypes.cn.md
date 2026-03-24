# GrOpsTypes — Ganesh 操作类型定义

> 源文件: `src/gpu/ganesh/GrOpsTypes.h`

## 概述

`GrOpsTypes.h` 定义了 Ganesh GPU 渲染管线中绘制操作所需的两个核心数据结构：`GrQuadSetEntry` 和 `GrTextureSetEntry`。它们分别用于批量绘制彩色四边形集合和带纹理的四边形集合，是 `SurfaceDrawContext`（SDC）批量绘制 API 和对应 Op 实现之间的数据传输接口。

## 架构位置

```
SurfaceDrawContext (SDC)
    ├── drawQuadSet() ─────→ FillRectOp ──→ GrQuadSetEntry
    └── drawTextureSet() ──→ TextureOp ───→ GrTextureSetEntry
        └── GPU 命令缓冲区
```

这些结构体处于绘图命令的打包层，将高层绘图调用参数化为可批量处理的条目。

## 主要类与结构体

### GrQuadSetEntry

用于 `SDC::drawQuadSet` 和 `FillRectOp` 的彩色矩形条目：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fRect` | `SkRect` | 目标矩形区域 |
| `fColor` | `SkPMColor4f` | 预乘颜色值，覆盖 GrPaint 中的颜色 |
| `fLocalMatrix` | `SkMatrix` | 局部坐标变换矩阵 |
| `fAAFlags` | `GrQuadAAFlags` | 抗锯齿边标志（控制哪些边启用 AA） |

### GrTextureSetEntry

用于 `SDC::drawTextureSet` 和 `TextureOp` 的纹理绘制条目：

| 成员 | 类型 | 描述 |
|------|------|------|
| `fProxyView` | `GrSurfaceProxyView` | 纹理代理视图 |
| `fSrcAlphaType` | `SkAlphaType` | 源纹理的 Alpha 类型 |
| `fSrcRect` | `SkRect` | 纹理中的源矩形采样区域 |
| `fDstRect` | `SkRect` | 渲染目标中的目标矩形 |
| `fDstClipQuad` | `const SkPoint*` | 目标裁剪四边形（null 或 4 个点的数组） |
| `fPreViewMatrix` | `const SkMatrix*` | 前视图矩阵，若非 null 则 CTM = viewMatrix * fPreViewMatrix |
| `fColor` | `SkPMColor4f` | 颜色调制：RGB 纹理使用 `{a,a,a,a}`，仅 Alpha 纹理使用 `{r,g,b,a}` |
| `fAAFlags` | `GrQuadAAFlags` | 抗锯齿边标志 |

## 公共 API 函数

本文件仅定义数据结构，无函数。

## 内部实现细节

1. **颜色语义双重性**: `GrTextureSetEntry::fColor` 的含义取决于纹理类型。对于 RGB 纹理，四个分量全为 alpha 值实现透明度调制；对于仅 Alpha 纹理，使用完整 RGBA 实现颜色着色。

2. **可选指针成员**: `fDstClipQuad` 和 `fPreViewMatrix` 为裸指针，不拥有所指向的数据。调用者需确保指针在条目使用期间保持有效。

3. **`fDstClipQuad` 约束**: 注释明确要求该指针必须为 null 或指向恰好 4 个 `SkPoint` 的数组，这允许绘制非矩形的凸四边形。

## 依赖关系

- **`include/core/SkMatrix.h`**: 变换矩阵
- **`include/core/SkRect.h`**: 矩形区域
- **`src/core/SkColorData.h`**: `SkPMColor4f` 预乘颜色
- **`src/gpu/ganesh/GrSurfaceProxyView.h`**: 纹理代理视图
- **`GrQuadAAFlags`**: 四边形抗锯齿边标志枚举（前向声明）

## 设计模式与设计决策

1. **POD 风格结构体**: 使用简单的聚合结构体而非带方法的类，方便高效的批量内存操作和数组存储。

2. **批量绘制优化接口**: 这些结构体的设计允许调用者一次性提交大量绘制条目，减少 CPU-GPU 交互次数。每个条目包含独立的变换和颜色参数，支持合并到单个绘制调用。

3. **裸指针设计**: `fDstClipQuad` 和 `fPreViewMatrix` 使用裸指针避免智能指针的开销，因为这些条目通常是短生命周期的临时对象。

## 性能考量

- 结构体设计为连续内存存储，有利于 CPU 缓存命中。
- `GrTextureSetEntry` 包含 `GrSurfaceProxyView`（持有引用计数指针），因此拷贝成本高于 `GrQuadSetEntry`。
- 批量绘制模式通过减少状态切换和绘制调用次数来提升 GPU 利用率。

## 相关文件

- `src/gpu/ganesh/SurfaceDrawContext.h` — 使用这些类型的 drawQuadSet/drawTextureSet 方法
- `src/gpu/ganesh/ops/FillRectOp.h` — 使用 GrQuadSetEntry 的填充矩形操作
- `src/gpu/ganesh/ops/TextureOp.h` — 使用 GrTextureSetEntry 的纹理绘制操作
- `src/gpu/ganesh/GrSurfaceProxyView.h` — 纹理代理视图
