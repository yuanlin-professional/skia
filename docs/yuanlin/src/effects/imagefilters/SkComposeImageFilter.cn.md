# SkComposeImageFilter

> 源文件: `src/effects/imagefilters/SkComposeImageFilter.cpp`

## 概述

`SkComposeImageFilter` 实现了图像滤镜的组合(Compose)操作,将两个滤镜串联起来:内部滤镜(Inner)的输出作为外部滤镜(Outer)的源图像输入。这类似于函数组合 `outer(inner(source))`。该滤镜是构建复杂图像滤镜链的基础操作。

## 架构位置

```
SkImageFilter (公共接口)
  └─ SkImageFilter_Base (内部基类)
       └─ SkComposeImageFilter (本文件)
            ├─ 输入[0]: 外部滤镜 (kOuter)
            └─ 输入[1]: 内部滤镜 (kInner)

工厂方法: SkImageFilters::Compose(outer, inner)
```

组合滤镜在滤镜 DAG 中扮演特殊角色:它是唯一会**替换源图像**的滤镜。通常源图像在整个 DAG 求值过程中是固定的,但组合滤镜将内部滤镜的输出作为外部滤镜的新源图像。

## 主要类与结构体

### `SkComposeImageFilter`
- 继承自 `SkImageFilter_Base`,接收两个必须非空的输入滤镜
- **构造逻辑**: 第三个基类参数控制 `usesSource` 标志 -- 组合滤镜仅在内部滤镜使用源图像时才声明使用源图像,因为外部滤镜对源的引用会被重新绑定到内部滤镜的输出

## 公共 API 函数

### `SkImageFilters::Compose(outer, inner) -> sk_sp<SkImageFilter>`
创建组合滤镜。包含退化处理:
- `outer` 为 null -> 返回 `inner`
- `inner` 为 null -> 返回 `outer`
- 两者都非 null -> 创建组合滤镜

## 内部实现细节

### 滤镜核心逻辑
`onFilterImage()` 的工作流程:
1. 获取内部滤镜的预期输出边界
2. 计算外部滤镜覆盖期望输出所需的输入区域,以内部输出边界作为外部的内容边界
3. 使用所需输入区域作为内部滤镜的期望输出,求值内部滤镜
4. 将内部滤镜结果作为**新的源图像**传递给外部滤镜进行求值

关键注释指出:这是图像滤镜系统中唯一源图像不固定的位置。

### 边界计算

#### `onGetInputLayerBounds()`
1. 计算内部滤镜的输出边界(作为外部的内容边界)
2. 计算外部滤镜需要什么输入来覆盖期望输出(使用内部输出作为外部内容边界)
3. 将外部所需输入作为内部滤镜的期望输出,递归求解内部所需输入

#### `onGetOutputLayerBounds()`
1. 内部滤镜处理内容边界,产生中间输出边界
2. 外部滤镜处理中间输出边界,产生最终输出边界
3. 即使内部输出无界,外部滤镜(如包含 Crop)仍可能将其限制为有界

### 无额外状态
组合滤镜不包含额外的序列化状态(不需要 `flatten()`)。基类的输入滤镜序列化已经足够。

### 快速边界
`computeFastBounds()` 是简洁的函数组合: `outer.computeFastBounds(inner.computeFastBounds(src))`

## 依赖关系

- `src/core/SkImageFilterTypes.h` - FilterResult 和空间类型
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `include/effects/SkImageFilters.h` - 工厂方法

## 设计模式与设计决策

### 源图像重新绑定
这是整个图像滤镜系统中的独特设计:通过 `ctx.withNewSource(innerResult)` 将内部滤镜的输出注入为外部滤镜的源图像。虽然打破了"源图像固定"的约定,但这是实现滤镜串联的唯一正确方式。

### usesSource 传递
构造时精确传递内部滤镜的 `usesSource` 标志,避免不必要的源图像处理。外部滤镜对源的引用会被重新绑定,因此其 usesSource 不影响组合滤镜。

### 简化的 null 处理
工厂方法将 null 输入视为恒等变换,简化了 API 使用:若只有一个滤镜,直接返回该滤镜而不创建组合节点。

### 三阶段边界协调
边界计算精确地模拟了滤镜求值的数据流:内容 -> 内部 -> (中间结果作为内容) -> 外部 -> 最终输出。

## 性能考量

- 无额外状态意味着序列化/反序列化开销最小
- 边界计算中的双向分析(外部所需 -> 内部产出)可以限制中间图像的大小
- 即使内部滤镜输出无界,外部滤镜的 Crop 节点也能限制处理范围
- 源图像替换操作本身是轻量级的(仅引用计数变化)

## 使用场景

典型的组合滤镜使用场景:

1. **模糊后着色**: `Compose(ColorFilter(cf), Blur(sigma))` - 先模糊再上色
2. **变换后裁剪**: `Compose(Crop(rect), MatrixTransform(m))` - 先变换再裁剪
3. **多步效果链**: 将多个效果串联为一个滤镜对象

注意:组合的顺序很重要 -- `Compose(outer, inner)` 等同于 `outer(inner(source))`。

## 边界协调详解

三阶段边界协调是理解组合滤镜的关键:

**onGetInputLayerBounds(desiredOutput, contentBounds)**:
```
step 1: outerContentBounds = inner.getOutputBounds(contentBounds)
         // 内部滤镜的输出范围即外部滤镜的内容范围

step 2: innerDesiredOutput = outer.getInputBounds(desiredOutput, outerContentBounds)
         // 外部滤镜覆盖期望输出所需的输入(= 内部的期望输出)

step 3: return inner.getInputBounds(innerDesiredOutput, contentBounds)
         // 内部滤镜覆盖其期望输出所需的原始输入
```

**onGetOutputLayerBounds(contentBounds)**:
```
step 1: innerBounds = inner.getOutputBounds(contentBounds)
step 2: return outer.getOutputBounds(innerBounds)
         // 即使 innerBounds 无界,outer 中的 Crop 仍可能将其限制
```

## 与 Blend 滤镜的对比

| 特性 | Compose | Blend |
|------|---------|-------|
| 输入数量 | 2 (串联) | 2 (并联) |
| 数据流 | inner -> outer | 两个输入独立求值 |
| 源图像 | 被内部结果替换 | 两个输入共享同一源 |
| 状态 | 无额外状态 | 混合器、系数等 |

## usesSource 标志的精确传递

组合滤镜的 `usesSource` 标志计算:
```cpp
inputs[kInner] ? as_IFB(inputs[kInner])->usesSource() : false
```

这意味着:
- 若内部滤镜是叶子节点(如 SkImageImageFilter),`usesSource` 为 false
- 若内部滤镜引用源图像(如 SkBlendImageFilter 的子滤镜为 null),`usesSource` 为 true
- 外部滤镜的 `usesSource` 不影响组合滤镜,因为外部对源的引用会被重新绑定

这个精确计算避免了不必要的源图像准备工作。

## 相关文件

- `include/effects/SkImageFilters.h` - 工厂方法声明
- `src/core/SkImageFilter_Base.h` - 滤镜基类
- `src/core/SkImageFilterTypes.h` - FilterResult 和 Context
