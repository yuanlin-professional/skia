# SkTrimPE

> 源文件: `src/effects/SkTrimPE.h`

## 概述

`SkTrimPE` 是 Skia 路径裁剪效果(Trim Path Effect)的内部实现类。它根据归一化的起始和结束参数(0 到 1 之间)截取路径的一部分,类似于 SVG 中的 `stroke-dashoffset` 概念,但更通用。该效果常用于动画中的路径绘制进度控制,例如 Lottie 动画中的描边动画效果。

## 架构位置

```
SkPathEffect (公共接口)
  └─ SkPathEffectBase (内部基类)
       └─ SkTrimPE (本文件)
            └─ 支持 Normal 和 Inverted 两种裁剪模式
```

该类位于效果层(`src/effects`),通过 `SkTrimPathEffect::Make()` 工厂方法创建,是 `SkPathEffectBase` 的具体子类。

## 主要类与结构体

### `SkTrimPE`
- 继承自 `SkPathEffectBase`
- **构造参数**:
  - `SkScalar startT`: 裁剪起始位置,归一化值 [0, 1]
  - `SkScalar stopT`: 裁剪结束位置,归一化值 [0, 1]
  - `SkTrimPathEffect::Mode`: 裁剪模式(Normal 或 Inverted)
- **成员变量**:
  - `fStartT` / `fStopT` (`const SkScalar`): 不可变的裁剪参数
  - `fMode` (`const SkTrimPathEffect::Mode`): 不可变的裁剪模式

## 公共 API 函数

### `flatten(SkWriteBuffer&) const`
将裁剪参数序列化到写缓冲区,支持 SKP 格式持久化。

### `onFilterPath(SkPathBuilder*, const SkPath&, SkStrokeRec*, const SkRect*, const SkMatrix&) const`
核心路径过滤方法。根据 `fStartT`、`fStopT` 和 `fMode` 从源路径中提取指定范围的子路径。

### `computeFastBounds(SkRect*) const -> bool`
返回 `true` 且不修改边界,因为裁剪操作只会产生源路径的子集。

## 内部实现细节

- **不可变设计**: `fStartT`、`fStopT` 和 `fMode` 均声明为 `const`,确保线程安全
- **两种模式**:
  - `Normal`: 保留 [startT, stopT] 范围内的路径
  - `Inverted`: 保留 [0, startT] 和 [stopT, 1] 范围内的路径(即反转选择)
- **SK_FLATTENABLE_HOOKS**: 注册序列化和反序列化回调

## 依赖关系

- `include/effects/SkTrimPathEffect.h` - 公共接口和 Mode 枚举定义
- `src/core/SkPathEffectBase.h` - 路径效果基类

## 设计模式与设计决策

### 不可变值对象
所有成员变量声明为 `const`,使实例在创建后不可修改。这简化了线程安全分析,并与 Skia 的不可变效果设计理念一致。

### 归一化参数
使用 [0, 1] 归一化参数而非绝对长度,使效果与路径的实际长度解耦,适用于任意长度的路径。

### 保守边界估计
与 `SkDashImpl` 一致,`computeFastBounds` 利用裁剪结果是源路径子集这一不变量,直接返回源边界。

## 性能考量

- 裁剪计算需要遍历路径以确定总长度和各段长度,对于复杂路径可能有较高开销
- 不可变设计允许安全的多线程共享,无需同步开销
- 在动画场景中,通常每帧更新 startT/stopT,需要重新创建 SkTrimPE 实例

## 相关文件

- `include/effects/SkTrimPathEffect.h` - 公共 API 和 Mode 枚举
- `src/effects/SkTrimPathEffect.cpp` - 实际路径裁剪逻辑实现
- `src/core/SkPathEffectBase.h` - 路径效果基类
- `src/core/SkPathMeasure.cpp` - 路径测量工具,用于计算路径长度
- `src/core/SkPathBuilder.h` - 输出路径构建器
- `src/core/SkWriteBuffer.h` - 序列化支持
