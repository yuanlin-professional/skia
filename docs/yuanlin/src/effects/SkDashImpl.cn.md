# SkDashImpl

> 源文件: `src/effects/SkDashImpl.h`

## 概述

`SkDashImpl` 是 Skia 虚线路径效果(Dash Path Effect)的内部实现类。它将连续的路径转换为虚线样式,通过指定间隔数组和相位偏移来控制虚线的 "画" 和 "跳" 模式。该类是 `SkDashPathEffect::Make()` 工厂方法返回的实际对象类型,广泛用于 UI 框架中虚线边框、虚线分隔线等场景。

## 架构位置

```
SkPathEffect (公共接口)
  └─ SkPathEffectBase (内部基类)
       └─ SkDashImpl (本文件)
            ├─ 序列化支持 (SK_FLATTENABLE_HOOKS)
            └─ 与 GPU 后端的快速路径优化 (asADash/asPoints)
```

该类位于效果层(`src/effects`),是 `SkPathEffectBase` 的具体实现,可以被 Ganesh/Graphite GPU 后端识别并进行硬件加速。

## 主要类与结构体

### `SkDashImpl`
- 继承自 `SkPathEffectBase`
- **构造参数**: `SkSpan<const SkScalar> intervals`(间隔数组)和 `SkScalar phase`(相位)
- **成员变量**:
  - `fIntervals` (`AutoTArray<SkScalar>`): 虚线间隔数组,交替表示"画"和"跳"的长度
  - `fPhase` (`SkScalar`): 用户指定的相位偏移
  - `fInitialDashLength` (`SkScalar`): 根据相位计算的首段虚线长度
  - `fIntervalLength` (`SkScalar`): 一个完整周期的总长度
  - `fInitialDashIndex` (`size_t`): 根据相位计算的起始间隔索引

## 公共 API 函数

### `flatten(SkWriteBuffer&) const`
序列化虚线参数到缓冲区,支持 SKP 文件格式的持久化。

### `onFilterPath(SkPathBuilder*, const SkPath&, SkStrokeRec*, const SkRect*, const SkMatrix&) const`
核心方法,将输入路径转换为虚线路径。接收原始路径、描边信息、裁剪矩形和变换矩阵作为参数。

### `onAsPoints(PointData*, const SkPath&, const SkStrokeRec&, const SkMatrix&, const SkRect*) const`
特殊优化路径,将虚线转换为点数据,供 GPU 后端高效渲染。

### `asADash() const -> std::optional<DashInfo>`
返回虚线参数信息,允许 GPU 后端识别并使用硬件加速路径。

### `computeFastBounds(SkRect*) const -> bool`
快速边界计算,由于虚线是输入路径的子集,始终返回 `true` 且不修改边界值。

## 内部实现细节

- **相位预计算**: 构造时根据 `phase` 计算 `fInitialDashLength`、`fIntervalLength` 和 `fInitialDashIndex`,避免运行时重复计算
- **快速边界**: `computeFastBounds` 直接返回 `true`,因为虚线路径永远是源路径的子集,不会扩展边界
- **序列化**: 通过 `SK_FLATTENABLE_HOOKS` 宏支持 SkFlattenable 的注册和反序列化机制

## 依赖关系

- `include/core/SkSpan.h` - 间隔数组的视图类型
- `include/private/base/SkTemplates.h` - `AutoTArray` 自动内存管理模板
- `src/core/SkPathEffectBase.h` - 路径效果基类
- `<optional>` - `asADash()` 返回值类型

## 设计模式与设计决策

### 预计算策略
将相位相关的参数在构造时一次性计算完成(`fInitialDashLength`、`fInitialDashIndex`),以空间换时间,避免每次路径过滤时的重复计算。

### 双重优化路径
`onAsPoints()` 和 `asADash()` 提供了两种 GPU 优化方式:前者直接输出点数据,后者暴露虚线参数供 GPU 后端自行实现。

### 保守的边界估计
`computeFastBounds` 返回未修改的边界,这是正确且保守的估计,因为虚线路径是原始路径的子集。

## 性能考量

- 间隔数组使用 `AutoTArray` 管理,避免小数组的堆分配
- `asADash()` 允许 GPU 后端跳过 CPU 端的路径分解,直接在硬件上绘制虚线
- `onAsPoints()` 支持将简单虚线转换为点列表,利用 GPU 的点绘制能力
- 相位预计算将 O(n) 的运行时开销移至构造时

## 相关文件

- `include/effects/SkDashPathEffect.h` - 公共工厂方法
- `src/core/SkPathEffectBase.h` - 路径效果基类
- `src/effects/SkDashPathEffect.cpp` - 工厂方法实现
- `src/gpu/ganesh/ops/DashOp.cpp` - Ganesh 虚线绘制优化
