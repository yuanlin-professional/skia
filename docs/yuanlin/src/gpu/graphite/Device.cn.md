# Device (Graphite 绘制设备)

> 源文件：[src/gpu/graphite/Device.h](../../../../src/gpu/graphite/Device.h)、[src/gpu/graphite/Device.cpp](../../../../src/gpu/graphite/Device.cpp)

## 概述

`Device` 是 Skia Graphite 渲染后端中实现 `SkDevice` 接口的核心类。它是所有 Canvas 绘制操作的最终接收者，负责将高层 SkCanvas API 调用（如 `drawRect`、`drawPath`、`drawImage` 等）转化为 Graphite 的内部绘制记录。`Device` 管理裁剪栈、深度排序、渲染器选择、路径图集（PathAtlas）交互、以及与 `DrawContext` 的协作，最终产出可提交给 GPU 执行的渲染任务。

每个 `Device` 绑定到一个 `Recorder`，并持有一个 `DrawContext`（封装了绘制目标纹理和绘制列表）。设备区分"常规设备"（与客户端 Surface 关联）和"临时设备"（scratch device，用于图层、滤镜等内部操作），两者在任务管理和生命周期上有不同行为。

## 架构位置

`Device` 位于 Graphite 渲染管线的客户端 API 与内部记录之间的桥梁位置：

```
SkCanvas -> SkDevice(Device) -> DrawContext -> DrawList -> DrawPass -> RenderPassTask -> CommandBuffer
```

- **上游**：`SkCanvas` 通过 `SkDevice` 接口调用 `Device` 的绘制和裁剪方法。
- **核心协作者**：
  - `DrawContext`：持有绘制目标和绘制列表，接收最终的绘制记录。
  - `ClipStack`：管理裁剪状态，计算每个绘制的可见区域和深度。
  - `Recorder`：全局记录器，管理多个 Device 并最终生成 Recording。
  - `RendererProvider`：根据几何体类型和样式提供合适的渲染器。
  - `PathAtlas` / `AtlasProvider`：路径图集渲染，用于小路径或计算着色器渲染的路径。

## 主要类与结构体

### `Device` (final class, 继承自 SkDevice)

**关键成员变量：**
- `fRecorder`：指向所属 Recorder 的指针，生命周期管理的核心。
- `fDC` (DrawContext)：封装渲染目标、绘制列表和当前渲染通道状态。
- `fLastTask`：scratch 设备保存的最近一次快照的 DrawTask。
- `fClip` (ClipStack)：裁剪栈，管理裁剪元素和深度裁剪。
- `fColorDepthBoundsManager`：边界管理器（HybridBoundsManager），跟踪已记录绘制的交叉关系以确保正确的画家排序。
- `fDisjointStencilSet` (IntersectionTreeSet)：管理不相交的 stencil 索引分配。
- `fCachedLocalToDevice`：缓存的 local-to-device 变换。
- `fCurrentDepth`：当前最大深度值，每次绘制递增以保证唯一。
- `fSubRunControl`：文本渲染子运行控制参数。

### `Device::IntersectionTreeSet` (内部类)
管理多个 `IntersectionTree`，按 `CompressedPaintersOrder` 分组，为每个绘制分配最小的 `DisjointStencilIndex`，确保使用相同画家排序和 stencil 索引的绘制在空间上不相交。

### `ScopedDrawBuilder` (匿名命名空间)
RAII 包装器，从 Recorder 的对象池获取 `PipelineDataGatherer` 和 `PaintParamsKeyBuilder`，在作用域结束时自动归还。

## 公共 API 函数

### 工厂方法
- `Make(Recorder*, sk_sp<TextureProxy>, SkISize, SkColorInfo, ...)`：从已有纹理代理创建设备。
- `Make(Recorder*, SkImageInfo, Budgeted, Mipmapped, SkBackingFit, ...)`：自动创建纹理代理并创建设备。
- `registerWithRecorder` 参数控制设备是否注册到 Recorder（未注册的即为 scratch 设备）。

