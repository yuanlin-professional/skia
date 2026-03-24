# BoundsManager - 设备空间边界管理加速结构

> 源文件: `src/gpu/graphite/geom/BoundsManager.h`

## 概述

BoundsManager 是 Skia Graphite 渲染后端中用于管理设备空间像素边界查询的加速结构。它跟踪每个绘制操作的边界矩形（Rect）及其关联的 CompressedPaintersOrder（压缩画家顺序），以支持高效查询与给定边界矩形相交的最近绘制操作。

BoundsManager 的核心功能是在 Graphite 的绘制排序阶段，帮助确定哪些绘制操作可能相互重叠，从而决定它们的提交顺序。CompressedPaintersOrder 强制执行绘制操作到 GPU 的特定提交顺序，但允许在 GREATER 深度测试和绘制 Z 值能正确解析乱序渲染的情况下，对绘制操作进行重排。

该头文件提供了一个抽象基类 `BoundsManager` 和四个具体实现：`NaiveBoundsManager`、`BruteForceBoundsManager`、`GridBoundsManager` 和 `HybridBoundsManager`。

## 架构位置

```
Graphite 渲染管线
  -> Device (设备)
    -> DrawOrder (绘制排序)
      -> BoundsManager (边界管理)
        -> 查询/记录绘制操作的空间边界
```

BoundsManager 位于 Graphite 渲染管线的绘制排序阶段，被 Device 类使用来管理绘制操作之间的空间关系。它依赖于 `Rect`（SIMD 矩形）和 `DrawOrder`（绘制顺序）模块。

## 主要类与结构体

### `BoundsManager`（抽象基类）
- **职责**: 定义边界管理的统一接口
- **纯虚方法**:
  - `getMostRecentDraw(const Rect&)`: 查询与给定边界相交的最近绘制顺序
  - `recordDraw(const Rect&, CompressedPaintersOrder)`: 记录一个绘制操作及其边界
  - `reset()`: 重置所有已记录的数据

### `NaiveBoundsManager`
- **职责**: 最简单的实现，假设所有绘制操作都会被前面的绘制操作遮挡
- **行为**: `getMostRecentDraw` 始终返回全局最大的顺序值，不进行任何空间查询
- **成员**: `fLatestDraw` - 跟踪最新的绘制顺序
- **适用场景**: 正确性测试和基线对比

### `BruteForceBoundsManager`
- **职责**: 暴力搜索所有已记录的绘制操作，精确计算空间相交
- **数据结构**: 使用两个并行的 `SkTBlockList` 分别存储矩形和顺序值
- **特点**: 结果完全精确，但对于大量绘制操作性能较差
- **额外方法**:
  - `count()`: 返回已记录的绘制数量
  - `replayDraws(BoundsManager*)`: 将所有记录回放到另一个 BoundsManager

### `GridBoundsManager`
- **职责**: 基于均匀空间网格追踪每个网格单元中的最高 CompressedPaintersOrder
- **工厂方法**:
  - `Make(SkISize, SkISize)`: 根据设备尺寸和网格尺寸创建
  - `Make(SkISize, int)`: 使用相同的宽高网格尺寸
  - `MakeRes(SkISize, int, int)`: 根据单元格像素大小创建，可限制最大网格尺寸
- **内部实现**: 将设备坐标归一化后映射到网格坐标，使用 SIMD 整数运算夹紧坐标

### `HybridBoundsManager`
- **职责**: 自适应混合管理器，先使用暴力搜索，超过阈值后切换到网格管理器
- **策略**: 对于少量绘制操作使用 BruteForce（精度高、内存低），大量绘制操作时切换到 Grid（性能复杂度更低）
- **生命周期管理**: 网格管理器一旦创建就保留（假设帧间绘制量相似），但如果连续两帧不使用则释放

## 公共 API 函数

| 函数 | 所属类 | 说明 |
|------|--------|------|
| `getMostRecentDraw(const Rect&)` | BoundsManager | 查询与边界相交的最新绘制顺序 |
| `recordDraw(const Rect&, CompressedPaintersOrder)` | BoundsManager | 记录绘制的边界和顺序 |
| `reset()` | BoundsManager | 重置管理器状态 |
| `Make(SkISize, SkISize)` | GridBoundsManager | 静态工厂：按网格尺寸创建 |
| `MakeRes(SkISize, int, int)` | GridBoundsManager | 静态工厂：按网格单元像素大小创建 |
| `count()` | BruteForceBoundsManager | 返回已记录绘制数 |
| `replayDraws(BoundsManager*)` | BruteForceBoundsManager | 回放所有绘制到另一管理器 |

