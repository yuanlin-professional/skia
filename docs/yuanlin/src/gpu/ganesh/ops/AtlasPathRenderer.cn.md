# AtlasPathRenderer

> 源文件
> - src/gpu/ganesh/ops/AtlasPathRenderer.h
> - src/gpu/ganesh/ops/AtlasPathRenderer.cpp

## 概述

`AtlasPathRenderer` 是 Skia Ganesh GPU 后端的路径渲染器，通过将路径的覆盖率遮罩渲染到离屏图集纹理中，然后重复使用这些遮罩进行高效渲染。该渲染器特别适合小面积路径的批量渲染，如裁剪路径、图标等，通过图集技术显著减少绘制调用和纹理切换开销。

该类同时实现了 `PathRenderer` 和 `GrOnFlushCallbackObject` 接口，在刷新时实例化图集纹理并实现纹理复用。支持路径缓存机制，对于重复绘制的路径（如裁剪路径）可以直接复用图集中的遮罩。

## 架构位置

```
Skia GPU 渲染架构:
├── PathRenderer 系统
│   ├── AALinearizingConvexPathRenderer
│   ├── AtlasPathRenderer ← 本类
│   ├── AAHairLinePathRenderer
│   └── DefaultPathRenderer
├── 图集管理
│   ├── GrDynamicAtlas
│   └── AtlasRenderTask
├── GrOnFlushCallbackObject
│   └── 刷新时回调处理
└── 片段处理器
    └── GrModulateAtlasCoverageEffect
```

## 主要类与结构体

### AtlasPathRenderer 类

继承自 `PathRenderer` 和 `GrOnFlushCallbackObject`。

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fAtlasMaxSize` | `float` | 图集的最大尺寸（像素） |
| `fAtlasMaxPathWidth` | `float` | 路径的最大宽度限制（1024 像素） |
| `fAtlasInitialSize` | `int` | 图集的初始尺寸（默认 512） |
| `fAtlasRenderTasks` | `STArray<4, sk_sp<AtlasRenderTask>>` | 自上次刷新以来创建的所有图集任务 |
| `fAtlasPathCache` | `THashMap<AtlasPathKey, SkIPoint16>` | 路径位置缓存，记录最近图集中的路径位置 |

### AtlasPathKey 结构体

用于缓存查找的路径键：

| 成员变量 | 类型 | 说明 |
|---------|------|------|
| `fPathGenID` | `uint32_t` | 路径的生成 ID |
| `fAffineMatrix[6]` | `float[6]` | 仿射变换矩阵的 6 个分量 |
| `fFillRule` | `uint32_t` | 填充规则 |

## 公共 API 函数

### 静态方法

```cpp
static bool IsSupported(GrRecordingContext*)
```
检查当前上下文是否支持图集路径渲染器。要求：
- 必须是直接上下文（不支持 DDL）
- Alpha8 格式支持 MSAA
- 支持镶嵌渲染
- 不在已知有 bug 的平台（iOS OpenGL、Windows Direct3D）

```cpp
static sk_sp<AtlasPathRenderer> Make(GrRecordingContext*)
```
创建图集路径渲染器实例，如果不支持则返回 `nullptr`。

### PathRenderer 接口

```cpp
const char* name() const override
```
返回渲染器名称 "GrAtlasPathRenderer"。

```cpp
CanDrawPath onCanDrawPath(const CanDrawPathArgs&) const override
```
判断是否可以渲染给定路径。支持条件：
- 简单填充样式
- 抗锯齿（非 `kNone`）
- 无 path effect
- 无透视变换
- 路径尺寸符合图集限制

```cpp
bool onDrawPath(const DrawPathArgs&) override
```
执行路径渲染，将路径添加到图集并创建 `DrawAtlasPathOp` 绘制操作。

### 图集裁剪效果

```cpp
GrFPResult makeAtlasClipEffect(const SurfaceDrawContext*, const GrOp* opBeingClipped,
                               std::unique_ptr<GrFragmentProcessor> inputFP,
                               const SkIRect& drawBounds, const SkMatrix&, const SkPath&)
