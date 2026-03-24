# ComputePathAtlas (计算路径图集)

> 源文件：[src/gpu/graphite/ComputePathAtlas.h](../../../../src/gpu/graphite/ComputePathAtlas.h)、[src/gpu/graphite/ComputePathAtlas.cpp](../../../../src/gpu/graphite/ComputePathAtlas.cpp)

## 概述

`ComputePathAtlas` 是使用 GPU 计算着色器光栅化覆盖遮罩的路径图集基类。当新形状被添加时，它被记录为 GPU 计算通道的输入。通过 `recordDispatches()` 将数据记录到 `DispatchGroup` 中，可以添加到 `ComputeTask` 执行。

当前的主要实现是 `VelloComputePathAtlas`，使用 Vello GPU 渲染器（基于计算着色器的 2D 渲染引擎）进行路径光栅化。Vello 支持三种抗锯齿模式：解析面积 AA、8x MSAA 和 16x MSAA。

图集纹理大小固定为 4096x4096，使用 `RectanizerSkyline` 算法进行矩形分配。

## 架构位置

`ComputePathAtlas` 位于路径渲染系统的计算着色器分支：

- **上游**：`Device::chooseRenderer()` 选择计算路径渲染策略时返回 `ComputePathAtlas`。
- **同级**：与 `RasterPathAtlas`（CPU 光栅化）是路径渲染的两种替代方案。
- **下游**：`DrawContext::flush()` 调用 `recordDispatches()` 将计算任务记录到任务图。

## 主要类与结构体

### `ComputePathAtlas` (继承自 PathAtlas)
计算路径图集基类。

**核心成员：**
- `fRectanizer`：Skyline 矩形分配器（4096x4096）。
- `fTexture`：懒加载的图集纹理代理。

### `VelloComputePathAtlas` (继承自 ComputePathAtlas)
使用 Vello 渲染器的具体实现。

**核心成员：**
- `fCachedAtlasMgr`：基于 DrawAtlas 的缓存图集管理器，支持多页和驱逐。
- `fUncachedScene`：未缓存形状的 Vello 场景数据。
- `fUncachedOccupiedArea`：未缓存图集的已占用区域。

### `VelloAtlasMgr` (VelloComputePathAtlas 内部类)
封装 DrawAtlas 和 Vello 场景渲染，管理缓存的路径遮罩。每页维护独立的 VelloScene 和占用区域。

## 公共 API 函数

### `CreateDefault(Recorder*) -> unique_ptr<ComputePathAtlas>`
工厂方法。如果编译时启用了 Vello 着色器（`SK_ENABLE_VELLO_SHADERS`），返回 `VelloComputePathAtlas`；否则返回 nullptr。

### `recordDispatches(Recorder*, DispatchGroupList*) -> bool` (纯虚)
记录计算着色器调度命令，由子类实现。

### `reset()`
清除所有已调度的图集绘制和分配。不影响正在执行的 GPU 命令使用的纹理内容。

### `isSuitableForAtlasing(Rect, Rect) -> bool`
判断形状是否适合在图集中渲染。拒绝条件：
- 遮罩尺寸超过图集维度。
- 遮罩面积超过阈值（1024 * 512 像素）。
- 坐标值过大（> 1e10，Vello 无法高效处理）。

## 内部实现细节

### 双层缓存策略
`VelloComputePathAtlas` 使用两层图集：
1. **缓存图集**（`fCachedAtlasMgr`）：基于 DrawAtlas，支持多页和 LRU 驱逐。非 volatile 路径优先放入缓存图集。
2. **未缓存图集**（直接使用 `fRectanizer`）：volatile 路径或缓存未命中的路径放入此处，每次 flush 后重置。

### Vello 场景构建
`add_shape_to_scene()` 将形状编码到 Vello 场景中：
- 应用图集变换（将设备空间路径定位到图集槽中）。
- 使用裁剪矩形限制渲染到图集槽边界。
- 发线描边特殊处理：宽度小于 1 设备像素时，使用 1px 宽度渲染并按实际宽度缩放 alpha。
- stroke-and-fill 样式绘制两个遮罩到同一槽位。

### AA 配置选择
根据 `PathRendererStrategy` 选择 Vello 的 AA 模式：
- `kComputeAnalyticAA` -> `VelloAaConfig::kAnalyticArea`
- `kComputeMSAA8` -> `VelloAaConfig::kMSAA8`
- `kComputeMSAA16` -> `VelloAaConfig::kMSAA16`

## 依赖关系

- `PathAtlas`：路径图集基类。
- `RectanizerSkyline`：矩形打包算法。
- `VelloRenderer`：Vello GPU 渲染引擎。
- `DispatchGroup`：计算任务调度组。
- `AtlasProvider`：图集纹理管理。
- `DrawAtlas`：缓存图集的底层分配器。

## 设计模式与设计决策

1. **双层缓存策略**：可缓存路径使用带 LRU 驱逐的 DrawAtlas，不可缓存路径使用临时分配器，平衡缓存效率和内存使用。
2. **面积阈值限制**：限制大路径进入图集，避免图集快速填满导致频繁刷新。
3. **编译时特性门控**：通过 `SK_ENABLE_VELLO_SHADERS` 宏控制 Vello 实现的编译。

## 性能考量

- 计算着色器路径光栅化避免了 CPU 光栅化的开销和 CPU-GPU 数据传输。
- 批量渲染多个路径到同一图集纹理，减少绘制调用。
- 面积阈值防止大路径独占图集空间。
- 缓存图集减少重复路径的计算着色器开销。

## 相关文件

- `src/gpu/graphite/PathAtlas.h/.cpp`：路径图集基类。
- `src/gpu/graphite/RasterPathAtlas.h/.cpp`：CPU 光栅路径图集。
- `src/gpu/graphite/compute/VelloRenderer.h/.cpp`：Vello 渲染器。
- `src/gpu/graphite/compute/DispatchGroup.h/.cpp`：计算调度组。
- `src/gpu/graphite/AtlasProvider.h/.cpp`：图集提供者。
- `src/gpu/RectanizerSkyline.h`：Skyline 矩形分配器。