## 内部实现细节

### GridBoundsManager 的坐标映射
`getGridCoords` 方法通过预计算的缩放因子 `fScaleX` 和 `fScaleY`（包含设备到网格的归一化和网格维度缩放），将 Rect 的 LTRB 坐标转换为网格单元索引。使用 `skvx::pin` 将结果夹紧到 `[0, gridDim-1]` 范围。

### 并行数组设计
`BruteForceBoundsManager` 将 `Rect` 和 `CompressedPaintersOrder` 存储在两个独立的 `SkTBlockList` 中，而非合并为一个结构体。这是因为 `Rect` 是过度对齐的 SIMD 类型（16 字节对齐），与较小的 `CompressedPaintersOrder` 合并存储会浪费填充字节。

### HybridBoundsManager 的切换策略
- 初始使用 `BruteForceBoundsManager`
- 当 `BruteForceBoundsManager` 中的绘制数达到 `fMaxBruteForceN` 时，创建或复用 `GridBoundsManager`
- 切换时通过 `replayDraws` 将暴力管理器中的所有绘制转移到网格管理器
- 帧重置（`reset()`）后回退到暴力管理器，但保留网格管理器实例以备下一帧复用
- 如果网格管理器连续一帧未使用则释放

### ComplementRect 优化
`Rect::ComplementRect` 预计算了补矩形的形式 `[right, bottom, -left, -top]`，使得 `intersects()` 检测可以通过一次 SIMD 比较 `all(fVals < comp.fVals)` 完成。`BruteForceBoundsManager` 在 `getMostRecentDraw` 中利用此优化加速遍历。

## 依赖关系

| 依赖 | 用途 |
|------|------|
| `src/gpu/graphite/geom/Rect.h` | SIMD 矩形实现 |
| `src/gpu/graphite/DrawOrder.h` | CompressedPaintersOrder 类型定义 |
| `src/base/SkTBlockList.h` | 块分配链表容器 |
| `src/base/SkBlockAllocator.h` | 块分配器 |
| `src/base/SkVx.h` | SIMD 向量操作 |
| `include/core/SkSize.h` | SkISize 类型 |
| `include/private/base/SkTemplates.h` | AutoTMalloc 内存管理 |

## 设计模式与设计决策

1. **策略模式（Strategy Pattern）**: 通过虚函数基类 BoundsManager 定义统一接口，允许不同实现策略可互换使用。源码注释表明未来可能移除虚函数层，选定一个最佳实现。

2. **自适应策略（HybridBoundsManager）**: 结合了暴力搜索和网格搜索的优势，在小规模绘制时使用高精度的暴力方法，大规模时切换到网格方法。这体现了"按需升级"的设计思路。

3. **帧间资源复用**: HybridBoundsManager 在帧重置时不立即释放网格管理器，而是假设帧间工作量相似，保留已分配的网格以避免每帧重新分配。

4. **Fibonacci 增长策略**: BruteForceBoundsManager 使用 Fibonacci 增长策略的块分配器，这比倍增策略更节省内存，同时仍然提供良好的摊还时间复杂度。

## 性能考量

1. **网格查询复杂度**: GridBoundsManager 的查询和记录操作复杂度为 O(k)，其中 k 是边界矩形覆盖的网格单元数，与绘制操作总数无关。

2. **暴力搜索复杂度**: BruteForceBoundsManager 的查询复杂度为 O(n)，但对于少量绘制操作（由于缓存局部性和 SIMD 优化），实际性能可能优于网格方法。

3. **内存开销**: GridBoundsManager 需要 `gridWidth * gridHeight * sizeof(CompressedPaintersOrder)` 的固定内存，通过 `MakeRes` 的 `maxGridSize` 参数可限制最大网格尺寸以控制内存。

4. **SIMD 利用**: 网格坐标计算使用 `skvx::float2` 和 `skvx::int4` 进行批量运算，ComplementRect 使得交叉检测可以通过单条 SIMD 比较指令完成。

5. **memset 重置**: GridBoundsManager 使用 `memset` 零填充来重置网格，利用了 `CompressedPaintersOrder::First()` 值为零的特性。

## 相关文件

- `src/gpu/graphite/geom/Rect.h` - SIMD 矩形实现，BoundsManager 的基础数据类型
- `src/gpu/graphite/DrawOrder.h` - 定义 CompressedPaintersOrder 类型
- `src/gpu/graphite/Device.h` - BoundsManager 的主要使用者
- `src/base/SkTBlockList.h` - 块分配链表，用于 BruteForceBoundsManager
- `src/base/SkVx.h` - SIMD 向量库
