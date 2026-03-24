# SkColorFilterImageFilter

> 源文件: `src/effects/imagefilters/SkColorFilterImageFilter.cpp`

## 概述

`SkColorFilterImageFilter` 实现了在图像滤镜管线中应用颜色滤镜(`SkColorFilter`)的功能。它对子滤镜的输出图像逐像素应用颜色变换,支持所有 `SkColorFilter` 类型(如色彩矩阵、混合模式着色、色阶调整等)。该滤镜对应 SVG 的 `feColorMatrix` 和 `feComponentTransfer` 等颜色操作滤镜。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkColorFilterImageFilter (本文件)
            └─ 输入[0]: 待处理的子滤镜
            └─ 持有 sk_sp<SkColorFilter>

工厂方法: SkImageFilters::ColorFilter(cf, input, cropRect)
```

## 主要类与结构体

### `SkColorFilterImageFilter`
- 继承自 `SkImageFilter_Base`，接收一个子滤镜输入
- **成员变量**:
  - `fColorFilter` (`sk_sp<SkColorFilter>`): 颜色滤镜对象

## 公共 API 函数

### `SkImageFilters::ColorFilter(cf, input, cropRect) -> sk_sp<SkImageFilter>`
创建颜色滤镜图像滤镜。包含重要的优化:
- 若子输入本身也是颜色滤镜节点,将两个颜色滤镜合并为一个(`cf->makeComposed(inputCF)`)
- 合并后的输入变为原始颜色滤镜的子输入,减少了滤镜层次
- null `cf` 时仅应用 cropRect(若有)
- 若提供 cropRect,在外层包裹 Crop 滤镜

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 极其简洁:
```cpp
return this->getChildOutput(0, ctx).applyColorFilter(ctx, fColorFilter);
```
获取子滤镜输出并应用颜色滤镜。

### 颜色滤镜节点检测
`onIsColorFilterNode()` 返回 `true` 并输出 `fColorFilter` 指针。这使得:
- 父级 `ColorFilter` 工厂可以检测并合并相邻的颜色滤镜
- `FilterResult` 可以将非相邻的颜色滤镜节点组合在一起

### 透明黑色影响
`onAffectsTransparentBlack()` 委托给 `as_CFB(fColorFilter)->affectsTransparentBlack()`。例如:
- 色彩矩阵可能将透明黑色映射为非透明颜色
- 简单的色调调整不影响透明黑色

### 输出边界计算
`onGetOutputLayerBounds()`:
- 若颜色滤镜影响透明黑色:返回 `Unbounded()`（任何透明像素都可能变为可见）
- 否则:直接返回子滤镜的输出边界（颜色变换不改变像素的空间分布）

### 输入边界计算
`onGetInputLayerBounds()` 直接传递期望输出给子滤镜,因为颜色滤镜是逐像素操作,不改变空间需求。

### 矩阵能力
声明 `MatrixCapability::kComplex`,颜色滤镜与变换矩阵无关。

## 依赖关系

- `include/core/SkColorFilter.h` - 颜色滤镜接口
- `src/effects/colorfilters/SkColorFilterBase.h` - `as_CFB()` 内部转换
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkRectPriv.h` - 无限边界工具

## 设计模式与设计决策

### 颜色滤镜合并优化
工厂方法中的自动合并是一个关键优化:当连续应用多个颜色滤镜时(如先调亮度再调对比度),它们被合并为单个组合颜色滤镜,减少了图像处理的 Pass 数。

注释提到 `FilterResult` 也能组合非相邻的颜色滤镜节点,因此工厂方法的合并主要是减少构造时的冗余。

### 逐像素操作的空间无关性
颜色滤镜是纯粹的逐像素操作,不改变像素的空间位置和范围。这使得:
- 输入边界 = 期望输出（直接传递）
- 输出边界 = 子输出边界（或无界,若影响透明黑色）

### ColorFilter 节点自识别
`onIsColorFilterNode()` 接口允许系统识别颜色滤镜节点,是实现自动合并和 FilterResult 优化的基础。

## 性能考量

- 颜色滤镜合并将多次逐像素操作降为一次,显著减少内存带宽消耗
- `applyColorFilter` 可能延迟到最终绘制时与其他操作合并
- 不影响透明黑色的颜色滤镜不会扩展处理范围
- 无空间变换意味着不需要额外的图像重采样

## 颜色滤镜合并优化详解

工厂方法中的合并是一个关键的性能优化:

```
// 连续两个颜色滤镜:
ColorFilter(cf2, ColorFilter(cf1, input))

// 优化后等价于:
ColorFilter(cf2.makeComposed(cf1), input)
```

合并条件:
1. 传入的 `cf` 非 null
2. `input` 是颜色滤镜节点(`input->isColorFilterNode()` 返回 true)

合并效果:
- 减少一层滤镜节点(减少 DAG 深度)
- 运行时仅需一次颜色变换而非两次
- 减少中间图像的创建

此外,`FilterResult` 系统也能在运行时组合非相邻的颜色滤镜节点,进一步优化执行。

## 透明黑色影响分析

颜色滤镜是否影响透明黑色决定了输出边界:

| 颜色滤镜类型 | 影响透明黑色 | 输出边界 | 示例 |
|------------|------------|---------|------|
| 色彩矩阵 (带偏移) | 可能 | 无界 | 亮度偏移 |
| 色彩矩阵 (无偏移) | 否 | = 子输出 | 饱和度/色相调整 |
| Blend(color, kSrcIn) | 否 | = 子输出 | 着色 |
| Blend(color, kSrcOver) | 是 | 无界 | 叠加颜色 |
| 色阶/曲线 | 取决于 | 取决于 | Gamma 校正 |

当输出无界时,后续的 Crop 滤镜可以将其限制到合理范围。

## ColorFilter 节点识别接口

`onIsColorFilterNode()` 方法是 Skia 图像滤镜优化管线的重要接口:
- 返回 `true` 表示该节点是纯颜色变换
- 输出 `fColorFilter` 指针供调用者使用
- 工厂方法使用此接口检测并合并相邻颜色滤镜
- `FilterResult` 使用此接口延迟颜色变换到最终绘制

该接口使得颜色滤镜节点在 DAG 中可被识别和优化,即使它们不相邻。

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `include/core/SkColorFilter.h` - SkColorFilter API
- `src/effects/colorfilters/SkColorFilterBase.h` - 颜色滤镜内部接口
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
- `src/effects/imagefilters/SkDropShadowImageFilter.cpp` - 使用颜色滤镜的投影效果