```
创建基于图集的裁剪片段处理器。将路径添加到图集，返回调制覆盖率的片段处理器。失败时返回 `GrFPFailure`。

### 刷新回调

```cpp
bool preFlush(GrOnFlushResourceProvider*) override
```
在刷新时实例化所有图集纹理，相同尺寸的图集共享后备纹理以优化内存使用。

## 内部实现细节

### 图集尺寸和限制

常量配置：
- `kAtlasInitialSize = 512`：初始图集尺寸
- `kAtlasMaxPathHeight = 256`：最大路径高度（保证在 pow2 矩形打包带中）
- `kAtlasMaxPathHeightWithMSAAFallback = 128`：MSAA 降级时的高度限制
- `kAtlasMaxPathWidth = 1024`：最大路径宽度（避免 skbug.com/40043377）

### 转置优化

`addPathToAtlas` 方法自动决定是否转置路径：
1. 如果宽高的 pow2 相同，使用较大维度作为高度
2. 如果宽高的 pow2 不同，使用较小 pow2 作为高度
3. 转置后交换宽高，优化图集空间利用

这种策略确保路径高度较小，配合 pow2 算法实现高效打包。

### 路径缓存机制

`fAtlasPathCache` 缓存非易失路径的位置：
- **键**：路径 GenID + 仿射矩阵 + 填充规则
- **值**：图集中的位置（`SkIPoint16`）
- **生命周期**：在创建新图集或刷新时重置
- **用途**：主要用于裁剪路径的重复使用

### 图集任务依赖管理

多个图集任务通过依赖链串联：
1. 新图集任务依赖于前一个图集的所有使用者
2. 保证每次只有一个图集活跃
3. 所有图集可以共享同一个后备纹理

`validate_atlas_dependencies` （debug 模式）验证依赖正确性。

### 图集满时的处理

当前图集无法容纳新路径时：
1. 检查绘制操作是否已引用当前图集（通过 `DrawRefsAtlasCallback`）
2. 如果已引用，返回失败（避免单个绘制引用多个图集）
3. 否则创建新图集任务，添加到渲染任务 DAG
4. 重置路径缓存（旧缓存位置失效）

### 可见性检查

`is_visible` 函数检查路径是否在裁剪范围内：
- 使用 SIMD 向量化比较
- 处理 NaN 情况（返回不可见）
- 早期剔除完全在裁剪外的路径

### 纹理实例化

`preFlush` 阶段实例化策略：
1. 首先实例化第一个图集
2. 遍历剩余图集，尺寸相同则共享第一个图集的纹理
3. 尺寸不同则独立实例化（通常只有最后一个图集）
4. 刷新后清空所有图集任务和缓存

### 坐标变换

`makeAtlasClipEffect` 计算图集变换矩阵：
- **非转置**：`Translate(atlasX - devLeft, atlasY - devTop)`
- **转置**：90 度旋转矩阵加平移

### 反向填充处理

图集内部不存储反向路径（由 `AtlasRenderTask` 处理），但裁剪效果支持反向：
- 设置 `kInvertCoverage` 标志
- 片段处理器反转覆盖率

### 边界检查

当路径边界不包含绘制边界时：
- 设置 `kCheckBounds` 标志
- 片段着色器检查坐标是否在路径边界内

## 依赖关系

### 依赖的模块

| 模块 | 依赖关系 | 说明 |
|------|---------|------|
| `PathRenderer` | 继承 | 路径渲染器基类 |
| `GrOnFlushCallbackObject` | 继承 | 刷新回调接口 |
| `AtlasRenderTask` | 核心依赖 | 图集渲染任务 |
| `GrDynamicAtlas` | 强依赖 | 动态图集管理 |
| `DrawAtlasPathOp` | 强依赖 | 图集路径绘制操作 |
| `GrModulateAtlasCoverageEffect` | 强依赖 | 图集覆盖率调制片段处理器 |
| `TessellationPathRenderer` | 依赖 | 图集任务内部使用镶嵌渲染 |

### 被依赖的模块

| 模块 | 依赖类型 | 说明 |
|------|---------|------|
| `GrDrawingManager` | 使用 | 管理图集渲染任务的调度 |
| `SurfaceDrawContext` | 使用 | 通过路径渲染器选择使用此渲染器 |
| `GrClip` | 使用 | 裁剪系统使用图集裁剪效果 |

## 设计模式与设计决策

### 1. 双接口模式

同时实现 `PathRenderer` 和 `GrOnFlushCallbackObject`：
- **PathRenderer**：提供路径渲染能力
- **GrOnFlushCallbackObject**：在刷新时实例化纹理
- **优势**：分离路径记录和资源分配阶段

### 2. 延迟实例化

图集纹理在 `preFlush` 阶段才实例化：
- 录制阶段只管理图集布局
- 允许多个图集共享纹理
- 优化内存使用

### 3. 缓存优化

使用简单的哈希表缓存路径位置：
- **目标**：裁剪路径通常重复使用
- **限制**：只缓存最近图集中的路径
- **权衡**：简单实现 vs 复杂的多图集缓存

### 4. 尺寸限制设计

多层尺寸限制：
- **路径宽度**：最大 1024（避免已知 bug）
- **路径高度**：最大 256（或 128 with MSAA）
- **总面积**：限制像素数量
- **理由**：小路径才从图集中受益，大路径直接渲染更优

### 5. 转置策略

自动转置瘦长路径：
- **目标**：提高 pow2 算法的空间利用率
- **实现**：根据宽高的 pow2 关系决定
- **效果**：所有路径高度≤256，打包效率高

### 6. 平台兼容性处理

显式禁用已知有问题的平台：
- iOS OpenGL（b/195095846）
- Windows Direct3D Radeon（skbug.com/40044606）
- 通过编译时宏和运行时检测结合

### 7. 图集任务链设计

通过依赖链串联多个图集：
- **原因**：确保图集顺序执行
- **效果**：所有图集共享纹理
- **验证**：debug 模式检查依赖完整性

## 性能考量

### 1. 纹理复用

相同尺寸的图集共享后备纹理：
- 减少纹理内存占用
- 避免重复分配/释放
- 依赖于图集顺序执行的保证

### 2. 路径缓存

缓存重复路径的图集位置：
- 裁剪路径通常高频重复
- 避免重复镶嵌和图集分配
- 缓存查找成本低（哈希表 O(1)）

### 3. 早期可见性剔除

在添加路径前检查可见性：
- 避免不可见路径占用图集空间
- 使用 SIMD 加速边界检查
- 反向填充路径的特殊处理

### 4. MSAA 降级策略

MSAA 场景使用更严格的尺寸限制：
- **原因**：MSAA 本身已提供良好效果
- **效果**：只有非常小的路径才使用图集
- **权衡**：图集空间 vs MSAA 成本

### 5. pow2 打包算法

使用 `GrDynamicAtlas::RectanizerAlgorithm::kPow2`：
- 配合转置策略，所有路径高度≤256
- 在 256 像素带内高效打包
- 比通用矩形打包更快

### 6. 单图集引用限制

单个绘制操作不能引用多个图集：
- 简化纹理绑定逻辑
- 图集满时，如已引用则拒绝添加
- 调用者需要提前绘制并重试

### 7. 透视变换拒绝

不支持透视变换：
- 透视下路径尺寸难以预测
- 图集坐标变换复杂
- 其他渲染器更适合透视场景

### 8. 仿射矩阵缓存键

缓存键只存储仿射分量（6 个浮点数）：
- 忽略透视分量（已拒绝透视路径）
- 缓存键紧凑（32 字节）
- 支持高效 memcmp 比较

## 相关文件

| 文件路径 | 关系 | 说明 |
|---------|------|------|
| `src/gpu/ganesh/PathRenderer.h` | 基类 | 路径渲染器抽象接口 |
| `src/gpu/ganesh/GrOnFlushResourceProvider.h` | 接口 | 刷新时资源提供者 |
| `src/gpu/ganesh/ops/AtlasRenderTask.h` | 核心组件 | 图集渲染任务 |
| `src/gpu/ganesh/GrDynamicAtlas.h` | 核心组件 | 动态图集管理 |
| `src/gpu/ganesh/ops/DrawAtlasPathOp.h` | 使用 | 图集路径绘制操作 |
| `src/gpu/ganesh/effects/GrModulateAtlasCoverageEffect.h` | 使用 | 图集覆盖率片段处理器 |
| `src/gpu/ganesh/ops/TessellationPathRenderer.h` | 依赖 | 镶嵌路径渲染器 |
| `src/gpu/ganesh/GrDrawingManager.h` | 管理者 | 渲染任务调度 |
| `src/core/SkTHash.h` | 依赖 | 哈希表实现 |
