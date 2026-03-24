# SkDisplacementMapImageFilter

> 源文件: `src/effects/imagefilters/SkDisplacementMapImageFilter.cpp`

## 概述

`SkDisplacementMapImageFilter` 实现了位移贴图(Displacement Map)图像滤镜效果,对应 SVG 的 `feDisplacementMap` 滤镜。它使用一张位移图的颜色通道值来偏移另一张颜色图的像素位置,产生扭曲变形效果。通过选择 R/G/B/A 通道分别控制 X 和 Y 方向的位移量,可以实现各种视觉扭曲效果,如水波、热浪等。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkDisplacementMapImageFilter (本文件)
            ├─ 输入[0]: 位移图 (kDisplacement)
            ├─ 输入[1]: 颜色图 (kColor)
            └─ SkSL 运行时效果 (kDisplacement StableKey)

工厂方法: SkImageFilters::DisplacementMap(...)
```

## 主要类与结构体

### `SkDisplacementMapImageFilter`
- 继承自 `SkImageFilter_Base`,接收两个输入滤镜
- **成员变量**:
  - `fXChannel` (`SkColorChannel`): X 方向位移使用的颜色通道
  - `fYChannel` (`SkColorChannel`): Y 方向位移使用的颜色通道
  - `fScale` (`SkScalar`): 位移缩放系数
- **采样方式**: 使用最近邻采样(`kDisplacementSampling`),注释标记为历史行为,未来可能成为工厂选项

## 公共 API 函数

### `SkImageFilters::DisplacementMap(xChannelSelector, yChannelSelector, scale, displacement, color, cropRect)`
创建位移贴图滤镜。验证:
- 通道选择器必须有效(R/G/B/A)
- scale 必须有限
- 若提供 cropRect,在输出外包裹 Crop 滤镜

## 内部实现细节

### 位移公式
对于每个输出像素 (x, y):
```
dx = (channel_value - 0.5) * scale
dy = (channel_value - 0.5) * scale
output(x, y) = color(x + dx, y + dy)
```
颜色通道值 [0, 1] 映射到位移 [-scale/2, +scale/2]。

### 滤镜核心逻辑
`onFilterImage()` 的工作流程:
1. 扩展期望输出 `maxDisplacement` 像素,获取颜色图输出
2. 若颜色图为空,直接返回(透明黑色位移后仍是透明黑色)
3. 根据颜色图实际边界进一步限制输出区域
4. 在**无色彩空间**上下文中获取位移图输出(见下方详细说明)
5. 若位移图为空,将其视为常量位移 (-scale/2, -scale/2),使用 `applyTransform` 优化
6. 否则构建 SkSL 着色器执行逐像素位移

### 色彩空间处理
位移图在无色彩空间(`nullptr`)上下文中获取。这是因为位移图是纯数学构造:
- 若用户提供 sRGB 位移图并渲染到更广色域,色彩空间变换会减少位移量
- 忽略色彩空间确保结果一致且可预测

### SkSL 位移着色器
`make_displacement_shader()` 构建运行时着色器:
- 使用 `SkKnownRuntimeEffects::StableKey::kDisplacement` 引用内置 SkSL
- uniform `scale`: 图层空间中的位移向量
- uniform `xSelect` / `ySelect`: 通道选择向量(one-hot 编码)
- child `displMap` / `colorMap`: 位移图和颜色图着色器

### 最大位移量计算
`outsetByMaxDisplacement()` 将 scale 作为**尺寸**而非**向量**处理,自动考虑坐标变换后的绝对值。最大位移为 `0.5 * |scale|`。

## 依赖关系

- `include/core/SkTypes.h` - `SkColorChannel` 枚举
- `include/effects/SkRuntimeEffect.h` - 运行时着色器
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类

## 设计模式与设计决策

### 空位移图优化
当位移图为空(透明黑色)时,所有像素的通道值为 0,产生常量位移 (-scale/2, -scale/2)。此时退化为简单平移变换,使用 `applyTransform` 避免了逐像素着色器求值。

### 通道选择向量化
通道选择使用 one-hot 向量(`channelSelector` lambda)而非条件分支,允许 GPU 使用向量点积高效提取通道值。

### 双重边界约束
输出边界同时受到期望输出和颜色图实际边界的约束:先根据颜色图边界计算可能的位移输出范围,再与期望输出取交集。

## 性能考量

- 空位移图的常量平移优化避免了不必要的 SkSL 着色器执行
- 位移图的无色彩空间处理减少了颜色变换开销
- `ShaderFlags::kNonTrivialSampling` 标记确保颜色图提供足够的边界数据
- 最大位移量限制了输入数据请求范围,避免过度请求
- 运行时着色器使用内置 StableKey,确保 SkSL 编译缓存命中

## 位移计算数学

对于每个输出像素 (x, y),位移公式为:
```
channel_value = displacement_image(x, y).[selected_channel]  // 范围 [0, 1]
offset = (channel_value - 0.5) * scale                       // 范围 [-scale/2, +scale/2]

output(x, y) = color_image(x + x_offset, y + y_offset)
```

其中 `x_offset` 使用 `fXChannel` 指定的通道值,`y_offset` 使用 `fYChannel` 指定的通道值。

当位移图为空(透明黑色)时,所有通道值为 0:
```
offset = (0 - 0.5) * scale = -scale/2
```
因此退化为常量偏移 (-scale/2, -scale/2),可用简单变换替代。

## 边界计算详解

输入边界计算是该滤镜最复杂的部分:

```
desiredOutput
  -> outsetByMaxDisplacement(desiredOutput)              // 颜色图需要额外范围
  -> getChildInputLayerBounds(kColor, expanded, ...)     // 颜色子滤镜输入

desiredOutput (原始)
  -> getChildInputLayerBounds(kDisplacement, original, ...)  // 位移子滤镜输入

最终输入 = union(颜色输入, 位移输入)
```

输出边界计算:
```
contentBounds
  -> getChildOutputLayerBounds(kColor, ...)     // 颜色子滤镜的输出
  -> outsetByMaxDisplacement(colorOutput)       // 颜色像素可能被位移到更远的位置
```

## 版本兼容性

注册了旧版名称的反序列化回调:
- `SkDisplacementMapEffect` / `SkDisplacementMapEffectImpl` -> `SkDisplacementMapImageFilter`

序列化格式:基类数据 + xChannel(int) + yChannel(int) + scale(scalar)

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkKnownRuntimeEffects.h` - 内置 SkSL 效果注册
- `src/sksl/sksl_rt_shader.sksl` - 位移着色器的 SkSL 源码
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型系统
