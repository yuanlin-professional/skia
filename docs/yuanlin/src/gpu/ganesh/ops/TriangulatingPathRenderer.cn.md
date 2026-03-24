# TriangulatingPathRenderer

> 源文件: `src/gpu/ganesh/ops/TriangulatingPathRenderer.h`, `src/gpu/ganesh/ops/TriangulatingPathRenderer.cpp`

## 概述

`TriangulatingPathRenderer` 通过将路径线性化并分解为三角形来渲染非凸路径。它使用 `GrTriangulator` 将路径转换为屏幕空间的三角形列表，上传到顶点缓冲区，并以单个绘制调用渲染。支持屏幕空间抗锯齿（通过 1 像素覆盖率渐变）和通过线程安全缓存进行三角化数据的缓存复用。

## 架构位置

位于 Ganesh 路径渲染系统中，处理凸路径渲染器不能处理的凹面填充路径。在 `SK_ENABLE_OPTIMIZE_SIZE` 未定义时可用。它是路径渲染链中的重要一环，配合 `AAConvexPathRenderer` 和 tessellation 渲染器共同覆盖各类路径场景。

## 主要类与结构体

### `TriangulatingPathRenderer`
- 继承自 `PathRenderer`
- `fMaxVerbCount` 控制 AA 模式下的最大动词数（默认 10）
- 不支持模板操作（`kNoSupport_StencilSupport`）

### `TriangulatingPathOp`（内部）
- 继承自 `GrMeshDrawOp`，实际执行三角化和渲染
- 支持 AA 和非 AA 两种模式
- 非 AA 模式使用 `GrThreadSafeCache` 缓存三角化结果

### `TessInfo`（内部）
- 存储三角化的辅助信息：顶点数、是否线性、容差值

### `StaticVertexAllocator`（内部）
- 用于非 AA 模式的静态顶点缓冲区分配，支持缓冲区映射和数据上传

## 公共 API 函数

- `onCanDrawPath()` - 接受非凸简单填充路径，排除动态 MSAA 表面和动词过多的路径
- `onDrawPath()` - 创建 `TriangulatingPathOp` 并提交

## 内部实现细节

### 缓存机制
- 使用 `skgpu::UniqueKey` 基于路径形状和裁剪区域生成缓存 key
- `GrThreadSafeCache::findVertsWithData()` 查找已缓存的三角化数据
- `is_newer_better()` 比较缓存中的数据精度，更精确的三角化会替换旧的
- `UniqueKeyInvalidator` 监听路径 genID 变化，自动使缓存失效

### 两种路径
- **非 AA 模式**: 使用 `GrTriangulator::PathToTriangles()`，结果缓存在 `GrThreadSafeCache` 中，支持 pre-prepare
- **AA 模式**: 使用 `GrAATriangulator::PathToAATriangles()`，生成带覆盖率的顶点，不缓存

### Pre-Prepare 支持
- 非 AA 模式在 `onPrePrepareDraws()` 中提前在录制线程完成三角化
- AA 模式目前不支持 pre-prepare（TODO）

## 依赖关系

- **PathRenderer** - 基类
- **GrTriangulator / GrAATriangulator** - 三角化算法
- **GrThreadSafeCache** - 线程安全的顶点数据缓存
- **GrDefaultGeoProcFactory** - 创建几何处理器
- **GrPathUtils** - 容差计算
- **GrStyledShape** - 路径和样式的组合表示

## 设计模式与设计决策

1. **缓存优先**: 非 AA 模式优先使用缓存的三角化数据，减少重复计算
2. **线程安全设计**: 通过 `GrThreadSafeCache` 支持多线程录制中的数据共享
3. **精度比较**: 缓存中的三角化精度不足时自动替换，确保视觉质量
4. **路径复杂度限制**: 通过 `kMaxGPUPathRendererVerbs` 和 `fMaxVerbCount` 限制处理的路径复杂度

## 性能考量

- 三角化结果的缓存显著减少了重复路径的 CPU 开销
- Pre-prepare 支持将三角化工作转移到录制线程
- 对于 Coverage AA 的路径，最大动词数限制为 10，更复杂的路径交给其他渲染器
- 使用静态顶点缓冲区（`kStatic_GrAccessPattern`）利于 GPU 缓存

## 相关文件

- `src/gpu/ganesh/PathRenderer.h` - 路径渲染器基类
- `src/gpu/ganesh/geometry/GrTriangulator.h` - 三角化算法
- `src/gpu/ganesh/geometry/GrAATriangulator.h` - AA 三角化算法
- `src/gpu/ganesh/GrThreadSafeCache.h` - 线程安全缓存
- `src/gpu/ganesh/ops/AAConvexPathRenderer.h` - 凸路径渲染器
