# SkSVGFilter

> 源文件: [modules/svg/src/SkSVGFilter.cpp](../../../../modules/svg/src/SkSVGFilter.cpp)

## 概述

`SkSVGFilter` 实现了 SVG `<filter>` 元素的功能，是 SVG 滤镜效果系统的顶层容器。它负责管理滤镜效果区域（filter effects region）的定义，并将其子元素（各种 `<fe*>` 滤镜基元）组合成一个 Skia `SkImageFilter` DAG（有向无环图），最终应用于被滤镜引用的元素。

该类继承自 `SkSVGHiddenContainer`，意味着它本身不参与可视化渲染，仅作为滤镜定义的容器存在。

## 架构位置

```
SkSVGNode
  └── SkSVGContainer
        └── SkSVGHiddenContainer
              └── SkSVGFilter          ← 本文件
                    └── children: SkSVGFe*  （各种滤镜基元子节点）
```

`SkSVGFilter` 与 `SkSVGFilterContext` 协同工作：Filter 定义滤镜的宏观参数和区域，FilterContext 则在构建滤镜链时管理中间结果和输入/输出的解析。

## 主要类与结构体

### `SkSVGFilter`

| 属性 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `fX` | `SkSVGLength` | -10% | 滤镜效果区域 X 坐标 |
| `fY` | `SkSVGLength` | -10% | 滤镜效果区域 Y 坐标 |
| `fWidth` | `SkSVGLength` | 120% | 滤镜效果区域宽度 |
| `fHeight` | `SkSVGLength` | 120% | 滤镜效果区域高度 |
| `fFilterUnits` | `SkSVGObjectBoundingBoxUnits` | objectBoundingBox | 滤镜区域坐标系统 |
| `fPrimitiveUnits` | `SkSVGObjectBoundingBoxUnits` | userSpaceOnUse | 滤镜基元坐标系统 |

## 公共 API 函数

### `parseAndSetAttribute(const char* name, const char* value)`
解析并设置滤镜元素属性，支持 `x`、`y`、`width`、`height`、`filterUnits` 和 `primitiveUnits` 六个属性。先调用基类方法，再尝试逐个属性匹配。

### `applyProperties(SkSVGRenderContext* ctx) const`
将滤镜自身的继承属性（如 `color-interpolation-filters`）传播到渲染上下文中，供子滤镜基元使用。

### `buildFilterDAG(const SkSVGRenderContext& ctx) const`
核心方法，构建完整的滤镜效果 DAG。返回一个 `sk_sp<SkImageFilter>` 对象，可直接用于 Skia 的绘图管线。

## 内部实现细节

### 滤镜 DAG 构建流程 (`buildFilterDAG`)

1. **初始化**: 创建 `SkSVGFilterContext` 上下文，传入解析后的滤镜效果区域和基元单位
2. **属性传播**: 创建本地渲染上下文并应用滤镜自身的属性
3. **遍历子节点**: 依次处理每个 `SkSVGFe` 子节点：
   - 跳过非滤镜效果节点（通过 `SkSVGFe::IsFilterEffect` 判断）
   - 对每个 fe 节点显式传播继承属性（因为 fe 节点不走正常的 onRender 路径）
   - 解析滤镜子区域（filter subregion）
   - 解析色彩空间
   - 调用 `makeImageFilter()` 生成 `SkImageFilter`
   - 将具名结果注册到上下文中（供后续 fe 引用）
   - 将当前结果设为"前一个结果"（供未指定 `in` 的 fe 隐式引用）
4. **色彩空间转换**: 如果最终结果不在 sRGB 色彩空间中，应用 `LinearToSRGBGamma` 转换

### 滤镜链的隐式串联

SVG 规范规定，当 `<fe*>` 元素的 `in` 和 `in2` 属性未指定时，隐式使用前一个滤镜的输出。这通过 `SkSVGFilterContext::setPreviousResult()` 实现。

## 依赖关系

- **Skia Core**: `SkColorFilter`, `SkImageFilter`, `SkRect`
- **Skia Effects**: `SkImageFilters`, `SkColorFilters`（用于色彩空间转换）
- **SVG 模块**: `SkSVGFe`, `SkSVGFilterContext`, `SkSVGRenderContext`, `SkSVGAttributeParser`

## 设计模式与设计决策

1. **DAG 构建模式**: 滤镜效果链被建模为有向无环图，而非简单的线性链，允许 fe 元素通过 `in`/`result` 属性引用任意前序结果。

2. **显式属性传播**: 由于 fe 节点不参与正常渲染路径，需要在构建 DAG 时显式调用 `applyProperties` 传播继承属性。

3. **默认滤镜区域扩展**: 默认的滤镜区域为 -10% 到 120%，即比目标对象边界框各向外扩展 10%，这是 SVG 规范定义的默认值，确保模糊等效果不被裁切。

## 性能考量

- 滤镜 DAG 的构建发生在渲染时而非解析时，避免了不必要的预计算
- 每个 fe 节点的属性传播需要创建 `SkSVGRenderContext` 副本，复杂滤镜链会增加开销
- 最终的色彩空间转换仅在需要时执行（非 sRGB 时才添加额外的 ColorFilter）

## 相关文件

- `modules/svg/include/SkSVGFilter.h` - 头文件，定义 SkSVGFilter 类及其属性
- `modules/svg/include/SkSVGFe.h` - 滤镜基元基类
- `modules/svg/src/SkSVGFilterContext.cpp` - 滤镜上下文实现
- `modules/svg/include/SkSVGHiddenContainer.h` - 隐藏容器基类
- `modules/svg/include/SkSVGRenderContext.h` - 渲染上下文