### 生命周期管理
- `abandonRecorder()`：断开与 Recorder 的关联。
- `setImmutable()`：刷新待处理工作、注销设备、断开 Recorder。
- `flushPendingWork(DrawContext*)`：将内部工作（裁剪绘制、atlas 上传等）刷新为 RenderPassTask。
- `isScratchDevice() -> bool`：通过目标纹理是否已实例化判断是否为临时设备。
- `lastDrawTask() -> sk_sp<Task>`：返回 scratch 设备的最近快照任务。
- `notifyInUse(Recorder*, DrawContext*) -> bool`：通知设备其内容被另一设备读取，触发必要的刷新。

### 裁剪操作
- `pushClipStack() / popClipStack()`：保存/恢复裁剪栈。
- `clipRect / clipRRect / clipPath / clipRegion`：各种裁剪形状。
- `replaceClip(SkIRect)`：当前在 Graphite 中不支持（仅用于 Android 旧版兼容）。
- `isClipWideOpen / isClipEmpty / isClipRect`：裁剪状态查询。

### 绘制操作
所有标准 SkDevice 绘制方法：
- 基础图元：`drawPaint`、`drawRect`、`drawOval`、`drawRRect`、`drawArc`、`drawDRRect`、`drawPath`、`drawPoints`。
- 图像：`drawImageRect`、`drawEdgeAAQuad`、`drawEdgeAAImageSet`。
- 顶点与网格：`drawVertices`。
- 文本：`onDrawGlyphRunList` -> `drawAtlasSubRun`。
- 特殊图像：`drawSpecial`、`drawCoverageMask`、`drawBlurredRRect`。
- 表面与子设备：`makeSurface`、`createDevice`、`snapSpecial`。
- 像素操作：`onReadPixels`、`onWritePixels`。

## 内部实现细节

### 绘制管线流程 (drawGeometry)
所有绘制操作最终汇聚到 `drawGeometry()` 方法，这是最核心的内部方法：

1. **变换验证**：检查 local-to-device 变换是否有效（可逆、有限）。透视变换下的非简单形状会被预先变换到设备空间。
2. **裁剪计算**：调用 `fClip.visitClipStackForDraw()` 计算裁剪区域和影响绘制的裁剪元素。
3. **渲染器选择**：`chooseRenderer()` 根据几何体类型、样式和绘制边界选择合适的渲染器或 PathAtlas。
4. **着色参数构建**：创建 `ShadingParams` 并通过 `toKey()` 生成管线键和收集 uniform。
5. **刷新判断**：检查是否需要在绘制前刷新（渲染步数超限或需要 dst 纹理拷贝）。
6. **全屏优化**：如果绘制覆盖整个目标且不依赖 dst，可以替换为 clear 或 discard。
7. **路径图集处理**：如果选择了 PathAtlas，将形状添加到图集并记录 CoverageMask 绘制。
8. **排序与深度**：计算 `DrawOrder`（包括画家排序、裁剪依赖、stencil 索引），记录到 DrawContext。
9. **内部填充优化**：对不依赖 dst 的填充渲染器，可能添加额外的 non-AA 内部填充绘制以减少过度绘制。

### 渲染器选择策略 (chooseRenderer)
按几何体类型分派：
- **子运行（文本）**：使用 `bitmapText` 或 `sdfText` 渲染器。
- **顶点**：使用 `vertices` 渲染器。
- **覆盖遮罩/EdgeAA 四边形/解析模糊**：使用各自的专用渲染器。
- **简单形状**（矩形、圆角矩形、线段）：使用 `analyticRRect` 或 `nonAABounds`（像素对齐时）。
- **圆弧**：在均匀缩放下使用 `circularArc` 渲染器。
- **复杂路径**：根据 `PathRendererStrategy` 选择：
  - `kComputeAnalyticAA/kComputeMSAA*`：使用计算路径图集。
  - `kTessellationAndSmallAtlas`：小路径使用 CPU 光栅图集，大路径使用曲面细分。
  - `kRasterAtlas`：全部使用 CPU 光栅图集。
  - `kTessellation`：全部使用 GPU 曲面细分。

