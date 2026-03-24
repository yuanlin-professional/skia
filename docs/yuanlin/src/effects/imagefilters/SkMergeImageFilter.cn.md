# SkMergeImageFilter

> 源文件: `src/effects/imagefilters/SkMergeImageFilter.cpp`

## 概述

`SkMergeImageFilter` 实现了多个图像滤镜输出的合并操作,将所有子滤镜的结果按照 src-over 混合模式依次叠加。它是构建复杂图像效果(如多重光照、多层阴影)的基础组件,对应 SVG 的 `feMerge` 滤镜。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkMergeImageFilter (本文件)
            ├─ 输入[0]: 第一层 (底层)
            ├─ 输入[1]: 第二层
            ├─ ...
            └─ 输入[n-1]: 顶层

工厂方法: SkImageFilters::Merge(filters[], count, cropRect)
```

## 主要类与结构体

### `SkMergeImageFilter`
- 继承自 `SkImageFilter_Base`,接收任意数量的子滤镜
- 无额外成员变量(所有状态由基类管理)
- 不需要覆盖 `flatten()`,基类的输入序列化已足够

## 公共 API 函数

### `SkImageFilters::Merge(filters[], count, cropRect)`
创建合并滤镜。验证:
- `count <= 0` 或 `filters` 为 null 时返回 `SkImageFilters::Empty()`
- 若提供 cropRect,在外层包裹 Crop 滤镜

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 极其简洁:
1. 使用 `FilterResult::Builder` 收集所有子滤镜输出
2. 调用 `builder.merge()` 执行 src-over 合并

### 输入边界计算
`onGetInputLayerBounds()`:
- 返回所有子滤镜输入需求的并集
- 使用 `skif::LayerSpace<SkIRect>::Union()` 汇总

### 输出边界计算
`onGetOutputLayerBounds()`:
- 合并操作的输出是所有子输出的并集
- 若任一子输出无界,则整体无界
- 使用标志变量 `childIsUnbounded` 追踪无界情况

### 快速边界
委托给基类的 `computeFastBounds()`,它计算所有子滤镜快速边界的并集。

### 序列化
`CreateProc` 使用 `-1` 作为 `unflatten` 的输入数量参数,允许任意数量的子滤镜。

## 依赖关系

- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkReadBuffer.h` - 反序列化支持

## 设计模式与设计决策

### 零状态设计
SkMergeImageFilter 没有自己的状态,完全依赖基类管理输入滤镜列表。这使得序列化和反序列化都由基类统一处理。

### 联合边界策略
由于 src-over 混合不会缩小任何输入的可见区域,输出边界正确地为所有输入的并集。

### 矩阵能力
声明 `MatrixCapability::kComplex`,因为合并操作本身不受变换复杂度影响。

## 性能考量

- `builder.merge()` 可以将多个输入高效地合并到单个输出图像中
- 所有子滤镜共享相同的期望输出区域,可以并行求值
- 输入边界联合确保源图像足以满足所有子滤镜的需求
- 无额外序列化开销

## 使用场景

1. **多重阴影**: 使用不同偏移和颜色的多个阴影效果合并
2. **多光源光照**: 多个 SkLightingImageFilter 输出的合并
3. **图层合成**: 模拟图层面板中的多层 src-over 叠加
4. **投影效果**: SkDropShadowImageFilter 内部使用 Merge 合并阴影和原图

## 与 Blend 滤镜的对比

| 特性 | Merge | Blend |
|------|-------|-------|
| 输入数量 | 任意 N 个 | 固定 2 个 |
| 混合模式 | 固定 src-over | 可配置 |
| 边界处理 | 每个子输入独立绘制 | 统一着色器求值 |
| 输出边界 | 并集 | 取决于混合模式 |
| 状态 | 无 | 混合器参数 |

Merge 使用每个子输入独立绘制的方式,避免了 Blend 在不一致边界上需要处理瓦片边缘条件的问题。

## 边界计算详解

输入边界:
```
requiredInput = union(child[0].getInputBounds(desiredOutput, contentBounds),
                      child[1].getInputBounds(desiredOutput, contentBounds),
                      ...
                      child[n-1].getInputBounds(desiredOutput, contentBounds))
```

输出边界:
```
output = union(child[0].getOutputBounds(contentBounds),
               child[1].getOutputBounds(contentBounds),
               ...
               child[n-1].getOutputBounds(contentBounds))
// 若任一子输出无界,则整体无界
```

## 反序列化特殊处理

与其他固定输入数量的滤镜不同,Merge 的 `CreateProc` 使用 `-1` 作为 `unflatten` 的预期输入数量,允许从序列化数据中读取任意数量的子滤镜。这是因为 Merge 的子滤镜数量在构建时确定,可以是任意正整数。

## 版本兼容性

- 旧版名称: `SkMergeImageFilterImpl` -> `SkMergeImageFilter`
- 无额外序列化数据(仅基类的子滤镜列表)
- 旧版曾支持每个子输入配置独立的混合模式,该功能已被移除

## 零输入边界情况

当 `count <= 0` 或 `filters` 为 null 时,工厂方法返回 `SkImageFilters::Empty()`。这确保了合并滤镜始终有至少一个有意义的输入。空合并在语义上等同于透明输出。

在 `computeFastBounds` 中,零子滤镜的情况也被处理:调用基类实现会返回空矩形(基类对零输入返回输入 rect)。

## 实现简洁性

SkMergeImageFilter 是所有图像滤镜中实现最简洁的之一:
- `onFilterImage()`: 3 行 (循环收集子输出 + merge)
- `flatten()`: 不需要覆盖 (无额外状态)
- `CreateProc()`: 3 行 (unflatten + 调用工厂)
- `computeFastBounds()`: 1 行 (委托基类)

这种简洁性得益于:
1. `FilterResult::Builder::merge()` 封装了合并逻辑
2. 基类处理了所有子滤镜的序列化
3. `LayerSpace::Union()` 提供了通用的边界联合计算

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/effects/imagefilters/SkDropShadowImageFilter.cpp` - 使用 Merge 实现阴影+前景合成