### 非 AA 像素对齐模拟
Graphite 默认所有绘制都是抗锯齿的。对于非 AA 请求，通过 `snap_rect_to_pixels()` 将局部矩形对齐到设备空间像素边界，模拟非 AA 光栅化行为。该函数还处理描边宽度的对齐。

### Scratch 设备机制
Scratch 设备用于图层、滤镜等临时操作：
- 目标纹理未实例化（延迟分配）。
- 刷新时保存 `fLastTask`，供后续绘制该设备内容时引用。
- 通过 `notifyInUse()` 机制在被读取时正确处理任务依赖。

### DRRect 优化
`drawDRRect` 尝试将双圆角矩形转化为描边圆角矩形（如果内外矩形的间距均匀）。如果不能，尝试矩形差集。最后回退到使用裁剪实现：`drawRRect(outer)` + `clipRRect(inner, kDifference)`。

## 依赖关系

### 上游依赖
- `SkDevice` / `SkCanvas`：继承接口。
- `DrawContext`：绘制记录和目标管理。
- `ClipStack`：裁剪状态管理。
- `Recorder`：全局记录和资源管理。
- `RendererProvider`：渲染器注册和查找。
- `PathAtlas` / `AtlasProvider`：路径图集。
- `BoundsManager`（HybridBoundsManager）：边界交叉跟踪。
- `PaintParams` / `ShadingParams`：绘制参数封装。

### 下游使用者
- `Surface`：创建和持有 Device。
- `Image`：通过 `WrapDevice` 引用 Device 的内容。
- `Recorder`：管理 Device 注册和刷新。

## 设计模式与设计决策

1. **画家深度排序**：使用深度缓冲区实现画家算法，每个绘制分配唯一深度值。不透明绘制可以前后排序以利用 early-Z 测试。

2. **延迟裁剪绘制**：裁剪形状的深度值在刷新时才确定，允许多个绘制共享同一裁剪元素而不浪费深度值。

3. **混合边界管理器**（HybridBoundsManager）：前 64 次绘制使用暴力搜索，之后切换到网格加速结构，在低绘制数和高绘制数场景下都保持良好性能。

4. **渲染器抽象**：通过 `chooseRenderer()` 将几何体类型与渲染策略解耦，允许在不同平台和配置下选择不同的渲染路径。

5. **全屏绘制优化**：检测覆盖整个目标的不透明绘制，将其转化为 clear/discard 操作，避免不必要的渲染。

## 性能考量

- **刷新频率控制**：`needsFlushBeforeDraw()` 仅在渲染步数接近上限或需要 dst 纹理拷贝时触发刷新，最小化 RenderPass 切换。
- **路径图集复用**：小路径通过图集批量渲染，避免每个路径单独的 MSAA 渲染开销。图集满时触发刷新。
- **非 AA 内部填充**：对大面积 AA 填充额外添加 non-AA 内部填充，利用 early-Z 减少着色器执行。
- **像素对齐优化**：像素对齐的矩形使用无覆盖率的渲染器（`nonAABounds`），避免混合开销。
- **前后排序**：不依赖 dst 的矩形填充以逆深度排序，最大化 early-Z 剔除。
- **ScopedDrawBuilder 池化**：`PipelineDataGatherer` 和 `PaintParamsKeyBuilder` 通过对象池复用，避免频繁分配。

## 相关文件

- `src/gpu/graphite/DrawContext.h/.cpp`：绘制上下文，管理绘制列表和任务生成。
- `src/gpu/graphite/ClipStack.h/.cpp`：裁剪栈实现。
- `src/gpu/graphite/Renderer.h/.cpp`：渲染器基类和步骤定义。
- `src/gpu/graphite/RendererProvider.h/.cpp`：渲染器注册和查找。
- `src/gpu/graphite/DrawList.h/.cpp`：绘制列表。
- `src/gpu/graphite/DrawOrder.h`：绘制排序与深度管理。
- `src/gpu/graphite/PaintParams.h/.cpp`：绘制参数封装。
- `src/gpu/graphite/PathAtlas.h/.cpp`：路径图集基类。
- `src/gpu/graphite/geom/BoundsManager.h`：边界管理器。
- `src/gpu/graphite/geom/IntersectionTree.h`：交叉树。
